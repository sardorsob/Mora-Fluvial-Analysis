# Curated salt records

These four CSVs implement the compact salt-data schema agreed October 13. They were populated October 14 from the saved [October 12 notebook transcription](../processed/field_notes/2026-10-12/README.md), then edited by the user. The October 20 reconciliation preserves those reviewed values, repairs duplicate IDs and fills confirmed recording links. The [schema guide](../../../docs/field_data_schema.md) describes their columns and joins; the [reconciliation note](../../../docs/salt_record_reconciliation_2026_10_20.md) records the changes and checks.

| File | Records | One row represents |
| --- | ---: | --- |
| `trials.csv` | 38 | One physical salt release: 32 Nisqually and six Paradise releases |
| `calibrations.csv` | 43 | One preparation/attempt, including restarts and unresolved supporting calibrations |
| `calibration_points.csv` | 262 | One recorded conductivity observation, including uncertain readings |
| `trial_inputs.csv` | 59 | One recording/calibration candidate association or an explicit placeholder awaiting a recording |

The association table has **48 linked rows across 31 files**, covering 28 releases, and **11 rows with unresolved recording paths**, covering ten releases. Every release is represented. File and measurement-probe identities are established for the populated paths; calibration applicability and integration windows still require review. Multiple rows can represent paired probes, repeated calibration attempts, split logs, or successive releases in one recording. July 17 retains two notebook calibration candidates for the same RL recording; those are alternatives, not two observations to count twice.

## What the blanks mean

Unknown and inapplicable values stay empty. All review-status fields are `needs_review`; the trial table's review details live in `provenance.json` because its agreed header has no status column. No association is discharge-ready.

- UTC dump times and windows await reconciliation of notebook and instrument clocks. Original local times and written zone labels remain in provenance.
- A reported or nominal salt mass is not proof of delivered mass. Read each trial's `quantity_basis` before using it in a calculation. The spilled September solution has no accepted delivered-volume value.
- Starting water and final stock-solution volume remain distinct. No final stock volumes were established from these notes, and grams of water have not been converted to milliliters. Final volume is optional: the user-confirmed working mass-stock calculation uses recorded preparation-water volume when no measured final volume exists, and records that basis in its results.
- `mass_based` does not identify the physical delivery form. The user's later delivery-form and nominal-quantity edits are preserved; original uncertainty remains in provenance and does not establish delivered mass.
- A missing calibration procedure, probe, conductivity basis, or channel value is unresolved. Numeric column names do not establish that abbreviated source units were verified.
- `trial_inputs.csv` rows without a dataset are placeholders preserving notebook trial/calibration associations. Rows with a dataset still need accepted event windows. Under the October 20 shared-probe clarification, a different probe number alone does not withhold the notebook calibration link; aliases remain in provenance and the conductivity channel must match.

The original 226 date-only recording candidates remain unselected in staging. The October 19 inventory's 363 screening pairs are also proposals, not input selections. Accepted file identities use source blocks, event-clock context, measured serials and bank/mixing evidence; no nearest-date calibration was assigned. The July 24 legacy configuration is useful lineage evidence, but its background interval extends beyond the written dump time and has not been adopted.

The unresolved files concern July 3, 2025 (two releases without downstream detection), August 6, 2026 (the paired logs start after the NISQ release and their peaks align with the separately recorded Tahoma release), September 1, 2026 (six Paradise releases without individual clocks or confirmed exports), and September 18, 2026 (stream-event versus other live-activity identity unresolved). Their empty paths should not be filled from date matching alone.

## Identity and provenance

`NISQ-YYYYMMDD-T01` and `PAR-YYYYMMDD-T01` identify separate physical releases. A dry and solution release in one field round have different IDs. Initial assignment used known clocks followed by unresolved source blocks; IDs do not guarantee chronological order. October 2 T01 is later than T02, and October 4 T03 is later than T04. Preserve assigned IDs and use source blocks and literal clocks when new evidence is added.

Calibration IDs use the corresponding `C01` pattern; their sequence does not assert clock order. The user's PAR assignments for four supporting preparations are preserved. Their colliding IDs were changed by source block to `PAR-20260903-C06` through `C09`, keeping the original PAR C01-C05 preparations. All 16 point-parent references were repaired together. Historical UNK aliases and the original bench, Edith or unlabelled source descriptions remain in provenance; the ID repair does not independently validate site assignments. One abandoned extra-dilution attempt remains flagged and must not be treated as an accepted direct-stock preparation.

`step_no` starts at zero and follows the original source-row position. Gaps preserve excluded rows. Written pipette additions remain incremental, cumulative or unconfirmed; no calculated concentration or fitted K is stored in these tables. The unequal October 4 additions are preserved as written and total 46 mL.

Three recording identities reuse historical `inventory.csv` IDs after every timestamp and both conductivity channels matched the existing examples. The other 28 identities use source-file checksums. All seven pre-existing dataset IDs and eight populated links are retained. The same dataset ID always references one processed file; repeated use across different releases is intentional. Original electronic exports are preferred over overlapping spreadsheet slices. The August 8 mixing CSV has the same EC observations as its original live HTML but floors timestamps to whole minutes; the original HTML-derived output is linked.

The October 20 shared-probe update restores 23 notebook-supported calibration IDs and changes 31 channel selections to match existing actual-conductivity calibration observations. The table now has 16 `specific`, 32 `actual` and 11 blank channel selections; ten calibration IDs remain blank. No conductivity measurements were copied or converted. Probe aliases remain available for QA. All 46 linked rows with calibration IDs have a provisional fit on the selected channel; the two other linked rows lack a notebook calibration. These selections do not approve event windows or discharge.

Companion files, versioned with the CSVs:

- `provenance.json`: current source-block ID maps, historical aliases, unchanged original transcription rows/raw tokens/stock stages, reviewed current trial/preparation values, source references, probe and electronic-file identities, quantity bases, excluded records and per-link field status/open checks. Historical `review_issues` and `missing_required_fields` describe the original transcription; current CSV values and the dated review overlay describe the reviewed revision.
- `manifest.json`: exact CSV headers, counts and checksums, input hashes and procedure-profile hash.
- `validation_report.json`: structural checks and review limits. Successful checks do not validate handwriting or scientific assumptions.

Tahoma remains in the full transcription but is outside this NISQ/PAR subset. The crossed-out empty calibration template and rows without conductivity observations are also retained in provenance/staging rather than promoted as measurements. Sediment, seismic and cross-section data remain in the broader transcription bundle.

## Using the tables

Read these CSVs as separate relational tables. Join points to preparations by `calibration_id`, then use reviewed `trial_inputs.csv` rows to associate release quantities with an appropriate recording, probe, channel and calibration. `processed_path` is relative to the project root. Do not concatenate calibration points with stream time-series rows or treat placeholders as selected inputs.

The [calibration runner](../../../docs/calibration.md) now calculates provisional K factors and derived calibration concentrations without modifying these observations or waiting for stream windows. Before a discharge calculation, resolve the release/calibration/channel combination, delivered input, units, clock alignment, background and full tail. Discharge processing remains unimplemented; the [saved run](../../results/2026-10-20_calibration/README.md) contains calibration results only.

The user's dates are retained as `M/D/YYYY`; parse them explicitly with `%m/%d/%Y` when comparing to ISO logger dates. All UTC fields remain blank. July 21 metadata explicitly names Pacific Daylight Time, but the notebook/event alignment and integration segment are still unresolved. October HTML export-creation offsets do not establish measurement-clock offsets. File bounds in provenance are not integration windows. Use `procedure_id` to choose preparation stages: populated secondary-dilution fields must not introduce an extra dilution into a direct-stock method.

Run `python -m unittest discover -s tests -v` for clone-safe table and parser checks. Set `MORA_CHECK_LOCAL_RECORDINGS=1` to additionally verify the ignored local source/output/metadata hashes, measured probe serials, channels and row counts. Local processing is required before that opt-in check can pass.

The four CSVs, their provenance, manifest, validation report and this README are versioned together at the user's direction. Large generated stream tables and metadata remain ignored under `processed/`. Original scans, the October 12 bundle, raw exports, historical inventory and scientific scripts are preserved. Source-document and older staging links require the local source files; the compact records and their retained transcription evidence are available in this folder.
