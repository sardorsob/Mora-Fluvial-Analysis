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

The runner uses the preparation and point tables and the native exports and worksheet pinned by the recovery configs. Fitting uses calibration observations only.

```sh
python -m salt_dilution.scripts.processing.calibration --basis both --output salt_dilution/results/new_calibration_run
```

Choose a new output directory. `--basis` accepts `specific`, `actual` or `both` and defaults to `specific`. Outputs include provisional coefficients, derived points, skipped series, figures and a run record. The recovery configuration retains source measurements and identifies the alternate worksheet preparations used in the fits. See [calibration](calibration.md).

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
python -m salt_dilution.scripts.processing.matching \
  --calibrations salt_dilution/results/new_calibration_run \
  --overrides salt_dilution/config/pairing_overrides.json \
  --field-clock salt_dilution/config/field_clock.json \
  --output salt_dilution/results/matching/new_run
```

Use a new output directory. `--records` and `--processed` select other input directories. The matcher checks saved calibration hashes, inventories local recordings and writes `recording_candidates.csv`, `calibration_candidates.csv`, `pairing_summary.csv`, `trial_associations.csv` and `run_info.json`. Read the summary first, then follow its edge IDs to the evidence and alternatives. Structured CSV cells contain JSON.

Matching groups observations by field date, compares written release times with Aqua TROLL acquisitions and treats substantial recording breaks as candidate session boundaries. The recovery run uses the participant-confirmed fixed UTC−8 field clock year-round for Nisqually and Paradise. The matcher preserves the local timestamps, the offset encoded in the native export, and the derived UTC times for both interpretations. A recorded UTC timestamp or a reviewed trial-specific offset retains priority where supplied. Distinct releases can refer to the same continuous log and require their own pulse windows.

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

The runner also supports the original-solution-volume route described in [research methods](research_methods.md#salt-dilution-measuring-water-discharge). For recovery, use `--all-sites` to include Nisqually and Paradise and `--include-relative` to evaluate compatible relative-concentration fits. With `--allow-reported-volume`, a matching notebook and compact-record volume can support an estimate conditional on that amount entering the stream.

The recovery commands below require the local normalized recordings and other files pinned by the saved runs. Use a fresh output directory. `--records`, `--processed`, `--calibrations` and `--pairing` select inputs explicitly. Recovered pulse decisions identify their pairing run and processed sources by hash, so use the saved pairing run when replaying those decisions. For a new pairing run, review the pulse decisions against its sources before pinning them.

Use the saved calibration and pairing to replay the reviewed windows.

```sh
calibration_run=salt_dilution/results/calibrations/2026-11-10_recovery_v2
pairing_run=salt_dilution/results/matching/2026-11-10_recovery_v4
reuse_run=salt_dilution/results/calibration_reuse/2026-11-10_recovery_v2
recovery_out=$(mktemp -d)

python -m salt_dilution.scripts.processing.mass_slug \
  --calibrations "$calibration_run" --pairing "$pairing_run" --reuse "$reuse_run" \
  --windows salt_dilution/config/pulse_windows_recovery.json \
  --all-sites --include-relative --allow-reported-volume --output "$recovery_out/mass"
```

To regenerate the reuse assessment, pass the same `--calibrations` and `--pairing` to `python -m salt_dilution.scripts.processing.calibration_reuse --all-sites` with a fresh `--output`. Use that path for `--reuse` when you run the discharge calculation.

Without `--windows`, the runner proposes automatic windows. Inspect the pulse plots and blocked reasons. The windows file uses `schema_version: 1` and a `windows` list keyed by `trial_id`, `logical_recording_id` and `channel`. Supply local-clock timestamps for `pre`, `pulse` and `post`, and record the evidence, reviewer, date and review status. A `checker_proposed` window can support a proposed estimate. A `reviewed` window requires `user_signoff: true`. A `blocked` decision retains the recorded reason.

The runner reads [release confirmations](../salt_dilution/config/release_confirmations.json) by default. A confirmation applies only to its named release, field date and site. The result stores the selected estimate, comparison channels, release dispositions, recording outcomes and window choices. The selected estimate generally uses specific conductivity where a compatible fit and pulse are available. Review `estimate_support` and the quality flags for assumptions about volume, worksheet variants and capture.

## Review the saved release estimates

The review command verifies the discharge, pairing and calibration bundles and recomputes the selected integrals and discharge values. It writes release and channel reviews, window sensitivity, notebook/native comparisons, calibration diagnostics and within-placement pressure or depth diagnostics where available. Provide [conditional window evidence](../salt_dilution/config/conditional_pulse_windows.json) to calculate the separately reported observed-interval scenarios. These scenarios depend on the capture and background assumptions in the table.

Run the review with the variables from the discharge example.

```sh
python -m salt_dilution.scripts.processing.discharge_review \
  --mass-run "$recovery_out/mass" --pairing "$pairing_run" --calibrations "$calibration_run" \
  --conditional-windows salt_dilution/config/conditional_pulse_windows.json \
  --output "$recovery_out/review"
```

## Export the analysis package

Use the same recovery review bundle for `--audit-run` and `--review-run`. Both must refer to the selected discharge run, which must in turn refer to the selected reuse run. `--refresh-figures` redraws the published figures from the verified tables, windows and local recordings.

Reproduce the published package from the saved source runs.

```sh
review_run=salt_dilution/results/discharge/2026-11-10_recovery_review_v2
export_out=$(mktemp -d)

python -m salt_dilution.scripts.processing.export_discharge \
  --mass-run salt_dilution/results/discharge/2026-11-10_recovery_v2 \
  --audit-run "$review_run" --review-run "$review_run" \
  --reuse-run salt_dilution/results/calibration_reuse/2026-11-10_recovery_v2 \
  --refresh-figures --output "$export_out/discharge_analysis"
```

Open [the stable analysis package](../salt_dilution/results/discharge_analysis/README.md) to read its tables and figures without the raw recordings. Start with `tables/discharge_by_release.csv` for one row per release. Use `tables/discharge_primary.csv` for the selected estimates, including their support qualifications, and `tables/conditional_discharge.csv` for capture-assumed scenarios. Blank Q means no selected estimate; separate capture-assumed scenarios are identified explicitly. `bundle_index.json` records the exact export command and `analysis_limits.json` describes the remaining evidence gaps. Rebuild into a separate, absent output directory.

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
