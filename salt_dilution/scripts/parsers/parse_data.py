import argparse
import csv
import json
from pathlib import Path

from .aquatroll import read_aquatroll
from .calibration_table import detect_calibration_type, read_calibration_table
from .general_logger import read_general_logger


def _csv_header(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.reader(stream):
            values = [value.strip() for value in row]
            if len(values) > 1:
                return values
    return []


def read_data(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    if suffix == ".html":
        return read_aquatroll(path)
    if suffix in {".xls", ".xlsx"}:
        return read_general_logger(path)
    if suffix == ".csv":
        header = _csv_header(path)
        try:
            detect_calibration_type(header)
        except ValueError:
            if header and header[0] in {"Date Time", "Time"}:
                return read_aquatroll(path)
            raise ValueError(f"Unsupported CSV schema: {path}")
        return read_calibration_table(path)

    raise ValueError(f"Unsupported data file: {path}")


def _write_processed(df, metadata, source, output_dir):
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
