"""Read Aqua TROLL, VuSitu and WinSitu exports into a table and source metadata.

Recognized column labels get consistent names. Other columns keep their source
names so they remain available for later checks and analysis.
"""

import csv
from datetime import timedelta, timezone
import re
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

from .filename_metadata import parse_filename


class SupportingReportError(ValueError):
    """A recognized report with no measurement time series to normalize."""

    def __init__(self, report_type):
        self.report_type = report_type
        super().__init__(f"Supporting {report_type}; not a measurement table")


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
        self.channel_attributes = []
        self.headings = []
        self._heading_text = None
        self._value_depth = 0
        self._value_text = None
        self._cell_value = None
        self._row_attrs = None
        self._cells = None
        self._cell_attrs = None
        self._cell_text = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"h1", "h2"}:
            self._heading_text = []
        if self._cell_text is not None:
            if "isi-value" in attrs:
                self._value_depth = 1
                self._value_text = []
            elif self._value_depth and tag not in {"br", "img", "input", "hr", "meta", "link"}:
                self._value_depth += 1
        if tag == "meta" and attrs.get("name"):
            self.meta_tags[attrs["name"]] = attrs.get("content", "")
        elif tag == "tr":
            self._row_attrs = attrs
            self._cells = []
        elif tag == "td" and self._cells is not None:
            self._cell_attrs = attrs
            self._cell_text = []
            self._cell_value = None

    def handle_data(self, data):
        if self._heading_text is not None:
            self._heading_text.append(data)
        if self._value_depth:
            self._value_text.append(data)
        if self._cell_text is not None:
            self._cell_text.append(data)

    def handle_endtag(self, tag):
        if tag in {"h1", "h2"} and self._heading_text is not None:
            self.headings.append("".join(self._heading_text).strip())
            self._heading_text = None
        if self._value_depth:
            self._value_depth -= 1
            if self._value_depth == 0:
                self._cell_value = "".join(self._value_text).strip()
        if tag == "td" and self._cell_text is not None:
            text = "".join(self._cell_text).strip()
            attrs = dict(self._cell_attrs or {})
            if self._cell_value is not None:
                attrs["_inline_value"] = self._cell_value
            self._cells.append((attrs, text))
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
            self.channel_attributes = [
                dict(attrs) for attrs, _ in self._cells if "isi-data-column-header" in attrs
            ]
            return

        if self._row_attrs is not None and "isi-data-row" in self._row_attrs:
            self.rows.append([text for _, text in self._cells])
            return

        for index, (attrs, text) in enumerate(self._cells):
            group = attrs.get("isi-group-member")
            prop = attrs.get("isi-property")
            if not group or not prop:
                continue
            # New VuSitu reports put label and value in spans in ONE cell.
            # Keep the older separate-label/value-cell format as a fallback.
            value = attrs.get("_inline_value")
            if value is None and "=" in text:
                value = text.split("=", 1)[1].strip()
            if value is None:
                values = [text for _, text in self._cells[index + 1 :] if text]
                value = values[-1] if values else None
            if value is not None:
                self.metadata.setdefault(group, {})[prop] = value


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


def _column_unit(label):
    match = re.search(r"\(([^()]*)\)", str(label))
    return match.group(1).strip() if match else None


def _normalize(df):
    rename = {}
    # Rename a channel only when its label matches once. If two temperature
    # sensors are present, keep both names so we don't choose one by accident.
    # Unit-labelled names are used only for matching units; no conversion.
    patterns = {
        "Actual Conductivity": "actual_conductivity_us_cm",
        "Specific Conductivity": "specific_conductivity_us_cm",
        "Temperature": "temperature_c",
    }

    if "Date Time" in df.columns:
        rename["Date Time"] = "timestamp"
    elif "Date and Time" in df.columns:
        rename["Date and Time"] = "timestamp"
    elif "Time" in df.columns:
        rename["Time"] = "timestamp"

    for prefix, normalized in patterns.items():
        matches = [column for column in df.columns if str(column).startswith(prefix)]
        if len(matches) == 1:
            unit = (_column_unit(matches[0]) or "").lower()
            accepted = {"°c", "c", "deg c"} if prefix == "Temperature" else {"µs/cm", "μs/cm", "us/cm"}
            if unit in accepted:
                rename[matches[0]] = normalized

    df = df.rename(columns=rename)

    if "timestamp" in df:
        # Never allow pandas to attach the execution date to clock-only data.
        text = df["timestamp"].astype(str)
        full_date = text.str.contains(
            r"(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4})", regex=True
        )
        if not full_date.all():
            raise ValueError("Clock-only or missing full-date timestamps require explicit date reconciliation")
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
        if df["timestamp"].isna().any():
            raise ValueError("Missing measurement timestamps")

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
    parser.feed(path.read_text(encoding="utf-8-sig"))
    parser.close()
    if not parser.headers:
        report_type = parser.meta_tags.get("isi-report-type", "").lower()
        if report_type in {"deploymentreport", "calibrationreport"}:
            raise SupportingReportError(report_type)
        if report_type not in {"livereadings", "log"} and any(
            title.lower() == "calibration report" for title in parser.headings
        ):
            raise SupportingReportError("instrument_calibration_report")
        raise ValueError(f"No Aqua TROLL measurement table found in {path}")
    if not parser.rows:
        raise ValueError(f"Empty Aqua TROLL measurement table: {path}")
    if len(set(parser.headers)) != len(parser.headers):
        raise ValueError(f"Duplicate Aqua TROLL column labels: {path}")
    if any(len(row) != len(parser.headers) for row in parser.rows):
        raise ValueError(f"Aqua TROLL table width does not match headers in {path}")

    df = pd.DataFrame(parser.rows, columns=parser.headers)
    return df, parser.metadata, parser.meta_tags, parser.channel_attributes


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
    return df, metadata, {"text_encoding": encoding}, []


def read_aquatroll(path):
    """Return the measurement table, source details and column-name mapping."""

    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in {".html", ".htm"}:
        df, embedded, meta_tags, channel_attrs = _read_html(path)
    elif suffix == ".csv":
        df, embedded, meta_tags, channel_attrs = _read_csv(path)
    else:
        raise ValueError(f"Unsupported Aqua TROLL file type: {suffix}")

    if df.empty:
        raise ValueError(f"Empty Aqua TROLL measurement table: {path}")
    source_columns = list(df.columns)
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

    metadata["channels"] = []
    metadata["warnings"] = []
    for index, label in enumerate(source_columns):
        attrs = channel_attrs[index] if channel_attrs else {}
        channel = {"source_column": label, "column": column_map.get(label, label),
                   "unit": _column_unit(label)}
        for key in ("device-serial-number", "sensor-serial-number", "sensor-type", "parameter-type", "unit-type"):
            if "isi-" + key in attrs:
                channel[key.replace("-", "_")] = attrs["isi-" + key]
        metadata["channels"].append(channel)
        if str(label).startswith(("Actual Conductivity", "Specific Conductivity", "Temperature")) and label not in column_map:
            metadata["warnings"].append(f"Kept source channel label (multiple sensors or unmatched units): {label}")
    _add_utc(df, metadata)
    return df, metadata


def _add_utc(df, metadata):
    """Add UTC only from source timestamps or an explicit report numeric offset.

    The original timestamp column and report text are retained. No filename,
    report creation date, local-machine zone, PST/PDT label or trial is inferred.
    """
    if "timestamp" not in df:
        metadata["warnings"].append("No recognized measurement timestamp column")
        return
    offsets = {str(value).strip()
               for fields in metadata["embedded_metadata"].values()
               for key, value in fields.items()
               if re.sub(r"[^a-z]", "", key.lower()) == "timeoffset"}
    seconds = None
    if len(offsets) == 1:
        raw_offset = next(iter(offsets))
        match = re.fullmatch(r"([+-])(\d{2}):(\d{2})(?::(\d{2}))?", raw_offset)
        if match:
            sign, hh, mm, ss = match.groups()
            if int(hh) < 24 and int(mm) < 60 and int(ss or 0) < 60:
                seconds = (int(hh) * 3600 + int(mm) * 60 + int(ss or 0)) * (-1 if sign == "-" else 1)
        metadata["source_time_offset"] = raw_offset
    if df["timestamp"].dt.tz is not None:
        if seconds is not None and any(t.utcoffset().total_seconds() != seconds for t in df["timestamp"]):
            raise ValueError("Timestamp offset conflicts with report time offset")
        df["timestamp_utc"] = df["timestamp"].dt.tz_convert("UTC")
        metadata["timestamp_basis"] = "offset_in_source_timestamps"
    elif seconds is not None:
        df["timestamp_utc"] = df["timestamp"].dt.tz_localize(timezone(timedelta(seconds=seconds))).dt.tz_convert("UTC")
        metadata["timestamp_basis"] = "explicit_report_numeric_offset"
        metadata["utc_offset_seconds"] = seconds
    else:
        metadata["timestamp_basis"] = "unresolved_source_clock"
        metadata["warnings"].append("Missing, invalid or conflicting numeric time offset; UTC not inferred")
