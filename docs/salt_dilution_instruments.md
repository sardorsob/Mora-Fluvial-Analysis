# Salt-discharge instruments and procedure history

Initially reviewed October 24, 2026; updated October 26 with the user-reported General Tools DCT430SD identification. This catalog separates source-confirmed equipment, user-reported identification, recording software and experimental procedure changes. It is a research reference, not an approved field SOP or proof that an instrument was calibrated.

**The main finding:** Aqua TROLL equipment appears in the available July 2025 records. A September 18, 2026 notebook entry specifically changes the calibration approach to use the river TROLL instruments rather than the General instruments. These are different milestones. A calibration fitted on one instrument is not automatically applicable to another downstream instrument, even when both report conductivity.

## Instrument catalog

| Equipment or label | Role and evidence | Identification | Documentation |
| --- | --- | --- | --- |
| In-Situ Aqua TROLL 200 | Water sensor/logger. Raw report headers name this model; both actual and specific conductivity occur. A July 3, 2025 workbook contains Aqua TROLL 200 and Wireless TROLL Com properties. | Confirmed model in the available records; exact device, settings and role must still be resolved per recording. | [100/200 operator manual](https://in-situ.com/pub/media/support/documents/Aqua_TROLL_100-200_Manual.pdf); [measurement-methodology technical note](https://in-situ.com/uk/pub/media/support/documents/Aqua-TROLL-200-Measurement-Methodology-Tech-Note.pdf) |
| In-Situ Wireless TROLL Com | Communications adapter between a cabled instrument and VuSitu or a computer. Its name can appear in a report without identifying the water sensor. | Confirmed in raw headers and earlier field-photo interpretation. | [Manufacturer instructions, document 0031242](https://in-situ.com/pub/media/support/documents/0031242.pdf) |
| In-Situ TROLL Com Plus | Later communications adapter. Appears in September 18 and October 2026 raw reports and collaborator examples. | Confirmed report identity; not a conductivity-sensor model. | [In-Situ instructions, 2025-05-05, document 0104032, distributor-hosted original](https://www.jsgroup.ie/wp-content/uploads/2025/09/TROLL-Com-Plus-Instructions.pdf) |
| VuSitu | Mobile interface for configuration, calibration, live readings, logging and export. App/firmware version and recording mode matter. | Confirmed by report layout and prior field photographs. | [Manufacturer app page](https://in-situ.com/en/products/vusitu-app); [In-Situ's application listing](https://play.google.com/store/apps/details?id=com.insitu.vusitu) |
| Win-Situ 5 | Desktop configuration/download/export software. July 2026 source CSVs explicitly identify `WinSitu.exe`, version 5.7.8.0. | Confirmed export software; export date is not the field date. | Software/clock/logging sections of the [Aqua TROLL manual](https://in-situ.com/pub/media/support/documents/Aqua_TROLL_100-200_Manual.pdf) |
| General1 / General2; General Tools DCT430SD | Legacy conductivity/temperature logs with generic channel labels. On October 26 the user identified the older system as General conductivity/TDS/salt, writing `dtc430sd`; the published model spelling is `DCT430SD`. | User-reported model identification supported by the manufacturer catalog. The identity of each physical General1/2 unit, attached probe, per-session role and settings still need a source mapping. | [General Tools CDPB03 replacement-probe page naming DCT430SD](https://generaltools.com/replacement-conductivity-salt-tds-probe-for-dct430sd); [General ICAT14 catalog, printed I-108, mirrored text](https://device.report/m/166bfa07edea4027ca8616912ad337b7a1513790b973905686cc5f5301b1d802); [October 26 implications](#october-26-dct430sd-identification-and-processing-implications). |
| Black case in the supplied photograph | Closed transport/instrument enclosure with cable and an obscured, blurred label. The meter/sensor inside is not visible. | Unidentified contents. Do not assign a manufacturer, calibration specification or General1/2 identity from the case alone. | Requires a legible meter/probe label or original equipment record. The full photograph is not reproduced here. |
| Pipette/syringes, vessels, salt scale and mixing implements | Prepare known salt stock and additions, establish receiving volume and mix samples uniformly. | These functions are documented; particular makes/models and calibration certificates are not established. | Follow the actual equipment's instructions once identified; maintain measured quantities and method changes in the [curated records](../salt_dilution/data/records/README.md). |

The water sensor measures conductivity. A communications adapter, software connection, marked file or stirred sample does not by itself calibrate another sensor. Distinguish the deployed water-temperature channel from an adapter's air-temperature/barometric channels. Wireless TROLL Com instructions explicitly describe data transfer rather than internal storage. [Manufacturer instructions](https://in-situ.com/pub/media/support/documents/0031242.pdf)

### October 24 model candidates (retained history)

The following ranked guesses record the earlier review. The October 26 user identification now favors **General Tools DCT430SD** rather than leaving General and Lutron as equally supported candidates. This does not establish historical operating settings or map every General-labelled file to an individual meter. Do not import the CD-4307SD default settings into DCT430SD records.

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
| October 26, 2026 identification update | User reports the legacy General conductivity/TDS/salt meter as `dtc430sd`, matching the documented General Tools **DCT430SD** model. The earlier R. T. Clark/IGU-16 recollection was corrected to the seismic equipment. | This is the date of the identification clarification, **not** a field-adoption or calibration date. It narrows the legacy model but supplies no historical compensation setting or measured cross-device correction. |

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

1. **Recover identities and settings first.** Use the October 26 DCT430SD identification as the legacy-model lead, then match General1/2 to physical meter/probe pairs and per-session roles. Record source units, EC mode, compensation algorithm/coefficient/reference temperature, clock, logging mode, firmware and calibration history. The user report does not supply those historical settings; the earlier case photograph alone remains insufficient.
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

The October 24 review inspected local workbook/report headers and the September 18 scan directly. Its old-case model guesses are retained as historical inferences; the October 26 update adds user-reported DCT430SD identification without claiming a new nameplate or handwritten-scan inspection. The same-probe recommendation is direct primary research, corroborated by independent instrument-quality guidance. In-Situ's linked PDFs and the General archived catalog were readable through owner-domain indexed content but returned 403/404 on direct retrieval here; their full current contents were not independently downloaded or visually reviewed. The CD-4307SD operation manual and distributor-hosted In-Situ Com Plus instructions were accessible as original technical documents. An inaccessible link is not evidence that a model or feature does not exist.

This catalog covers the functionality relevant to salt-discharge work; it is not a reproduction of every manual or a complete fleet inventory. Confirm the old nameplate, applicable manual revision and actual settings before selecting a hardware-specific correction. Preserve future changes as dated additions with source evidence, rather than replacing this history with the newest procedure.


## October 26 DCT430SD identification and processing implications

### What is established, and what is not

The user-reported name is a much stronger identification lead than the earlier enclosure/photo inference. General Tools publishes the model as **DCT430SD**, and its current manufacturer page names **CDPB03** as a replacement conductivity/TDS/salt probe for it. This confirms the product naming, not which probe was attached to each historical meter. The earlier IGU-16 name belongs to the SmartSolo seismic family sold by R. T. Clark, not the conductivity instrument. [General Tools](https://generaltools.com/replacement-conductivity-salt-tds-probe-for-dct430sd); [R. T. Clark](https://rtclark.com/product/smartsolo-nodal-system/); [SmartSolo IGU-16](https://smartsolo.com/igu-16.html).

The General ICAT14 manufacturer catalog, printed page I-108, specifies automatic temperature compensation with an adjustable coefficient from 0 to 5% per degree Celsius and conductivity accuracy expressed as 2% of full scale plus one digit. These describe model capabilities, not recovered settings or a measured bias. The exact DCT430SD operator-manual revision, reference-temperature setting, compensation equation/coefficient, selected range, calibration history and attached probe for the field units remain unverified. A specification tolerance is not an offset or gain to apply to every observation. [Manufacturer catalog, mirrored text](https://device.report/m/166bfa07edea4027ca8616912ad337b7a1513790b973905686cc5f5301b1d802).

### The important channel issue

An old General reading labelled only `conductivity`, `uS` or `mS` may already have temperature compensation applied. The label alone does not establish uncompensated actual conductivity, and it does not establish numerical equivalence to an Aqua TROLL specific-conductivity channel. Aqua TROLL actual and specific channels are explicitly distinguished in its exports; a brand-level identification is not permission to relabel those established source channels. The In-Situ manual describes specific conductivity as derived from actual conductivity and temperature with default Standard Methods 2510B treatment. [In-Situ original manual, mirrored text, specific-conductivity section](https://manualzz.com/doc/66578284/in-situ-cfg-at2dl-aqua-troll-200-data-logger-manual).

Audit **only the rows whose measurement device or EC basis is uncertain** back to their notebook source block, raw instrument channel and settings. Leave observed numbers and source column labels untouched until there is evidence for a separate interpretation/correction record. In particular, do not bulk-move older `actual_conductivity_us_cm` values into the specific column based solely on this identification. `General1`/`General2` and `probe_01`/`probe_02` are different naming systems; no one-to-one mapping is established by their numbers.

### Do we add another calibration constant?

**Not solely because the model is now known.** Retain the separate notions of instrument calibration, the experimental concentration-per-conductivity slope and an inter-instrument transfer relationship.

| Evidence for the selected calibration/river pair | Appropriate treatment |
| --- | --- |
| Same physical meter/probe, compatible channel and temperature treatment, and stable response across calibration and release | A separately added brand correction is not automatically needed. The experimental slope already incorporates a stable linear scale response. This does not waive instrument checks, linearity, temperature, mixing or stability review. |
| Different devices with valid same-solution comparison over the relevant temperatures and EC range | A measured transfer may be justified. Under the affine model above, use `k_B = k_A / g` or transform B readings into A's scale, **not both**. Save validity range, dates and uncertainty. |
| Different devices, unknown temperature treatment or no suitable comparison | Keep the fit as provisional evidence for the device that produced it; downstream applicability remains unresolved. Do not invent a constant from model specifications, a typical literature K or agreement between unrelated river events. |

This is an applicability recommendation, not a newly implemented automatic gate. For actual-to-reference-temperature conversion, recover temperature, reference temperature and the actual algorithm/coefficient first. A temperature coefficient in percent per degree is not the concentration slope K, and a temperature-dependent correction need not be constant through a run. If the required historic inputs are absent, model identity alone cannot reconstruct them. [Primary salt-calibration research, pp. 1, 3 and 10–12](https://confluence-jwsm.ca/index.php/jwsm/article/view/1/2).

A constant sensor offset cancels when subtracting that sensor's own compatible background. A multiplicative scale difference does not cancel when a coefficient from another sensor is applied unchanged; see the derivation above. High within-calibration R² cannot diagnose that transfer error. Conversely, a stable scale error can cancel between an empirical calibration and a river measurement made with the same physical sensor and settings. These are conditional algebraic properties, not demonstrations that any historical unit was stable.

### Smallest useful follow-up

For each candidate discharge result, retain the calibration-device identity, downstream-device identity, source EC channel/units, temperature treatment, date-validity and comparison evidence in its applicability record. First seek contemporaneous same-vessel calibration readings from both systems. Where the original meter/probe pairs remain available, a controlled comparison across the relevant concentration and temperature range can test present equivalence, but it cannot by itself prove unchanged historical calibration. Different river banks or different release dates are not controlled same-solution comparisons: travel time, incomplete mixing and real discharge changes can confound the apparent scale difference.

Preserve conductivity, TDS and salt-percent modes as different quantities, normalize verified conductivity units, and integrate using actual elapsed timestamps only after checking gaps and clock alignment. General-meter identity does not resolve the separately documented clock errors or the DI-stock ionic-background correction. The existing generic Excel reader appropriately preserves unknown channels rather than guessing their meaning.

No new correction factor, channel reassignment, modified point, fitted result or discharge estimate is introduced by this update. The existing results remain provisional. The next step is a device-and-channel applicability audit, followed by evidence-supported conversion/refitting or a bounded sensitivity analysis where transfer cannot be established.

Source-access note for this update: General's live replacement-probe page and the manufacturer's mirrored catalog text were available; a DCT430SD-specific operator manual and historical field settings were not recovered. The primary salt-calibration paper was read with its equation page visually checked. The October 24 CD-4307SD defaults above remain candidate-document history, not verified General settings.
