import csv
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

from .filename_metadata import parse_filename


class _VuSituHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta_tags = {}
        self.metadata = {}
        self.headers = []
        self.rows = []
        self._row_attrs = None
        self._cells = None
        self._cell_attrs = None
        self._cell_text = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name"):
            self.meta_tags[attrs["name"]] = attrs.get("content", "")
        elif tag == "tr":
            self._row_attrs = attrs
            self._cells = []
        elif tag == "td" and self._cells is not None:
            self._cell_attrs = attrs
            self._cell_text = []

    def handle_data(self, data):
        if self._cell_text is not None:
            self._cell_text.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self._cell_text is not None:
            text = "".join(self._cell_text).strip()
            self._cells.append((self._cell_attrs or {}, text))
            self._cell_attrs = None
            self._cell_text = None
        elif tag == "tr" and self._cells is not None:
            self._finish_row()
            self._row_attrs = None
            self._cells = None

    def _finish_row(self):
        header_cells = [
            text for attrs, text in self._cells if "isi-data-column-header" in attrs
        ]
        if header_cells:
            self.headers = header_cells
            return

        if self._row_attrs is not None and "isi-data-row" in self._row_attrs:
            self.rows.append([text for _, text in self._cells])
            return

        for index, (attrs, _) in enumerate(self._cells):
            group = attrs.get("isi-group-member")
            prop = attrs.get("isi-property")
            if not group or not prop:
                continue
            values = [text for _, text in self._cells[index + 1 :] if text]
            if values:
                self.metadata.setdefault(group, {})[prop] = values[-1]


def _source_type(path, meta_tags, filename_meta):
    report_type = meta_tags.get("isi-report-type", "").lower()
    if report_type == "livereadings":
        return "live_reading"
    if report_type == "log":
        return "log"
    if filename_meta.get("source_type"):
        return filename_meta["source_type"]

    parent = path.parent.name.lower()
    if parent == "livereadings":
        return "live_reading"
    if parent == "logs":
        return "log"
    return "unknown"


def _normalize(df):
    rename = {}
    patterns = {
        "Actual Conductivity": "actual_conductivity_us_cm",
        "Specific Conductivity": "specific_conductivity_us_cm",
        "Temperature": "temperature_c",
    }

    if "Date Time" in df.columns:
        rename["Date Time"] = "timestamp"
    elif "Date and Time" in df.columns:
        rename["Date and Time"] = "timestamp"

    for prefix, normalized in patterns.items():
        matches = [column for column in df.columns if str(column).startswith(prefix)]
        if len(matches) == 1:
            rename[matches[0]] = normalized

    df = df.rename(columns=rename)

    if "timestamp" in df:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")

    for column in df.columns:
        if column == "timestamp":
            continue
        series = df[column]
        nonempty = series.notna() & series.astype(str).str.strip().ne("")
        if not nonempty.any():
            continue
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric[nonempty].notna().all():
            df[column] = numeric

    return df, rename


def _read_html(path):
    parser = _VuSituHTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    if not parser.headers:
        raise ValueError(f"No Aqua TROLL measurement table found in {path}")
    if any(len(row) != len(parser.headers) for row in parser.rows):
        raise ValueError(f"Aqua TROLL table width does not match headers in {path}")

    df = pd.DataFrame(parser.rows, columns=parser.headers)
    return df, parser.metadata, parser.meta_tags


def _read_csv(path):
    header_index = None
    section = None
    metadata = {}

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        for index, row in enumerate(reader):
            values = [value.strip() for value in row]
            first = values[0] if values else ""

            is_measurement_header = (
                first in {"Date Time", "Date and Time", "Time"}
                and any(
                    value.startswith(("Actual Conductivity", "Specific Conductivity"))
                    for value in values[1:]
                )
            )
            if is_measurement_header:
                header_index = index
                break

            if not any(values):
                continue

            if len(values) == 1:
                value = first
                if "=" in value:
                    key, item = (part.strip() for part in value.split("=", 1))
                    metadata.setdefault(section or "Preamble", {})[key] = item
                elif ":" in value and value.split(":", 1)[1].strip():
                    key, item = (part.strip() for part in value.split(":", 1))
                    metadata.setdefault(section or "Preamble", {})[key] = item
                else:
                    section = value.rstrip(":")
            elif first and values[1]:
                metadata.setdefault(section or "Preamble", {})[first.rstrip(":")] = values[1]

    if header_index is None:
        raise ValueError(f"No Aqua TROLL measurement header found in {path}")

    df = pd.read_csv(path, skiprows=header_index)
    return df, metadata, {}


def read_aquatroll(path):
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".html":
        df, embedded, meta_tags = _read_html(path)
    elif suffix == ".csv":
        df, embedded, meta_tags = _read_csv(path)
    else:
        raise ValueError(f"Unsupported Aqua TROLL file type: {suffix}")

    filename_meta = parse_filename(path)
    df, column_map = _normalize(df)

    metadata = {
        "source_file": str(path),
        "source_format": suffix.lstrip("."),
        "source_type": _source_type(path, meta_tags, filename_meta),
        "instrument_family": "aquatroll",
        "filename_metadata": filename_meta,
        "embedded_metadata": embedded,
        "column_map": column_map,
    }
    if meta_tags:
        metadata["report_metadata"] = meta_tags

    return df, metadata
