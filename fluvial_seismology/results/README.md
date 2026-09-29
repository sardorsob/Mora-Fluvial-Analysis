# Analysis results

Keep each run in its own named directory. `_template/` describes the structure and contains no scientific result.

- `figures/`: exported graphs and diagnostics.
- `tables/`: numerical outputs and summaries.
- `run_info.json`: run ID, status, input references, configuration reference, Git revision, and notes.

The Python `result_path` helper creates a run location using `MORA_RUN_ID` or a UTC timestamp. Its initial record has status `started`; complete the inputs, configuration and outcome when the run finishes. The primary dilution notebook fills these fields automatically and also saves its input configuration.

Use the same structure for exploratory/model runs, recording their purpose and status. Add model-output files when a run actually produces them. Generated runs are ignored by Git; this guide and `_template/` are tracked.
