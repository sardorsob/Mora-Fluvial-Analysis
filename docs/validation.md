# Validation and limits

The checks below establish source preservation, software behavior and numerical consistency. They do not establish accepted field discharge, instrument equivalence or a complete measurement-uncertainty budget.

## Current salt workflow

Run from the repository root with the project dependencies installed:

```sh
python -m unittest discover -s tests -v
```

The suite covers parser dispatch, metadata/units, source timestamps and explicit UTC offsets, batch discovery and output safety, calibration equations and skip rules, recording/K pairing and unresolved-case handling, record keys/joins, provenance hashes and portable paths. The raw-export integration tests compare every measurement cell in ten tracked live-reading exports and exercise four supporting reports. Missing raw files cause explicit skips unless `MORA_REQUIRE_RAW_TESTS=1` is set. The [CI configuration](../.github/workflows/salt-parser-tests.yml) targets Python 3.13 on Linux and Windows; configuration alone is not evidence that a particular revision passed.

Set `MORA_CHECK_LOCAL_RECORDINGS=1` to also verify the ignored local recordings/metadata against curated provenance. Those checks need the referenced source, output and metadata files. The [record validation report](../salt_dilution/data/records/validation_report.json) records 78 passing tests for the October 26 calibration review, including local-recording checks and 39 identity-evidence files. That is a recorded run, not a test result for every future checkout.

The [reviewed calibration bundle](../salt_dilution/results/calibrations/2026-10-26_probe_review/README.md) contains an independent `numpy.linalg.lstsq` verification of all 49 fits from rebuilt concentrations. K, intercept, R², RMSE and point counts match the earlier bundle. The identity changes did not alter observed quantities or addition labels. See its `numerical_verification.json` and `run_info.json` for scope, software versions and exact hashes.

These checks leave 19 preparation identities unresolved, including 12 fitted series. They do not resolve handwritten units, preparation/delivery uncertainty, the DI-stock ionic-background correction, clock alignment, event windows, mixing or tracer recovery. A high R² is not a calibration-acceptance test.

## Pairing proposals

The matcher proposes release/recording and recording/calibration links separately. Tests cover duplicate and split exports, conflicting samples and sensor identities, uncertain clocks, actual/specific channel compatibility, mass/relative units, exact fit references, current curated claims and output protection. Source metadata and reviewed labels remain distinguishable.

Protocol-based pairing uses field dates, written release times and acquisition breaks under the reported local-clock assumption. Tests include missing trials without sequence shifts, several releases in one log, split sessions, competing recordings, reviewed clock corrections, current-link disagreements and documented missing roles. Placeholder probe aliases do not establish or contradict physical identity. Regression tests pair source-linked fits with blank or different aliases, preserve conflicts found in pinned native calibration evidence even when aliases agree, and reject stale hashes, incompatible channels/units and competing fit series. Approximate question-marked clocks are not silently made exact. Test association settings against reasonable alternatives before promoting inferred links.

A candidate K link does not settle the release-to-recording association. Review the generated `pairing_summary.csv`, selected edge references and retained alternatives; no pairing output is scientific acceptance or a discharge result. The runner reproduces pinned electronic calibration observations where available, rather than searching river curves for convenient calibration values.

Missing-cell tests retain known file/K relationships and exact source-row references, while keeping all-empty conductivity unselected. Reviewed whole-file links preserve uncertain event clocks and cannot select between acquisition segments. Documented continuations require one ordered chain from the same native device/date, reject branching and retain gaps. Abandoned preparations cannot compete with retained fits; practice exclusions require a source-labelled practice release. Supporting-file pins are checked before matching. Folder-date tests preserve disagreements with internal timestamps. Method-label discrepancies remain explicit without changing saved K values or units.

## Mass-slug and coefficient-reuse checks

Synthetic tests cover dimensional conversion, known pulse area/Q, irregular elapsed times, background drift, signed negative excess, duplicates, gaps, missing cells, truncated pulses and event selection. Batch fixtures cover all-release accounting, exact fit references, sensor conflicts, alternate-source rejection, unsigned windows and output protection. Reuse tests distinguish uncertainty in a mean from application uncertainty and prevent unknown preparation/settings from passing a stable-series test.

An independent CSV reader and explicit trapezoid loop reproduce October 4, 2026 T02 specific-channel Q to better than 1e-9 relative for identical windows and K. A port of the historical WRD constant-background, nonnegative-excess, fixed-interval trapezoid calculation differs by about −0.184%; background treatment and clamping explain the difference. This validates numerical agreement under the same assumptions, not tracer recovery or a complete measurement-uncertainty budget.

A saved quantitative review tests 1,188 channel-specific scenarios across the ten estimates, varying pre/post backgrounds and observed pulse edges while rejecting gaps, missing cells and overlapping windows. Primary specific-channel changes range from −4.43% to +4.75% across the tested cases. The review also checks absolute EC and conductivity-increment domains and compares retained notebook observations with native readings. It flags the October 4 T03 background disagreement and two increment-span exceedances without altering the source fits or Q. Numerical window review is complete; complete tracer recovery and cross-section mixing remain unverified. See the [results guide](../salt_dilution/results/README.md#local-discharge-results).

Every new bundle checks its source hashes before and after calculation. Missing values in used windows block integration; no finite-neighbour value is claimed to bound an unseen peak. The plotted RSS combines slope-fit standard error and deterministic background/window sensitivity. It is neither a confidence interval nor total Q uncertainty; mass, stock preparation, clocks, mixing and tracer recovery are not quantified. Five releases have proposed Q, not five validated discharge measurements. Local records and previous bundles are preserved.

The analysis exporter also checks release-key uniqueness, exact primary/master Q agreement, compatible source-run references and figure hashes. Regression fixtures retain blank Q values, prevent comparison-channel double counting, preserve the source-background flag, reject stale or unpinned files, and protect existing/input folders. Case closure means a result or a documented no-estimate outcome exists for this dataset; it does not change scientific acceptance or waive field evidence.

## Migration checks

The September 29, 2026 check used Python 3.13 to compare the initial reorganization with the pinned [source revisions](provenance.md). Its recorded scope was:

- All 53 imported files had a destination and original SHA-256 entry in the [source manifest](source_manifest.csv).
- All eleven example CSVs matched source bytes; five R files differed only in trailing whitespace.
- Python files parsed; all twelve notebooks validated as nbformat 4.5, and their Python cells compiled after IPython transformation. Saved outputs and execution counts were cleared.
- Four portability tests covered configuration-relative inputs, parser entry points, contained result paths/run records and acquisition setup without embedded credentials.
- Credential-literal, local Markdown-link and environment-YAML checks passed; source environment dependency lists were retained.

These are historical migration checks. Later helper retirement means the original file destinations and notebook interfaces are not a current execution guarantee.

## Dilution regression

At migration, the July 24 notebook's code cells ran with the included inputs. Migrated `RC_ss`, `slope_k`, `Q` and `bg_value` exactly matched the source calculation. Three PNGs, a discharge table, configuration snapshot and run record were saved under the local ignored `salt_dilution/results/migration_verification/` directory.

That comparison demonstrated fidelity to the historical calculation, not scientific validity. Its conductivity labels, calibration choices and injection bounds were not resolved. The notebook now imports a retired helper and is not the maintained discharge workflow; see the [salt guide](../salt_dilution/README.md#known-source-limitations).

## Seismic and environment limits

The seismic workflows and R models have not been executed end to end here. The migration environment lacked ObsPy, rpy2, R and the required waveform/instrument inputs. Acquisition used an empty interval and a stand-in at the network boundary, not a live-service test.

Historical Conda exports and current unpinned Python requirements are not verified cross-platform lockfiles. Exploratory notebooks retain missing inputs and inherited errors. Review the [seismic guide](../fluvial_seismology/README.md) before running selected workflows; no validated seismic finding is claimed by the import.
