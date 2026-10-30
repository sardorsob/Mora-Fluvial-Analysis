# Field-data schema

The maintained data separates physical releases, calibration preparations, readings and recording associations. This keeps one observation from being counted again when it has several candidate files or calibrations. The [records guide](../salt_dilution/data/records/README.md) explains coverage and missing values; [calibration](calibration.md) defines the calculations.

## Current compact salt interface

Four UTF-8 CSVs under `salt_dilution/data/records/` provide the calculation inputs:

| Table | One row represents | Key or relationship |
| --- | --- | --- |
| `trials.csv` | One physical salt release; 38 rows. | `trial_id` |
| `calibrations.csv` | One preparation/attempt; 43 rows. | `calibration_id` |
| `calibration_points.csv` | One observed calibration reading; 262 rows. | `calibration_id`, `probe_alias`, `step_no` |
| `trial_inputs.csv` | One candidate recording/calibration association or placeholder; 59 rows. | References `trial_id`, optional `calibration_id`, and `dataset_id`/`processed_path`. |

Exact headers:

```text
trials.csv
trial_id,site_alias,field_date,trial_label,sourcebook_reference,injection_form,salt_mass_g,injection_solution_volume_ml,dump_timestamp_utc

calibrations.csv
calibration_id,field_date,site_alias,procedure_id,stock_water_source,stock_salt_mass_g,stock_water_initial_ml,stock_solution_final_ml,injectate_aliquot_ml,secondary_water_initial_ml,calibration_water_initial_ml,sourcebook_reference,review_status

calibration_points.csv
calibration_id,step_no,probe_alias,recorded_added_volume_ml,addition_kind,recorded_vessel_volume_ml,actual_conductivity_us_cm,specific_conductivity_us_cm,temperature_c,sourcebook_reference,review_status

trial_inputs.csv
trial_id,dataset_id,processed_path,calibration_id,probe_alias,recording_role,window_start_utc,window_end_utc,conductivity_basis,review_status
```

Join points to preparations with a many-to-one check. Preserve source positions in `step_no`, including gaps. Keep paired probes, split files and alternative calibrations separate. `processed_path` is relative to the repository root. Salt-table dates use `M/D/YYYY`; parse with `%m/%d/%Y` before comparing with ISO dates.

The [procedure profiles](../salt_dilution/config/procedure_versions.json) distinguish `solution_secondary`, `mass_stock_river` and `mass_stock_deionized`. Choose from recorded preparation evidence, not the date or the presence of a secondary-water value. Measured final stock volume is optional; the nominal starting-water fallback and its recorded basis are described in [calibration](calibration.md).

Source additions remain `incremental`, `cumulative` or `unconfirmed`; derived cumulative quantities belong in results. Uncertain readings stay blank numerically, with original tokens in provenance. The tables, `provenance.json`, `manifest.json` and `validation_report.json` are versioned together.

The association table currently has 48 file-linked rows and 11 unresolved-path rows. All salt review states remain `needs_review`, and UTC release/integration-window fields are blank. Populated file or calibration IDs do not establish discharge readiness. Same-day records need event, instrument/channel and clock review before they can be joined.

## Rock observations

`records/sediment/rock_observations.csv` contains one row per individual tethered-rock test or qualitative observation. It has 331 unique `rock_observation_id` values. `session_id`, `trial_block`, `repeat_no`, `rock_category` and `test_number` describe the experiment hierarchy; they are not permanent physical-specimen IDs.

Categories are ordered `38.5mm`, `54.5mm`, `D50`, `79mm`, `119mm`. One category remains unresolved. The working duration is 60 seconds by protocol convention. Local `time_raw` values have been normalized despite that column's historical name; 316 have UTC equivalents under the stated Los Angeles timezone assumption, and 15 individual times remain missing. Discharge associations are still blank.

See the [rock-record guide](../salt_dilution/data/records/README.md#rock-observations) for the full column groups, source history, timing assumptions and apparatus-distance limits.

## Preserved October 12 transcription

The broader local staging bundle at `salt_dilution/data/processed/field_notes/2026-10-12/` retains the original handwritten transcription, source pages, raw tokens and review issues. It is not an additional input requirement for the maintained calibration runner.

| Location | Contents |
| --- | --- |
| Bundle root | Sessions, source PDFs/hashes, page coverage, field observations, review issues, schema and manifest. |
| `discharge/` | Releases, stock stages, calibration attempts/points, instrument assignments, recording links and cross-sections. |
| `sediment/` | Original rock observations before later category/time/duration conventions. |
| `seismic/` | Controlled hammer-strike records. |

The local bundle's `README.md` and `table_schema.json` define its full schema. These tables use stable text IDs and ISO field dates. Stocks can reference a parent stock/aliquot; points reference a preparation; candidate file links reference existing recordings instead of duplicating their readings. Shared session IDs provide grouping, not a confirmed event match or proof of constant flow.

Staging preserves raw values alongside numeric fields. Unknown values remain empty; written zero, written “nothing” and unreadable values stay distinct. Crossed-out rows remain evidence and are excluded from derived quantities. `addition_semantics` is cumulative, incremental or unknown; missing increments interrupt derived totals. The October 4 round-2 sequence `0, 2, 6, 6, 6, 6, 6, 6, 4, 4` totals 46 mL. Written vessel disagreements remain review issues. Stock fields distinguish grams of salt, starting-water volume, starting-water mass, parent aliquots and measured final volume; no mass-to-volume conversion is assumed.

The staging-only calibration-file screen compared same-date/equal-length `Conductivity` tables with absolute tolerance 0.005 in stored units and no unit conversion. Full agreement required all points; partial comparisons retained their counts. This was reconciliation evidence, not a verified identity, universal matching tolerance or accepted calibration.

Cross-section records retain written feet and original/corrected series. Their velocity records are incomplete for an independent velocity-area calculation; instrument-reported totals remain supporting observations in cfs. Hammer records retain strike order, source times and distances; undated transects stay undated. Radio tests, rock characterization and local depth/velocity notes remain separate supporting observations. Air-quality records are outside this dataset.

## Loading and reviewing records

Load relational tables directly with pandas; `read_data()` reads instrument exports and legacy calibration formats, not these curated tables.

```python
from pathlib import Path
import pandas as pd

records = Path("salt_dilution/data/records")
points = pd.read_csv(records / "calibration_points.csv")
preparations = pd.read_csv(records / "calibrations.csv")
inputs = points.merge(preparations, on="calibration_id", validate="many_to_one")
```

Do not concatenate calibration points, releases, rock tests and logger time-series rows: they represent different measurements. Review source units, preparation stages, additions, device/channel, delivered quantity and clocks before using an association for Q. The staging bundle remains `unreviewed`/`analysis_ready=false`; structural checks do not verify every handwritten digit. Corrections retain the original token and reviewer evidence. Derived fits and eventual discharge estimates belong in results, separate from observations.
