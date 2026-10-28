# Getting started

Run commands from the repository root. The project-level [requirements.txt](../requirements.txt) targets the team's Python 3.12 workflow and includes salt, seismic and geospatial packages. It is an unpinned package list, not a tested cross-platform lockfile. Saved calibration runs record their own Python and NumPy versions.

## Environment

Where virtual environments are permitted:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate`. On managed systems, use the approved interpreter and installation method; the requirements file also describes a user-install option for environments where policy permits it.

For salt-only work, [salt_dilution/requirements.txt](../salt_dilution/requirements.txt) supplies the numerical and notebook packages. Add `openpyxl` for XLSX and `xlrd` for legacy XLS inputs; those readers are included in the root requirements.

## Salt-dilution example

Start with the maintained calibration runner. It uses the tracked preparation and point tables, so large stream recordings are not needed:

```sh
python -m salt_dilution.scripts.processing.calibration --basis both --output salt_dilution/results/new_calibration_run
```

Use a new output directory. `--basis` accepts `specific`, `actual` or `both`; its default is `specific`. The run saves fit/point/skip CSVs, figures and input/code hashes. Read [calibration](calibration.md) before interpreting K. The [reviewed saved run](../salt_dilution/results/calibrations/2026-10-26_probe_review/README.md) is an example of these outputs, not an accepted discharge calculation.

The historical [July 24 notebook](../salt_dilution/notebooks/salt_dilution_discharge.ipynb) and its [configuration](../salt_dilution/config/2025-07-24_trial_01.ini) retain the earlier calculation. The notebook imports a retired helper and is not expected to run against the current processing modules. Its original index-based event selection and scientific limitations remain documented in the [salt guide](../salt_dilution/README.md#known-source-limitations).

## Salt-dilution parser

Inspect one supported Aqua TROLL HTML/CSV, General logger XLS/XLSX, or calibration CSV without writing files:

```sh
python -m salt_dilution.scripts.parsers.parse_data path/to/source.html
```

Normalize a reviewed folder selection into a fresh processed-data directory:

```sh
python -m salt_dilution.scripts.parsers.parse_data salt_dilution/data/raw --recursive --output salt_dilution/data/processed/new_run
```

The CLI saves normalized CSVs, metadata JSON and a per-file manifest while preserving raw files. Read [parser ingestion](parser_ingestion.md) for filters, supporting-report skips, timestamp rules and overwrite protection. Check failures and warnings before using a recording; extraction does not select a release, integration window or calibration.

## Fluvial seismology

The seismic notebooks use ObsPy, NumPy, SciPy and Matplotlib. The Python/R notebook additionally needs R, rpy2, and the R packages `eseis` and `fields`; the supplied clipping routine can use `caTools` for optional smoothing. R/rpy2 setup is separate from the Python requirements. The four [source Conda exports](../fluvial_seismology/config/source_environments/README.md) are historical records, not a verified portable environment.

Supply the inputs in the [seismic data guide](../fluvial_seismology/data/README.md), then launch Jupyter:

```sh
python -m jupyterlab
```

Select the environment's Python kernel. Notebook setup cells discover the repository root when Jupyter starts within it. Review station/date settings and the [workflow limitations](../fluvial_seismology/README.md) before running acquisition, file-management or model cells. The formatting notebook contains alternative move/copy/rollback operations; use working copies and select the intended cells.

Launch package scripts from the repository root, for example `python -m fluvial_seismology.scripts.processing.screen_waveforms`, after reviewing their settings. Authenticated acquisition uses both `MORA_IRIS_USERNAME` and `MORA_IRIS_PASSWORD` in the environment; leave both unset for public access.

Existing Python figure saves use the shared path helper. Set `MORA_RUN_ID` to name a run, or allow a UTC timestamp; complete its `run_info.json` with inputs, settings and outcome. Functions that only display figures do not automatically export them.

## Checks

```sh
python -m unittest discover -s tests -v
```

The suite covers parsers, calibration calculations, curated-table integrity and portable paths. Optional local-recording checks need generated files. See [validation](validation.md) for the check boundaries; a passing suite does not establish scientific acceptance.
