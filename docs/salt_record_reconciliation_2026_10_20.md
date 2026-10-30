# Salt-record identity and quantity lineage

This record explains the October 20, 2026 repair of colliding preparation IDs and the origin of reviewed stock masses. Use the [records guide](../salt_dilution/data/records/README.md) for the current data interface and [calibration](calibration.md) for calculations.

## Preparation identity repair

At source revision `5cd3f5e443bba6b0e379f735fa241601d837cad3`, four duplicate preparation IDs left 16 point rows without a unique parent. Repair `7d7647e2fc289147d007035731eba96db89ada0d` mapped distinct notebook source blocks as follows:

| Source block | Historical point parent | Repaired ID |
| --- | --- | --- |
| `c_06_test_left` | `UNK-20260903-C01` | `PAR-20260903-C06` |
| `c_06_test_right` | `UNK-20260903-C02` | `PAR-20260903-C07` |
| `c_07_pr02` | `UNK-20260903-C03` | `PAR-20260903-C08` |
| `c_08_p_unknown` | `UNK-20260903-C04` | `PAR-20260903-C09` |

PAR C01–C05 remain separate. The repair preserves all 43 preparations,262 point observations, measured quantities and source references. Historical aliases and bench/Edith/unlabelled descriptions remain in provenance. The PAR prefix retains the reviewed assignment; it does not independently verify each preparation's site.

## Stock-mass correction lineage

The reviewed local quantities came from `ff6c08597eab24253f22f47e846e6d1b40ff7372` and were combined with main `54598c9a5e7d13f51fa44086fb45a53a2deb1b89` in [PR 2](https://github.com/sardorsob/Mora-Fluvial-Analysis/pull/2). Applying the same four source-based ID repairs filled 35 stock-mass cells; all 43 preparations then had a nominal mass. The 262 points and 59 recording-link/placeholder rows were unchanged from that main revision.

`manifest.json` records the original calibration blob, source commit, exact 35 reviewed-setting overrides and four ID mappings. `provenance.json` retains the earlier source snapshot. Current CSV values plus this finite overlay define the calculation inputs; older `current_csv_values` apply except where the overlay explicitly replaces them. Regression tests reconstruct the uploaded CSV after reversing the four ID repairs and check its original Git blob, then check the provenance/override relationship.

Nominal mass is not established delivered mass. Spills, incomplete mixing, restarts and preparation uncertainty remain relevant; the ID repair did not establish discharge readiness.

## Recording links and remaining gaps

The association table contains 48 file-linked rows across 31 files for 28 releases, plus 11 unresolved placeholders for ten releases. Paired probes, split recordings, multiple releases per log and July 17 alternative calibrations remain distinct. Existing dataset IDs/paths were retained; source, processed-output and metadata hashes record their lineage.

July 21, 2026 uses RL/RR Win-Situ recordings and a written 11:10:10 release; August labels are export dates. Its RL log spans several days. October 2 and 4 release suffixes are not always chronological. The August 8 mixing CSV floors times to minutes; original live HTML retains seconds. These distinctions affect event matching and must not be replaced by date-only joins.

| Unlinked releases | Evidence gap |
| --- | --- |
| July 3, 2025: two | No confirmed downstream detection; clock-only output quarantined. |
| August 6, 2026: one | Written NISQ release 14:09 precedes logs after 14:24; their peak near 14:56 is close to a separately recorded Tahoma release 14:54:52. Date alone cannot select NISQ. |
| September 1, 2026: six | Individual Paradise dump clocks and release-specific exports unavailable. |
| September 18, 2026: one, two attempt placeholders | Dump/event identity remains unresolved. |

All 59 associations remain `needs_review`; UTC event/integration windows are blank. File bounds, sensor identity and a plausible pulse do not by themselves approve calibration applicability or full-tail coverage.

## Procedure changes and verification

The October 20 protocol clarification allowed shared calibration across numbered probes of the same device class and treated final stock volume as optional. The later [October 26 review](../salt_dilution/results/calibrations/2026-10-26_probe_review/README.md) retains notebook associations but requires support for the physical calibration/river pair; same model alone does not establish interchangeability. The nominal starting-water basis remains explicit where final stock volume was not measured.

The earlier repair reported 32 passing tests, including checks of all 31 registered local source/output/metadata sets. Its historical `validation_report.json` is retained at `7d7647e2fc289147d007035731eba96db89ada0d`. The local [audit bundle](../salt_dilution/results/2026-10-20_record_reconciliation/README.md) contains the driver, baseline and preservation checks; generated files remain Git-ignored. These are historical checks, not fresh results for another revision. See [validation](validation.md) for current test commands and [the saved calibration bundle](../salt_dilution/results/calibrations/README.md) for subsequent provisional fits. Q remains unimplemented in the maintained workflow.
