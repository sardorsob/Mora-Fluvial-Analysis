# Salt-discharge results and scenarios

Start with [figures/plot_estimates.csv](figures/plot_estimates.csv) for the combined Q results. It contains **79 instrument/channel/calibration estimates across 33 experimental releases**. Use [figures/release_coverage.csv](figures/release_coverage.csv) to see all 38 recorded releases: 33 with Q, three without a chosen Q, and two excluded practice releases.

This folder holds the additional conditional calculations and the current combined graphs. The original selected calculations remain in [discharge_analysis](../discharge_analysis/README.md). Together they cover **27 of 30 experimental Nisqually releases and all six Paradise releases**. “Selected” and “working” describe how an estimate was retained; neither means scientific acceptance.

## Which file should I open?

- **Compare the current Q values:** `figures/plot_estimates.csv`.
- **Check whether a release has Q:** `figures/release_coverage.csv`.
- **Inspect K, dose, pulse area and assumptions:** `working_estimates.csv` for working results, or the [original channel-estimate table](../discharge_analysis/tables/discharge_estimates.csv) for selected results.
- **Find where a quantity came from:** `working_parameters.csv`.
- **Compare alternative assumptions:** `scenario_estimates.csv`.

There is no single table containing every calculation detail from both result groups. The combined Q table identifies the source of each row.

## CSV guide

Counts below describe the saved package. A **release** is one physical injection. An **estimate** is a calculation for a particular recording, conductivity channel, calibration and set of assumptions. Several estimates can belong to one release.

A **recipe** specifies calibration preparation and dose assumptions. A **window** identifies the recording intervals used for the background and salt pulse.

### Combined results and graph references

| File | One row represents | What it provides |
| --- | --- | --- |
| [figures/plot_estimates.csv](figures/plot_estimates.csv) | One plotted Q estimate; **79 rows** | Q in `q_m3_s`, date, site, instrument, calibration, status and source table. Combines 16 selected-result rows with 63 working-result rows. It excludes per-litre spill responses and releases without a chosen Q. |
| [figures/release_coverage.csv](figures/release_coverage.csv) | One release; **38 rows** | `plot_status` and `plotted_q_count`. Includes missing and practice cases, making this the appropriate table for coverage counts. It does not contain Q magnitudes. |
| [figures/figure_index.csv](figures/figure_index.csv) | A figure entry or an estimate-to-pulse link; **86 rows for 82 images** | The image path in `figure`, its `kind`, and the relevant recording, channel, calibration and window IDs. Several calibration estimates can share a pulse image, so repeated image paths are expected. |

In `plot_estimates.csv`, `status` distinguishes `selected_proposed`, `selected_conditional` and `working_conditional`. In `release_coverage.csv`, `no_chosen_q` identifies the three unresolved releases; `excluded_practice` identifies the two practice releases.

### Working calculations

These three files cover the **25 experimental Nisqually releases without Q in the original selected-results table**. They do not repeat the original 11 releases with selected estimates.

| File | One row represents | What it provides |
| --- | --- | --- |
| [working_by_release.csv](working_by_release.csv) | One recovery-case release; **25 rows** | The working recipe decision, estimate counts, remaining requirements and limitations. There are 22 releases with conditional Q, two with unresolved recipes, and one with only a per-litre response. `working_q_min_m3_s` and `working_q_max_m3_s` summarize the retained estimates for that release. |
| [working_estimates.csv](working_estimates.csv) | One retained calculation; **65 rows** | Full quantities, K, integration results, Q and assumptions. There are 63 Q rows across 22 releases and two per-litre response rows for the spill release. Separate instruments, channels and calibration attempts are retained. |
| [working_parameters.csv](working_parameters.csv) | One parameter decision for a release, optionally a particular calibration; **98 rows** | `field`, `value`, `unit`, the decision's `basis` and `reason`, source references, and preceding trials used as evidence. `used_by_working_recipes` lists the recipes that actually use the decision. An empty list means the recorded decision was not applied to a working recipe. |

Working recipes follow the trial records and reviewed nominal settings, shared preparations, then preceding same-site/year/protocol evidence until an explicit method change. The working selection also specifies a background and gap treatment. It does not choose the recipe whose Q looks most plausible or whose fit has the highest R².

`parameter_source_status` distinguishes **recorded**, **participant_confirmed**, **reviewed_nominal**, **inferred** and **unresolved** values. Read `basis` and `reason` as well: a recorded nominal dose is not necessarily a measured delivered dose. `donor_ids` identifies preceding records, and `donor_age_days` gives their age relative to the target trial. An inferred quantity remains an assumption.

### Sensitivity experiments

These files retain the broader set of tested alternatives from which the working results were drawn. They are useful for examining how an assumption changes Q, rather than adding more independent field observations.

| File | One row represents | What it provides |
| --- | --- | --- |
| [scenario_by_release.csv](scenario_by_release.csv) | One recovery-case release; **25 rows** | Recipe, window and result counts; the full tested Q range; and unresolved evidence. Twenty-four releases have numerical Q scenarios and one has per-litre responses. This is broader coverage than the working selection. |
| [scenario_estimates.csv](scenario_estimates.csv) | One recipe/calibration/recording/window/background/gap combination; **398 rows** | The full calculation and assumptions for 392 conditional Q results and six per-litre responses. Use it to compare alternatives within a release. |
| [scenario_calibrations.csv](scenario_calibrations.csv) | One recipe-specific calibration series; **80 rows** | K, its fit standard error, units, point count, R² and the fitted conductivity range. A calibration fit can support several integration scenarios, so it is not a release-level Q result. |
| [scenario_rejections.csv](scenario_rejections.csv) | One excluded candidate or failed calculation attempt; **3 rows** | The affected recipe/window, `stage` and `reason`. The saved rows are source-screen exclusions: an abandoned calibration and two incomplete recording fragments. This is not a list of the three releases still missing a chosen Q. |

The two July 9, 2025 releases have numerical alternatives in `scenario_estimates.csv` but no chosen working recipe. Some stock-stage alternatives produce implausibly large Q. Neither the full scenario range nor the working minimum/maximum is a confidence interval or an instruction to average the values.

## Reading the calculation columns

The detailed estimate tables share the following field groups. The working table adds `working_recipe_status`, `protocol_source_decisions`, `protocol_exceptions` and `working_choice_is_measurement` to preserve the working-selection decision.

| Fields | Meaning and units |
| --- | --- |
| `q_m3_s` | Discharge Q in **m³/s**. Multiply by 1,000 for L/s. Blank does not mean zero flow. |
| `q_m3_s_per_delivered_litre`, `result_class` | A unit response for the spill case. When `result_class` is `unit_response`, `q_m3_s` is blank. The response could be multiplied by a known delivered volume in litres; the planned volume does not establish the spilled release's actual delivery. |
| `mass_g`, `injection_solution_volume_ml`, `quantity_kind` | The dose used by the applicable mass or original-solution-volume method. The unused quantity can be blank. These are calculation inputs; read their recorded or assumed basis before treating them as delivered measurements. |
| `k`, `k_se`, `coefficient_unit` | The concentration-per-conductivity coefficient and its fit standard error. Units are either `(mg/L) / (uS/cm)` or `(mL/mL) / (uS/cm)`. These coefficients serve different calculation methods and cannot be pooled as one quantity. |
| `n_points`, `r_squared`, `ec_min`, `ec_max`, `fit_note` | Calibration fit diagnostics. The conductivity range is in µS/cm. A good fit does not resolve stock identity or delivered quantity; K standard error excludes recipe and field uncertainty. |
| `dose_fraction_slope`, `concentration_scale`, `secondary_fraction` | Intermediate calibration terms. K is the dose-fraction slope multiplied by the concentration scale; that scale already includes any secondary dilution fraction. |
| `integral_us_cm_s`, `observed_interval_integral_us_cm_s`, `modelled_gap_integral_us_cm_s` | Total integrated excess conductivity and its observed/modelled components, in **µS/cm × seconds**. A modelled component is not an additional sensor observation. |
| `background_mode`, `background_pre_us_cm`, `background_post_us_cm` | The selected background treatment and background conductivity in µS/cm. `pre` or `post` uses that background; `linear` interpolates between the two. |
| `gap_mode`, `modelled_gap_seconds`, `in_pulse_gap_count`, `gap_interpretation` | Whether and how a gap enters the integration. Read these before comparing a fully observed pulse with an estimate that models missing samples. |
| `pre_samples`, `pulse_samples`, `post_samples`, duration and peak fields | Sensor observations and intervals supporting integration, distinct from calibration-point counts. Durations are seconds; `pulse_peak_us_cm` is conductivity in µS/cm. |
| `recipe_assumptions`, `capture_assumptions`, `sensor_applicability`, `event_link_status`, limitation and issue fields | Qualifications concerning preparation, full pulse capture, sensor transfer, event association and data quality. Keep these attached when exporting or comparing Q. |

`conductivity_basis` distinguishes **actual** conductivity from temperature-compensated **specific** conductivity. Use the matching channel's K. `sensor_serial` identifies the recording instrument; calibration aliases are series labels and do not independently establish physical sensor identity.

All saved `scientifically_accepted` values are false. `selected_for_primary` and `working_choice_is_measurement` likewise do not promote the working estimates into accepted field measurements. Fit errors and tested scenario ranges do not quantify total Q uncertainty.

## Follow a Q value back to its source

The `source_table` field in `figures/plot_estimates.csv` resolves as follows:

| Stored value | Detailed table |
| --- | --- |
| `working_estimates.csv` | [working_estimates.csv](working_estimates.csv) in this folder |
| `tables/discharge_estimates.csv` | [discharge_analysis/tables/discharge_estimates.csv](../discharge_analysis/tables/discharge_estimates.csv) in the sibling baseline folder |

For example, filter the combined table to **`NISQ-20261004-T01`**, specific conductivity. Its conditional Q is **2.285 m³/s** when rounded. The matching working row records calibration `NISQ-20261004-C01`, recipe `NISQ-20261004-T01:NISQ-20261004-C01:scenario_01`, and window `window_021`. That row supplies the 4,000 g dose, K ≈ 0.366499 `(mg/L) / (µS/cm)` and integrated excess conductivity ≈ 4,777.400 µS/cm × seconds. Its capture status still assumes the recorded interval contains the full pulse.

To trace any working result:

1. Find its detailed row using `trial_id`, `recording_edge_id`, `conductivity_basis`, `calibration_id`, `calibration_series_alias`, `window_id` and `recipe_id`.
2. Read the corresponding parameter decisions and their `used_by_working_recipes` lists in `working_parameters.csv`.
3. Find the recipe under `cases[].recipes[]` and the window under `windows[]` in [scenario_settings.json](scenario_settings.json). Windows define the pre-background, pulse and optional post-background intervals. Field clock times use the confirmed fixed **PST, UTC−08:00** interpretation.
4. Use the same IDs in `figures/figure_index.csv` to open the pulse graph. The example above is [window 021, specific conductivity](figures/pulses/NISQ-20261004-T01_window_021_specific.png).

For joins, keep the full estimate identity: `trial_id` alone will multiply rows across sensors, channels and assumptions. When matching a working row to `scenario_estimates.csv`, also include `background_mode` and `gap_mode`. To join `working_estimates.csv` or `scenario_estimates.csv` to `scenario_calibrations.csv`, use `trial_id`, `recipe_id`, `calibration_id`, conductivity basis and the calibration-series label; that label is named `calibration_series_alias` in the estimate tables and `probe_alias` in the calibration table.

For the original selected results, `recipe_id` and `window_id` in the combined table are blank. Use the trial, recording, channel and calibration IDs to reach the sibling source table, which stores its own `windows` and `fit_reference` details. Bring dates and sites into working-table analyses from `figures/release_coverage.csv` using its unique `trial_id`.

Cells containing lists or objects, such as `source_refs`, `donor_ids`, `recipe_assumptions` and `protocol_source_decisions`, contain JSON. Parse them as JSON rather than splitting on commas. Do not turn blank quantities or uncertainty fields into zero; for example, a two-point calibration fit cannot supply a residual-based slope standard error.

## Graphs, settings and reproduction

[figures/](figures/) contains **82 images**: five overview/detail graphs and 77 pulse plots. Of those pulse plots, 75 show Q and two show per-litre spill responses. The graph index has more rows than images because some pulse plots display multiple calibration estimates. Diagnostic figures retained under `discharge_analysis` describe the earlier selected run and may still say “No selected Q.”

The remaining experimental releases without a chosen Q are **July 9, 2025, T01 and T02** (unresolved stock-stage interpretations) and **September 3, 2025, T02** (unknown delivered volume after a spill).

| File | Purpose |
| --- | --- |
| [scenario_settings.json](scenario_settings.json) | Saved recipes, windows, protocol choices, excluded candidates, source references and method references used for the calculations. |
| [run_info.json](run_info.json) | Scenario/working run metadata, software versions, counts, and input/output hashes. |
| [historical_code.json](historical_code.json) | Recorded hashes and Git revisions identifying historical source code used by upstream bundles. |
| [figures/run_info.json](figures/run_info.json) | Separate metadata and hashes for the combined graph build. |
| [figures/historical_code.json](figures/historical_code.json) | Historical code references encountered when checking the graph build's inputs. |

The [scenario runner](../../scripts/processing/discharge_scenarios.py) produces the calculation tables; the [graph runner](../../scripts/processing/plot_discharge_working.py) combines the selected and working results without choosing new Q values. Follow the existing commands to [rebuild the scenarios](../../../docs/getting_started.md#explore-discharge-assumptions) or [regenerate the graphs](../../../docs/getting_started.md#regenerate-the-current-discharge-graphs). Use a fresh output directory and retain the pinned local recordings and source runs. Reading the published CSVs and PNGs does not require those local inputs.

See [research methods](../../../docs/research_methods.md#salt-dilution-measuring-water-discharge) for the equations and assumptions, and [references](../../../docs/references/README.md) for the scientific sources.
