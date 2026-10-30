# Getting started

Run commands from the repository root. Use an approved Python environment; the root requirements target Python 3.12, while saved runs record the versions actually used. The package lists are unpinned.

## Install dependencies

Where virtual environments are permitted:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r salt_dilution/requirements.txt openpyxl xlrd
```

On Windows, activate with `.venv\Scripts\activate`. This installs the salt and notebook dependencies, including readers for XLSX and legacy XLS files. For the broader seismic, statistical and geospatial stack, use `python -m pip install -r requirements.txt`. On managed systems, follow the approved installation method.

## Fit calibration curves

The runner uses the tracked preparation and point tables; stream recordings are not required.

```sh
python -m salt_dilution.scripts.processing.calibration --basis both --output salt_dilution/results/new_calibration_run
```

Choose a new output directory. `--basis` accepts `specific`, `actual` or `both` and defaults to `specific`. Outputs include coefficients, derived points, skipped series, figures and a run record. Read [calibration](calibration.md) to interpret them; they are provisional fits, not discharge estimates.

## Read instrument files

Inspect a supported file without writing outputs:

```sh
python -m salt_dilution.scripts.parsers.parse_data path/to/source.html
```

Process a folder into a new directory:

```sh
python -m salt_dilution.scripts.parsers.parse_data salt_dilution/data/raw --recursive --output salt_dilution/data/processed/new_run
```

The parser writes CSVs, metadata and a per-file manifest. Review its errors and warnings before analysis. [Parser ingestion](parser_ingestion.md) explains supported formats, file selection, clocks and output protection.

## Work with seismic recordings

Supply the inputs described in the [seismic data guide](../fluvial_seismology/data/README.md), then start Jupyter:

```sh
python -m jupyterlab
```

Choose the environment's Python kernel and review each notebook's station, date and path settings. The [seismic guide](../fluvial_seismology/README.md) lists the workflows and limitations. Run formatting operations on working copies; its move/copy/rollback cells are alternatives, not a sequence to execute together.

The Python/R notebook additionally needs R, rpy2, and the R packages `eseis` and `fields`; `caTools` supports optional smoothing. These are separate from the Python requirements. The [source Conda exports](../fluvial_seismology/config/source_environments/README.md) are historical references, not verified installation recipes.

Launch package scripts from the root with `python -m ...`, such as `python -m fluvial_seismology.scripts.processing.screen_waveforms`. Authenticated acquisition reads both `MORA_IRIS_USERNAME` and `MORA_IRIS_PASSWORD`; leave both unset for public access. Existing Python figure saves use the shared path helper and `MORA_RUN_ID` or a UTC run name. Complete each run's `run_info.json` with inputs, settings and outcome; display-only plots are not automatically exported.

## Run checks

```sh
python -m unittest discover -s tests -v
```

See [validation](validation.md) for test coverage and optional local-data checks. The [historical July 24 notebook](../salt_dilution/notebooks/salt_dilution_discharge.ipynb) uses retired helpers; use the maintained scripts above for current salt work.
