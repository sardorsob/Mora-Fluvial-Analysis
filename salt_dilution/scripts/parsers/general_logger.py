from datetime import datetime, time
from pathlib import Path

import pandas as pd

from .filename_metadata import parse_filename


def _find_header_row(path):
    preview = pd.read_excel(path, header=None, nrows=25)
    for index, row in preview.iterrows():
        labels = {
            str(value).strip().lower()
            for value in row
            if pd.notna(value) and str(value).strip()
        }
        if {"date", "time"} <= labels or "date time" in labels:
            return index
    raise ValueError(f"No General logger measurement header found in {path}")


def _time_text(value):
    if isinstance(value, (datetime, time)):
        return value.strftime("%H:%M:%S")
    if isinstance(value, (int, float)) and 0 <= value < 1:
        seconds = round(value * 24 * 60 * 60)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return str(value).strip()


def read_general_logger(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in {".xls", ".xlsx"}:
        raise ValueError(f"Unsupported General logger file type: {suffix}")

    try:
        header_row = _find_header_row(path)
        df = pd.read_excel(path, header=header_row)
    except ImportError as exc:
        if suffix == ".xls":
            raise ImportError("Legacy .xls files require the xlrd package") from exc
        raise

    if "Date Time" in df.columns:
        df["timestamp"] = pd.to_datetime(df["Date Time"], errors="raise")
    elif {"Date", "Time"} <= set(df.columns):
        dates = pd.to_datetime(df["Date"], errors="raise").dt.strftime("%Y-%m-%d")
        times = df["Time"].map(_time_text)
        df["timestamp"] = pd.to_datetime(dates + " " + times, errors="raise")

    filename_meta = parse_filename(path)
    metadata = {
        "source_file": str(path),
        "source_format": suffix.lstrip("."),
        "source_type": "general",
        "instrument_family": "general_logger",
        "filename_metadata": filename_meta,
        "embedded_metadata": {},
    }
    return df, metadata
