# Analysis results

Keep each run in its own named directory. `_template/` describes the structure and contains no scientific result.

- `figures/`: exported graphs and diagnostics.
- `tables/`: numerical outputs and summaries.
- `run_info.json`: run ID, status, input references, configuration reference, Git revision, and notes.

The historical Python `result_path` helper creates a run location using `MORA_RUN_ID` or a UTC timestamp. Its initial record has status `started`; complete the inputs, configuration and outcome when the run finishes. Historical notebooks are retained as provenance, not the maintained runner.

The maintained [calibration runner](../../docs/calibration.md) writes its small fit/point/skip CSVs directly in the run directory alongside `figures/` and `run_info.json`. The selected [October 20 calibration bundle](2026-10-20_calibration/README.md) is tracked at the user's request. Other generated runs and local MLflow tracking remain ignored. Large normalized stream readings stay in the ignored processed-data folder.
