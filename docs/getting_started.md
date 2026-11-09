# Getting started

Run commands from the repository root. Use an approved Python environment; the root requirements target Python 3.12, while saved runs record the versions actually used. The package lists are unpinned.

## Install dependencies

Where virtual environments are permitted:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r salt_dilution/requirements.txt openpyxl xlrd
```

On Windows, activate with `.venv\Scripts\activate`. This installs the salt and notebook dependencies, including readers for XLSX and legacy XLS files. For the broader seismic, statistical and geospatial stack, use `python -m pip install -r requirements.txt`. On managed systems, follow the approved installation method.

## Fit calibration curves

The runner uses the tracked preparation and point tables; stream recordings are not required.

```sh
python -m salt_dilution.scripts.processing.calibration --basis both --output salt_dilution/results/new_calibration_run
```

Choose a new output directory. `--basis` accepts `specific`, `actual` or `both` and defaults to `specific`. Outputs include coefficients, derived points, skipped series, figures and a run record. Read [calibration](calibration.md) to interpret them; they are provisional fits, not discharge estimates.

## Read instrument files

Inspect a supported file without writing outputs:

```sh
python -m salt_dilution.scripts.parsers.parse_data path/to/source.html
```

Process a folder into a new directory:

```sh
python -m salt_dilution.scripts.parsers.parse_data salt_dilution/data/raw --recursive --output salt_dilution/data/processed/new_run
```

The parser writes CSVs, metadata and a per-file manifest. Review its errors and warnings before analysis. [Parser ingestion](parser_ingestion.md) explains supported formats, file selection, clocks and output protection.

## Pair releases, recordings and K fits

After parsing the field recordings and fitting calibration curves, run:

```sh
python -m salt_dilution.scripts.processing.matching --calibrations salt_dilution/results/calibrations/2026-10-26_probe_review --overrides salt_dilution/config/pairing_overrides.json --output salt_dilution/results/matching/new_run
```

Use a new output directory. `--records` and `--processed` select other input directories. The matcher checks saved calibration hashes, inventories local recordings and writes `recording_candidates.csv`, `calibration_candidates.csv`, `pairing_summary.csv`, `trial_associations.csv` and `run_info.json`. Read the summary first, then follow its edge IDs to the evidence and alternatives. Structured CSV cells contain JSON.

The default follows the reported field protocol: group by field date, compare written release times with Aqua TROLL acquisition sessions, and use substantial recording breaks as candidate session boundaries. Shared local clocks are an explicit matching assumption; absolute UTC and a bank name are not required for these proposals. Recording breaks are not pulse-integration windows. Distinct releases can refer to the same continuous log.

An `inferred` edge follows this protocol; a `supported` edge has explicit reviewed evidence. `selected_recording_edge_ids` and `selected_calibration_edge_ids` identify the proposed links; the full edge lists retain alternatives. `inferred_proposal` means the selected recording links have compatible K fits under the stated assumptions. `partial` can mean the recording is identified but K is missing or incompatible. None of these statuses is scientific acceptance.

The default candidate break exceeds both 60 seconds and ten median sampling intervals. A release may fall up to 120 seconds outside acquisition coverage to allow rounded field times and delayed logging. These are working association settings, not measured travel times or instrument corrections. Change them with `--session-gap-seconds`, `--session-gap-factor` and `--association-tolerance-seconds`; examine changes in the selected links. `--no-protocol-inference` restores the explicit-review-only comparison.

An existing notebook-to-file relationship can identify a recording even when the release clock is uncertain. The matcher rechecks its registered file hashes, native probe identity, date and current CSV path before using it. This does not create an exact timestamp or choose between acquisition segments within that file. Competing sessions and source contradictions remain visible. Reviewed clock corrections and known missing recording roles take precedence over the default assumptions. Multiple sites on a day prevent automatic site inference for an unlabelled recording. Both conductivity channels and mass/relative concentration fits retain their own units. Numeric trial/calibration suffixes and fit quality do not establish associations.

`trial_associations.csv` audits each current `trial_inputs.csv` row. It retains the original calibration ID and alias labels alongside source relationships, native serial evidence and review flags. Record-table probe aliases were entered as placeholders, so a missing or different alias does not reject an otherwise supported K link. A fit's alias remains part of its saved lookup key; it does not establish physical identity. Isolated missing conductivity cells retain their source-row references in `measurement_quality` and do not erase a supported pairing. A recording with no finite conductivity remains unselected. `measurement_review_required` flags gaps for later pulse/background checks; no values are filled.

The supplied [pairing evidence](../salt_dilution/config/pairing_overrides.json) records the documented July 31 continuation, session-based August 6 and September 18 proposals, and Paradise dose-sequence/site-calibration links. `pairing_evidence_bases` distinguishes these from clock-based proposals. Whole-file links retain `event_alignment_review_required`; they do not recover an exact release time or select a pulse. Folder dates corroborate acquisition dates or limit candidates when internal dates are absent. Internal timestamps take precedence, and folder disagreements remain visible. Known practice releases without downstream detection are `excluded_practice`, rather than missing usable experiments.

`identity_status` distinguishes a reproduced electronic calibration with matching native serials (`native_match`), identity carried through the reported within-trial procedure (`source_protocol_match`), and a source-linked K without independent device confirmation (`unverified`). Genuine native serial disagreements and conflicting identity evidence still block the affected link. The matcher applies no cross-device transfer factor. `identity_review_required` remains visible even when the source pairing is complete. `mass_route_eligible` describes compatible K units and a supported link, not an accepted Q calculation. All pairing outputs remain scientifically unaccepted until the later quantity, background and pulse-window checks.

`preparation_method_review_required` flags a source mass-stock label paired with a saved relative-concentration fit. Candidate rows retain the source method, selected procedure, stock stages and exact fitted units. Matching does not decide which historical interpretation is correct or refit K. Resolve this discrepancy before applying the coefficient to discharge.

The matcher compares proposals with current curated links and preserves disagreements. It leaves those links unchanged. It does not choose background or integration windows, apply K, calculate discharge or link rock trials to Q. Those are later analysis steps. Older processed files are checked against raw exports before metadata are recovered in memory; normalized files are not overwritten.

### Supply reviewed association evidence

`--overrides path/to/evidence.json` accepts `schema_version: 1` and the optional lists below. Every entry requires nonempty `evidence` and `source_ref` strings. Use dataset IDs from provenance, or the run-local `FILE-…` references in the inventory, as `content_ref`.

| List | Entry fields, in addition to evidence/source_ref |
| --- | --- |
| `recordings` | `content_ref`; optionally `site_alias`, `role`, `activity`, `clock_correction_seconds`, `clock_basis` |
| `recording_links` | `trial_id`, `content_ref`; optionally `scope: "whole_file"`, `association_basis`, `continuation_of` |
| `calibration_links` | `trial_id`, `calibration_id`, `probe_alias` |
| `trial_clocks` | `trial_id`, `utc_offset_seconds`, for a notebook local clock |
| `expected_roles` | `trial_id`, `roles` (a nonempty list of main-discharge roles) |
| `trial_dispositions` | `trial_id`, `disposition: "practice_no_detection"`, for a source-labelled practice release |

For example, a reviewed link has this shape; replace the illustrative IDs and source reference with verified records:

```json
{"schema_version": 1, "recording_links": [{"trial_id": "TRIAL_ID", "content_ref": "DATASET_ID", "evidence": "Release identified in the field record", "source_ref": "notebook-page-reference"}]}
```

A recording correction shifts its existing UTC series by the stated seconds and requires `clock_basis`; it cannot create UTC for an unresolved local series. Notebook offsets must agree within a site/day, and recording corrections within a physical device/day. Supported numeric report offsets and source timestamps with offsets are recognized automatically. Overrides cannot remove source hash or physical-device conflicts. Keep evidence for a real protocol change rather than adjusting clocks or choosing K until the answer looks plausible.

`association_basis` can be `source_documented`, `session_inferred` or `dose_sequence_inferred`. A whole-file link cannot choose between acquisition segments. `continuation_of` references an earlier piece from the same physical device and date; the pieces remain separate, with no fabricated samples across the gap. `evidence_files` is an optional top-level list of `{ "path": "...", "sha256": "..." }` pins for supporting files inside the repository. Changed or missing pinned evidence stops the run. Without `--overrides`, the matcher uses current source associations and chronology alone.

## Calculate mass-slug discharge

These commands need the local normalized recordings and source files pinned by the saved pairing bundle. A clone containing only tracked tables cannot run this batch. Changed or missing inputs stop the run; parsing into another directory does not repair a saved bundle's source references.

```sh
python -m salt_dilution.scripts.processing.calibration_reuse --output salt_dilution/results/calibration_reuse/new_reuse_test
python -m salt_dilution.scripts.processing.mass_slug --reuse salt_dilution/results/calibration_reuse/new_reuse_test --windows salt_dilution/config/pulse_windows.json --output salt_dilution/results/discharge/new_mass_slug
```

Use fresh output directories. Defaults select the reviewed calibration and pairing bundles above; `--records`, `--processed`, `--calibrations` and `--pairing` select explicit inputs. Alternate record locations must contain the same source bytes as the saved bundles. Code hashes are also pinned: rerun reuse after changing its implementation.

Without `--windows`, the mass runner proposes automatic windows. Inspect every pulse plot; a rejected automatic tail check can need manual review. Window configuration has `schema_version: 1` and a `windows` list keyed by `trial_id`, `logical_recording_id` and `channel` (`specific` or `actual`). Each usable entry supplies `pre`, `pulse` and `post` pairs of local-clock timestamps, plus `evidence`, `reviewer`, `reviewed_on` and `review_status`. `checker_proposed` requires user signoff before becoming `reviewed`; the latter requires explicit `user_signoff: true`. A `blocked` decision retains its reason and cannot produce Q. Stored pairing/source pins protect decisions against use with changed inputs.

The runner reads `salt_dilution/config/release_confirmations.json` when present, or an explicit `--confirmations` file. It applies delivered-mass confirmations only to named release IDs with matching field date/site and recorded evidence. The file and its hash are saved with the run. These confirmations supplement historical records; they do not approve windows or scientific acceptance.

The bundle contains `discharge_estimates.csv`, one `release_summary.csv` row per release, per-recording outcomes, window proposals, pulse/comparison figures and hashed `run_info.json`. The used windows file is copied into the result bundle for reproduction. Specific conductivity is primary when it computes; actual conductivity is a comparison. Neither channels nor sensors are averaged. The current runner keeps every estimate `proposed` and `scientifically_accepted=false`; applicability, mixing and windows still need review. October delivered masses are confirmed by the field participant; weighing uncertainty remains unquantified.

## Export the analysis package

After producing the saved mass, source-audit, numerical-review and reuse bundles, assemble the current handoff:

```sh
python -m salt_dilution.scripts.processing.export_discharge --output salt_dilution/results/discharge/new_analysis_bundle
```

Defaults select the current reviewed bundles documented in the [results guide](../salt_dilution/results/README.md#use-the-analysis-bundle). Use `--mass-run`, `--audit-run`, `--review-run` and `--reuse-run` for explicit versions; audit and review must reference the selected mass run. The exporter verifies source hashes, preserves original Q strings and blanks, and refuses existing output folders. It writes one table covering every release, a primary subset, exact channel estimates, settings, review evidence and copied figures. It performs no new discharge inference or field approval.

Start with `discharge_by_release.csv`; use `discharge_primary.csv` for the five proposed primary estimates and retain its flags in analysis. `analysis_limits.json` defines closure and scientific limits. `bundle_index.json` contains the exact rebuild command. The package needs the local source bundles when rebuilding; reading its tables and figures does not require the raw recordings.

## Work with seismic recordings

Supply the inputs described in the [seismic data guide](../fluvial_seismology/data/README.md), then start Jupyter:

```sh
python -m jupyterlab
```

Choose the environment's Python kernel and review each notebook's station, date and path settings. The [seismic guide](../fluvial_seismology/README.md) lists the workflows and limitations. Run formatting operations on working copies; its move/copy/rollback cells are alternatives, not a sequence to execute together.

The Python/R notebook additionally needs R, rpy2, and the R packages `eseis` and `fields`; `caTools` supports optional smoothing. These are separate from the Python requirements. The [source Conda exports](../fluvial_seismology/config/source_environments/README.md) are historical references, not verified installation recipes.

Launch package scripts from the root with `python -m ...`, such as `python -m fluvial_seismology.scripts.processing.screen_waveforms`. Authenticated acquisition reads both `MORA_IRIS_USERNAME` and `MORA_IRIS_PASSWORD`; leave both unset for public access. Existing Python figure saves use the shared path helper and `MORA_RUN_ID` or a UTC run name. Complete each run's `run_info.json` with inputs, settings and outcome; display-only plots are not automatically exported.

## Run checks

```sh
python -m unittest discover -s tests -v
```

See [validation](validation.md) for test coverage and optional local-data checks. The [historical July 24 notebook](../salt_dilution/notebooks/salt_dilution_discharge.ipynb) uses retired helpers; use the maintained scripts above for current salt work.
