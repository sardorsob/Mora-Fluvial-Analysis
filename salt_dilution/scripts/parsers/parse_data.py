"""Single public entry point for salt-dilution source ingestion.

Readers stay format-specific; this module only decides which reader owns a file
and optionally writes normalized outputs. Scientific calculations never happen
during dispatch.
"""

import argparse
import csv
import json
from pathlib import Path

from .aquatroll import read_aquatroll
from .calibration_table import detect_calibration_type, read_calibration_table
from .general_logger import read_general_logger


def _csv_header(path):
    # Dispatch must tolerate the same encodings as the reader or a valid legacy
    # WinSitu file could fail before it reaches `read_aquatroll()`.
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with path.open("r", encoding=encoding, newline="") as stream:
                for row in csv.reader(stream):
                    values = [value.strip() for value in row]
                    if len(values) > 1:
                        return values
            return []
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode CSV: {path}")


def read_data(path):
    """Read one supported source file and return `(DataFrame, metadata)`."""

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    if suffix == ".html":
        return read_aquatroll(path)
    if suffix in {".xls", ".xlsx"}:
        return read_general_logger(path)
    if suffix == ".csv":
        # Calibration CSVs have compact, recognizable schemas. Other CSVs are
        # given to the Aqua TROLL reader, which performs the stricter search for
        # a real conductivity measurement table.
        header = _csv_header(path)
        try:
            detect_calibration_type(header)
        except ValueError:
            try:
                return read_aquatroll(path)
            except ValueError as exc:
                raise ValueError(f"Unsupported CSV schema: {path}") from exc
        return read_calibration_table(path)

    raise ValueError(f"Unsupported data file: {path}")


def _write_processed(df, metadata, source, output_dir):
    """Write reproducible normalized data separately from the untouched source."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data_path = output_dir / f"{source.stem}.csv"
    metadata_path = output_dir / f"{source.stem}_metadata.json"

    df.to_csv(data_path, index=False)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return data_path, metadata_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read one salt-dilution source file into the normalized parser schema."
    )
    parser.add_argument("path", help="Source HTML, CSV, XLS, or XLSX file")
    parser.add_argument(
        "-o",
        "--output",
        help="Optional processed-data directory for normalized CSV and metadata JSON",
    )
    args = parser.parse_args(argv)

    source = Path(args.path)
    df, metadata = read_data(source)

    print(json.dumps(metadata, indent=2, default=str))
    print(f"rows={len(df)} columns={len(df.columns)}")

    if args.output:
        data_path, metadata_path = _write_processed(
            df, metadata, source, args.output
        )
        print(f"data={data_path}")
        print(f"metadata={metadata_path}")


if __name__ == "__main__":
    main()
