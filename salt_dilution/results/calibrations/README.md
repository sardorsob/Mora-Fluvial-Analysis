# October 20 calibration run

**49 provisional channel fits across 35 of 43 preparations**, with 35 diagnostic figures. There are 19 specific-conductivity fits and 30 actual-conductivity fits. These are concentration-on-conductivity regressions for review, not Q estimates or accepted field results.

Start with [calibration_fits.csv](calibration_fits.csv), then inspect the linked figure and [derived point calculations](calibration_points.csv). The [method guide](../../../docs/calibration.md) explains the equations, symbols, units and interpretation. Relative-injectate and mass-concentration K factors have different units and must not be pooled as one quantity.

| Output | Use |
| --- | --- |
| [calibration_fits.csv](calibration_fits.csv) | K, intercept, channel, units, R², RMSE, point counts, ranges and stock-volume basis |
| [calibration_points.csv](calibration_points.csv) | Calculated volumes/concentrations, residuals, missing-point reasons and written-vessel discrepancies |
| [calibration_skips.csv](calibration_skips.csv) | Every attempted channel series that could not be fitted |
| [run_info.json](run_info.json) | Code revision, software versions, input/output hashes and local tracking reference |
| [numerical_verification.json](numerical_verification.json) | Independent high-precision check of an October 2 specific-conductivity fit |

## Inputs and protocol

The run uses tracked `data/records/calibrations.csv`, `calibration_points.csv`, their provenance and `config/procedure_versions.json`. No stream windows or `trial_inputs.csv` are needed to fit these curves. Raw exports, normalized stream readings, historical notebooks and the three observation tables were unchanged; 540 file hashes were checked against the starting snapshot.

Mass-stock calculations use recorded preparation-water volume when final stock-solution volume is unmeasured, under the user-confirmed working protocol. No source final-volume cells were filled. The shared-probe policy permits notebook-supported application across the numbered probes of the same device class; probe aliases remain recorded, and actual/specific channels remain separate. This policy does not quantify instrument or preparation uncertainty.

The fitted relation is `concentration = k × conductivity + intercept`, with a free intercept and at least three usable observations. It is not an inverted EC-on-concentration fit. Added volumes include unequal increments and use the changing receiving-vessel volume. The fit table reports written-volume disagreements in two channel fits; those observations were not corrected.

## Why some series are skipped

The 43 preparations produce 86 possible channel-series attempts. Thirty-seven attempts are skipped:

| Reason | Channel-series attempts |
| --- | ---: |
| Fewer than three usable specific-conductivity/addition pairs | 17 |
| Fewer than three usable actual-conductivity/addition pairs | 6 |
| Receiving-water volume missing: four PAR supporting preparations × two channels | 8 |
| Unconfirmed addition interpretation: two early July 9 preparations × two channels | 4 |
| Abandoned September 18 preparation × two channels | 2 |

A missing channel often leaves the other channel usable. Eight preparations have no fit: NISQ July 9 C01–C03, PAR September 3 C06–C09 and abandoned NISQ September 18 C01. The first July 9 preparation has only two usable pairs. Their absence does not prevent fitting the other preparations. See the skip CSV for exact IDs and reasons.

## Reproduction and checks

From a clean checkout of implementation commit `eff679c7499cfd5e2616cc6e25e7f6646a81e398`, with Python, NumPy and Matplotlib:

```sh
python -m salt_dilution.scripts.processing.calibration --basis both --output salt_dilution/results/reproduced_calibrations
```

The new directory must not already exist. Timestamps and Git/runtime metadata can differ; inspect input/code hashes and numerical outputs. The saved run used Python 3.13.9 and NumPy 2.5.0. Local MLflow tracking and artifacts are kept under the ignored `salt_dilution/results/.mlflow/`; the CSV/JSON/PNG bundle remains the portable record and MLflow is not needed to reproduce the calculations.

All 74 tests passed, including opt-in checks of 31 registered local source/output/metadata sets. Excel tests temporarily used the bundled pure-Python openpyxl/et_xmlfile packages. Existing NumPy timedelta deprecation warnings were nonfatal. An independent 45-digit Decimal reconstruction of NISQ-20261002-C01 gave specific-conductivity K = `0.41189733537185335 (mg/L)/(µS/cm)`, matching the saved fit at relative tolerance `1e-12`. A separate visual review found no major readability issue in the sample fit/residual figure; it does not establish scientific acceptance.

The input table has 46 linked rows with matching-channel fits, two linked rows without a notebook calibration, and 11 unresolved recording placeholders. Q still requires event identity, delivered quantity, background and full-tail windows, units and clock alignment. No acceptance threshold or uncertainty interval was invented for these provisional fits.
