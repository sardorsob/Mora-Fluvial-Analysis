# Curated salt records

These four local CSVs implement the compact salt-data schema agreed October 13. They were populated October 14 from the saved [October 12 notebook transcription](../processed/field_notes/2026-10-12/README.md), with targeted checks against the original scans. The [schema guide](../../../docs/field_data_schema.md) describes their columns and joins.

| File | Records | One row represents |
| --- | ---: | --- |
| `trials.csv` | 38 | One physical salt release: 32 Nisqually and six Paradise releases |
| `calibrations.csv` | 43 | One preparation/attempt, including restarts and unresolved supporting calibrations |
| `calibration_points.csv` | 262 | One recorded conductivity observation, including uncertain readings |
| `trial_inputs.csv` | 42 | One candidate association or an explicit placeholder awaiting a recording |

The association table has **eight recording candidates across seven files** and **34 rows with unresolved recording paths**. Every release is represented. A populated path is a candidate for review, not approval to use that recording or calibration in a calculation. Multiple rows can represent separate files, repeated calibrations, or successive releases in one recording.

## What the blanks mean

Unknown and inapplicable values stay empty. All review-status fields are `needs_review`; the trial table's review details live in `provenance.json` because its agreed header has no status column. No association is discharge-ready.

- UTC dump times and windows await reconciliation of notebook and instrument clocks. Original local times and written zone labels remain in provenance.
- A reported or nominal salt mass is not proof of delivered mass. Read each trial's `quantity_basis` before using it in a calculation. The spilled September solution has no accepted delivered-volume value.
- Starting water and final stock-solution volume remain distinct. No final stock volumes were established from these notes, and grams of water have not been converted to milliliters.
- `mass_based` does not identify the physical delivery form. The Paradise page explicitly describes dissolved salt, so those releases are `solution`; later ambiguous delivery forms remain blank.
- A missing calibration procedure, probe, conductivity basis, or channel value is unresolved. Numeric column names do not establish that abbreviated source units were verified.
- `trial_inputs.csv` rows without a dataset are placeholders preserving notebook trial/calibration associations. Rows with a dataset still need accepted windows and calibration applicability. Known cross-probe pairings are withheld from the applicable-calibration field and documented as notebook candidates in provenance.

The original 226 date-only recording candidates remain unselected in staging. No nearest-date calibration was assigned. The July 24 legacy configuration is useful lineage evidence, but its background interval extends beyond the written dump time and has not been adopted.

## Identity and provenance

`NISQ-YYYYMMDD-T01` and `PAR-YYYYMMDD-T01` identify separate physical releases. A dry and solution release in one field round have different IDs. Sequence follows known local clock order; the Paradise releases without exact times retain source block/row order, with chronology flagged for review. Preserve assigned IDs when new evidence is added rather than renumbering existing records.

Calibration IDs use the corresponding `C01` pattern in source order; their sequence does not assert clock order. Four supporting calibration sessions have an empty study-site alias and provisional `UNK` IDs. Their original bench, Edith or unlabelled source sites remain in provenance; they have not been relabelled as Nisqually or Paradise. One abandoned extra-dilution attempt remains flagged in provenance and must not be treated as an accepted direct-stock preparation.

`step_no` starts at zero and follows the original source-row position. Gaps preserve excluded rows. Written pipette additions remain incremental, cumulative or unconfirmed; no calculated concentration or fitted K is stored in these tables. The unequal October 4 additions are preserved as written and total 46 mL.

Three recording identities reuse historical `inventory.csv` IDs after every timestamp and both conductivity channels matched the existing examples. Four additional identities were assigned from source-file checksums and frozen in the provenance registry. The same dataset ID always references one processed file; unchanged historical examples and their inventory remain available.

Companion files, versioned with the CSVs:

- `provenance.json`: stable old-to-new ID maps, original transcription rows and raw tokens, stock stages, source page/block references, probe aliases, electronic source identities, quantity bases, excluded records, notebook calibration candidates and open checks. It retains device mappings and original workstation source paths as evidence; the CSVs use repository-relative processed paths.
- `manifest.json`: exact CSV headers, counts and checksums, input hashes and procedure-profile hash.
- `validation_report.json`: structural checks and review limits. Successful checks do not validate handwriting or scientific assumptions.

Tahoma remains in the full transcription but is outside this NISQ/PAR subset. The crossed-out empty calibration template and rows without conductivity observations are also retained in provenance/staging rather than promoted as measurements. Sediment, seismic and cross-section data remain in the broader transcription bundle.

## Using the tables

Read these CSVs as separate relational tables. Join points to preparations by `calibration_id`, then use reviewed `trial_inputs.csv` rows to associate release quantities with an appropriate recording, probe, channel and calibration. `processed_path` is relative to the project root. Do not concatenate calibration points with stream time-series rows or treat placeholders as selected inputs.

Before the first calculation, resolve one complete release/calibration/probe combination, the stock or secondary-dilution quantities, delivered input, conductivity basis, units, UTC conversion, background and full tail. Calibration fitting and discharge processing are still separate implementation work. No new K factor, concentration or discharge was calculated while populating these records.

The four CSVs, their provenance, manifest, validation report and this README are versioned together at the user's direction. Large generated stream tables and metadata remain ignored under `processed/`. Original scans, the October 12 bundle, raw exports, historical inventory and scientific scripts are preserved. Source-document and older staging links require the local source files; the compact records and their retained transcription evidence are available in this folder.
