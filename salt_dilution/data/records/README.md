# Curated salt records

Four UTF-8 CSVs connect notebook preparations and conductivity observations to physical releases and candidate instrument recordings. Use them for calibration fitting and for reviewing the inputs to a future discharge calculation. The [schema guide](../../../docs/field_data_schema.md) defines their headers and joins.

| File | Records | One row represents |
| --- | ---: | --- |
| `trials.csv` | 38 | One physical release: 32 Nisqually and six Paradise releases |
| `calibrations.csv` | 43 | One preparation/attempt, including restarts and supporting calibrations |
| `calibration_points.csv` | 262 | One recorded conductivity observation, including uncertain readings |
| `trial_inputs.csv` | 59 | One candidate recording/calibration association or unresolved placeholder |

The association table has **48 linked rows across 31 files for 28 releases**, plus **11 rows with unresolved recording paths for ten releases**. Every release is represented. Multiple rows can describe paired probes, split logs, successive releases in one recording or alternative calibration attempts. July 17 has two calibration candidates for the same RL recording; they are alternatives, not two stream observations.

All salt-table review-status fields remain `needs_review`; trial review details are in provenance because `trials.csv` has no status column. All UTC event and integration-window fields are blank. No association is discharge-ready.

## What the blanks mean

Unknown and inapplicable values stay empty; a blank is never a substituted zero.

- **Clocks and windows:** local times and written zone labels remain in provenance. A file's start/end bounds are not integration limits. July 21 names Pacific Daylight Time, but event alignment is still unresolved; October export-creation offsets do not establish measurement-clock offsets.
- **Delivered quantity:** nominal salt mass or prepared volume does not prove delivery. Check each trial's `quantity_basis`; the spilled September solution has no accepted delivered-volume value. `mass_based` describes a calculation, not dry versus solution delivery.
- **Stock volume:** no measured final stock volumes were established from the notes. The working mass-stock method uses recorded preparation-water volume when measured final volume is absent and saves that basis in results. It does not fill `stock_solution_final_ml` or convert grams of water to milliliters.
- **Preparation and channel:** missing procedure, probe or conductivity values remain unresolved. Numeric column names do not verify abbreviated handwritten units. Select preparation stages by `procedure_id`; a populated secondary-water field must not add an extra dilution to a direct-stock recipe.
- **Association:** a blank path preserves a notebook association awaiting a recording. A populated path identifies a file and measured probe, but does not accept its calibration applicability or integration window.

The unresolved recordings concern July 3, 2025 (two releases without downstream detection), August 6, 2026 (the logs start after the NISQ release and their peaks align with a separately recorded Tahoma release), September 1, 2026 (six Paradise releases without individual clocks or confirmed exports), and September 18, 2026 (stream-event versus other activity unresolved). Date matching alone cannot fill these paths. The 226 original date-only candidates and 363 later screening pairs remain proposals in local staging.

## Instrument and addition review

The main discharge/calibration work uses Aqua TROLLs. General DCT430SD meters served farther-downstream attenuation monitoring. Within a supported physical trial/role, an identified Aqua TROLL can carry through its associated calibration; paired roles remain separate. Current provenance distinguishes same-instrument, unresolved-instrument and different-probe applicability. Earlier permission to share a calibration across numbered probes is not automatic transfer acceptance. See the [instrument catalog](../../../docs/salt_dilution_instruments.md).

The [October 26 review](../../results/calibrations/2026-10-26_probe_review/README.md) resolved 13 preparation identities, filling 100 point aliases, while preserving observed quantities, preparation edits and recording links. Nineteen preparation identities remain unresolved, including 12 fitted series. Evidence and source hashes are in `provenance.json` under `calibration_record_audit` and each preparation's `probe_identity_review`.

All 43 addition blocks were reviewed: 34 have supporting vessel-volume progression, five lack enough evidence, two have unconfirmed water changes, one is abandoned and one retains a conflicting written vessel volume. No addition labels or observed values were changed. The September 18 restart totals 26 mL; October 4 C02 uses unequal increments totaling 46 mL. Original PDFs are unavailable at their recorded Downloads paths, so the review uses retained transcription tokens and electronic exports rather than fresh handwriting verification.

## Identity and provenance

`NISQ-YYYYMMDD-T01` and `PAR-YYYYMMDD-T01` identify physical releases. Dry and solution releases in one round have different IDs. Assigned sequences are stable identifiers, not chronological ordering: October 2 T01 is later than T02, and October 4 T03 is later than T04. Use literal clocks and source blocks for ordering.

Calibration IDs use the corresponding `C01` pattern. Four supporting preparations now have distinct `PAR-20260903-C06`–`C09` IDs, with their historical UNK aliases and bench/Edith/unlabelled descriptions retained. PAR C01–C05 are separate preparations. The [reconciliation record](../../../docs/salt_record_reconciliation_2026_10_20.md) documents the source-block repair and 16 repaired point-parent references; it does not independently verify site assignments.

`step_no` starts at zero and follows source-row position, including gaps. Written additions remain `incremental`, `cumulative` or `unconfirmed`. Uncertain readings keep blank numeric cells and original tokens in provenance. No fitted K or derived concentration is stored in the observation CSVs; an abandoned extra-dilution attempt remains flagged.

Three recording identities reuse historical `inventory.csv` IDs after all timestamps and both conductivity channels matched the examples; the other 28 use source checksums. A dataset ID references one processed file, which may serve several releases. Prefer original electronic exports over overlapping spreadsheet slices. August 8's mixing CSV floors timestamps to whole minutes; its original live HTML retains seconds and is linked instead.

The current inputs select 16 specific and 32 actual conductivity routes, with 11 blank channel selections and ten blank calibration IDs. All 46 linked rows with calibration IDs have a provisional fit on their selected channel; two linked rows lack a notebook calibration. No channel values were copied or converted to obtain these associations.

Companion files are versioned with the CSVs:

- `provenance.json`: source blocks, historical aliases, transcription/raw tokens, preparation stages, probe/file identities, quantity bases and per-link open checks. Older `review_issues`, `missing_required_fields` and general-rule statements are transcription snapshots; use the current CSVs, finite manifest overrides and later review overlays for the current calculation inputs and policy.
- `manifest.json`: exact headers, counts, checksums, input hashes, procedure-profile hash and enumerated reviewed-setting overrides.
- `validation_report.json`: structural checks and scientific-review limits. Passing these checks does not verify every handwritten digit.

Tahoma, controlled seismic-source and cross-section observations remain in the broader local [transcription bundle](../processed/field_notes/README.md). The rock observations also have the separate CSV described below. Empty/crossed-out templates and rows without conductivity observations remain in staging/provenance rather than becoming measurements.

## Rock observations

[sediment/rock_observations.csv](sediment/rock_observations.csv) contains 331 tethered-rock observations from September 18 and October 2, 4 and 5, 2026. It is separate from the four salt-calibration tables. Each row is one recorded test or qualitative observation.

`rock_category` is the single rock classification and size-label field, replacing the former numbered `rock_number`. Use this exact category order in tables and plots, not alphabetical order:

```text
38.5mm
54.5mm
D50
79mm
119mm
```

The previous ranks 1 through 5 map to these categories in the listed order. The user confirmed the four numeric category measurements and requested the short label `D50`. No numeric D50 measurement was supplied: do not interpret it as 50 mm or zero. Category names do not establish the same physical specimen across dates.

At the user's request, `rock_label_source`, `rock_label_raw`, and `rock_size_mm` have been removed from the observation CSV. Use `rock_category` for rock grouping and size labels. The removed fields remain available in Git history at commit `c2c4148903b7ffaaffc2f779baa01c25aecbff91`. All 331 observations, their IDs, row order, categories, times, distances, durations, source references, notes and review states are unchanged by the column removal. The table now has 21 columns.

The September 18 entries originally labelled `79` and `119` map to `79mm` and `119mm`. The remaining relative description, `one_size_less_than_79_before119`, stays unassigned because its precise category is not established by the saved row context. Its observation ID and source reference are retained. This leaves 330 categorized observations and one unresolved category; do not infer D50 for that row solely from the relative wording.

`trial_block` preserves the source grouping; it is not a salt-release ID. `repeat_no=2` separates the repeated October 4 round-2 block. The two round-4 blocks remain distinct; `left`/`right` identify source-page blocks, not confirmed river banks. `test_number` counts observations within each session/block/repeat/rock series in source order, including continuation across pages. Most series have five tests; longer, shorter and lost-rock series are retained without padding or splitting them by an assumed five-test rule. Code that previously grouped by `rock_number` should now group by `rock_category` and explicitly use the category order above; CSV does not store an ordered categorical type.

Raw times, durations, distance tokens, zeros and notes are preserved. Seven written “nothing” entries remain distinct from 84 numeric zeros; ten distances are unresolved. `apparatus_distance_m` retains the provisional tether/reel measurement definition, not free-particle travel or velocity. UTC and discharge links remain blank, and observations remain `unreviewed`.

The source is the retained October 12 [rock transcription](../processed/field_notes/2026-10-12/sediment/rock_observations.csv), SHA-256 `173ad501878803885cb8cbbfe2f701b1af07ea6dbe501b7bfef1989a49b39216`. Original observation IDs are retained; `sourcebook_reference` identifies the scan, page, side and source row. The export uses that transcription rather than a fresh handwriting check: the original scan is unavailable at its recorded Downloads path. Category assignments are based on the user's later explicit clarifications, not a new reading of the scans. The numbered version remains in Git history at commit `83f4c191777f732236e663f9db99b07b723a85b7`.

## Using the tables

Join points to preparations by `calibration_id` with a many-to-one check. The [calibration runner](../../../docs/calibration.md) calculates provisional K and derived concentrations without requiring `trial_inputs.csv` or stream windows. For discharge work, review each input association, delivered quantity, units, device/channel, clock alignment and full background/rise/tail. Do not concatenate calibration points with stream time-series rows or count alternative links twice.

`processed_path` is relative to the repository root. Compact field dates retain `M/D/YYYY`; parse with `%m/%d/%Y` when comparing with ISO logger dates. Large processed readings and the older staging bundle are local and ignored; the compact tables and retained transcription evidence are tracked here.

Run `python -m unittest discover -s tests -v` for table/parser checks. Set `MORA_CHECK_LOCAL_RECORDINGS=1` to also verify local source/output/metadata hashes, measured sensor serials, channels and row counts. That opt-in check needs the referenced files on disk. See [validation](../../../docs/validation.md) for its limits.
