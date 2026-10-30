# Salt-discharge instruments and procedure history

Aqua TROLLs record the main discharge pulse and the associated salt calibration. General meters were sometimes placed farther downstream to monitor how the pulse changed. Identify the actual sensor and its role before pairing a calibration with a recording.

## Instrument catalog

| Equipment | Use | Documentation |
| --- | --- | --- |
| In-Situ Aqua TROLL 200 | Conductivity/temperature sensor and logger; identified in native reports. Actual and specific EC are separate channels. | [100/200 manual](https://in-situ.com/pub/media/support/documents/Aqua_TROLL_100-200_Manual.pdf); [measurement methodology](https://in-situ.com/uk/pub/media/support/documents/Aqua-TROLL-200-Measurement-Methodology-Tech-Note.pdf). |
| Wireless TROLL Com / TROLL Com Plus | Communications adapters. Their identities and air-temperature/barometric channels must not be mistaken for the water sensor. | [Wireless TROLL Com instructions](https://in-situ.com/pub/media/support/documents/0031242.pdf); [Com Plus instructions, 2025-05-05, distributor-hosted original](https://www.jsgroup.ie/wp-content/uploads/2025/09/TROLL-Com-Plus-Instructions.pdf). |
| VuSitu / Win-Situ 5 | Configuration, logging and export software. July 2026 CSVs identify Win-Situ 5.7.8.0. Export time is not measurement time. | [VuSitu](https://in-situ.com/en/products/vusitu-app); logging/software sections of the [Aqua TROLL manual](https://in-situ.com/pub/media/support/documents/Aqua_TROLL_100-200_Manual.pdf). |
| General Tools DCT430SD; `General1` / `General2` labels | Conductivity/temperature meter used for additional downstream monitoring. The team identified the model on October 26, 2026; individual meter/probe assignments remain unverified. | [General replacement probe naming DCT430SD](https://generaltools.com/replacement-conductivity-salt-tds-probe-for-dct430sd); [General ICAT 14 catalog, I-108, mirrored text](https://device.report/m/166bfa07edea4027ca8616912ad337b7a1513790b973905686cc5f5301b1d802). |
| Scale, pipette/syringes, vessels and mixing tools | Measure salt/stock quantities and mix calibration solutions. Makes, models and calibration certificates are not established. | Quantities and source references are in the [curated records](../salt_dilution/data/records/README.md). |

`probe_01`–`probe_06` are aliases for measured sensor identities. General labels and adapter serials do not identify those probes. Likewise, parser metadata `general_logger` names an Excel-reading route, not a hardware manufacturer. Wireless TROLL Com transfers data; it does not store the water measurements internally.

## Farther-downstream monitoring

The General meter was sometimes farther downstream than the Aqua TROLL. Its purpose was to examine pulse attenuation/persistence and exposure from the salt releases against the river's natural mineral background. The additional dataset described for this purpose has not been supplied or identified here; existing General filenames alone do not establish which records belong to it.

That analysis needs release, location, clock, channel and background information. Conductivity responds to many dissolved ions. A small or undetectable pulse alone cannot demonstrate ecological harmlessness, and the current calibration fits do not establish an environmental-safety result.

## What the available timeline establishes

The dates below describe retained evidence, not a complete deployment inventory. Notebook pages refer to `Document_261007_160953.pdf` unless named otherwise; locators remain in transcription/provenance. Original scans were unavailable for a fresh handwriting check.

| Date | Evidence and implication |
| --- | --- |
| July 2–3, 2025 | A `General2` test file has internal 2022 dates and a `%` channel: its filename cannot establish measurement time or EC units. The July 3 workbook identifies Aqua TROLL 200 and Wireless TROLL Com alongside a General log. This is the earliest located TROLL evidence, not proof of first deployment. [Files](../salt_dilution/data/raw/20250703/). |
| July 8–9 through September 2025 | Native July metadata includes a one-minute Linear log; General and TROLL records coexist. July 24 includes TROLL calibration evidence (`Document_261007_113237.pdf`, p.5 right); General files remain on September 17. Last retained files do not establish last use. [July 9](../salt_dilution/data/raw/20250709/), [July 24](../salt_dilution/data/raw/20250724/), [September 17](../salt_dilution/data/raw/20250917/). |
| July–August 2026 | Win-Situ reports identify TROLLs; July 16 observations were exported August 14. Use acquisition metadata. [July](../salt_dilution/data/raw/20260716/), [August](../salt_dilution/data/raw/20260806/). |
| September 3, 2026 | WRD notes discuss specific EC and known-mass calibration; some receiver quantities and assignments remain uncertain (pp.5–8). |
| September 18, 2026 | Page 9 right calls for calibration with the same river TROLL instead of Generals and restarts after a weak secondary dilution. This is a procedure change, not first TROLL use. The earlier instrument map on page 9 left contains corrections. [Files](../salt_dilution/data/raw/20260918/). |
| October 2–5, 2026 | Mass-stock tables and paired EC channels accompany TROLL reports; October 2 says “same troll, same calibration” (pp.12–21). Verify each trial/role; the wording does not identify a reusable numerical coefficient. [Files](../salt_dilution/data/raw/20261002/). |

The [probe review](../salt_dilution/results/calibrations/2026-10-26_probe_review/README.md) resolves 13 preparation identities and leaves 19 unresolved. Precise adoption dates, every General role and the final General deployment remain unknown.

## Four operations that must remain separate

| Operation | What it establishes |
| --- | --- |
| Instrument calibration/verification | Meter response against standards/reference measurements. |
| Experimental salt calibration | Added tracer concentration versus the selected sensor's EC. |
| Cross-instrument comparison | Agreement or a transfer relationship over tested solutions, temperatures and ranges. |
| Clock reconciliation | Time offset/drift relative to a common basis. |

Mixing or removing bubbles does not calibrate or synchronize a separate meter left downstream. A manufacturer cell constant, experimental K, TDS and salinity are different quantities. For handling and instrument verification, use the [Aqua TROLL manual, pp.14, 28, 35–39](https://in-situ.com/pub/media/support/documents/Aqua_TROLL_100-200_Manual.pdf) and [USGS specific-conductance guidance](https://pubs.usgs.gov/tm/09/a6.3/tm9-a6_3.pdf), together with the approved field procedure.

Actual EC and specific EC use different temperature treatments. Aqua TROLL specific EC uses reference settings; its manual describes default Standard Methods 2510B treatment. Recover recorded settings before converting a channel. Generic `conductivity`, `uS` or `mS` labels do not prove uncompensated EC. The General catalog lists adjustable compensation 0–5%/°C and accuracy 2% of full scale plus one digit; these are specifications, not historical settings or correction factors. The field unit's probe, range, compensation settings and manual revision remain unresolved. [General catalog original location](https://generaltools.com/pub/media/wysiwyg/ICAT_14_INSTRUMENTS_CATALOG_04_03_14_op2.pdf); [Aqua TROLL manual, mirrored text](https://manualzz.com/doc/66578284/in-situ-cfg-at2dl-aqua-troll-200-data-logger-manual).

Use saved logging mode and timestamps to establish cadence. The TROLL manual lists 1-second maximum output/Event logging and 1-minute Linear/Linear Average logging; a phone refresh rate does not establish internal logging cadence.

## Can a coefficient be carried to another instrument?

Prefer the same physical sensor for calibration and river measurements near stream temperature. A stable sensor response is included in its empirical K; there is no automatic brand correction. A different device needs suitable common-solution comparison evidence. Present-day agreement alone does not prove historical agreement. [Richardson et al. (2017)](https://confluence-jwsm.ca/index.php/jwsm/article/view/1/2).

For a supported linear transfer, A is the calibration instrument and B the river instrument:

```text
C = k_A × excess_EC_A
EC_B = g × EC_A + b
excess_EC_B = g × excess_EC_A
k_B = k_A / g
```

`C` is added concentration, `g` the relative EC scale and `b` a constant offset. Each sensor's own background removes a constant offset; it does not remove a scale difference. Use this relationship only where gain/offset remain stable across the relevant conditions, with range, dates and uncertainty recorded. Transfer K or transform EC, not both. Without comparison evidence, keep the coefficient provisional for its original device.

For compatible mass/concentration/time units:

```text
Q = delivered_mass / integral(C dt)
Q_estimated / Q_true = 1/g   [if k_A is incorrectly applied to B unchanged]
```

A hypothetical 10% high EC scale would make Q about 9.1% low; this illustrates the equation, not a dataset error estimate. Drift, nonlinear response, temperature changes and incomplete equilibration may require more than a constant factor. No transfer correction is implemented, and fit R² cannot establish sensor identity or transfer validity. The DI-stock ionic-background correction is also still unimplemented.

### Unsynchronized clocks are a different problem

A constant offset shifts a complete pulse without changing its integral if elapsed intervals and the full pulse are retained. It affects event selection and seismic alignment; drift, gaps, rounded times or truncated windows can also change the integral. Lag between locations includes travel time, so it cannot alone identify clock error.

Retained files include irregular General intervals, the internally 2022-dated General test and repeated minute-level TROLL timestamps. No historical instrument-clock correction is implemented. See [calibration](calibration.md) for the provisional concentration calculation and [parser ingestion](parser_ingestion.md) for timestamp handling.
