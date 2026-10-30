# Calibration curves

Calibration relates the probe's conductivity reading to a known added salt concentration. The stock recipe and each added volume supply the concentration values; the probe supplies the conductivity readings. The fitted slope, K, connects them.

The [calibration runner](../salt_dilution/scripts/processing/calibration.py) uses the curated preparation and point tables. It needs neither stream recordings nor discharge windows.

```sh
python -m salt_dilution.scripts.processing.calibration --basis both --output salt_dilution/results/new_calibration_run
```

Run from the repository root with NumPy and Matplotlib installed. Use a new output directory; existing runs are not overwritten. `--basis` accepts `specific`, `actual` or `both`, defaulting to `specific`.

## From a preparation to concentration

The recorded `procedure_id` selects one of two stock calculations.

For `mass_stock_river` and `mass_stock_deionized`:

```text
S = M × 1,000,000 / V_stock                  [mg/L]
```

`M` is `stock_salt_mass_g` in grams; `V_stock` is stock volume in mL. The factor converts g/mL to mg/L. Use measured `stock_solution_final_ml` when available; otherwise the working protocol uses `stock_water_initial_ml`. That fallback is a nominal preparation volume, and the output records it in `stock_volume_basis`.

For `solution_secondary`, a sample of the original injection solution is diluted with water:

```text
S = A / (W + A)                            [mL/mL of original injectate]
```

`A` is `injectate_aliquot_ml`; `W` is `secondary_water_initial_ml`. This stock has a relative injectate concentration, not a salt mass concentration.

Each calibration addition then gives:

```text
C_i = S × v_i / (V_receiver + v_i)
```

`C_i` is added concentration after step `i`. `V_receiver` is the initial water in the calibration vessel (`calibration_water_initial_ml`); `v_i` is the total stock added so far. The denominator includes the added volume. Sum incremental additions or use recorded cumulative totals according to `addition_kind`.

A missing EC reading leaves known additions in the volume total. A missing increment makes later totals unknown until an explicit cumulative value restores them. Unconfirmed addition semantics reject the series. Written vessel-volume disagreements are reported without changing source observations.

## From concentration to K

Ordinary least squares fits each recorded probe and conductivity channel separately:

```text
C_i = k × EC_i + b + residual_i
```

`EC_i` is conductivity in µS/cm, `k` is the fitted slope and `b` is a free intercept. The regression predicts concentration from conductivity; it is not the inverse of an EC-on-concentration fit or a manufacturer cell constant.

| Calibration basis | K units |
| --- | --- |
| Salt mass concentration | `(mg/L)/(µS/cm)` |
| Relative injectate concentration | `(mL/mL)/(µS/cm)` |

Actual conductivity is measured at sample temperature; specific conductivity uses the instrument's reference-temperature treatment. The channels remain separate. A fit needs at least three usable pairs, varying concentration and conductivity, and a positive slope. Missing inputs, abandoned preparations and unsupported series have explicit skip reasons.

Fit plots show concentration against EC; residual plots show observed minus fitted concentration. R² and RMSE describe fit quality, while saved ranges show the measured domain. They do not quantify all preparation or field uncertainty.

## Applying a fitted coefficient

Use a compatible calibration/river instrument pair, conductivity channel and temperature treatment within a supported physical trial/role. Two probes of the same model are not automatically interchangeable. The [instrument guide](salt_dilution_instruments.md) describes the September 18, 2026 same-river-TROLL procedure change and the evidence needed for cross-instrument use. General meters serve a separate downstream-monitoring role.

For a supported linear calibration, background subtraction gives `k × (EC − EC_background)` because the intercept cancels. Calculating Q still requires a confirmed release, delivered tracer quantity, aligned clocks, river background and full pulse window. Alternative calibrations for one recording are not additional stream observations. Apply a fit within its measured range or document any extrapolation.

The deionized-stock ionic-background correction is not implemented. The runner fits provisional series; it does not approve field applicability.

## Saved outputs and next step

| Output | Contents |
| --- | --- |
| `calibration_fits.csv` | K, intercept, units, fit direction, R², RMSE, point counts, ranges and stock-volume basis. |
| `calibration_points.csv` | Derived volumes/concentrations, predictions, residuals and exclusions. Source tables remain unchanged. |
| `calibration_skips.csv` | Series that could not be fitted and their reasons. |
| `figures/` | Fit and residual plots with distinct actual/specific channels. |
| `run_info.json` | Input/output/code hashes, Git revision, software versions and scope. |

The [reviewed bundle](../salt_dilution/results/calibrations/2026-10-26_probe_review/README.md) contains 49 provisional fits and 37 skips. Its identity review resolved 13 preparations without changing numerical fits; 12 fitted series still lack identities. The [earlier bundle](../salt_dilution/results/calibrations/README.md) remains available. The runner writes the portable file bundle; local MLflow logging, where present, is separate.
