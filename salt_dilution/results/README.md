# Analysis results

The [reviewed calibration bundle](calibrations/2026-10-26_probe_review/README.md) contains 49 provisional fits, 37 skipped series and diagnostic figures. Its supported identity fills leave all numerical fit fields unchanged from the [earlier bundle](calibrations/README.md). Both bundles are retained; neither contains accepted discharge estimates.

## Reproducing a calibration run

Use the [calibration runner](../../docs/calibration.md) with a fresh output directory. It writes fit/point/skip CSVs directly in that directory, with `figures/` and `run_info.json`. The run record includes input/output and code hashes, software versions and Git revision. The reviewed bundle also has an independent numerical verification; local MLflow is supplementary and is not required to reproduce the fit.

## Other runs

The [saved pairing summary](matching/2026-10-31_final_pairings/pairing_summary.csv) covers 38 releases: 9 have complete inferred recording/K proposals, 16 are partial and 13 remain ambiguous. Recording proposals cover 26 releases; this is not 26 complete K pairings. The [association table](matching/2026-10-31_final_pairings/trial_associations.csv) separates existing recording and calibration relationships from K applicability for all 59 input rows. It retains both source relationships for 27 releases, including files whose missing measurements still need review. Neither file contains Q estimates or accepted integration windows. See [setup](../../docs/getting_started.md#pair-releases-recordings-and-k-fits) for reproduction and status meanings.

Keep each analysis in a named directory. `_template/` provides `figures/`, `tables/` and `run_info.json`; it contains no scientific result. The historical `result_path` helper uses `MORA_RUN_ID` or a UTC timestamp and starts a run record with status `started`. Complete input references, configuration, Git revision and outcome when the run finishes.

Selected calibration bundles and the referenced pairing bundle are tracked. Other generated runs and local MLflow stay ignored; large normalized readings belong in the local processed-data folder. Historical notebooks use retired processing interfaces and are not the maintained runner.
