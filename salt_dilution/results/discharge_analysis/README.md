# Discharge analysis

38 releases are accounted for. 11 have a selected Q estimate; 6 of those depend on additional recipe or delivery assumptions. All estimates remain proposed.

Start with [release outcomes](tables/discharge_by_release.csv), [selected estimates](tables/discharge_primary.csv), or [channel estimates](tables/discharge_estimates.csv). Read `estimate_support`, `quality_flags` and `data_limits` alongside Q. A primary estimate is the selected channel for a release, not scientific acceptance. Blank Q is not zero.

- `figures/` shows discharge, observed pulses, calibration and sensitivity.
- `tables/` includes calibration diagnostics and separate capture-assumed scenarios.
- `settings/` preserves windows, quantities and study design.
- `provenance/` identifies source bundles and citations.

For blank Q, read [remaining requirements](tables/recovery_requirements.csv). [Recovered pulse areas](tables/observed_pulse_areas.csv) preserve usable observations without assuming a delivered quantity or compatible K.

`analysis_limits.json` records the interpretation limits. Window sensitivity and fit standard errors do not quantify total discharge uncertainty. Conditional NaCl reference checks are diagnostics, not coefficient corrections.

`bundle_index.json` contains a rebuild command; `run_info.json` records hashes. Rebuilding needs the original local source bundles.
