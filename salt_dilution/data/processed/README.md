# Normalized salt-data inputs

The local corpus contains **153 measurement CSVs and 153 metadata JSON files**, totaling **349,543 rows** at the October 19, 2026 ingestion cutoff. It includes stream recordings and electronic calibration tables; overlapping exports are not independent trials.

Subdirectories mirror `data/raw/` and retain original file stems. Each measurement table has a `_metadata.json` sidecar describing source properties, channels and clock warnings. Large readings, metadata and field-note staging stay Git-ignored. This index and the small [curated records](../records/README.md) are versioned.

## Data limitations

Eleven retained tables have timestamp flags. Two historical clock-only outputs are quarantined outside this folder: a July 3 export and an August 5 duplicate whose generated date changed with the execution date. Do not treat those generated dates as measurement dates or restore quarantined outputs without resolving their clocks.

Deployment and instrument-calibration reports are supporting documents, not measurement time series. Successful extraction does not establish event identity, calibration applicability or clock synchronization.

## Using the readings

Review the recording association, channel/units, clocks, gaps, duplicate timestamps and full event window before integrating a pulse. File bounds are not analysis windows, and overlapping exports must not be counted twice. The [calibration results](../../results/calibrations/2026-10-26_probe_review/README.md) are separate from these observations.

Use the [parser CLI](../../../docs/parser_ingestion.md) to extract into a fresh directory and retain its manifest. The broader [field-note bundle](field_notes/README.md) also requires local files and is not included in a fresh clone.
