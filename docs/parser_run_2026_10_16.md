# Parser corpus record: October 16, 2026

Historical run at source commit `50301f70363cb3cda9e617595628b89ca3cf56f6`.

| Measure | Result |
| --- | ---: |
| Tests in this run | 22 passed |
| Raw files hashed | 194 |
| Reader candidates attempted | 173 |
| Retained CSV/metadata pairs | 143 |
| Rows retained | 345,642 |
| Unsupported, failed or empty candidates | 28 |
| Quarantined pairs | 2 |
| Retained tables with timestamp flags | 11 |

All 286 installed output/metadata files matched their prior bytes; raw hashes were unchanged. Totals include stream and electronic-calibration tables, with overlapping exports not deduplicated. They are not physical-trial counts.

## Clock-only files

The July 3 clock-only export remains quarantined. The second affected source, `20250805_083343_mixing_riverLeft_DUPLICATE.csv`, reproduced 2,202 conductivity rows but acquired the execution date instead of a verified measurement date. Its report has a 2025 start date; reconstruction was not validated. The previous invalid output is preserved under `previous_processed/`, and the new pair is quarantined outside the normal processed tree.

This explains the change from 144 to 143 retained pairs. The historical transcription inventory still points to the duplicate's former location; use the run's relocation record. No raw data or conductivity observations were discarded. Other failures/warnings are listed individually in the manifest. Time/temperature handling, instrument applicability and event windows still need review; no K or Q was calculated by this run.

## Reproduction and evidence

The local [run report](../salt_dilution/results/2026-10-16_parser_ingestion/README.md) and [manifest](../salt_dilution/results/2026-10-16_parser_ingestion/run_info.json) retain paths, errors, hashes, quarantine/relocation details and the execution scripts `reproduce.py`, `finalize.py`, `promote.py`. These generated files are Git-ignored and require the original local run bundle. Preserve earlier runs and use a new staging/run directory for a rerun.

Recorded environment: Python 3.13.9, pandas 2.3.3, NumPy 2.5.0, openpyxl 3.1.5, xlrd 2.0.2. See [parser ingestion](parser_ingestion.md) for current commands and [processed data](../salt_dilution/data/processed/README.md) for local outputs.
