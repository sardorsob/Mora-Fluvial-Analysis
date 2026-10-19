# Curated salt records

These four CSVs implement the compact salt-data schema agreed October 13. They were populated October 14 from the saved [October 12 notebook transcription](../processed/field_notes/2026-10-12/README.md), with targeted checks against the original scans. The [schema guide](../../../docs/field_data_schema.md) describes their columns and joins; its original population discussion predates the inheritance resolutions below.

| File | Records | One row represents |
| --- | ---: | --- |
| `trials.csv` | 38 | One physical salt release: 32 Nisqually and six Paradise releases |
| `calibrations.csv` | 43 | One preparation/attempt, including restarts and unresolved supporting calibrations |
| `calibration_points.csv` | 262 | One recorded conductivity observation, including uncertain readings |
| `trial_inputs.csv` | 42 | One candidate association or an explicit placeholder awaiting a recording |

The association table retains eight recording candidates across seven files and 34 rows with unresolved recording paths. Every release is represented. A populated path remains a candidate, not scientific approval. Multiple rows can represent separate files, repeated calibrations, or successive releases in one recording.

## October 19: expanded protocol-setting inheritance

The CSVs contain the resolved settings directly. Under the user-directed interpretation, unreported settings can inherit the applicable delivery/method period or a documented calibration-series recipe until a recorded change or exception. Explicit observations always take precedence. Dates alone do not determine an unrelated trial, probe, fit or recording association.

The first pass in commit `d1f7a015ca80d55fcbdac931076d4dc802c47a92` filled 79 cells: 17 nominal release masses and 62 calibration settings. The second pass adds 44 cells: 10 injection forms, nine calibration procedures, nine stock-water sources, seven stock salt masses and nine nominal starting-stock-water volumes. Across both passes, 123 cells are resolved assumptions, not new measurements. All table headers, IDs, row order and row counts remain unchanged.

| Field | After first pass | After second pass |
| --- | ---: | ---: |
| Trial injection form | 26/38 | 36/38 |
| Trial salt mass | 36/38 | 36/38 |
| Calibration procedure | 29/43 | 38/43 |
| Calibration stock-water source | 30/43 | 39/43 |
| Calibration stock salt mass | 21/43 | 28/43 |
| Calibration starting-stock-water volume | 19/43 | 28/43 |

Nisqually salt mass remains populated for 30/32 releases; all six Paradise release masses remain as recorded. The two July 3 practice releases predate the first supported dose/delivery regime and remain unresolved.

### What was extended

- **Physical delivery:** ten Nisqually releases from September 18 through October 5, 2026 inherit `solution` from the documented 2026 dissolved-slug sequence. A change to mass-based discharge calculation is not itself a change to dry physical delivery. The 2025 dry releases remain dry.
- **Early dry-calibration method:** the two July 17, 2025 attempts are classified as `mass_stock_river` with river stock water within the matching 2025 dry-stock method period. Their 2 g salt and 1000 mL starting water were already recorded. This is explicitly a retrospective period assumption corroborated by July 31, not a claim that the July 17 H2O label specified river water. Their distinct 2000/3000 mL receiving volumes are preserved.
- **September standard series:** seven continuation calibrations on September 3, 2026 inherit `mass_stock_deionized`, deionized stock water and 2.5 g stock salt from the standard described on source C page 6. This applies to the documented pages 6-8 calibration series, not every same-day field site. Site aliases, receiving-water identity, probes and fitted factors are not shared by this rule.
- **Nominal stock-water recipe:** the same nine standard-series rows use 500 mL nominal starting water, resolved from the retained note's separate 0.5 L wording. The original 500 g notation remains in provenance. This is not a density conversion and not a measured final stock-solution volume.

The earlier applications still separate concurrent 2025 dry and solution-secondary workflows. October 4-5 direct-stock calibrations retain the October 2 recipe (1 g salt, 1000 mL starting river water), not September 18's 0.5 g recipe. Reusing a recipe never establishes reuse of physical stock, measurements or fitted K.

## Provenance and remaining unknowns

[inheritance.json](inheritance.json) records each rule, pre-edit source commit, original source record/page, finite target list, resolved fields, evidence and assumption basis. It supersedes historical unknown/no-inheritance annotations only for the enumerated cells. `provenance.json` remains unchanged original transcription evidence, including raw tokens, stock stages, source positions, quantity bases, exclusions and scientific warnings.

All calibration review states remain `needs_review`; trial review details remain in provenance. No association is discharge-ready. An inherited nominal salt mass is not verified delivered mass. Stock solvent is not automatically the receiving water. Initial water is not final solution volume. A smooth or complete table does not establish mixing or tracer recovery.

Four July 9 exploratory calibrations still lack a classified preparation and stock-water source. The abandoned September 18 extra-dilution attempt remains distinct and is not flattened into a direct-stock profile. All final stock volumes, delivered-volume gaps, receiving-water quantities and their mass/volume conflicts remain unchanged. September 3's solution spill, October 4's incomplete mixing and written-volume warnings, unequal aliquot additions, uncertain handwriting and field QA remain active.

UTC dump times/windows still require notebook/instrument clock reconciliation. Missing probes, selected conductivity basis, recording paths and calibration applicability are not inferred from a method period. The original 226 date-only recording candidates remain unselected in staging. The July 24 legacy configuration is lineage evidence, not an adopted window; its background interval extends beyond the written dump time.

## Identity and companions

`NISQ-YYYYMMDD-T01` and `PAR-YYYYMMDD-T01` identify physical releases. Dry and solution releases in one round retain separate IDs. Calibration C-sequences identify preparations/attempts, not guaranteed clock order. Four supporting sessions retain provisional UNK IDs and empty site aliases; assigning a standard recipe does not resolve their location. Source-order and chronology caveats remain in provenance.

Point `step_no` preserves source-row positions and gaps. Written additions and conductivity observations are unchanged; no concentration or K has been inserted. The unequal October 4 additions still total 46 mL. Historical dataset identities, inventory and original source references are preserved.

Versioned companions are `provenance.json` (original evidence), `inheritance.json` (current assumptions), `manifest.json` (headers, counts and checksums), and `validation_report.json` (current checks and references to previous reports). Previous reports remain retrievable at their recorded Git commits rather than being mistaken for fresh validation. Tahoma, excluded empty/crossed-out material, and sediment/seismic/cross-section data remain in the original broader transcription or its provenance.

## Using the tables

Join points to preparations by `calibration_id`, then use reviewed `trial_inputs.csv` associations to connect releases, recordings, probes, channels and calibrations. `processed_path` is project-relative. Do not concatenate calibration points with stream readings or treat placeholders as selected inputs.

Read the assumption overlay alongside the populated CSVs. Before a discharge calculation, check applicable quantities, units, clocks, background, full tracer response and field QA, and retain inherited settings as explicit analysis assumptions. No K, concentration, discharge or scientific acceptance is produced by this update.

Large generated stream tables remain local/ignored. Raw exports, historical inventory, original transcription provenance, calibration points, associations and scientific code are unchanged. Original scans and ignored local datasets were not re-read during this update; the review used the current repository tables and retained transcription notes.
