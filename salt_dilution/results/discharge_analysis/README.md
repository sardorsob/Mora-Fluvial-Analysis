# Discharge analysis

Start with [all release outcomes](tables/discharge_by_release.csv),
[primary estimates](tables/discharge_primary.csv), or
[all channel estimates](tables/discharge_estimates.csv).

- `tables/` contains results, quality checks and sensitivity tables.
- `figures/` contains discharge, pulse, review and calibration plots.
- `settings/` contains the window, quantity and study-design snapshots.
- `provenance/` contains source-run references and supporting citations.

`analysis_limits.json` retains the scientific limitations. Blank Q is not zero.
`bundle_index.json` provides navigation and a rebuild command; `run_info.json`
records hashes. Rebuilding needs the original local source bundles.

Executable code belongs in `salt_dilution/scripts/` or `salt_dilution/notebooks/`,
never in this results folder. Dates belong in records and run metadata, not in
a dated wrapper around this published analysis. Original source-run paths can
still contain dates because they document the historical calculation.

The published bundle was reorganized without recalculating Q. Its unchanged
original run record is preserved as `provenance/original_run_info.json`.
The root `run_info.json` records the layout migration and current output paths;
the original record retains the numerical run's original input paths and hashes.
