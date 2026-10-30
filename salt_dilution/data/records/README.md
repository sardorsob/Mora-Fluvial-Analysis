# Field records

Four salt tables connect notebook measurements to instrument recordings. A separate rock table records individual tethered-rock tests. These are observation and association records; derived fits belong in results.

## Salt tables

| File | Rows | One row represents |
| --- | ---: | --- |
| `trials.csv` | 38 | One physical release: 32 Nisqually and six Paradise. |
| `calibrations.csv` | 43 | One preparation/attempt, including restarts. |
| `calibration_points.csv` | 262 | One observed conductivity reading. |
| `trial_inputs.csv` | 59 | One candidate recording/calibration association or placeholder. |

See the [schema](../../../docs/field_data_schema.md) for exact headers. Points join to preparations by `calibration_id` with a many-to-one check. The [calibration runner](../../../docs/calibration.md) uses those two tables without requiring stream windows.

The association table has 48 file-linked rows across 31 files for 28 releases, plus 11 unresolved-path rows for ten releases. Paired probes, split recordings and alternative calibrations explain repeated release/file references. July 17's two calibration candidates are alternatives for one RL recording, not two stream observations. All salt review fields remain `needs_review`; release UTC times and integration windows are blank. File links are not accepted Q inputs.

## What the blanks mean

Unknown and inapplicable values stay empty. A blank is never a substituted zero.

- **Quantity:** prepared/nominal salt is not necessarily delivered salt. Check spills, retained samples and mixing. No measured final stock volume is established; the working mass-stock convention uses recorded starting water when final volume is absent and records that basis. Grams of water are not silently converted to mL.
- **Preparation:** `procedure_id` selects the calculation stages. A populated secondary-water field does not add a dilution to a direct-stock recipe. Unclear units, missing EC and uncertain additions remain review items.
- **Time:** source clocks and zone labels are in provenance. Export times and recording bounds are not event/integration windows; July 21's explicit daylight-time label still needs event alignment.
- **Association:** a populated path identifies a file, not calibration applicability. `processed_path` is relative to the repository root. All release/recording/calibration links need their own supporting evidence.

Unresolved recordings cover July 3, 2025 (two releases without confirmed downstream detection), August 6, 2026 (logs begin after the NISQ release and may belong to a separate Tahoma event), September 1, 2026 (six Paradise releases without individual dump clocks/confirmed exports), and September 18, 2026 (stream event versus other activity unresolved). Date matching alone cannot fill these paths.

## Instrument and addition review

The main discharge work uses Aqua TROLLs; General DCT430SD meters have a separate downstream-monitoring role. An identified TROLL may carry through its supported trial/role and calibration. Preserve paired roles and actual/specific channels; same model or same date does not establish device equivalence. See the [instrument guide](../../../docs/salt_dilution_instruments.md).

The [saved review](../../results/calibrations/2026-10-26_probe_review/README.md) records supported probe fills and a block-by-block addition check without changing numerical fits. Unidentified probes, uncertain water changes and a written-volume conflict remain explicit in provenance. September 18's restart totals 26 mL; October 4 C02 uses unequal increments totaling 46 mL. Original scans were unavailable for a fresh handwriting check; the evidence is retained source tokens and electronic exports.

## Identity and provenance

Release IDs use `NISQ-YYYYMMDD-T01` or `PAR-YYYYMMDD-T01`; calibration IDs use `C01`. They are stable identifiers, not clock order: October 2 T01 follows T02, and October 4 T03 follows T04. Use source times/blocks for chronology.

Supporting preparations `PAR-20260903-C06`–`C09` retain their historical UNK aliases, source-block mappings and descriptions in `provenance.json`. `step_no` preserves source position, including gaps.

A `dataset_id` identifies one processed file, which can serve several releases. Prefer original electronic exports over overlapping spreadsheet slices. August 8's mixing CSV rounds times to minutes; the linked live HTML retains seconds. Keep the selected actual/specific channel consistent with the calibration. A matching-channel fit alone does not accept the instrument pair or event window.

| Companion file | Purpose |
| --- | --- |
| `provenance.json` | Source blocks/tokens, historical aliases, preparation stages, identities, quantity bases and open checks. |
| `manifest.json` | Headers, counts, checksums, input/profile hashes and finite reviewed-setting overrides. |
| `validation_report.json` | Structural checks and scientific-review limits. |

Older provenance values/rules are transcription snapshots. Use current CSV values plus the documented manifest overrides and later review overlays. Abandoned/crossed-out attempts remain visible; no K or derived concentration is stored in the source CSVs. Salt dates retain `M/D/YYYY`; parse with `%m/%d/%Y` when comparing with ISO dates.

## Rock observations

[sediment/rock_observations.csv](sediment/rock_observations.csv) contains 331 observations from September 18 and October 2, 4, 5, 2026. Each row is one individual test or qualitative observation.

| Purpose | Columns |
| --- | --- |
| Identity/location | `rock_observation_id`, `session_id`, `site_id`, `field_date` |
| Experiment order | `trial_block`, `repeat_no`, `rock_category`, `test_number` |
| Times | `time_raw`, `timezone_label_raw`, `utc_timestamp` |
| Duration | `release_duration_s`, `release_duration_raw` |
| Distance | `apparatus_distance_m`, `distance_raw`, `distance_state`, `distance_definition` |
| Discharge association | `matched_discharge_trial_id` |
| Evidence/review | `sourcebook_reference`, `review_status`, `notes` |

Use this category order: `38.5mm`, `54.5mm`, `D50`, `79mm`, `119mm`. The four numeric sizes are team-confirmed; D50 has no supplied numeric diameter and does not mean 50 mm. There are 330 categorized observations and one unresolved September 18 relative-size description. Preserve its original ID rather than guessing a category. Categories do not identify a permanent physical specimen across dates.

`trial_block` groups rock tests, not salt releases. `repeat_no=2` distinguishes the repeated October 4 round 2. `round_4_left`/`round_4_right` identify source-page blocks, not river banks. `test_number` follows each session/block/repeat/category series across page boundaries. Keep longer, shorter and lost-rock series as recorded; do not pad them to five tests.

The current duration is **60 seconds for every row by the stated working protocol**. `release_duration_raw` still holds original tokens, including different or unclear durations. The standardized value is not proof that every test was independently timed to exactly one minute.

Despite its name, `time_raw` now contains cleaned local `HH:MM:SS` times. The 316 populated times use `America/Los_Angeles` to produce UTC (-07:00 on these dates), including next-day UTC rollover; 15 individual times remain blank. Afternoon interpretations used the reported daytime window and sequence evidence. Source `PST` labels remain as text and must not trigger a second conversion. Minute-resolution times formatted with `:00` do not have second-level accuracy. This convention does not independently synchronize instrument clocks or establish test start/end timing.

Distances retain 84 numeric zeros, seven written “nothing” entries and ten unresolved readings. `apparatus_distance_m` is a provisional tether/reel-associated measure, not established free-particle displacement or velocity. Discharge links remain blank, and all rock observations are `unreviewed`. Review timing and reach representativeness before linking whole rounds to a discharge estimate; tests sharing one Q are not independent flow measurements.

Source: the retained October 12 [transcription](../processed/field_notes/2026-10-12/sediment/rock_observations.csv), SHA-256 `173ad501878803885cb8cbbfe2f701b1af07ea6dbe501b7bfef1989a49b39216`, followed by explicit category/time/duration clarifications. Original IDs and scan/page/side references remain. The original export at commit `83f4c191777f732236e663f9db99b07b723a85b7` and the source-label/size fields at `c2c4148903b7ffaaffc2f779baa01c25aecbff91` retain earlier values. This is not a fresh handwriting verification.

## Using the tables

Keep calibration points, release records, rock tests and high-frequency stream readings separate and join through reviewed associations. The broader local [transcription bundle](../processed/field_notes/README.md) contains Tahoma, cross-section and controlled seismic-source evidence. Its staging candidates are not accepted links.

Run `python -m unittest discover -s tests -v` for software/table checks. `MORA_CHECK_LOCAL_RECORDINGS=1` adds checks of local source/output/metadata files when present. See [validation](../../../docs/validation.md) for what those checks establish.
