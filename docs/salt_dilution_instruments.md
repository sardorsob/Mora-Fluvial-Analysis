# Salt-discharge instruments and procedure history

The main discharge workflow uses Aqua TROLL river recordings and their associated salt calibration. General meters served farther-downstream attenuation monitoring. A General-to-TROLL transfer is therefore a conditional issue for an actual cross-instrument pairing, not a default missing calculation.

Aqua TROLL equipment is documented by July 2025. The September 18, 2026 notebook decision to calibrate with the river TROLL instruments is a later **procedure change**, not the first use of Aqua TROLLs. This catalog distinguishes field evidence, reported identities and manufacturer capabilities. It does not establish historical settings or instrument calibration, and it is not an approved field procedure.

## Instrument catalog

| Equipment or label | Role and evidence | Documentation |
| --- | --- | --- |
| In-Situ Aqua TROLL 200 | Water sensor/logger named in raw report headers and the July 3, 2025 workbook. Exports distinguish actual and specific conductivity. Resolve the physical sensor and role per recording. | [100/200 operator manual](https://in-situ.com/pub/media/support/documents/Aqua_TROLL_100-200_Manual.pdf); [measurement-methodology note](https://in-situ.com/uk/pub/media/support/documents/Aqua-TROLL-200-Measurement-Methodology-Tech-Note.pdf) |
| Wireless TROLL Com | Communications adapter, not the water sensor. Confirmed in workbook/report properties. Its serial is not a substitute for sensor identity. | [In-Situ instructions, document 0031242](https://in-situ.com/pub/media/support/documents/0031242.pdf) |
| TROLL Com Plus | Communications adapter appearing in September 18 and October 2026 reports. | [In-Situ instructions, 2025-05-05, document 0104032, distributor-hosted original](https://www.jsgroup.ie/wp-content/uploads/2025/09/TROLL-Com-Plus-Instructions.pdf) |
| VuSitu | Mobile software for configuration, calibration, live readings, logging and export. App/firmware version and recording mode matter. | [Manufacturer app page](https://in-situ.com/en/products/vusitu-app); [application listing](https://play.google.com/store/apps/details?id=com.insitu.vusitu) |
| Win-Situ 5 | Desktop configuration/download/export software. July 2026 CSVs name `WinSitu.exe` 5.7.8.0. Export date is not field date. | Software/clock/logging sections of the [Aqua TROLL manual](https://in-situ.com/pub/media/support/documents/Aqua_TROLL_100-200_Manual.pdf) |
| General1 / General2; General Tools DCT430SD | Legacy conductivity/temperature logs. DCT430SD is the user-reported model, clarified October 26, 2026; each physical meter/probe and session role still need mapping. General labels are not numbered Aqua TROLL aliases. | [General CDPB03 replacement probe naming DCT430SD](https://generaltools.com/replacement-conductivity-salt-tds-probe-for-dct430sd); [General ICAT14 catalog, printed I-108, mirrored text](https://device.report/m/166bfa07edea4027ca8616912ad337b7a1513790b973905686cc5f5301b1d802) |
| Black transport case in the supplied photograph | The blurred label and closed enclosure do not identify its contents or establish a General1/2 mapping. | A legible meter/probe label or equipment record is needed. |
| Pipette/syringes, vessels, scale and mixing implements | Establish stock/addition quantities and uniform mixing. Makes, models and calibration certificates are not established. | Retain measured quantities and procedure changes in the [curated records](../salt_dilution/data/records/README.md). |

Distinguish water-temperature channels from adapter air-temperature/barometric channels. Wireless TROLL Com transfers data rather than storing it internally. A connected adapter or stirred sample does not calibrate a separate water sensor. [Manufacturer instructions](https://in-situ.com/pub/media/support/documents/0031242.pdf)

`general_logger` in parser metadata is an ingestion route, not a manufacturer identification: an Aqua TROLL workbook also uses the Excel reader. `probe_01`–`probe_06` are aliases for registered measured sensor identities. Similar numbers in General labels do not establish equivalence.

## What the available timeline establishes

Dates distinguish acquisition/field headings from later exports. Notebook locators below refer to `Document_261007_160953.pdf` unless another scan is named. The retained transcription/provenance preserves these locators; original scans are unavailable at their recorded Downloads paths for a fresh check.

| Date | Evidence | Interpretation and limit |
| --- | --- | --- |
| July 2, 2025 filename | General2 test workbook, `CDA01001` sheet, internal 2022 dates, `%` channel and no usable second-channel unit. | Setup/test evidence with mode/clock problems, not a validated conductivity trial. [Folder](../salt_dilution/data/raw/20250703/) |
| July 3, 2025 | Workbook properties identify Aqua TROLL 200, Wireless TROLL Com, a 12:37 report start and both EC channels. A separate GeneralLogger file has July 3 timestamps. | Earliest located Aqua TROLL evidence, alongside General records. Workbook filename and measured identity disagree; this is not proof of first park deployment. [Folder](../salt_dilution/data/raw/20250703/) |
| July 8–9, 2025 | Native Aqua TROLL metadata: July 8 log start, Linear mode, one-minute interval. July 9 has TROLL live/log and General1/2 files. | Both systems were in use. [Folder](../salt_dilution/data/raw/20250709/) |
| July 24, 2025 | Aqua TROLL calibration reports and a notebook mixing/calibration assignment. | Some early calibrations already used TROLLs. [Folder](../salt_dilution/data/raw/20250724/); `Document_261007_113237.pdf`, p. 5 right. |
| July–September 2025 | General and Aqua TROLL records coexist; September 17 retains General files. | Calibration, mixing and attenuation are distinct roles. Last retained export does not prove last use. [September folder](../salt_dilution/data/raw/20250917/) |
| July 16 / July 21 / August 2026 | Win-Situ CSVs identify Aqua TROLL 200; July 16 observations were exported August 14. | Use acquisition dates and sensor properties rather than export dates. [July](../salt_dilution/data/raw/20260716/); [August](../salt_dilution/data/raw/20260806/) |
| September 3, 2026 | WRD notes discuss specific EC, known-mass calibration and field meters; receiver quantities/assignments remain qualified. | Method development, not an established model change. Scan pp. 5–8. |
| **September 18, 2026** | Page 9 right calls for calibration with the same river TROLL instruments instead of Generals; a weak secondary dilution is followed by an initial-stock restart. Page 9 left questions/corrects an earlier TROLL map. | Direct evidence of a same-river-instrument calibration decision. Written intention does not prove identical implementation for every later trial. [Folder](../salt_dilution/data/raw/20260918/) |
| October 2–5, 2026 | Mass-stock tables, paired EC channels and TROLL reports; October 2 says “same troll, same calibration.” | Track each instrument, preparation and release; the annotation does not establish reuse of a particular numerical fit. Scan pp. 12–21; [October folder](../salt_dilution/data/raw/20261002/). |
| October 26, 2026 identification clarification | User identifies the General conductivity/TDS/salt meter as `dtc430sd`; published spelling is DCT430SD. | Identification date, not adoption/calibration date; no historical settings or transfer coefficient supplied. |

The precise first Aqua TROLL adoption, every historical General role and the final General deployment remain unknown. The [record review](../salt_dilution/results/calibrations/2026-10-26_probe_review/README.md) resolves 13 preparation identities using electronic sequences or supported within-trial continuity. It leaves 19 preparation identities unresolved and does not establish a cross-device transfer.

## Four operations that must remain separate

| Operation | Establishes | Does not establish |
| --- | --- | --- |
| Instrument calibration/verification | A meter/probe's EC and temperature response against standards/reference measurements. | The salt concentration-per-EC coefficient for every sample. |
| Experimental salt calibration | Added concentration versus the chosen instrument's EC under recorded conditions. | Another instrument's gain, temperature treatment or clock. |
| Cross-instrument comparison | Agreement across common solutions, temperatures and ranges; a transfer relationship where justified. | Historical equivalence simply because a comparison passes today. |
| Clock reconciliation | Recorded time versus a common basis, including offset and drift. | Conductivity-scale agreement. |

Aqua TROLL derives specific conductivity from actual conductivity and temperature using reference settings. Its instrument adjustment/cell constant is different from experimental K. TDS, salinity and water-density outputs are derived quantities, not substitutes for a tracer-specific calibration. [Measurement-methodology note](https://in-situ.com/uk/pub/media/support/documents/Aqua-TROLL-200-Measurement-Methodology-Tech-Note.pdf)

The Aqua TROLL manual distinguishes output rate from internal logging: indexed specifications list 1-second maximum output/Event logging and 1-minute Linear/Linear Average logging. Use saved mode and actual timestamps; a phone refresh does not establish an independent logger's sampling interval. Calibration requires stable readings, adequate immersion and sample handling. Mixing and removing bubbles do not calibrate or synchronize a meter left downstream. [100/200 manual, printed pp. 14, 28, 35–39](https://in-situ.com/pub/media/support/documents/Aqua_TROLL_100-200_Manual.pdf); [USGS specific-conductance guidance](https://pubs.usgs.gov/tm/09/a6.3/tm9-a6_3.pdf)

## October 26 DCT430SD identification and processing implications

The user report supersedes the earlier equally ranked General/Lutron guesses. General's [CDPB03 page](https://generaltools.com/replacement-conductivity-salt-tds-probe-for-dct430sd) confirms the DCT430SD product name, not the probe attached to each field unit. The earlier R. T. Clark/IGU-16 recollection refers to seismic equipment: [R. T. Clark](https://rtclark.com/product/smartsolo-nodal-system/), [SmartSolo IGU-16](https://smartsolo.com/igu-16.html).

The General ICAT14 catalog specifies adjustable automatic temperature compensation, 0–5%/°C, and conductivity accuracy of 2% of full scale plus one digit. These are capabilities/tolerances, not historical settings or measured corrections. The applicable DCT430SD operator-manual revision, reference temperature, compensation equation/coefficient, range, calibration history and probe remain unverified. [Manufacturer catalog, printed I-108, mirrored text](https://device.report/m/166bfa07edea4027ca8616912ad337b7a1513790b973905686cc5f5301b1d802); [original catalog location](https://generaltools.com/pub/media/wysiwyg/ICAT_14_INSTRUMENTS_CATALOG_04_03_14_op2.pdf)

A generic `conductivity`, `uS` or `mS` label may already include temperature compensation; it does not establish uncompensated actual EC or equivalence to Aqua TROLL specific EC. The In-Situ manual describes default Standard Methods 2510B treatment for specific conductivity. Recover the actual temperature, reference temperature and algorithm before converting a channel. Preserve source labels and observations; model identity alone is not a reason to move historical values between actual and specific columns. [In-Situ manual, mirrored text](https://manualzz.com/doc/66578284/in-situ-cfg-at2dl-aqua-troll-200-data-logger-manual)

The earlier CD-4307SD candidate manual matches the `CDA01/CDA01001.XLS` naming pattern but is not proof of General hardware. It describes conductivity/TDS/salt modes, a carbon-rod probe, selectable ranges, manual/automatic logging, clock and serial/USB functions. Its adjustable 2%/°C compensation default, 2-second default interval and missing-data warning for 1-second logging are **candidate-model specifications**, not General field settings. Its calibration uses known standards and immersed, de-bubbled sensing elements. Do not import those defaults into DCT430SD records. [Original MRC manual, printed pp. 1–4, 8–12, 15–27](https://www.mrclab.co.il/Media/Uploads/CD-4307SD_OPR.pdf)

## Can a coefficient be carried to another instrument?

Salt-calibration research recommends the same probe for calibration and discharge, near stream temperature. It also identifies a separate correction for ionic-background dilution when using distilled-water stock; the current DI-stock fits have not implemented that correction. Published uncertainty or a typical literature K is not a measured error bound or replacement coefficient for this project. [Richardson et al. (2017)](https://confluence-jwsm.ca/index.php/jwsm/article/view/1/2)

For a conditional linear transfer, let A be the calibration instrument and B the river instrument:

```text
C = k_A × excess_EC_A
EC_B = g × EC_A + b

If g and b are stable over the relevant conditions:
excess_EC_B = g × excess_EC_A
k_B = k_A / g
```

`C` is added tracer concentration, `k_A` the experimental slope, `g` the relative EC scale and `b` a constant offset. Each instrument's own background subtraction cancels a constant offset, but not a scale difference. For a mass slug, with compatible mass/concentration/time units:

```text
Q = delivered_mass / integral(C dt)
Q_estimated / Q_true = 1/g   [if k_A is incorrectly applied to B unchanged]
```

A hypothetical 10% high EC scale gives Q about 9.1% low. This is an algebraic illustration, not a dataset error estimate. Temperature-dependent gain, drift, nonlinearity or incomplete equilibration need more than a constant factor. High calibration R² cannot diagnose transfer error or an incorrect stock recipe.

| Selected calibration/river pair | Treatment |
| --- | --- |
| Same physical sensor, compatible channel/temperature treatment, stable response | No extra brand correction is automatically needed: a stable linear scale response is included in the empirical slope. Instrument checks, mixing and uncertainty review still apply. |
| Different devices with valid common-solution comparisons over the relevant range/temperatures | A measured transfer may be justified. Use `k_B = k_A/g` or transform B onto A's scale, not both; save validity dates/range and uncertainty. |
| Different devices or unknown settings without suitable comparison | Keep the fit provisional for its calibration device. Do not invent a historical correction from specifications or unrelated river events. |

These are applicability conditions, not an automatic gate implemented by the runner. All 48 populated input rows currently reference 31 files with no General-labelled path, but some calibration-device/river-device relationships remain unresolved.

### Unsynchronized clocks are a different problem

A constant offset shifts a complete pulse without changing its area when correct elapsed intervals and the whole pulse are retained. It still affects event selection, travel times and seismic alignment. Drift, time-scale error, rounding, gaps, truncated tails and wrong windows can change the integral. Lag between different stream locations also includes physical travel time and cannot alone identify clock error.

July 9 General records have irregular intervals; the July-2-labelled test has 2022 dates; some July 3 Aqua workbook sheets repeat minute-level timestamps. Normalized clocks are not independently verified clocks. No historical clock correction is implemented.

## What can be checked or repaired

For each discharge candidate, establish calibration and river sensor identities, channel/units, temperature treatment, preparation, clock evidence and comparison validity. First seek contemporaneous common-vessel readings and instrument-calibration records. A present-day comparison can characterize current agreement but cannot prove unchanged historical response. Different banks or dates confound scale differences with travel, mixing and real flow changes.

When an approved comparison is possible, use well-mixed common solutions spanning relevant EC and temperature, allow stabilization and record both instruments. Preserve raw readings and save any supported scale/temperature/time transformation separately with its evidence and uncertainty. Missing samples or unknown historical gain cannot be uniquely recovered from another successful fit. Retain unsupported cases as provisional and assess sensitivity or seek independent discharge evidence.

Keep conductivity, TDS and salt-percent modes distinct. General identity does not fix clock errors or the DI-stock issue. The [calibration guide](calibration.md) explains the existing provisional calculation; no instrument-transfer or clock correction is currently applied.

## Source access and confidence

The equipment timeline draws on workbook/report headers and retained notebook evidence; reported model identification is not nameplate verification. General's replacement-probe page, manufacturer-authored mirrored catalog, MRC manual and Richardson paper are accessible sources. In-Situ and USGS PDF links remain the relevant originals but direct retrieval was blocked during the documentation check; the earlier catalog also records limited access to some manufacturer originals. The distributor-hosted Com Plus document and mirrored Aqua TROLL manual are alternatives, not proof of a field unit's manual revision or settings.

This is a catalog of relevant functionality, not a complete fleet inventory. Exact General meter/probe mapping, historical settings, first adoption/last use and unsupported calibration identities remain unresolved. Future procedure changes need dated field evidence, preserved alongside the methods they replace.
