"""Read Aqua TROLL, VuSitu and WinSitu exports into a table and source metadata.

Recognized column labels get consistent names. Other columns keep their source
names so they remain available for later checks and analysis.
"""

import csv
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

from .filename_metadata import parse_filename


class _VuSituHTMLParser(HTMLParser):
    """Read the tables and metadata marked by VuSitu's HTML attributes.

    The ``isi-*`` attributes distinguish measurements from report details that
    appear in the same table. This reader depends on those VuSitu markers.
    """

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
        # One table can contain headers, readings and instrument details.
        # Check the VuSitu markers before deciding where this row belongs.
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
    # Rename a channel only when its label matches once. If two temperature
    # sensors are present, keep both names so we don't choose one by accident.
    # These names assume the source uses µS/cm and °C; no units are converted.
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
        # This relies on the source containing a full date: pandas can assign
        # today's date to clock-only values. Time-zone text stays in metadata.
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")

    for column in df.columns:
        if column == "timestamp":
            continue
        series = df[column]
        nonempty = series.notna() & series.astype(str).str.strip().ne("")
        if not nonempty.any():
            continue
        numeric = pd.to_numeric(series, errors="coerce")
        # Keep mixed text/numeric columns intact instead of losing text as NaN.
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


def _scan_csv(path, encoding):
    header_index = None
    section = None
    metadata = {}

    with path.open("r", encoding=encoding, newline="") as stream:
        reader = csv.reader(stream)
        for index, row in enumerate(reader):
            values = [value.strip() for value in row]
            first = values[0] if values else ""

            # WinSitu notes can also start with "Date and Time". Look for a
            # conductivity column too, so we select the measurement table.
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

    return header_index, metadata


def _read_csv(path):
    # Try UTF-8 first. Older WinSitu exports use Windows-1252 for characters
    # such as the µ in conductivity units.
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            header_index, metadata = _scan_csv(path, encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Could not decode Aqua TROLL CSV: {path}")

    if header_index is None:
        raise ValueError(f"No Aqua TROLL measurement header found in {path}")

    df = pd.read_csv(path, skiprows=header_index, encoding=encoding)
    return df, metadata, {"text_encoding": encoding}


def read_aquatroll(path):
    """Return the measurement table, source details and column-name mapping."""

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
