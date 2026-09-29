# Analysis results

There are no completed runs. `_template/` is an empty layout for future runs, not an example result.

For each analysis, copy `_template/` to a descriptive run directory, such as `YYYY-MM-DD_analysis-name`, and fill in `run-info.json`.

- `figures/`: exported graphs and diagnostic plots.
- `tables/`: numerical results and summaries.
- `run-info.json`: input references, configuration reference, code revision, run status, and interpretation notes.

Use this same structure for experimental runs and identify them in the status and notes. Preserve each run's context together with its outputs. Add a model-output folder when a run actually saves model objects.

Generated runs are ignored by Git. The instructions and empty template are tracked.
