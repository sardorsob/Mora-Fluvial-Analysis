# Compact salt-discharge tables

Open [working estimates](scenarios/working_estimates_compact.csv) for conditional
calculations or [baseline channel estimates](baseline/discharge_estimates_compact.csv)
for the original retained calculations. Each compact CSV preserves the rows,
order, values and units of selected columns in its source. The full source
tables provide the detailed evidence, processing settings and other diagnostics.

## Original discharge analysis

| Compact table | Full source |
| --- | --- |
| [Release outcomes](baseline/discharge_by_release_compact.csv) | [discharge_by_release.csv](../discharge_analysis/tables/discharge_by_release.csv) |
| [Primary estimates](baseline/discharge_primary_compact.csv) | [discharge_primary.csv](../discharge_analysis/tables/discharge_primary.csv) |
| [Channel estimates](baseline/discharge_estimates_compact.csv) | [discharge_estimates.csv](../discharge_analysis/tables/discharge_estimates.csv) |
| [Capture-assumed discharge](baseline/conditional_discharge_compact.csv) | [conditional_discharge.csv](../discharge_analysis/tables/conditional_discharge.csv) |
| [Observed pulse areas](baseline/observed_pulse_areas_compact.csv) | [observed_pulse_areas.csv](../discharge_analysis/tables/observed_pulse_areas.csv) |
| [Capture coverage](baseline/capture_coverage_compact.csv) | [capture_coverage.csv](../discharge_analysis/tables/capture_coverage.csv) |
| [Stage diagnostics](baseline/stage_diagnostics_compact.csv) | [stage_diagnostics.csv](../discharge_analysis/tables/stage_diagnostics.csv) |
| [Channel quality review](baseline/quality_review_by_channel_compact.csv) | [quality_review_by_channel.csv](../discharge_analysis/tables/quality_review_by_channel.csv) |
| [Calibration compatibility](baseline/calibration_compatibility_compact.csv) | [calibration_compatibility.csv](../discharge_analysis/tables/calibration_compatibility.csv) |
| [Calibration quality](baseline/calibration_quality_compact.csv) | [calibration_quality.csv](../discharge_analysis/tables/calibration_quality.csv) |
| [Coefficient reuse](baseline/coefficient_reuse_compact.csv) | [coefficient_reuse.csv](../discharge_analysis/tables/coefficient_reuse.csv) |

The nine other [baseline tables](../discharge_analysis/tables/) already have
focused schemas. Use the saved versions for blocked capture, channel
consistency, field-note comparison, isolated method candidates, native-export
comparison, release quality review, recording outcomes, recovery requirements
and window sensitivity.

## Working calculations and sensitivity scenarios

| Compact table | Full source |
| --- | --- |
| [Working estimates](scenarios/working_estimates_compact.csv) | [working_estimates.csv](../discharge_scenarios/working_estimates.csv) |
| [Scenario estimates](scenarios/scenario_estimates_compact.csv) | [scenario_estimates.csv](../discharge_scenarios/scenario_estimates.csv) |
| [Scenario calibrations](scenarios/scenario_calibrations_compact.csv) | [scenario_calibrations.csv](../discharge_scenarios/scenario_calibrations.csv) |

Use the saved [working estimates summary](../discharge_scenarios/working_estimates_summary.csv)
for a 21-column view of `working_estimates.csv`. The compact copies and the
summary are reading views. The plot runner reads the full working and
selected estimate tables. See the [CSV lineage diagrams](../discharge_scenarios/README.md#how-the-csvs-fit-together).

## Reading and joining the tables

All saved discharge estimates remain proposed or conditional. Read status and
limitations with each value. Discharge is in m³/s. The spill rows have blank Q
and report a response in m³/s per litre delivered. A blank cell represents
missing or inapplicable information. Fit standard errors and sensitivity
ranges describe individual sources of variation. Total discharge uncertainty
remains unquantified.

For a scenario estimate, keep `trial_id`, `recipe_id`, `window_id`,
`recording_edge_id`, `conductivity_basis`, `calibration_id`,
`calibration_series_alias`, `background_mode` and `gap_mode` together.
The calibration table calls the series label `probe_alias`. Match baseline
estimates using the release, recording, channel and calibration identifiers.
The [full scenario guide](../discharge_scenarios/README.md) explains the
quantity, integration and calibration fields.

## Refresh the copies

From the repository root, run the [exporter](../../scripts/processing/export_discharge_reader_tables.py)
after refreshing the saved source tables. It uses the published CSVs as inputs
and requires only Python.

```sh
python salt_dilution/scripts/processing/export_discharge_reader_tables.py
python salt_dilution/scripts/processing/export_discharge_reader_tables.py --check
```
