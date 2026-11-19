# Fluvial seismology

Use these workflows to prepare seismic waveforms, compare instrument and hammer recordings, and explore how river flow and sediment transport contribute to seismic spectra. Bring your own waveform files and station metadata.

## Notebook guide

| Folder and notebook | Purpose |
| --- | --- |
| [Download waveforms](notebooks/preparation/download_waveforms.ipynb) | Download the selected historical waveform interval over the network. |
| [Organize miniSEED files](notebooks/preparation/format_mseed_files.ipynb) | Rename, move, or copy working files. Includes rollback options. |
| [Clip miniSEED recordings](notebooks/preparation/clip_miniseed.ipynb) | Extract shorter waveform windows from local recordings. |
| [Compare calibration recordings](notebooks/instrument_calibration/instrument_calibration.ipynb) | Compare waveforms and spectrograms from calibration recordings. |
| [Pick hammer arrivals in R](notebooks/instrument_calibration/pick_hammer_arrivals_r.ipynb) | Explore automatic first-arrival picking with STA/LTA and kurtosis. Requires R and rpy2. |
| [Test arrival pickers](notebooks/instrument_calibration/test_arrival_pickers.ipynb) | Compare candidate arrival picking methods on example shot recordings. |
| [Estimate Green’s function velocities](notebooks/instrument_calibration/estimate_greens_velocities.ipynb) | Compare manually marked arrivals and estimate velocities from travel times and distances. |
| [Estimate N11 hammer P-wave velocity](notebooks/instrument_calibration/estimate_n11_hammer_p_wave_velocity.ipynb) | Estimate velocity from paired hammer arrivals and flag inconsistent picks for review. |
| [Download and inspect waveforms](notebooks/spectral_analysis/download_and_plot_waveforms.ipynb) | Download recordings and inspect their waveforms and spectra. |
| [Plot waveform spectra](notebooks/spectral_analysis/plot_waveform_spectra.ipynb) | Plot signals and spectra from local recordings. |
| [Screen waveforms](notebooks/spectral_analysis/screen_waveforms.ipynb) | Screen recordings with the shared Python scripts. |
| [Plot probabilistic power spectral densities](notebooks/spectral_analysis/plot_ppsd.ipynb) | Explore the distribution of spectral power and its variation over time. |
| [Compare observed and model spectra](notebooks/spectral_analysis/compare_observed_and_model_spectra.ipynb) | Compare observed waveform spectra with experimental Python flow and bedload model curves. |
| [Explore river process models in R](notebooks/modelling/fluvial_models_rpy2.ipynb) | Explore turbulence, bedload, and inversion with eseis through rpy2. |
| [Explore waveform screening](notebooks/exploratory/screen_waveforms_inline.ipynb) | Screen waveforms with functions defined in the notebook. |
| [Explore Fourier analysis](notebooks/exploratory/explore_fourier_analysis.ipynb) | Practice Fourier transforms and filtering with example signals. |

## Scripts

`scripts/processing/` contains waveform acquisition, screening, calibration plots, spectra, waveform helpers, seismic amplitude ratios, and the two R spectrogram-processing routines.

The newer spectral tools include a [PPSD export to NPZ](scripts/processing/export_ppsd_npz.py), an [experimental Python port of the eseis spectrum estimator](scripts/processing/signal_spectrum.py), and a [Welch PSD helper](scripts/processing/welch_psd.py). The observed/model spectrum notebook imports the Python spectrum estimator.

[`scripts/models/`](scripts/models/) contains R functions for turbulence, bedload, and spectral inversion. The modelling notebook calls the installed `eseis` package. Source these local R files explicitly to use them.

See [getting started](../docs/getting_started.md), [source environments](config/source_environments/README.md), and the [data guide](data/README.md) before running a workflow.

## Source status and limitations

These are research workflows with historical station/date settings. They have not been validated end to end in this repository.

Several research notebooks retain local file paths. Set them to your waveform and marker files before running selected cells. Unfinished upstream snippets in the arrival and Fourier notebooks are retained as text. See [source provenance](../docs/provenance.md) for the upstream revision.

### Export and compare spectra

From the repository root, give the PPSD exporter a miniSEED file or quoted glob, the matching StationXML response, and a UTC interval with complete one-hour segments:

```sh
python -m fluvial_seismology.scripts.processing.export_ppsd_npz \
  "path/to/waveforms/*.mseed" path/to/stations.xml \
  --seed-id ZE.2416..GPZ --start 2024-07-26T12:00:00 --end 2024-07-26T14:00:00
```

The NPZ in the run's `tables/` directory stores `period_s`, ascending `frequency_hz`, and `mean_acceleration_psd_db` for the same bins. The export uses the recorded sample rate and skips gaps. For older files from the upstream exporter, the key `freq` contains periods in seconds. [ObsPy PPSD documentation](https://docs.obspy.org/packages/autogen/obspy.signal.spectral_estimation.PPSD.get_mean.html)

The Welch helper accepts one merged trace, its instrument response, and a frequency band inside the response filter passband. With density scaling, it returns velocity PSD in dB relative to `1 (m/s)²/Hz`. To express acceleration PSD in those units, subtract `20 × log10(2πf)` at each positive frequency `f` in Hz. Compare the same channel and overlapping passband. PPSD averages the distribution of segment values in dB, while Welch averages segment power before taking the logarithm. The experimental Python spectrum estimator returns linear power. Its numerical equivalence to the R implementation has yet to be established.

### Review hammer arrival pairs

For the manual notebooks, confirm the two marker lists and the distance list refer to the same strikes in the same order before enabling `shot_order_reviewed`. Equal file lengths alone cannot detect a shifted pairing. In the R experiment, use `max_first_arrival_delay_s` only when geometry, clock alignment, and the expected travel times support a bound. The notebook proposes mutually unique pairs within that bound and leaves missing or ambiguous picks blank. Review the proposals against the field log before interpreting a velocity.

Positive R delay means arrival at node B follows node A. The envelope calculation requires a common time grid across both traces. Keep the broadband first-arrival delays separate from the frequency-dependent envelope delays. Verify sensor positions and path geometry before interpreting either as a velocity.

## Setup notes for older notebooks

- The modelling notebook has alternative experiments, repeated velocity scaling, an inherited `fml_inv` spelling, and cells that depend on earlier manual selections. R-only cells use `%%R`.
- Model water depth (`h_w`) and sediment flux (`q_s`) are different quantities from salt-dilution water discharge. Document the intended comparison and units for each analysis.
- Some optional waveform helpers import `amp`, `ampCorrect`, and `intensityLocate`, which are absent from the source snapshot.
- The formatting notebook includes move and rollback operations. Its input paths point to working copies under `data/processed/staging/`; copy source data there before choosing the relevant cells. Do not run all formatting alternatives sequentially.
- Launch package modules from the repository root with `python -m ...`.

To export a selected Python figure, pass `result_path("fluvial_seismology", "figures/descriptive_name.png")` to its save method. The shared helper creates the run directory and its initial record. Complete inputs, settings, and outcome in that record.
