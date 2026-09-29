# Seismic data

No waveform recordings are included. The inventory contains only column headings. Add authorized input locations and provenance when recordings become available.

The migrated path expressions use the following local conventions:

- `raw/seismic_data/NO<station>/<channel>/`: node waveform files.
- `raw/infrasound_data/<station>/`: infrasound recordings.
- `raw/instrument_metadata/`: instrument-response XML.
- Other `raw/` directories: calibration and original-node recordings, as specified by the selected notebook's input cells.
- `processed/downloaded_waveforms/`: waveform files downloaded and resampled by the acquisition examples.
- `processed/staging/`: working copies for the file-formatting notebook's move/copy/rollback operations.
- Other `processed/` directories: renamed/calibrated input files referenced by the source workflows.

Preserve original field recordings and filenames. Review each notebook's chosen station, channel, period, and file patterns before running. Use `examples/` only for small documented examples suitable for Git. Raw/processed data are ignored; their approved storage location can be recorded in [inventory.csv](inventory.csv).
