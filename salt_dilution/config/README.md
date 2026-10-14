# Salt-dilution calibration procedures

`procedure_versions.json` lists calibration methods selected by `procedure_id` in the planned `data/records/calibrations.csv`. The file defines method inputs and calculation basis; each calibration session supplies its measured quantities.

| Procedure ID | Calibration method |
| --- | --- |
| `solution_secondary` | Dilute an aliquot of the injected solution, then add measured amounts of the secondary solution to a calibration vessel. |
| `mass_stock_river` | Prepare a known-mass salt stock with river water, then add it to the calibration vessel. |
| `mass_stock_deionized` | Prepare a known-mass salt stock with deionized water, then add it to the calibration vessel. |

## Fields

- `calibration_basis`: whether conductivity is fitted against relative injectate concentration or salt mass concentration.
- `required_calibration_fields`: preparation measurements expected in `data/records/calibrations.csv`.
- `stock_water_source`: water used to prepare a known-mass salt stock.
- `discharge_input`: injected quantity expected in `data/records/trials.csv`.

`data/records/calibration_points.csv` will hold the recorded addition volumes, incremental/cumulative interpretation, and conductivity observations. Calculate cumulative additions from these points and fit using a consistent probe and conductivity channel.

## Calculations

- **Secondary solution:** Find the original-injectate fraction in the secondary solution from its aliquot and water volumes. Use cumulative secondary-solution additions and calibration-vessel volume to calculate relative concentration at each point. Fit that against conductivity; slug discharge uses the delivered injectate-solution volume.
- **Mass stock:** Find stock concentration from salt mass and **final stock-solution volume**. Use cumulative stock additions and calibration-vessel volume to calculate added salt concentration at each point. Fit that against conductivity; slug discharge uses delivered salt mass.

These methods use different concentration units and corresponding discharge calculations. Record actual session quantities in the notebook-derived tables. The procedure IDs carry no inferred date ranges or default preparation volumes.

Existing historical `.ini` files remain available as source examples. `calibration.py` and `mass_slug.py` are not implemented yet.
