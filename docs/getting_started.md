# Getting started

Run commands from the repository root. Python 3.10 or newer is the intended baseline for the imported Python source. The migration checks used Python 3.13; that is not a validation of the seismic dependency stack.

For the current DOI-managed Python 3.12 workflow, install the organized project-level [requirements.txt](../requirements.txt). On systems where Conda or virtual-environment execution is blocked by policy, use the approved interpreter with `python -m pip install --user -r requirements.txt`. The historical Conda exports under `fluvial_seismology/config/source_environments/` remain provenance records, not the current setup recipe.

## Salt-dilution example

The salt-dilution-only minimum remains [salt_dilution/requirements.txt](../salt_dilution/requirements.txt). For the full current MORA Python stack, install the root [requirements.txt](../requirements.txt).

A conventional project environment can use:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m jupyterlab
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

Open [salt_dilution_discharge.ipynb](../salt_dilution/notebooks/salt_dilution_discharge.ipynb) and select the Python kernel for this environment. Its setup cell discovers the project root, configures imports, and selects the method's working directory. Launch Jupyter inside the repository or a method subdirectory.

The example uses [2025-07-24_trial_01.ini](../salt_dilution/config/2025-07-24_trial_01.ini) and tracked source CSVs. Paths inside that configuration resolve relative to the configuration file. Calculations and original selected indices remain unchanged.

Set `MORA_RUN_ID` before starting Jupyter to choose a descriptive run name. Otherwise, the shared path helper generates a UTC timestamp. Outputs go under `salt_dilution/results/<run_id>/`: three figures, a discharge table, a configuration snapshot, and a run record. Review the [scientific limitations](../salt_dilution/README.md#known-source-limitations) before interpreting results.

## AquaTROLL parsers

Launch parser modules from the repository root:

```sh
python -m salt_dilution.scripts.parsers.parse_aquatroll_filename_cli --help
python -m salt_dilution.scripts.parsers.parse_aquatroll_metadata_cli --help
python -m salt_dilution.scripts.parsers.parse_aquatroll_interactive
```

Batch parsers default to `salt_dilution/data/processed/`; use `--output` for another destination. The metadata parser's original `--dry-run` flag is not passed through to its writer; do not rely on that flag to prevent writes. See [parser differences](../salt_dilution/README.md#parsers).

## Fluvial seismology

The seismic notebooks need ObsPy, NumPy, SciPy, and Matplotlib. The Python/R notebook additionally needs R, rpy2, and the R packages `eseis` and `fields`; the supplied clipping routine can also use `caTools` for optional smoothing. Install R packages during environment setup.

The four [source environment exports](../fluvial_seismology/config/source_environments/README.md) are retained as records, not a tested cross-platform environment or an rpy2/R lockfile. No seismic recordings are included; supply inputs described in the [data guide](../fluvial_seismology/data/README.md).

Use `python -m fluvial_seismology.scripts.processing.screen_waveforms` after reviewing its station/date settings. Scripts use package imports and should be launched with `python -m ...` from the repository root rather than by filesystem path.

Seismic notebooks include historical station/date choices and unfinished alternatives. Read the [workflow status](../fluvial_seismology/README.md) and select intended cells before executing acquisition, file-management, or model notebooks.

For authenticated acquisition, supply both `MORA_IRIS_USERNAME` and `MORA_IRIS_PASSWORD` in the environment. Leave both unset for public access. No credentials are stored in the repository.

## Checks

```sh
python -m unittest discover -s tests -v
```

These checks cover portable paths, configuration inputs, and parser entry points. They do not establish scientific validity. See [validation](validation.md) for source-preservation and execution checks.
