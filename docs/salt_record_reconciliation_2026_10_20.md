# Salt-record reconciliation: October 20, 2026

The reviewed tables at `5cd3f5e443bba6b0e379f735fa241601d837cad3` contained four duplicate calibration IDs and 16 orphan point references. The repair uses source blocks, preserving every reviewed quantity, source reference, date and point observation. `trials.csv` is byte-for-byte unchanged. No parser, notebook, scientific calculation or raw/processed observation was changed.

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

Before K or Q, select one complete probe/channel/calibration/release case, establish the stock concentration and delivered input, reconcile clocks, and review baseline/full rise/tail. July 21 explicitly names Pacific Daylight Time; this alone does not select an integration interval. October export-creation offsets are not measurement-clock evidence. File bounds remain observations rather than analysis windows. Calibration fitting and discharge modules remain unimplemented.

## Verification

The 32 tests pass with local recording checks enabled: 22 existing parser/portability tests, nine table checks and one opt-in file check. They cover unique keys, foreign keys, a lossless point join, manifest hashes, aliases, paired/split/shared recordings, source/export dates, original timestamp selection, channel/probe consistency and explicit pending states. The file check reads all 31 registered source/output/metadata sets and confirms measurement serials, row counts and available selected channels.

Run the default clone-safe suite with `python -m unittest discover -s tests -v`. Set `MORA_CHECK_LOCAL_RECORDINGS=1` to include ignored local outputs. The [local audit bundle](../salt_dilution/results/2026-10-20_record_reconciliation/README.md) retains the migration driver, baseline snapshot, reconciliation summary and preservation verification. Generated observations and audit artifacts remain Git-ignored. No K or Q result is claimed.
