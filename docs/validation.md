# Migration validation

Checked locally on 2026-09-29 with Python 3.13. This checks the repository reorganization against the pinned sources in [provenance](provenance.md); it does not validate the scientific methods or field results.

## Checks completed

- All 53 source files have an existing destination and a matching original SHA-256 in the [source manifest](source_manifest.csv).
- All eleven example CSVs match the source bytes. The five R files preserve source content apart from trailing whitespace.
- Python files parse successfully. All twelve notebooks validate as nbformat 4.5, their Python cells compile after IPython transformation, and saved outputs and execution counts are cleared.
- Four portability tests pass: configuration inputs from a different working directory, both parser CLI entry points, contained result paths and run records, and acquisition setup without embedded credentials.
- Local checks found no retained source credential literals or new literal credential assignments in executable Python cells or scripts.
- Local Markdown links resolve. Source environment records parse as YAML and retain their original dependency lists.

Run the portability checks from the repository root:

```sh
python -m unittest discover -s tests -v
```

## Dilution regression

The code cells of `salt_dilution/notebooks/salt_dilution_discharge.ipynb` were executed in sequence from the notebook's directory using the included July 24 inputs. The migrated `RC_ss`, `slope_k`, `Q`, and `bg_value` equal the original notebook's calculation exactly. The run produced three PNG figures, a discharge table, a configuration snapshot, and a completed run record under the ignored `salt_dilution/results/migration_verification/` directory.

That agreement establishes fidelity to the historical calculation. It does not resolve the source's conductivity labels, calibration choices, injection bounds, or other scientific limitations listed in the [salt-dilution README](../salt_dilution/README.md).

## Limits

The seismic workflows and R models were not executed end to end: ObsPy, rpy2, R, and the required waveform/instrument inputs were unavailable in the checking environment. Acquisition was checked with an empty time interval and a network-boundary stand-in; live service access was not tested. Source environment exports are historical records, not verified installation recipes.

Exploratory notebooks and prototypes retain their documented missing inputs and source errors. See the method READMEs before running them. No new scientific result or field-ready workflow is claimed by this import.
