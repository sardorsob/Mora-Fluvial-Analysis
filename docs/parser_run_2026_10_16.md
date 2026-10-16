# Local raw-data processing: October 16, 2026

The existing salt parser was run again on this laptop at source commit `50301f70363cb3cda9e617595628b89ca3cf56f6`. No scientific or parser code was changed. Fresh outputs were compared with the existing files before being installed in `salt_dilution/data/processed/`, preserving the raw directory layout and source filenames.

| Check | Result |
| --- | ---: |
| Current unit tests | 22 passed |
| Raw source files hashed | 194 |
| CSV/HTML/XLS/XLSX inputs attempted | 173 |
| Retained normalized CSV/metadata pairs | 143 |
| Rows across retained tables | 345,642 |
| Unsupported, failed or empty candidates | 28 |
| Quarantined output pairs | 2 |
| Retained tables with timestamp flags | 11 |

All 286 installed CSV/metadata files matched their previous bytes. Raw source hashes are unchanged. CSV row counts/headers, metadata source paths and output checksums were checked after installation. These totals include stream observations and electronic calibration tables, and are not independent trial counts. Overlapping exports have not been deduplicated.

## Clock-only files

The July 3 clock-only export remains quarantined. The rerun exposed a second affected export, `20250805_083343_mixing_riverLeft_DUPLICATE.csv`: its 2,202 conductivity rows reproduced, but its timestamps changed from the October 6 execution date to the October 16 execution date. Its measurement column supplies clock times without full dates. Report metadata contains a 2025 start date, but date reconstruction has not been implemented or validated.

The previous invalid August output and metadata were preserved under the new run's `previous_processed/` directory. The new pair was quarantined and removed from the ordinary processed tree. This explains the change from the earlier run's 144 retained pairs to 143; no raw data or conductivity observations were discarded. The older transcription inventory remains a historical snapshot, so its reference to this duplicate's former processed path requires the new run's relocation record.

The other 28 unsupported/failed/empty candidates and all warnings are individually listed in the local run manifest. They include metadata sidecars/templates and genuine reader/schema gaps. Time-zone conversion, Fahrenheit handling, missing/duplicate/non-monotonic timestamps, probe/calibration applicability and full-wave selection still require review. No K factor, background correction, integration or discharge was computed.

## Files and environment

- [Processed-data index](../salt_dilution/data/processed/README.md): versioned navigation to locally generated readings.
- [Local run report](../salt_dilution/results/2026-10-16_parser_ingestion/README.md) and [run manifest](../salt_dilution/results/2026-10-16_parser_ingestion/run_info.json): exact sources, errors, warnings, hashes, counts, quarantine and relocation details; generated and Git-ignored.
- [Curated records](../salt_dilution/data/records/README.md): the small notebook tables and their provenance are versioned separately from large processed readings.

Environment: Python 3.13.9, pandas 2.3.3, numpy 2.5.0, openpyxl 3.1.5 and xlrd 2.0.2. The Excel readers were installed into `/private/tmp/mora-parser-deps-2026-10-16` for this run without altering the shared work environment. The project requirements list the needed readers for future environments.

Run the existing CLI from the project root for a supported source file:

```sh
python -m salt_dilution.scripts.parsers.parse_data <source-file> --output <processed-directory>
```

The local run bundle retains the exact `reproduce.py`, `finalize.py` and `promote.py` used for corpus execution, quarantine and verified installation. They record this particular run's paths and observed exceptions; a fresh rerun needs a new run ID and staging directory. Preserve previous runs and confirm quarantine/clock issues before using generated timestamps.
