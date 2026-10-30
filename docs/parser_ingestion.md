# Reading instrument files

The parser converts supported exports into CSV tables with source metadata. It reads Aqua TROLL/VuSitu HTML and metadata-prefixed CSV, General logger XLS/XLSX, and recognized electronic calibration CSVs. It does not choose a salt release, fit K or calculate Q.

Use the [setup guide](getting_started.md) to install dependencies. Pandas handles tables; `openpyxl` reads XLSX and `xlrd` reads legacy XLS.

## Inspect first, then write

Omit `--output` to inspect a file without writing:

```sh
python -m salt_dilution.scripts.parsers.parse_data path/to/source.html
```

Process a folder into a fresh directory:

```sh
python -m salt_dilution.scripts.parsers.parse_data salt_dilution/data/raw --recursive --output salt_dilution/data/processed/new_run
```

A directory scan is top-level unless `--recursive` is supplied. Output subfolders follow paths relative to the input root. To select files, repeat `--include` with quoted, case-sensitive input-relative globs, using forward slashes:

```sh
python -m salt_dilution.scripts.parsers.parse_data salt_dilution/data/raw --recursive --include "20260918/*.html" --include "2026100[245]/*.html" --output salt_dilution/data/processed/recent_vusitu
```

These filters select the September 18 and October 2, 4 and 5, 2026 exports. Filenames help select files; the reader uses file contents to recognize their format.

## Outputs and reports

Each measurement file produces `<stem>.csv` and `<stem>_metadata.json`. The metadata preserves report/device properties, original channel labels and units, and available identifiers. Extra columns remain available; multiple temperature channels are not collapsed or assumed to be water temperature.

Both older multi-cell and newer inline VuSitu metadata layouts are supported. Deployment and instrument-calibration reports are retained in raw storage and skipped as `supporting_report`. They are not conductivity time series or notebook salt calibrations. Malformed measurement files fail rather than becoming report skips.

The `ingestion_manifest.json` records source/output paths and SHA-256 hashes, parser hashes, row counts, time ranges, warnings and per-file status:

| Status | Meaning |
| --- | --- |
| `parsed` | Read-only inspection succeeded. |
| `written` | CSV and metadata were saved. |
| `skipped` | Supporting report, unsupported extension or symbolic-link file. |
| `failed` | Unrecognized/malformed measurements, unsafe output or another error. |

Batches continue after individual failures and exit 1 if any file fails. Successful extraction and intentional skips exit 0. Review the manifest for partial failures before using the outputs; it does not create accepted `trial_inputs.csv` associations or integration windows.

## Units and clocks

Actual/specific EC gets a `_us_cm` column name only when its source units match µS/cm. A single temperature gets `_c` only for Celsius. Ambiguous or other units keep their source labels and a warning; no unit conversion is guessed.

`timestamp` retains the source clock. `timestamp_utc` requires an offset-aware timestamp or a valid numeric report `TimeOffset`, such as `-07:00:00`. PST/PDT text, filenames, export dates and the computer timezone do not supply that evidence. Conflicting explicit offsets fail extraction. Without an explicit offset, UTC stays absent with a warning.

Clock-only or missing-date Aqua TROLL readings are rejected. Duplicate/non-monotonic timestamps remain in place and are flagged. The later user-authorized [rock-time normalization](../salt_dilution/data/records/README.md#rock-observations) is a separate dataset convention, not a rule applied to instrument clocks.

## Output protection and checks

Use a new output directory. Existing CSVs, sidecars and manifests are refused unless `--overwrite` is explicit. Even then, sources cannot be replaced, colliding names are not resolved automatically, and batch outputs cannot be placed inside the scanned source tree. Symbolic-link directories are not traversed, and output links cannot escape the output root. Each CSV/metadata pair is staged before writing; this is not a filesystem-wide transaction.

Raw exports and curated records are never rewritten. Large processed readings and manifests remain local under the existing ignore rules.

Run `python -m unittest discover -s tests -v` for parser, batch and calibration checks. Raw-export tests compare source cells in ten tracked measurement exports and exercise four supporting reports. `MORA_REQUIRE_RAW_TESTS=1` makes missing inputs fail rather than skip; CI uses that setting on Linux and Windows. See [validation](validation.md) for scope and limits.
