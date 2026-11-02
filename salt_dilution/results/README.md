# Analysis results

The [reviewed calibration bundle](calibrations/2026-10-26_probe_review/README.md) contains 49 provisional fits, 37 skipped series and diagnostic figures. Its supported identity fills leave all numerical fit fields unchanged from the [earlier bundle](calibrations/README.md). Both bundles are retained; neither contains accepted discharge estimates.

## Reproducing a calibration run

Use the [calibration runner](../../docs/calibration.md) with a fresh output directory. It writes fit/point/skip CSVs directly in that directory, with `figures/` and `run_info.json`. The run record includes input/output and code hashes, software versions and Git revision. The reviewed bundle also has an independent numerical verification; local MLflow is supplementary and is not required to reproduce the fit.

## Other runs

The [current pairing summary](matching/2026-11-01_reviewed_pairings/pairing_summary.csv) covers 38 releases: **32 complete inferred recording/K proposals**, one partial, three conflicting and two practice releases excluded for documented lack of downstream detection. The 32 proposals represent 84.2% of all records, or 88.9% of the 36 non-practice releases. Complete pairing does not confirm physical calibration applicability or make a release ready for Q.

Compared with the [17-proposal bundle](matching/2026-11-01_source_linked_pairings/pairing_summary.csv), the current run retains known links through isolated missing cells, includes the documented July 31 recording continuation, and adds cited session/site/dose-sequence inferences. The [evidence file](../config/pairing_overrides.json) records those decisions and their qualifications. August 6 event alignment and the first PR06 notebook/electronic peak disagreement remain unresolved. No exact release clocks were invented.

The remaining partial release is July 9, 2025 T01, with no supported calibration association. Native serial conflicts remain for July 9 T02, July 17 T01 and August 8 T01; unaffected logger candidates remain available. Eight older preparations have source mass-stock labels but saved relative-concentration fits. Their method discrepancies are flagged without changing K. Six releases retain missing-reading flags. Numerical fits and source observations are unchanged.

The [association table](matching/2026-11-01_reviewed_pairings/trial_associations.csv) still audits all 59 current input rows, including unresolved curated placeholders; proposed links are in the candidate tables and summary. Identity, method, measurement and event-alignment review flags describe different remaining checks. Neither file contains Q estimates or accepted integration windows. See [setup](../../docs/getting_started.md#pair-releases-recordings-and-k-fits) for reproduction and status meanings.

Keep each analysis in a named directory. `_template/` provides `figures/`, `tables/` and `run_info.json`; it contains no scientific result. The historical `result_path` helper uses `MORA_RUN_ID` or a UTC timestamp and starts a run record with status `started`. Complete input references, configuration, Git revision and outcome when the run finishes.

Selected calibration and pairing bundles are tracked. Other generated runs and local MLflow stay ignored; large normalized readings belong in the local processed-data folder. Historical notebooks use retired processing interfaces and are not the maintained runner.
