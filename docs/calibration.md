# Calibration curves

`salt_dilution/scripts/processing/calibration.py` fits the curated preparation and point tables. It does not need stream recordings, `trial_inputs.csv`, discharge windows or a final stock-volume measurement. Results are provisional coefficients for review, not discharge estimates or accepted field measurements.

Run from the repository root using Python with NumPy and Matplotlib installed:

```sh
python -m salt_dilution.scripts.processing.calibration --basis both --output salt_dilution/results/new_calibration_run
```

Choose `specific`, `actual` or `both`; the default is `specific`. Use a new output directory: an existing run is never overwritten. A clone can fit the tracked tables without the large local stream recordings. The [October 20 result bundle](../salt_dilution/results/2026-10-20_calibration/README.md) is the first saved run.

## From a preparation to concentration

The calculation follows `procedure_id`, rather than inferring a recipe from the date or applying every populated dilution field.

For `mass_stock_river` and `mass_stock_deionized`, stock concentration is:

```text
S = M × 1,000,000 / V_stock                  [mg/L]
```

`M` is `stock_salt_mass_g`, in grams. `V_stock` is stock volume in milliliters. Use measured `stock_solution_final_ml` when supplied; otherwise use `stock_water_initial_ml` under the user-confirmed working protocol. That fallback is a nominal preparation convention, not a claim that starting water was a measured final solution volume. Results save `stock_volume_basis`; no blank observation is filled or inferred.

For `solution_secondary`, the calibration stock is a diluted sample of the original injectate:

```text
S = A / (W + A)                            [mL/mL of original injectate]
```

`A` is `injectate_aliquot_ml`; `W` is `secondary_water_initial_ml`. The denominator includes the aliquot added to the secondary water. This relative concentration is not a mass concentration.

For each calibration step:

```text
C_i = S × v_i / (V_receiver + v_i)
```

`V_receiver` is `calibration_water_initial_ml`. `v_i` is the total stock volume added through step `i`: sum incremental additions, or use a recorded cumulative total directly. Unequal additions are preserved. A missing conductivity reading does not erase its known volume addition. A missing increment makes subsequent cumulative totals unknown until an explicit cumulative value restores them. Unconfirmed semantics reject the series. Written vessel-volume discrepancies are reported beside calculated volumes, without correcting observations.

## From concentration to K

Each channel and recorded probe series is fitted separately with ordinary least squares:

```text
C_i = k × EC_i + b + residual_i
```

`EC_i` is conductivity in µS/cm on the selected channel. `k` is the concentration-on-conductivity slope; `b` is the free intercept. This is not the inverse of an EC-on-concentration regression, and K is not an instrument cell constant. Mass-stock K has units `(mg/L)/(µS/cm)`; relative-injectate K has units `(mL/mL)/(µS/cm)`. Do not combine those factors as though they had the same units. A future background subtraction on the same linear calibration would give excess concentration `k × (EC − EC_background)` because the intercept cancels.

Actual and specific conductivity remain separate. Missing channel readings are excluded, never replaced by the other channel. A fit needs at least three usable paired observations, varying conductivity/concentration and a positive slope. Abandoned preparations are skipped. Missing receiving volume, unconfirmed additions or too few points produce explicit skip reasons rather than fabricated coefficients. A high R² alone does not establish calibration acceptance or measurement uncertainty.

The October 20 user clarification permits calibration across numbered probes of the same device class. Aliases remain traceable and available for QA, but a number difference alone does not prevent a notebook-supported link. The selected stream channel must still match the fitted channel. `trial_inputs.csv` now selects actual conductivity where that is the available notebook calibration route; no source values were converted.

## Saved outputs and next step

- `calibration_fits.csv`: one provisional fit per preparation/probe/channel, with K, intercept, units, fit direction, R², RMSE, point counts, observed ranges and volume basis.
- `calibration_points.csv`: calculated volumes, concentrations, fitted values, residuals and exclusion reasons, separate from the source observations.
- `calibration_skips.csv`: the attempted series that could not be fitted and the reason.
- `figures/`: concentration fits and residual plots; actual and specific channels use different markers and colors.
- `run_info.json`: input/output hashes, code hash, Git revision, software versions and calculation scope. The file bundle is sufficient to reproduce the run; local MLflow adds run tracking when available.

These outputs do not select an event, background or full breakthrough tail. Before calculating Q, resolve the relevant recording association, clock alignment, delivered salt/injectate quantity, units and integration limits. July 17 retains alternative calibrations for one recording; do not count both as separate stream observations. Do not extrapolate a fit beyond its saved range without a documented decision. Preparation uncertainty and shared-probe differences are not quantified by the regression residuals.
