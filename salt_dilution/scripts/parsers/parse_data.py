"""Read salt-dilution files and optionally save them as CSVs with metadata.

Each file goes to the reader for its format. Calibration and discharge
calculations are handled separately in scripts/processing/.
"""

import argparse
import csv
from datetime import datetime, timezone
import fnmatch
import hashlib
import os
import shutil
import sys
import tempfile
import json
from pathlib import Path

from .aquatroll import SupportingReportError, read_aquatroll
from .calibration_table import detect_calibration_type, read_calibration_table
from .general_logger import read_general_logger


def _csv_header(path):
    # Use the same encodings as the Aqua TROLL reader so older WinSitu files
    # can get through this first check too.
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
    """Return a pandas table and its source metadata without writing files."""

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return read_aquatroll(path)
    if suffix in {".xls", ".xlsx"}:
        return read_general_logger(path)
    if suffix == ".csv":
        # Check for a calibration table first. Otherwise, let the Aqua TROLL
        # reader look past any metadata rows for the measurement header.
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


SUPPORTED_SUFFIXES = {".html", ".htm", ".csv", ".xls", ".xlsx"}
MANIFEST_NAME = "ingestion_manifest.json"


def _sha256(path):
    with Path(path).open("rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _targets(source, output_dir):
    return (output_dir / f"{source.stem}.csv",
            output_dir / f"{source.stem}_metadata.json")


def _write_processed(df, metadata, source, output_dir, overwrite=False):
    """Stage a CSV/metadata pair and refuse existing targets by default.

    Source folders are never output destinations. Explicit overwrite replaces
    each file after staging; the pair is not a filesystem-wide transaction.
    """
    source, output_dir = Path(source), Path(output_dir)
    if output_dir.resolve() == source.parent.resolve():
        raise ValueError("Output must be outside the source directory")
    targets = _targets(source, output_dir)
    for target in targets:
        if target.is_symlink() or target.is_dir() or (target.exists() and not overwrite):
            raise FileExistsError(f"Refusing existing output: {target}")
    output_dir.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        with tempfile.TemporaryDirectory(prefix=".ingest-", dir=output_dir) as temp:
            staged = [Path(temp) / target.name for target in targets]
            df.to_csv(staged[0], index=False, lineterminator="\n")
            staged[1].write_text(json.dumps(metadata, indent=2, default=str) + "\n", encoding="utf-8")
            for prepared, target in zip(staged, targets):
                if overwrite:
                    os.replace(prepared, target)
                else:
                    # Exclusive creation prevents a concurrent run from being
                    # overwritten between the preflight check and publication.
                    with target.open("xb") as dest:
                        created.append(target)
                        with prepared.open("rb") as src:
                            shutil.copyfileobj(src, dest)
    except Exception:
        for target in created:
            target.unlink(missing_ok=True)
        raise
    return targets


def _discover(source, recursive, include):
    if source.is_symlink():
        raise ValueError("Symbolic-link inputs are not followed")
    if source.is_file():
        paths = [source]
    elif source.is_dir():
        paths = []
        for folder, dirs, filenames in os.walk(source, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not (Path(folder) / d).is_symlink()) if recursive else []
            paths.extend(Path(folder) / name for name in sorted(filenames))
    else:
        raise FileNotFoundError(source)
    root = source if source.is_dir() else source.parent
    return [path for path in sorted(paths) if not include or any(
        fnmatch.fnmatchcase(path.relative_to(root).as_posix(), pattern) for pattern in include
    )]


def _describe(df, metadata):
    warnings = list(metadata.get("warnings", []))
    info = {"row_count": len(df), "column_count": len(df.columns),
            "source_type": metadata.get("source_type"), "warnings": warnings}
    for column, suffix in (("timestamp", ""), ("timestamp_utc", "_utc")):
        if column in df and not df.empty:
            values = df[column]
            info[f"time_start{suffix}"] = values.min().isoformat()
            info[f"time_end{suffix}"] = values.max().isoformat()
            if column == "timestamp":
                if values.duplicated().any():
                    warnings.append("Duplicate timestamps retained; do not integrate without review")
                if not values.is_monotonic_increasing:
                    warnings.append("Non-monotonic timestamps retained; do not integrate without review")
                if values.isna().any():
                    warnings.append("Missing timestamps retained; review before analysis")
                if "timestamp_utc" not in df and not any("offset" in w.lower() for w in warnings):
                    warnings.append("No explicit numeric time offset; UTC not inferred")
    return info


def process_path(path, output_dir=None, *, recursive=False, overwrite=False, include=None):
    """Extract one file or a directory, returning a per-file audit manifest.

    No output directory means read-only inspection. Directory layout is kept
    relative to the input root. Supporting reports are skips; parse errors and
    unsafe output plans are failures. No trial or calibration joins are made.
    """
    source = Path(path)
    root = source if source.is_dir() else source.parent
    output = Path(output_dir) if output_dir is not None else None
    files = _discover(source, recursive, include)
    if not files:
        raise ValueError("No input files matched the requested selection")
    if output is not None:
        if (source.is_dir() and output.resolve().is_relative_to(root.resolve())) or output.resolve() == root.resolve():
            raise ValueError("Output must be outside the source directory")
        manifest_path = output / MANIFEST_NAME
        if manifest_path.is_symlink() or manifest_path.is_dir() or (manifest_path.exists() and not overwrite):
            raise FileExistsError(f"Refusing existing manifest: {manifest_path}; choose a fresh output directory")

    # Case-folding also catches output collisions on Windows/macOS. Plan all
    # candidates before writing; --overwrite never resolves two source files
    # mapping to one output name.
    owners = {}
    for file in files:
        if file.suffix.lower() in SUPPORTED_SUFFIXES and not file.is_symlink():
            relative = file.relative_to(root)
            for target in _targets(file, relative.parent):
                owners.setdefault(target.as_posix().casefold(), []).append(file)
    collisions = {file for group in owners.values() if len(group) > 1 for file in group}
    report = {
        "schema_version": 1, "started_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": root.as_posix(), "output_root": output.as_posix() if output else None,
        "recursive": recursive, "include": list(include or []), "overwrite": overwrite,
        "parser_sha256": {p.name: _sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
        "files": [],
    }
    for file in files:
        relative = file.relative_to(root)
        entry = {"source": file.as_posix(), "source_relative_path": relative.as_posix()}
        report["files"].append(entry)
        if file.is_symlink() or file.suffix.lower() not in SUPPORTED_SUFFIXES:
            entry.update(status="skipped", reason="symbolic_link" if file.is_symlink() else "non_input_extension")
            continue
        if file in collisions:
            entry.update(status="failed", reason="output_name_collision")
            continue
        try:
            digest = _sha256(file)
            entry["source_sha256"] = digest
            df, metadata = read_data(file)
            if df.empty:
                raise ValueError("Empty data table")
            if _sha256(file) != digest:
                raise ValueError("Source changed during extraction; rerun from a stable source")
            metadata["source_sha256"] = digest
            entry.update(_describe(df, metadata))
            metadata["warnings"] = entry["warnings"]
            if output is None:
                entry["status"] = "parsed"
            else:
                destination = output / relative.parent
                if not destination.resolve().is_relative_to(output.resolve()):
                    raise ValueError("Output subdirectory escapes the output root")
                data_path, meta_path = _write_processed(df, metadata, file, destination, overwrite)
                entry.update(status="written", processed_path=data_path.as_posix(),
                             metadata_path=meta_path.as_posix(),
                             processed_sha256=_sha256(data_path), metadata_sha256=_sha256(meta_path))
        except SupportingReportError as exc:
            entry.update(status="skipped", reason="supporting_report", source_type=exc.report_type)
        except Exception as exc:
            # Keep unrelated files processing, but preserve every error and make
            # the CLI exit nonzero. KeyboardInterrupt/SystemExit are not hidden.
            message = f"{exc}: {exc.__cause__}" if exc.__cause__ is not None else str(exc)
            entry.update(status="failed", reason=type(exc).__name__, error=message)
    report["completed_utc"] = datetime.now(timezone.utc).isoformat()
    report["counts"] = {status: sum(e["status"] == status for e in report["files"])
                        for status in ("parsed", "written", "skipped", "failed")}
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
        # A run manifest is useful even when some inputs failed or were skipped.
        with manifest_path.open("w" if overwrite else "x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, indent=2, default=str)
            stream.write("\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect or normalize salt-data files, with a per-file manifest.")
    parser.add_argument("path", help="Source HTML, CSV, XLS, XLSX file, or directory")
    parser.add_argument("-o", "--output", help="Output directory outside the source tree; omit for read-only inspection")
    parser.add_argument("--recursive", action="store_true", help="Include subdirectories of the input directory")
    parser.add_argument("--include", action="append", metavar="GLOB", help="Only matching input-relative paths (repeatable; use forward slashes)")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly replace existing outputs and manifest, never sources or collisions")
    args = parser.parse_args(argv)
    try:
        report = process_path(args.path, args.output, recursive=args.recursive,
                              overwrite=args.overwrite, include=args.include)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if not args.output:
        print(json.dumps(report, indent=2, default=str))
    else:
        for entry in report["files"]:
            detail = entry.get("error", entry.get("reason", f"rows={entry.get('row_count', 0)}"))
            print(f"{entry['status'].upper()}: {entry['source_relative_path']} ({detail})")
        print(f"manifest={Path(args.output) / MANIFEST_NAME}")
    print(" ".join(f"{key}={value}" for key, value in report["counts"].items()))
    return 1 if report["counts"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
