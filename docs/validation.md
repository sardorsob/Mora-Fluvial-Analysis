# Validation and limits

The checks below establish source preservation, software behavior and numerical consistency. They do not establish accepted field discharge, instrument equivalence or a complete measurement-uncertainty budget.

## Current salt workflow

Run from the repository root with the project dependencies installed:

```sh
python -m unittest discover -s tests -v
```

The suite covers parser dispatch, metadata/units, source timestamps and explicit UTC offsets, batch discovery and output safety, calibration equations and skip rules, record keys/joins, provenance hashes and portable paths. The raw-export integration tests compare every measurement cell in ten tracked live-reading exports and exercise four supporting reports. Missing raw files cause explicit skips unless `MORA_REQUIRE_RAW_TESTS=1` is set. The [CI configuration](../.github/workflows/salt-parser-tests.yml) targets Python 3.13 on Linux and Windows; configuration alone is not evidence that a particular revision passed.

Set `MORA_CHECK_LOCAL_RECORDINGS=1` to also verify the ignored local recordings/metadata against curated provenance. Those checks need the referenced source, output and metadata files. The [record validation report](../salt_dilution/data/records/validation_report.json) records 78 passing tests for the October 26 calibration review, including local-recording checks and 39 identity-evidence files. That is a recorded run, not a test result for every future checkout.

The [reviewed calibration bundle](../salt_dilution/results/calibrations/2026-10-26_probe_review/README.md) contains an independent `numpy.linalg.lstsq` verification of all 49 fits from rebuilt concentrations. K, intercept, R², RMSE and point counts match the earlier bundle. The identity changes did not alter observed quantities or addition labels. See its `numerical_verification.json` and `run_info.json` for scope, software versions and exact hashes.

These checks leave 19 preparation identities unresolved, including 12 fitted series. They do not resolve handwritten units, preparation/delivery uncertainty, the DI-stock ionic-background correction, clock alignment, event windows, mixing or tracer recovery. A high R² is not a calibration-acceptance test.

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
