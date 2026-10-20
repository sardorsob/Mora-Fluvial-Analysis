# Local incremental processing: October 19, 2026

The existing parser was run at commit `5cd3f5e443bba6b0e379f735fa241601d837cad3` on the fourteen raw files added after the [October 16 run](parser_run_2026_10_16.md). Local and remote main were verified identical. Parser/scientific code and reviewed record CSVs were preserved.

| Check | Result |
| --- | ---: |
| Current unit tests | 22 passed |
| Raw files present and hashed | 208 |
| Newly added raw HTML inputs attempted | 14 |
| New normalized CSV/metadata pairs | 10 |
| Rows added | 3,901 |
| New supporting reports without measurement-table output | 4 |
| Current retained CSV/metadata pairs | 153 |
| Current retained rows | 349,543 |

The ten time series cover September 18 and October 2, 4 and 5, 2026. Each has actual and specific conductivity and full source-local calendar dates, with no missing/duplicate/non-increasing timestamps observed. No UTC conversion, calibration fit, background correction, integration or discharge calculation was performed. The prior corpus's timestamp flags and two quarantines remain unresolved; successful normalization does not establish scientific acceptance.

The four other inputs are one instrument-calibration report and three deployment reports. The measurement reader reports no recognized measurement table; they remain unchanged under `data/raw/` as supporting evidence. They must not be confused with handwritten field titration points or silently counted as missing stream data.

The [local run bundle](../salt_dilution/results/2026-10-19_parser_ingestion/README.md) includes per-file errors/warnings, source/output checksums, exact execution code and installation verification. The [processed-data index](../salt_dilution/data/processed/README.md) points to the saved data. Generated observations, metadata and run artifacts stay Git-ignored.

The run also created a local recording inventory and candidate-link audit for later review. That audit did not edit `trial_inputs.csv` or other reviewed records. It identified four duplicate calibration-parent identities, 16 orphan point rows and stale hashes in the reviewed records manifest; those record-reconciliation findings are distinct from parser execution.

The existing Python 3.13.9 work environment used pandas 2.3.3, numpy 2.5.0, openpyxl 3.1.5 and xlrd 2.0.2. Excel readers were available through the temporary dependency path recorded in the earlier run; no packages or application dependencies were installed for this run. The unchanged parser CLI remains the entry point for individual files.
