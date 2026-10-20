# Reusable salt-data extraction

Run commands from the repository root in your project Python environment.
For the parser/test suite alone, install `pandas`, `openpyxl` (XLSX) and `xlrd`
(legacy XLS). No new calibration or discharge calculation is performed here.

## Inspect first, then write

The existing single-file interface remains available. Without `--output` it is
read-only; it now prints an inspection manifest and summary.

```sh
python -m salt_dilution.scripts.parsers.parse_data path/to/source.html
python -m salt_dilution.scripts.parsers.parse_data path/to/source.html --output salt_dilution/data/processed/single_run
```

A directory is scanned at its top level unless `--recursive` is supplied. Output
paths preserve subdirectories relative to the input directory. Thus using
`data/raw` as input preserves date folders; using one date folder as input puts
its files directly in the output directory you specify.

```sh
python -m salt_dilution.scripts.parsers.parse_data salt_dilution/data/raw --recursive
python -m salt_dilution.scripts.parsers.parse_data salt_dilution/data/raw --recursive --output salt_dilution/data/processed/new_run
```

To process only the four recently added field dates (ten live-reading exports
and four supporting reports), use these input-relative filters. The quotes and
forward slashes work in PowerShell, Command Prompt, Bash and Zsh. This is an
example selection, not a hard-coded date list inside the parser.

```sh
python -m salt_dilution.scripts.parsers.parse_data salt_dilution/data/raw --recursive --include "20260918/*.html" --include "2026100[245]/*.html" --output salt_dilution/data/processed/recent_vusitu
```

`--include` can be repeated; matching any filter includes the file. Filters use
case-sensitive glob matching on input-relative paths. HTML/HTM, CSV, XLS and XLSX
are reader candidates. Unsupported extensions and symbolic-link files are
reported as skips; symbolic-link directories are not traversed. Filenames are
not used to decide scientific trial identity. Unknown names are acceptable when
the file contents have a supported schema.

## Measurement files versus supporting reports

Both old multi-cell VuSitu metadata and new inline `isi-label` / `isi-value`
metadata are supported. Measurement rows are identified by vendor attributes,
not by every HTML table or every number appearing in the document.

Deployment reports identified by their report-type tag, and instrument
calibration reports identified by their tag or `Calibration Report` heading,
are recorded as `skipped` with `reason=supporting_report`. They are retained
unchanged in raw storage; their deployment settings are not merged into a
recording by date. An instrument cell constant is not a fitted salt-titration
coefficient. A malformed measurement file is `failed`, not silently reclassified
as a supporting document. Supported electronic calibration CSV tables still
use the existing calibration reader.

## Metadata, units and clocks

Every written file has its original stem plus `.csv` and `_metadata.json`.
Metadata preserves report/device properties and a `channels` list mapping
source labels to output labels, unit text, and available device/sensor/parameter/
unit identifiers. Extra source columns remain available. The parser does not
collapse two temperature channels or guess which one is water temperature.

Actual/specific conductivity is given a `_us_cm` name only for matching µS/cm
units; a single temperature gets a `_c` name only for matching Celsius units.
Other units or ambiguous channels keep their original labels and a warning;
no unit conversion is silently performed.

`timestamp` retains the source clock. An additional `timestamp_utc` is created
only from offset-aware source timestamps or an explicit valid numeric report
`TimeOffset` (for example `-07:00:00`). The original offset text is retained.
An offset label such as PST/PDT, a filename, a report-export date, or the local
computer's timezone is not a substitute for an explicit numeric offset.
Without one, UTC stays absent and a warning is recorded. Conflicting offset-aware
timestamps and a numeric report offset fail extraction rather than guessing.
Clock-only or missing-date Aqua TROLL readings fail instead of acquiring the
computer's current date. Date reconstruction for quarantined historical sources
is still separate work. Duplicate/non-monotonic times are preserved and flagged,
not sorted or filled automatically.

## Safe output and audit manifest

Choose a fresh output directory for each run. Existing CSVs, sidecars and the
`ingestion_manifest.json` are refused by default. `--overwrite` is an explicit
opt-in to replacing existing outputs and the manifest; it never permits source
replacement, output-name collisions, or an output directory inside a directory
being scanned. A CSV and HTML with the same relative stem are a collision;
neither is arbitrarily selected. Each CSV/sidecar pair is staged before writing,
but publication of a pair is not a filesystem-wide transaction.

A single-file extraction may write to a separate child output folder next to
its source, but cannot write directly into the source's own directory. In a
batch, output subdirectory symlinks may not escape the specified output root.

The manifest contains source/output roots, relative source paths, source and
output SHA-256 hashes, parser-file hashes, row/column counts, local/UTC time
ranges when available, warnings, and a status for every selected file:

- `parsed`: read-only extraction succeeded;
- `written`: CSV and metadata were saved;
- `skipped`: supporting report, non-input extension, or symbolic-link file;
- `failed`: unsupported schema, malformed data, unsafe output, or other error.

A batch continues after individual file failures and exits with status 1 if any
failed. Input/setup errors also exit 1. Successful extraction or intentional
supporting-report skips exit 0. Check the summary and manifest rather than
assuming every file was processed. This manifest does not assign `dataset_id`,
select `trial_inputs.csv` associations, approve integration windows, or calculate
K, concentration or discharge. Those remain separate reviewed operations.

Generated CSVs/manifests stay local under the existing processed-data ignore
policy. Do not force-add large derived readings or change raw files to make an
extraction succeed. Existing curated records are never rewritten by this CLI.

## Tests

```sh
python -m unittest discover -s tests -v
```

The unit tests cover both metadata layouts, explicit/missing/invalid offsets,
clock-only rejection, unit labels, multiple temperatures, recursive discovery,
filters, report skips, per-file errors, collisions and overwrite safety. The
integration tests read all ten tracked recent live-reading exports, compare
all source measurement cells, verify explicit offsets/counts and exercise a
batch with the four supporting reports. No field values are copied to fixtures.
A source-only checkout explicitly skips those integration tests if raw files
are absent; `MORA_REQUIRE_RAW_TESTS=1` makes absence fail instead. The repository
workflow runs the complete suite with that requirement on Linux and Windows.
