# Calibration after probe-identity and addition review

Run date: October 26, 2026. This reruns the existing calibration runner after supported probe-identity fills. The [October 20 bundle](../README.md) is retained unchanged.

## Result

- 49 provisional preparation/channel fits and 37 skipped series, with explicit reasons in `calibration_skips.csv`.
- 13 preparation identities resolved, filling 100 formerly blank point-level aliases. Twenty-five fitted series gain a probe identity; 12 fitted series still have none.
- Every numerical fit field, including K, intercept, R², RMSE and point counts, is unchanged from the earlier bundle. Only probe/figure identity changes in fit rows. This is expected: observed quantities and addition labels were not changed.
- Independent `numpy.linalg.lstsq` checks rebuilt concentrations from the current preparation/addition records and verified all 49 fits. See `numerical_verification.json`.

## Confirmed identity fills

| Preparation | Probe alias | Evidence |
| --- | --- | --- |
| NISQ-20250709-C04 | probe_02 | Native Aqua TROLL recording: all six specific and five actual readings match in channel order within 0.005001 µS/cm. The two channels need not have been written simultaneously. |
| NISQ-20250717-C01 | probe_03 | Native Calibration 1 export identifies the sensor; both channels at the first two levels match. The third level is outside the truncated export. The following Calibration 2 and established trial association support continuity; the unverified reading is retained. |
| NISQ-20250717-C02 | probe_03 | Native Calibration 2 export identifies the sensor; three paired steps and all four specific readings match. The actual baseline discrepancy is retained. |
| NISQ-20250808-C01 | probe_01 | All five actual readings match the native electronic calibration. The separate legacy table's differing second reading is not substituted. |
| NISQ-20261002-C01, C02 | probe_03 | Confirmed event/source-block association plus measured Aqua TROLL identity and the user's within-trial continuity rule. |
| NISQ-20261004-C01–C04 | probe_03 | Same trial-specific continuity evidence; IDs are not assumed to be chronological. |
| NISQ-20261005-C01–C03 | probe_03 | Same trial-specific continuity evidence, separately for each associated release. |

Detailed file paths, source/output/metadata hashes, matching row indices/readings and individual October trial IDs are in the [record provenance](../../../data/records/provenance.json). No date-only, bank-only or shared-model identity assignment was made. Nineteen preparation identities remain unresolved overall; some of these do not produce fits.

## Addition audit

All 43 blocks were compared against their preserved additions and written vessel-volume progression:

| Disposition | Blocks |
| --- | ---: |
| Existing interpretation supported by written volume progression | 34 |
| Insufficient written-volume evidence | 5 |
| Unconfirmed water changes within the block | 2 |
| Abandoned attempt with a missing addition | 1 |
| Existing interpretation retained with a written-volume conflict | 1 |

The September 18 restart already uses increments totaling 26 mL. October 4 C02 already uses unequal increments totaling 46 mL. October 4 C01 step 2 retains a 5 mL cumulative addition beside a written 2004 mL vessel volume, a −1 mL discrepancy. No source observation was repaired by assumption, and no interpretation was chosen to improve regression quality. No addition-kind changes were confirmed.

The original notebook PDF paths in Downloads are no longer available. This review uses retained transcription/raw tokens and electronic exports; it does not claim fresh visual verification of the handwriting. Unconfirmed water changes and incomplete supporting/abandoned attempts remain explicit.

## Reproduce and interpret

From the repository root, with NumPy and Matplotlib installed, choose a new output directory:

```sh
python -m salt_dilution.scripts.processing.calibration --basis both --output salt_dilution/results/new_probe_review
```

`run_info.json` records exact input hashes, unchanged runner code hash, software versions and the parent Git revision. The revision precedes the commit containing these reviewed input bytes; use the saved hashes to identify the exact inputs. CSVs and diagnostic figures are self-contained here. Local MLflow adds tracking under the existing `salt_dilution/results/.mlflow/` store; it is not required to reproduce the fits.

Figure filenames and the identity table above identify the resolved probes; the unchanged plot titles retain the preparation ID. For October 4 C02, actual EC has nine fitted observations versus ten for specific EC because step 2 has no recorded actual reading. The blank is preserved, not borrowed from the other channel. Source rows are in [calibration_points.csv](../../../data/records/calibration_points.csv), with exact input hashes in `run_info.json`. Figures are intended for inspection at their native 1800-pixel width.

All 262 point observations, preparation settings, releases and recording links are preserved. Different-probe associations now explicitly require applicability review rather than blanket acceptance. The General meter's attenuation role does not imply a default General-to-Aqua-TROLL correction for main Q.

These results do not establish accepted discharge, delivered quantity, integration windows, clock alignment, calibration uncertainty or a DI-stock background correction. High R² and a filled probe alias do not establish scientific acceptance. No Q was calculated.
