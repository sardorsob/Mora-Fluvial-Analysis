# Analysis results

The [reviewed calibration bundle](calibrations/2026-10-26_probe_review/README.md) contains 49 provisional fits, 37 skipped series and diagnostic figures. Its supported identity fills leave all numerical fit fields unchanged from the [earlier bundle](calibrations/README.md). Both bundles are retained; neither contains accepted discharge estimates.

## Local discharge results

Processing and numerical review are complete for the current mass-slug dataset. All **38 releases** have a recorded disposition: **five proposed primary Q estimates**, with five actual-channel comparisons, and **33 releases without a mass-slug estimate**. The five estimates use trial-specific K and 4000 g delivered per release, confirmed by the field participant for October 2–5, 2026. Numerical window review is complete. Field mixing, tracer recovery and total measurement uncertainty remain unverified; no discharge is certified by this export.

| Release | Primary Q (m³/s) | Tested window/background change |
| --- | ---: | ---: |
| NISQ-20261002-T01 | 4.2442 | −4.43% to +4.75% |
| NISQ-20261004-T02 | 2.0438 | −0.80% to +0.49% |
| NISQ-20261004-T03 | 2.7758 | −2.83% to +2.83% |
| NISQ-20261005-T02 | 2.3375 | −2.49% to +2.52% |
| NISQ-20261005-T03 | 2.6638 | −2.92% to +2.66% |

These ranges describe tested choices within observed data, not confidence intervals or total discharge uncertainty. The October 2 T01 and October 4 T03 pulses exceed their calibrations' measured conductivity-increment spans by about 16.3% and 1.6% at the peak. Absolute EC limits and increment spans are separate checks; neither gives a numerical bound on extrapolation error. October 4 T03 also needs reconciliation: the transcribed notebook background is 45 µS/cm, while its matched recording averages 26.36 µS/cm before the pulse, despite close agreement in peak height. No K, recording link or Q was changed to remove this disagreement.

Five candidate releases lack a defensible settled tail/background; July 31, 2025 also has missing pulse sections and unresolved event alignment. No tails are extrapolated. Across all 38 releases, the remaining categories are ten relative-basis releases, five unresolved method conflicts, three identity conflicts, one missing calibration, two practice exclusions and six Paradise releases excluded from scope. Per-recording outcomes retain more than one blocker where present.

The reuse test covers nine October calibration sessions over three days for sensor 790481. Specific-channel reuse fails the ±5% Q criterion; actual-channel reuse is inconclusive without calibration temperatures. Consequently, there are no reference-K comparisons. Actual-channel Q differs from specific-channel Q and is retained as a diagnostic, not averaged into the primary result.

## Use the analysis bundle

The current handoff is `discharge/2026-11-08_discharge_analysis/`:

- `discharge_by_release.csv`: all 38 releases, exact Q values or blanks, final processing dispositions, review status, flags and data limits. `case_disposition` is the export status; `category` preserves the earlier stage's classification.
- `discharge_primary.csv`: the five proposed primary estimates, including the flagged October 4 T03 result.
- `discharge_estimates.csv`: all ten channel estimates with exact K references, windows, units and sensitivity components. Comparison channels are not additional releases.
- `figures/mass/`, `figures/review/`, `figures/reuse/`: discharge/pulse, window-sensitivity and calibration-consistency figures.
- `bundle_index.json`, `source_bundles.json`, `run_info.json` and the review tables: file meanings, reproducibility commands, source hashes and evidence.

A blank Q means not estimated, never zero flow. Six mass-route releases are closed as not estimable from the current capture; the remaining no-estimate cases retain their method, identity, calibration, practice or scope reasons. A case can be revisited if new source evidence becomes available. Processing closure does not remove scientific flags or confer field acceptance.

Generate a fresh package with the [export command](../../docs/getting_started.md#export-the-analysis-package). The bundle remains ignored and local; ordinary clones do not contain the normalized recordings or intermediate run bundles needed to rebuild it. Historical calibration, pairing, discharge and review runs remain intact.

## Reproducing a calibration run

Use the [calibration runner](../../docs/calibration.md) with a fresh output directory. It writes fit/point/skip CSVs directly in that directory, with `figures/` and `run_info.json`. The run record includes input/output and code hashes, software versions and Git revision. The reviewed bundle also has an independent numerical verification; local MLflow is supplementary and is not required to reproduce the fit.

## Other runs

The [current pairing summary](matching/2026-11-01_reviewed_pairings/pairing_summary.csv) covers 38 releases: **32 complete inferred recording/K proposals**, one partial, three conflicting and two practice releases excluded for documented lack of downstream detection. The 32 proposals represent 84.2% of all records, or 88.9% of the 36 non-practice releases. Complete pairing does not confirm physical calibration applicability or make a release ready for Q.

Compared with the [17-proposal bundle](matching/2026-11-01_source_linked_pairings/pairing_summary.csv), the current run retains known links through isolated missing cells, includes the documented July 31 recording continuation, and adds cited session/site/dose-sequence inferences. The [evidence file](../config/pairing_overrides.json) records those decisions and their qualifications. August 6 event alignment and the first PR06 notebook/electronic peak disagreement remain unresolved. No exact release clocks were invented.

The remaining partial release is July 9, 2025 T01, with no supported calibration association. Native serial conflicts remain for July 9 T02, July 17 T01 and August 8 T01; unaffected logger candidates remain available. Eight older preparations have source mass-stock labels but saved relative-concentration fits. Their method discrepancies are flagged without changing K. Six releases retain missing-reading flags. Numerical fits and source observations are unchanged.

The [association table](matching/2026-11-01_reviewed_pairings/trial_associations.csv) still audits all 59 current input rows, including unresolved curated placeholders; proposed links are in the candidate tables and summary. Identity, method, measurement and event-alignment review flags describe different remaining checks. Neither file contains Q estimates or accepted integration windows. See [setup](../../docs/getting_started.md#pair-releases-recordings-and-k-fits) for reproduction and status meanings.

Keep each analysis in a named directory. `_template/` provides `figures/`, `tables/` and `run_info.json`; it contains no scientific result. The historical `result_path` helper uses `MORA_RUN_ID` or a UTC timestamp and starts a run record with status `started`. Complete input references, configuration, Git revision and outcome when the run finishes.

Selected calibration and pairing bundles are tracked. Other generated runs and local MLflow stay ignored; large normalized readings belong in the local processed-data folder. Historical notebooks use retired processing interfaces and are not the maintained runner.
