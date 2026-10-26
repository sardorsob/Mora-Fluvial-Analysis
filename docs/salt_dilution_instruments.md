# Salt-discharge instruments and procedure history

Reviewed October 24, 2026. This catalog separates confirmed equipment, plausible legacy-meter candidates, recording software and experimental procedure changes. It is a research reference, not an approved field SOP or proof that an instrument was calibrated.

**The main finding:** Aqua TROLL equipment appears in the available July 2025 records. A September 18, 2026 notebook entry specifically changes the calibration approach to use the river TROLL instruments rather than the General instruments. These are different milestones. A calibration fitted on one instrument is not automatically applicable to another downstream instrument, even when both report conductivity.

## Instrument catalog

| Equipment or label | Role and evidence | Identification | Documentation |
| --- | --- | --- | --- |
| In-Situ Aqua TROLL 200 | Water sensor/logger. Raw report headers name this model; both actual and specific conductivity occur. A July 3, 2025 workbook contains Aqua TROLL 200 and Wireless TROLL Com properties. | Confirmed model in the available records; exact device, settings and role must still be resolved per recording. | [100/200 operator manual](https://in-situ.com/pub/media/support/documents/Aqua_TROLL_100-200_Manual.pdf); [measurement-methodology technical note](https://in-situ.com/uk/pub/media/support/documents/Aqua-TROLL-200-Measurement-Methodology-Tech-Note.pdf) |
| In-Situ Wireless TROLL Com | Communications adapter between a cabled instrument and VuSitu or a computer. Its name can appear in a report without identifying the water sensor. | Confirmed in raw headers and earlier field-photo interpretation. | [Manufacturer instructions, document 0031242](https://in-situ.com/pub/media/support/documents/0031242.pdf) |
| In-Situ TROLL Com Plus | Later communications adapter. Appears in September 18 and October 2026 raw reports and collaborator examples. | Confirmed report identity; not a conductivity-sensor model. | [In-Situ instructions, 2025-05-05, document 0104032, distributor-hosted original](https://www.jsgroup.ie/wp-content/uploads/2025/09/TROLL-Com-Plus-Instructions.pdf) |
| VuSitu | Mobile interface for configuration, calibration, live readings, logging and export. App/firmware version and recording mode matter. | Confirmed by report layout and prior field photographs. | [Manufacturer app page](https://in-situ.com/en/products/vusitu-app); [In-Situ's application listing](https://play.google.com/store/apps/details?id=com.insitu.vusitu) |
| Win-Situ 5 | Desktop configuration/download/export software. July 2026 source CSVs explicitly identify `WinSitu.exe`, version 5.7.8.0. | Confirmed export software; export date is not the field date. | Software/clock/logging sections of the [Aqua TROLL manual](https://in-situ.com/pub/media/support/documents/Aqua_TROLL_100-200_Manual.pdf) |
| General1 / General2 | Legacy labels on conductivity/temperature logs. Worksheets include `CDA01001` and generic `Ch1_Value`, `Ch1_Unit`, `Ch2_Value`, `Ch2_unit` columns. | Recording identities are established; exact manufacturer, meter, attached probe and compensation settings remain unconfirmed. | Ranked candidates below; the [CD-4307SD manual](https://www.mrclab.co.il/Media/Uploads/CD-4307SD_OPR.pdf) documents the matching filename family. |
| Black case in the supplied photograph | Closed transport/instrument enclosure with cable and an obscured, blurred label. The meter/sensor inside is not visible. | Unidentified contents. Do not assign a manufacturer, calibration specification or General1/2 identity from the case alone. | Requires a legible meter/probe label or original equipment record. The full photograph is not reproduced here. |
| Pipette/syringes, vessels, salt scale and mixing implements | Prepare known salt stock and additions, establish receiving volume and mix samples uniformly. | These functions are documented; particular makes/models and calibration certificates are not established. | Follow the actual equipment's instructions once identified; maintain measured quantities and method changes in the [curated records](../salt_dilution/data/records/README.md). |

The water sensor measures conductivity. A communications adapter, software connection, marked file or stirred sample does not by itself calibrate another sensor. Distinguish the deployed water-temperature channel from an adapter's air-temperature/barometric channels. Wireless TROLL Com instructions explicitly describe data transfer rather than internal storage. [Manufacturer instructions](https://in-situ.com/pub/media/support/documents/0031242.pdf)

### Ranked guesses for the legacy General system

These are leads, not confirmed inventory entries. No correction or manufacturer-specific acceptance limit should be selected from them yet.

1. **General Tools DCT430SD: moderate-confidence candidate.** The General name, conductivity/temperature pairing and Excel/SD-card workflow fit the recording labels. General's original catalog describes this model with a separate probe and adjustable temperature compensation. The exact model is not readable in the photo. [Manufacturer catalog, printed I-108; owner-hosted archived/indexed source](https://generaltools.com/pub/media/wysiwyg/ICAT_14_INSTRUMENTS_CATALOG_04_03_14_op2.pdf)
2. **Lutron/MRC CD-4307SD family: moderate-confidence candidate.** The model's original manual explicitly describes `CDA01/CDA01001.XLS`, matching the retained worksheet/export pattern. Shared file naming does not prove which brand, hardware revision or firmware was used. [Original operation manual, printed pp. 18–20](https://www.mrclab.co.il/Media/Uploads/CD-4307SD_OPR.pdf)
3. **Another compatible SD logger or a meter inside a separate enclosure: unresolved alternative.** The case and generic columns cannot exclude this. A General/Lutron-style export should not be treated as a unique hardware fingerprint.

For the CD-4307SD candidate, the manual describes conductivity/TDS/salt modes, temperature, a carbon-rod probe, selectable ranges, automatic/manual SD logging, clock settings, hold/min/max, backlight and serial/USB output. Its default compensation is 2%/°C; the setting is adjustable. The default recording interval is 2 seconds; a nominal 1-second option carries a missing-data warning. Manual calibration uses known standards and requires immersed, de-bubbled sensing elements. These are **candidate-model** features, not recovered field settings. [Manual, printed pp. 1–4, 8–12, 15–27](https://www.mrclab.co.il/Media/Uploads/CD-4307SD_OPR.pdf)

An important conditional consequence is that this candidate can export temperature-compensated EC with a generic `uS` label. Such a label is not sufficient to call the channel uncompensated “actual conductivity.” The range's accuracy is also specified against full scale, not simply the observed reading. Confirm model, range, units and settings before using those specifications.

## What the available timeline establishes

Dates below distinguish source acquisition/field headings from later exports. Source files live in the date folders linked below; notebook locators refer to the supplied scan `Document_261007_160953.pdf` unless otherwise stated. Original scans remain in authorized local storage.

| Date | Evidence | Interpretation and limit |
| --- | --- | --- |
| July 2, 2025 filename | A General2 test workbook has the `CDA01001` sheet, but its internal dates are in 2022 and its first channel uses `%` with no usable second-channel unit. | Setup/test evidence with clock/mode problems; not a validated dated conductivity trial. [Source folder](../salt_dilution/data/raw/20250703/) |
| July 3, 2025 | The Aqua TROLL workbook's acquisition sheet identifies Aqua TROLL 200, a Wireless TROLL Com, a 12:37 report start and both EC channels. A separate GeneralLogger file has July 3 timestamps and the generic channel format. | Earliest located Aqua TROLL evidence in this corpus, with concurrent legacy-system evidence. The workbook filename and embedded sensor identity disagree; it is not proof of the first-ever park deployment. [Source folder](../salt_dilution/data/raw/20250703/) |
| July 8–9, 2025 | Native metadata gives Aqua TROLL 200, a July 8 log start, Linear mode and a one-minute interval. July 9 contains original TROLL live/log exports and General1/2 files. | Strong native-export evidence of overlapping systems, not a General-only era ending in summer 2026. [Source folder](../salt_dilution/data/raw/20250709/) |
| July 24, 2025 | Raw calibration reports identify Aqua TROLL 200; the notebook assigns a TROLL to a mixing/calibration role. | Aqua TROLL was already used for calibration in at least some early trials; do not assume every pre-September-2026 calibration used General. [Source folder](../salt_dilution/data/raw/20250724/); scan `Document_261007_113237.pdf`, p. 5 right |
| July–September 2025 | General-labelled and Aqua TROLL records coexist on several dates; General-labelled files remain in the September 17 folder. | Roles could differ: calibration, mixing and attenuation are separate assignments. Last retained General export is not proof of last use. [September 17 folder](../salt_dilution/data/raw/20250917/) |
| July 16 / July 21 / August 2026 | Win-Situ CSVs identify Aqua TROLL 200. For example, July 16 data were exported on August 14. | Use in-file log dates and measured sensor properties, not the export filename's latest date. [July folder](../salt_dilution/data/raw/20260716/); [August folder](../salt_dilution/data/raw/20260806/) |
| September 3, 2026 notes | WRD notes discuss specific conductivity, known-mass calibration and use of field meters; several receiver quantities and assignments remain qualified. | A method-development milestone, not an unambiguous model change. Scan pp. 5–8. |
| **September 18, 2026 notes** | Page 9 right says calibration will use the same river TROLL instrumentation instead of Generals. It records a weak secondary-dilution attempt, then a restart with the initial stock. Page 9 left contains a corrected/questioned retrospective TROLL map. | **Direct evidence of a same-river-instrument calibration decision.** It is not the first Aqua TROLL use, and the written intention does not prove every later assignment was implemented identically. [Source folder](../salt_dilution/data/raw/20260918/) |
| October 2–5, 2026 | Repeated mass-stock tables, paired actual/specific readings and TROLL/communications reports. October 2 includes a “same troll, same calibration” annotation. | Track each physical instrument, stock/attempt and release; the annotation alone does not prove a reused numerical fit. Scan pp. 12–21; [October source folder](../salt_dilution/data/raw/20261002/). |

The available evidence therefore locates an explicit **September 18 calibration-practice change**, while placing Aqua TROLL use by **July 2025**. The precise first adoption date, every historic General role and the final General deployment are not established.

## Four operations that must remain separate

| Operation | What it establishes | What it does not establish |
| --- | --- | --- |
| Instrument calibration/verification | A particular meter/probe's EC and temperature response against suitable standards/reference measurements. | The NaCl concentration-per-EC coefficient for every stream sample. |
| Experimental salt calibration | Relationship between known added salt concentration and the chosen instrument's EC channel under the recorded conditions. | Another instrument's gain, temperature treatment or clock. |
| Cross-instrument comparison | Whether two meter/probe pairs agree across relevant shared solutions, temperatures and response ranges; any justified transfer relationship. | Historical equivalence merely because a comparison passes today. |
| Clock synchronization/reconciliation | Relationship between recorded times and a common time basis, including offset and possible drift. | Agreement in conductivity magnitude or temperature compensation. |

Aqua TROLL reports actual EC and derives specific EC using temperature and reference settings. Its software can adjust the sensor response; that instrument adjustment/cell constant is different from the [experimental concentration-per-EC K](calibration.md). TDS, salinity and water-density outputs are derived quantities and are not substitutes for a tracer-specific calibration. [Manufacturer measurement-methodology note](https://in-situ.com/uk/pub/media/support/documents/Aqua-TROLL-200-Measurement-Methodology-Tech-Note.pdf)

The manual distinguishes measurement/output rate from internal logging modes and requires stable calibration readings. Its indexed specifications give 1-second maximum output/Event logging and 1-minute Linear/Linear Average logging; actual timestamps and the saved mode control interpretation. A phone's refresh display does not prove that an independent downstream logger saved every second. [100/200 manual, printed pp. 14, 28, 35–39](https://in-situ.com/pub/media/support/documents/Aqua_TROLL_100-200_Manual.pdf)

The stirred pipette sequence establishes an experimental relation only for the instrument taking those stabilized readings. Mixing the receiver and removing bubbles are necessary sample-handling steps; they do not synchronize or calibrate an instrument left downstream. Manufacturer instrument verification, experimental salt calibration and the recorded field method all remain necessary considerations. [USGS specific-conductance guidance](https://pubs.usgs.gov/tm/09/a6.3/tm9-a6_3.pdf)

## Can a coefficient be carried to another instrument?

Original salt-dilution research recommends using the same probe for calibration and discharge and calibrating near stream temperature. Differences in EC response, temperature measurement and compensation can matter even between similar probes. Its examples do not quantify this project's General–TROLL difference. It also treats stock-water chemistry as a separate issue: a DI-water stock may require an ionic-background dilution correction. The current provisional DI-stock fits should not be treated as having evaluated that correction. [Richardson et al. (2017), abstract, methods and printed pp. 10–12](https://confluence-jwsm.ca/index.php/jwsm/article/view/1/2)

The following is a conditional mathematical explanation, not a measured correction for these instruments. Let A be the calibration instrument and B the downstream instrument:

```text
C = k_A × excess_EC_A
EC_B = g × EC_A + b

If g and b are stable over the relevant conditions:
excess_EC_B = g × excess_EC_A
k_B = k_A / g
```

Here `C` is added tracer concentration, `k_A` the experimental factor for A, `g` the relative EC scale and `b` a constant offset. Subtracting each instrument's own background cancels a constant `b`; it does not cancel `g`. For a mass slug, `Q = delivered_mass / integral(C dt)`. Using A's factor directly on B would give `Q_estimated / Q_true = 1/g`. An illustrative 10% high EC scale would therefore make Q about 9.1% low. This is an example, not an estimate of this dataset's error.

Temperature-dependent gain, drifting background, nonlinearity or a sensor that has not equilibrated require more than a constant transfer factor. A high R² on A can coexist with a wrong B scale or an incorrect stock recipe. Do not use the paper's typical factor, an app label or a nominal manufacturer accuracy as an invented historical repair.

### Unsynchronized clocks are a different problem

A constant time offset shifts a complete pulse without changing its area when the correct elapsed intervals and complete pulse are retained. It still affects event selection, travel times and alignment with seismic or other observations. Drift/time-scale error, timestamp rounding, missing samples, truncated tails and wrong windows can change the area. Apparent lag between probes at different stream locations includes physical travel time and cannot alone identify clock error.

The legacy July 9 General example has irregular recorded intervals. A July-2-labelled test has internal 2022 dates, and the July 3 Aqua workbook contains repeated minute-level timestamps in some sheets. These are concrete reasons to inspect clocks and intervals; no historical clock correction was inferred in this research. The original acquisition timestamps remain evidence, while current normalized outputs must not be treated as independently verified clocks.

## What can be checked or repaired

1. **Recover identities and settings first.** Identify the old meter and attached probe, match General1/2 to physical equipment, and record source units, EC mode, compensation algorithm/coefficient/reference temperature, clock, logging mode, firmware and calibration history. The present photo is insufficient for that assignment.
2. **Search existing comparison evidence.** Look for same-solution multi-level measurements, instrument-calibration reports and contemporaneous clock checks. Historical overlap can support a bounded transfer correction; nearby dates or similar-looking curves cannot establish it alone.
3. **Make a controlled comparison when equipment is available.** Under the approved field/lab procedure, verify each meter/probe, use common well-mixed solutions spanning the intended EC range at relevant temperatures, wait for stabilization, and record readings on both instruments. Prefer an experimental salt calibration on each deployed sensor. A modern comparison characterizes present agreement and needs an explicit limit if applied to older records.
4. **Correct only what the evidence supports.** Preserve raw readings; save any temperature/scale/time transformation and its provenance separately. Missing temperature or unknown compensation can prevent reconstruction of actual EC. Missing pulse samples, historical gain changes or unknown old calibration cannot be uniquely recovered from another instrument's successful regression.
5. **Keep unsupported cases provisional.** If no historical comparison can establish transfer, retain the fitted coefficient as evidence for its calibration device and mark downstream applicability unresolved. Evaluate uncertainty/sensitivity or obtain an independent discharge reference before promoting a result.

For future recording documentation, associate each trial with the **calibration meter/probe**, **downstream meter/probe**, **EC channel and units**, **temperature treatment**, **clock evidence**, and **comparison/calibration record**. Preserve model revisions and time validity. These are documentation requirements; this catalog does not change the agreed CSV headers or fill unmeasured values.

## Implications for the current repository

- The 49 saved fits remain provisional calculations from their recorded inputs. Their existence does not validate cross-instrument application. The October 20 permission to share across numbered probes must not be generalized to a different meter family, and even same-model agreement needs an appropriate check or stated uncertainty.
- `probe_01` through `probe_06` are repository aliases for registered measured sensor identities. `General1` and `General2` are legacy source labels. Similar numbers do not establish that they are the same devices.
- `general_logger` in parser metadata identifies an ingestion route, not a verified manufacturer. The Aqua TROLL workbook itself goes through the Excel route. Inspect the raw in-file properties before assigning hardware.
- The 48 populated input rows currently reference 31 registered files and none has a General-labelled path. This does not prove that every calibration-device/stream-device pairing is resolved; source roles, including uncertain older calibration assignments, still control applicability.
- No source measurements, calibration links, K values, result hashes, clocks or Q values were changed by this research. The first saved bundle remains intact under [results/calibrations](../salt_dilution/results/calibrations/README.md).

## Source access and confidence

Local workbook/report headers and the September 18 scan were inspected directly. The old-case model guesses are explicitly inferred. The same-probe recommendation is direct primary research, corroborated by independent instrument-quality guidance. In-Situ's linked PDFs and the General archived catalog were readable through owner-domain indexed content but returned 403/404 on direct retrieval here; their full current contents were not independently downloaded or visually reviewed. The CD-4307SD operation manual and distributor-hosted In-Situ Com Plus instructions were accessible as original technical documents. An inaccessible link is not evidence that a model or feature does not exist.

This catalog covers the functionality relevant to salt-discharge work; it is not a reproduction of every manual or a complete fleet inventory. Confirm the old nameplate, applicable manual revision and actual settings before selecting a hardware-specific correction. Preserve future changes as dated additions with source evidence, rather than replacing this history with the newest procedure.
