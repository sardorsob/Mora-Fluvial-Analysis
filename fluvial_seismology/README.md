# Fluvial seismology

Waveform preparation, calibration, spectral analysis, and river-flow/sediment modelling from the archived seismic repository. No seismic recordings are bundled.

## Notebook guide

| Folder and notebook | Purpose |
| --- | --- |
| `preparation/download_waveforms.ipynb` | Acquire the selected historical waveform interval; requires network access. |
| `preparation/format_mseed_files.ipynb` | Rename/move/copy miniSEED working files, with rollback alternatives. |
| `instrument_calibration/instrument_calibration.ipynb` | Preliminary waveform and spectrogram comparisons for calibration recordings. |
| `spectral_analysis/download_and_plot_waveforms.ipynb` | Acquisition followed by signal and spectrum inspection. |
| `spectral_analysis/plot_waveform_spectra.ipynb` | Plot already available recordings. |
| `spectral_analysis/screen_waveforms.ipynb` | Screening workflow that calls the reusable Python modules. |
| `spectral_analysis/plot_ppsd.ipynb` | PPSD and related spectral/temporal experiments. |
| `modelling/fluvial_models_rpy2.ipynb` | Historical R/eseis turbulence, bedload, and inversion experiments through rpy2. |
| `exploratory/screen_waveforms_inline.ipynb` | Alternative screening notebook with functions defined inline. |

## Scripts

`scripts/processing/` contains waveform acquisition, screening, calibration plots, spectra, waveform helpers, seismic amplitude ratios, and the two R spectrogram-processing routines.

`scripts/models/` contains `model_turbulence.R`, `model_bedload.R`, and `fmi_inversion.R`. The R function bodies are preserved apart from whitespace. The modelling notebook loads installed `eseis`; it does not automatically load these checked-in functions.

See [getting started](../docs/getting_started.md), [source environments](config/source_environments/README.md), and the [data guide](data/README.md) before running a workflow.

## Source status and limitations

These are research workflows with historical station/date settings. They have not been validated end to end in this repository.

- ObsPy, R, rpy2, and the field recordings are not available in the migration-check environment.
- The R notebook contains alternative experiments, repeated velocity scaling, an inherited `fml_inv` spelling, and cells that depend on previous manually selected state. Two R-only cells now have `%%R` for language dispatch; scientific expressions remain unchanged.
- Model water depth (`h_w`) and sediment flux (`q_s`) are different quantities from salt-dilution water discharge. Document the intended comparison and units for each analysis.
- Some optional waveform helpers import `amp`, `ampCorrect`, and `intensityLocate`, which are absent from the source snapshot.
- The formatting notebook includes move and rollback operations. Its input paths now point to working copies under `data/processed/staging/`; copy source data there before choosing the relevant cells. Do not run all formatting alternatives sequentially.
- Renamed package modules are launched from the repository root with `python -m ...`. Functions and parameter names retain the source interfaces.

Existing explicit file saves use portable paths; plotting functions that only display figures still only display figures. To export a selected Python figure, pass `result_path("fluvial_seismology", "figures/descriptive_name.png")` to its save method. The shared helper creates the run directory and its initial record. Complete inputs, settings, and outcome in that record.
