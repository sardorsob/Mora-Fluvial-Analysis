# Normalized salt-data inputs

This local corpus contains **153 normalized CSVs and 153 metadata JSON files**, totaling **349,543 rows** at the October 19, 2026 ingestion cutoff. It includes stream observations and electronic calibration tables, with possible overlap between exports. These totals are not independent trial counts.

Subdirectories mirror `data/raw/`, retaining original stems. Large generated readings, metadata and field-note staging stay Git-ignored; this index and the small [curated records](../records/README.md) are versioned.

## Coverage and evidence

| Ingestion cutoff | Retained pairs | Retained rows | Evidence |
| --- | ---: | ---: | --- |
| October 16, 2026 | 143 | 345,642 | [Versioned summary](../../../docs/parser_run_2026_10_16.md); [local run manifest](../../results/2026-10-16_parser_ingestion/run_info.json) |
| October 19, 2026 | 153 | 349,543 | [Versioned summary](../../../docs/parser_run_2026_10_19.md); [local run bundle](../../results/2026-10-19_parser_ingestion/README.md) |

The second cutoff adds ten live series (3,901 rows) from September 18 and October 2, 4 and 5, 2026. Four additional inputs are supporting instrument-calibration/deployment reports rather than time series. The ten series contain actual and specific EC and clean source-local timestamp ordering. Their successful extraction does not establish event identity or accepted clocks.

Eleven retained tables have timestamp flags. Two clock-only outputs are quarantined outside this folder: the July 3 export and the August 5 duplicate whose generated date changed with execution date. The October 16 bundle preserves the prior August output and its relocation record. Its manifest also lists 28 unsupported, failed or empty candidates and exact source/output hashes; raw observations were preserved. The [October 6 local run](../../results/2026-10-06_parser_ingestion/README.md) records the earlier 144-pair cutoff.

## Using the readings

Resolve the recording association, channel/units, clocks, duplicate/irregular timestamps and event window before integrating a pulse. File bounds are not analysis windows, and overlapping exports must not be counted twice. The ingestion runs calculated no K, discharge, correction factors, background models or weather joins; later [calibration results](../../results/calibrations/2026-10-26_probe_review/README.md) are separate.

Use the maintained [parser CLI](../../../docs/parser_ingestion.md) for extraction into a fresh directory and retain its manifest. Local run links and the broader [field-note bundle](field_notes/README.md) require files on disk and are not included in a fresh clone.
