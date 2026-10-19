# Curated salt records

These four CSVs implement the compact salt-data schema agreed October 13. They were populated October 14 from the saved [October 12 notebook transcription](../processed/field_notes/2026-10-12/README.md), with targeted checks against the original scans. The [schema guide](../../../docs/field_data_schema.md) describes their columns and joins.

| File | Records | One row represents |
| --- | ---: | --- |
| `trials.csv` | 38 | One physical salt release: 32 Nisqually and six Paradise releases |
| `calibrations.csv` | 43 | One preparation/attempt, including restarts and unresolved supporting calibrations |
| `calibration_points.csv` | 262 | One recorded conductivity observation, including uncertain readings |
| `trial_inputs.csv` | 42 | One candidate association or an explicit placeholder awaiting a recording |

The association table has **eight recording candidates across seven files** and **34 rows with unresolved recording paths**. Every release is represented. A populated path is a candidate for review, not approval to use that recording or calibration in a calculation. Multiple rows can represent separate files, repeated calibrations, or successive releases in one recording.

## October 19: explicit protocol-setting inheritance

Missing protocol settings now carry forward within the applicable experimental sequence under the user-directed continuity assumption: settings remain unchanged until a recorded change or exception. Explicit values always take precedence. The four table headers, IDs, row order and row counts are unchanged.

This manual update fills **79 cells**: 17 nominal release masses and 62 calibration-setting fields, affecting 17 trial rows and 17 calibration rows. Nisqually salt-mass coverage increases from 13/32 to 30/32 releases. Calibration procedure coverage increases from 16/43 to 29/43 attempts. These are resolved assumptions, not additional measurements.

[inheritance.json](inheritance.json) centralizes each applied recipe/dose rule, its original source record and page reference, exact target IDs, inherited fields and values, and limitations. Each group expands to one provenance entry per target and field. The target lists are deliberately finite; this is not an automatic rule for future records or a blind date-only fill.

The applications distinguish the concurrent 2025 dry and solution-secondary workflows. The October 4-5 direct-stock calibrations inherit the October 2 recipe (1 g salt, 1,000 mL starting river water), not the September 18 recipe (0.5 g). Existing receiving-water volumes and all handwritten additions remain unchanged. Reusing a recipe does not assert that the same physical stock, probe, measurements or fitted K were reused.

`provenance.json` remains unchanged original transcription evidence. For exactly the cells enumerated in `inheritance.json`, read that companion as the current field-resolution overlay: an older `unknown` or no-inheritance note is the historical source state, while the CSV contains the explicitly assumed setting. Do not rewrite the original source tokens or interpret an inherited value as newly observed. The older schema/staging discussion of not inheriting recipes is superseded only for these enumerated protocol settings, not for measurements, clocks, links or scientific acceptance.

## What the remaining blanks and populated values mean

Unknown and inapplicable values stay empty unless explicitly resolved by the inheritance overlay. All review-status fields remain `needs_review`; the trial table's original review details live in `provenance.json` because its agreed header has no status column. No association is discharge-ready.

- UTC dump times and windows await reconciliation of notebook and instrument clocks. Original local times and written zone labels remain in provenance.
- A reported or inherited nominal salt mass is not proof of delivered mass. For inherited `salt_mass_g`, the quantity basis is **assumed nominal dose; delivery unverified**. The spilled September solution still has no accepted delivered-volume value.
- Starting water and final stock-solution volume remain distinct. No final stock volumes were established or inherited, and grams of water have not been converted to milliliters.
- `mass_based` does not identify the physical delivery form. The Paradise page explicitly describes dissolved salt, so those releases remain `solution`; later ambiguous delivery forms remain blank.
- Missing probe identity, conductivity basis or channel values remain unresolved. Numeric column names do not establish that abbreviated source units were verified.
- `trial_inputs.csv` rows without a dataset remain placeholders. Known cross-probe pairings remain withheld from the applicable-calibration field and documented as notebook candidates in original provenance.
- July 3 practice releases precede the first recorded dose and are not backward-filled. Paradise and unresolved-site records are unchanged.
- The abandoned September 18 extra-dilution attempt remains unchanged. October 4's incomplete-mixing and written-volume warnings remain active even where the intended recipe is inherited.

The original 226 date-only recording candidates remain unselected in staging. No nearest-date calibration was assigned. The July 24 legacy configuration remains lineage evidence; its background interval extends beyond the written dump time and has not been adopted.

## Identity and provenance

`NISQ-YYYYMMDD-T01` and `PAR-YYYYMMDD-T01` identify separate physical releases. A dry and solution release in one field round have different IDs. Existing IDs are preserved; source ordering and chronology caveats remain in provenance rather than being resolved by the ID suffix.

Calibration IDs use the corresponding `C01` pattern in source order, not necessarily clock order. Four supporting calibration sessions retain empty study-site aliases and provisional `UNK` IDs. Bench, Edith and unlabelled source sites have not been relabelled as study sites. The abandoned extra-dilution attempt must not be treated as an accepted direct-stock preparation.

`step_no` preserves source-row position and gaps. Pipette additions remain incremental, cumulative or unconfirmed; no calculated concentration or fitted K is stored. The unequal October 4 additions remain unchanged and total 46 mL.

Three recording identities reuse historical `inventory.csv` IDs after the original full-series comparisons. Four additional identities remain frozen in the provenance registry. The same dataset ID references one processed file; historical examples and their inventory are unchanged.

Companion files are versioned with the CSVs:

- `provenance.json`: unchanged original transcription rows/tokens, stock stages, page/block references, probe and dataset identities, exclusions and scientific warnings.
- `inheritance.json`: applied protocol-setting assumptions and exact source-to-target field lineage; use alongside, not instead of, original provenance.
- `manifest.json`: current CSV headers, counts and checksums, original input hashes, procedure-profile hash and inheritance checksum.
- `validation_report.json`: current inheritance-table checks plus the preserved previous validation report. Structural success does not validate field assumptions or discharge.

Tahoma remains in the full transcription outside this subset. Crossed-out empty templates and rows without conductivity observations remain in provenance/staging, not promoted as measurements. Sediment, seismic and cross-section data remain in the broader transcription bundle.

## Using the tables

Join points to preparations by `calibration_id`, then use reviewed `trial_inputs.csv` rows to associate releases with recordings, probes, channels and calibrations. `processed_path` is relative to the project root. Do not concatenate calibration points with stream readings or treat placeholders as selected inputs.

The CSVs display the inherited settings directly; consumers must also retain their assumption status from `inheritance.json`. Before a discharge calculation, resolve a complete release/calibration/probe combination, applicable quantities, units, clocks, background, complete tracer response and field QA. Retain or test inherited settings as explicit analysis assumptions. No K, concentration, discharge or scientific acceptance was produced by this update.

Large generated stream tables and metadata remain ignored under `processed/`. Original source evidence, raw exports, historical inventory and scientific scripts are preserved. Original scans and the older staging bundle require local source files and were not newly inspected during the inheritance update.
