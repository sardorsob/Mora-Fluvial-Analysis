# Salt-record reconciliation: October 20, 2026

## Latest integration of the local stock-mass corrections

[PR #2](https://github.com/sardorsob/Mora-Fluvial-Analysis/pull/2) reconciles the uploaded local commit `ff6c08597eab24253f22f47e846e6d1b40ff7372` with `main` at `54598c9a5e7d13f51fa44086fb45a53a2deb1b89`. The main branch already contains the repaired recording links and the reusable batch parser. Those changes are retained rather than replaced by the older local snapshot.

The combined calibration table preserves every uploaded quantity, date, method and source reference. Only the four old, colliding preparation IDs are mapped by source block to the established PAR C06-C09 IDs listed below. This fills 35 previously blank `stock_salt_mass_g` cells relative to main; all 43 preparations now have a nominal stock mass. The 262 observed calibration points and 59 recording-link/placeholder rows remain byte-for-byte unchanged from main, as do raw observations and parser code.

The locally deleted `manifest.json` is restored and its calibration checksum refreshed. Its finite `reviewed_setting_overrides` entry records the uploaded source commit, original calibration blob, the 35 field updates and the four source-block ID mappings. `provenance.json` is preserved as the earlier evidence snapshot: for those explicitly enumerated stock-mass cells only, the manifest overrides its older `current_csv_values`. Original `source_record` tokens, warnings, preparation stages, historical aliases and recording identities are not rewritten. Current CSV values are the calculation inputs; the override records their lineage, not another set of measurements.

The added regression tests reconstruct the uploaded calibration CSV after reversing exactly those four ID repairs and check its original Git blob hash. They also require every preparation to equal its provenance snapshot plus the finite review overlay, and require the validation summary to match the current tables and manifest. The existing parser, raw-export integration and record tests run on the combined pull request in Linux/Windows CI. See the [checks for the exact revision](https://github.com/sardorsob/Mora-Fluvial-Analysis/pull/2/checks); historical test totals below are not fresh results for this merge. The opt-in ignored local-recording check is not rerun by normal CI.

This integration does not fit K, compute discharge, change dilution stages, invent final stock volumes, select integration windows or accept abandoned/restarted preparations. A filled nominal salt mass does not remove an existing scientific warning.

## Earlier reconciliation at 7d7647e

The reviewed tables at `5cd3f5e443bba6b0e379f735fa241601d837cad3` contained four duplicate calibration IDs and 16 orphan point references. The repair uses source blocks, preserving every reviewed quantity, source reference, date and point observation. `trials.csv` is byte-for-byte unchanged. No parser, notebook, scientific calculation or raw/processed observation was changed by that earlier reconciliation.

| Source block | Historical point parent | Repaired ID |
| --- | --- | --- |
| `c_06_test_left` | `UNK-20260903-C01` | `PAR-20260903-C06` |
| `c_06_test_right` | `UNK-20260903-C02` | `PAR-20260903-C07` |
| `c_07_pr02` | `UNK-20260903-C03` | `PAR-20260903-C08` |
| `c_08_p_unknown` | `UNK-20260903-C04` | `PAR-20260903-C09` |

Original PAR C01-C05 remain unchanged. The user's PAR labels are preserved without erasing the original bench/Edith/unlabelled source context. There are 43 unique preparations and all 262 point rows join to exactly one preparation. Historical IDs and raw source records remain in provenance. Duplicate PAR IDs cannot be resolved by a global replacement; their source blocks disambiguate them.

## Recording links

The [input table](../salt_dilution/data/records/trial_inputs.csv) now has 59 rows: 48 recording associations across 31 distinct files for 28 releases, plus 11 unresolved placeholders for ten releases. This adds 40 linked rows to the previous eight while retaining all seven earlier dataset IDs and their paths. Multiple rows accommodate paired probes, split files, continuous logs spanning releases and July 17's two alternative calibration attempts.

- July 21, 2026 uses both RL/RR WinSitu recordings. Measured dates and the literal 11:10:10 dump establish the event context; August labels are export dates. The RL log spans several days and must be segmented.
- Nine October 2/4/5 live recordings use measured sensor 790481 (`probe_03`). Source blocks identify the releases, including the nonchronological October 2 T01/T02 and October 4 T03/T04 IDs. Their distinct conductivity responses support recording identity. Exact integration limits remain unselected.
- Older July 9/17/31, August 5/8 and September 3/17 records use measured sensor serials, notebook dump clocks, original mixing/bank labels and source-page assignments. Continuous logs can serve multiple releases. Overlapping spreadsheet slices and calibration-only live exports are not added as separate stream inputs.
- August 8's labelled mixing CSV preserves the conductivity observations but floors timestamps to whole minutes. The original live HTML-derived data retains seconds and is linked. July 31's existing split RR links are preserved; its separate 790481 continuous log is also linked, with bank left unresolved.

Source, processed-output and metadata hashes, channels, sensor identities and local bounds are recorded in `provenance.json`. The [records guide](../salt_dilution/data/records/README.md) explains the fields. Direct paths remain relative to the repository; the four CSV headers have not changed.

## Remaining decisions

| Unlinked releases | Reason |
| --- | --- |
| July 3, 2025: two | Notes report no downstream detection; old clock-only output was quarantined |
| August 6, 2026: one | Written dump precedes retained logs by about 15 minutes; notebook and recording sensor identities differ |
| September 1, 2026: six Paradise | Individual dump clocks and confirmed release-specific electronic exports unavailable |
| September 18, 2026: one, two attempt placeholders | Live transient exists, but dump time and stream-event versus other activity remain unresolved |

All 59 rows remain `needs_review`, and no UTC event/integration windows were invented. Forty-seven linked rows select specific conductivity; July 24 retains its explicit historical actual-conductivity route. Sixteen newly linked rows have known cross-probe notebook calibration candidates withheld from `calibration_id` and retained in provenance. Populated calibration IDs still require applicability review, especially when the titration's probe is unknown. Added rows and withheld cross-probe candidates explain why a larger table can have more empty calibration cells despite better recording coverage.

The user's recipe/quantity edits remain current. Original transcription fields, raw tokens, stock stages and historical issues are preserved separately from the dated review overlay. Select dilution stages by procedure, not by whether a secondary-water cell is filled. Nominal salt mass is not established delivered mass; spills, incomplete mixing, restarts and unequal additions remain relevant. The October 4 round-2 increments still total 46 mL.

Before K or Q, select one complete probe/channel/calibration/release case, establish the stock concentration and delivered input, reconcile clocks, and review baseline/full rise/tail. July 21 explicitly names Pacific Daylight Time; this alone does not select an integration interval. At the earlier reconciliation, October export-creation offsets were not used as measurement-clock evidence. The subsequently merged parser can retain explicit measurement-report offsets; its newly generated UTC values still require event alignment. File bounds remain observations rather than analysis windows. Calibration fitting and discharge modules remain unimplemented.

## Historical verification at 7d7647e

The earlier reconciliation reported 32 passing tests with local recording checks enabled: 22 existing parser/portability tests, nine table checks and one opt-in file check. They covered unique keys, foreign keys, a lossless point join, manifest hashes, aliases, paired/split/shared recordings, source/export dates, original timestamp selection, channel/probe consistency and explicit pending states. The file check read all 31 registered source/output/metadata sets and confirmed measurement serials, row counts and available selected channels. The complete historical report remains at `7d7647e2fc289147d007035731eba96db89ada0d:salt_dilution/data/records/validation_report.json`.

Run the default clone-safe suite with `python -m unittest discover -s tests -v`. Set `MORA_CHECK_LOCAL_RECORDINGS=1` to include ignored local outputs. The [local audit bundle](../salt_dilution/results/2026-10-20_record_reconciliation/README.md) retains the migration driver, baseline snapshot, reconciliation summary and preservation verification. Generated observations and audit artifacts remain Git-ignored. No K or Q result is claimed.

## Later October 20 protocol clarification and calibration run

The user confirmed that the numbered probes are the same device class and the notebook calibrations can be shared across those aliases. This supersedes the earlier probe-number withholding rule above. Twenty-three notebook-supported calibration IDs are restored; measured aliases remain in provenance. Thirty-one channel selections now use actual conductivity to match the available calibration observations. The table has 16 specific, 32 actual and 11 blank channel selections, with ten calibration IDs still blank. No raw, normalized or notebook measurement values were changed.

Final stock-solution volume is optional under the clarified working protocol. Mass-stock calculations use recorded preparation-water volume when no measured final volume exists, record that basis in results and leave source final-volume cells blank. The [calibration runner](calibration.md) now fits preparations and points independently of release windows. The [saved run](../salt_dilution/results/2026-10-20_calibration/README.md) includes provisional fits and explicit skips; Q remains separate.

The remaining recording gaps reflect source evidence, rather than probe-number differences. In particular, August 6 NISQ's written dump is at 14:09; paired logs start after 14:24 and peak around 14:56. The broader transcription separately records a Tahoma release at 14:54:52. Those paired files must not be assigned to NISQ merely because the dates match. July 3 lacks a confirmed downstream detection, September 1 lacks release-specific electronic exports/individual clocks, and September 18 lacks a conclusive stream-event identity. These cases do not prevent fitting other calibration series.
