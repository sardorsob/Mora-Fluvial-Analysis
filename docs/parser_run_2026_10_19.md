# Parser corpus record: October 19, 2026

Historical incremental run at commit `5cd3f5e443bba6b0e379f735fa241601d837cad3`, following the [October 16 corpus](parser_run_2026_10_16.md).

| Measure | Result |
| --- | ---: |
| Tests in this run | 22 passed |
| Raw files hashed | 208 |
| Added HTML inputs | 14 |
| Added CSV/metadata pairs | 10 |
| Rows added | 3,901 |
| Supporting reports without measurement tables | 4 |
| Retained pairs after this run | 153 |
| Retained rows after this run | 349,543 |

The ten measurement exports cover September 18 and October 2, 4, 5, 2026, with actual/specific EC and complete source-local dates. This run found no missing, duplicate or non-increasing timestamps in those new tables. The four other inputs are one instrument-calibration report and three deployment reports, retained as supporting raw evidence.

Earlier timestamp flags and two quarantines remain unresolved. This run did not convert UTC, fit K, select event windows or calculate Q. Its candidate-link screen was separate from parser execution and did not edit reviewed tables; the later [reconciliation record](salt_record_reconciliation_2026_10_20.md) documents the source-ID repairs.

The local [run bundle](../salt_dilution/results/2026-10-19_parser_ingestion/README.md) retains exact execution code, per-file warnings/errors, source/output hashes and installation checks. It and the [processed readings](../salt_dilution/data/processed/README.md) require local generated files. Recorded environment: Python 3.13.9, pandas 2.3.3, NumPy 2.5.0, openpyxl 3.1.5, xlrd 2.0.2. Use [parser ingestion](parser_ingestion.md) for current commands.
