# Analysis results

The [reviewed calibration bundle](calibrations/2026-10-26_probe_review/README.md) contains 49 provisional fits, 37 skipped series and diagnostic figures. Its supported identity fills leave all numerical fit fields unchanged from the [earlier bundle](calibrations/README.md). Both bundles are retained; neither contains accepted discharge estimates.

## Reproducing a calibration run

Use the [calibration runner](../../docs/calibration.md) with a fresh output directory. It writes fit/point/skip CSVs directly in that directory, with `figures/` and `run_info.json`. The run record includes input/output and code hashes, software versions and Git revision. The reviewed bundle also has an independent numerical verification; local MLflow is supplementary and is not required to reproduce the fit.

## Other runs

The [current pairing summary](matching/2026-11-01_source_linked_pairings/pairing_summary.csv) covers 38 releases: 17 have complete inferred recording/K proposals, six are partial, 12 remain ambiguous and three have conflicts. Recording proposals cover 26 releases. Complete source pairing does not confirm physical calibration applicability or make a release ready for Q.

Record-table probe aliases were placeholders. Removing them as identity gates adds eight complete proposals compared with the [earlier bundle](matching/2026-10-31_final_pairings/pairing_summary.csv), which had nine. The current run keeps source-linked K values with unverified device identity clearly flagged. It preserves native serial conflicts for July 9, July 17 and August 8, 2025; an unaffected logger can still retain a valid candidate link within a conflicting release. Numerical K fits and source observations are unchanged.

The [association table](matching/2026-11-01_source_linked_pairings/trial_associations.csv) audits all 59 input rows separately from recording selection. Both source relationships remain available for 27 releases, including files whose missing measurements need review. Identity status distinguishes reproduced electronic evidence, reported within-trial continuity and unverified identity. Neither file contains Q estimates or accepted integration windows. See [setup](../../docs/getting_started.md#pair-releases-recordings-and-k-fits) for reproduction and status meanings.

Keep each analysis in a named directory. `_template/` provides `figures/`, `tables/` and `run_info.json`; it contains no scientific result. The historical `result_path` helper uses `MORA_RUN_ID` or a UTC timestamp and starts a run record with status `started`. Complete input references, configuration, Git revision and outcome when the run finishes.

Selected calibration and pairing bundles are tracked. Other generated runs and local MLflow stay ignored; large normalized readings belong in the local processed-data folder. Historical notebooks use retired processing interfaces and are not the maintained runner.
