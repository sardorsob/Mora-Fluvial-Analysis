# Salt-dilution discharge analysis

This workflow calculates proposed slug-injection discharge from conductivity recordings, concentration-per-conductivity calibrations (K), release quantities and explicit pulse windows. It preserves source observations and reports unresolved cases.

## Workflows

| Location | Purpose and status |
| --- | --- |
| `scripts/parsers/parse_data.py` | Maintained single-file and batch extraction for supported instrument exports and calibration CSVs. |
| `scripts/processing/calibration.py` | Maintained concentration-on-conductivity fits from curated preparation and point tables. |
| `scripts/processing/matching.py` | Source- and protocol-based release/recording/K proposals. |
| `scripts/processing/calibration_reuse.py` | Calibration compatibility audit and conditional coefficient-reuse test. |
| `scripts/processing/mass_slug.py` | Mass-based pulse integration, proposed discharge, sensitivity diagnostics and figures. |
| `scripts/processing/export_discharge.py` | Verified analysis handoff with all release dispositions, proposed estimates, quality flags and figures. |
| `notebooks/salt_dilution_discharge.ipynb` | Historical July 24, 2025 example using a retired helper API. |
| `notebooks/exploratory/` | Historical interactive calculations with older assumptions and incomplete inputs. |
| `scripts/experimental/` | Unfinished class-based dilution implementation and launcher. |
| `config/dilution_draft.ini` | Incomplete historical configuration. |

Follow [getting started](../docs/getting_started.md) for dependencies and commands, then [calibration](../docs/calibration.md) for equations and output interpretation. The [reviewed calibration bundle](results/calibrations/2026-10-26_probe_review/README.md) contains 49 provisional fits and 37 skipped series, with coefficients, diagnostics and reasons for exclusion.

## Data and calibration applicability

The [curated records](data/records/README.md) separate 38 physical releases, 43 calibration attempts, 262 observations and 59 candidate recording associations/placeholders. The [schema](../docs/field_data_schema.md) defines joins, units and the broader local transcription containing sediment and seismic-source observations. Calibration fitting needs preparations and points; unresolved stream links do not prevent those fits.

Before applying K, identify the instrument, conductivity channel and preparation associated with the selected release. The main discharge work uses Aqua TROLL river recordings and their associated calibration. General meters served farther-downstream attenuation monitoring. Within a supported physical trial/role, an identified Aqua TROLL can carry through its calibration; different probes require applicability review. Existing notebook links do not automatically approve transfer. See the [instrument catalog and procedure history](../docs/salt_dilution_instruments.md).

The curated association rows remain `needs_review`. Window proposals in `config/pulse_windows.json` retain reviewer evidence and pending user signoff; none is an accepted measurement. Paired probes, split logs and alternative calibrations stay separate; repeated file links are not additional physical releases.

## Parsers

The public Python entry point reads without modifying its source:

```python
from salt_dilution.scripts.parsers.parse_data import read_data

df, metadata = read_data(path)
```

Focused readers handle Aqua TROLL/VuSitu HTML and metadata-prefixed CSV, General logger XLS/XLSX, and recognized legacy calibration tables. Filename metadata supplies provisional hints, not trial identity. The CLI supports recursive discovery, input-relative filters and a per-file manifest:

```sh
python -m salt_dilution.scripts.parsers.parse_data salt_dilution/data/raw --recursive --output salt_dilution/data/processed/new_run
```

Choose a fresh directory. Source timestamps, extra columns and distinct actual/specific conductivity channels are retained. UTC requires explicit offset evidence. Duplicate or nonmonotonic times are flagged; clock-only Aqua TROLL records are rejected. Supporting deployment/instrument reports are skips, while malformed measurements are failures. See [parser ingestion](../docs/parser_ingestion.md) for the complete behavior and audit manifest.

## Known source limitations

- Historical notebooks call retired helper functions and select event intervals by hard-coded indices. They are reference material rather than the maintained workflow.
- Earlier helpers assumed equal calibration increments in places and used inconsistent definitions of the calibration relationship. The maintained runner instead uses recorded addition semantics and fits concentration on EC with a free intercept.
- Historical conductivity labels did not consistently distinguish actual and temperature-compensated measurements. Current parsers keep identified channels separate; ambiguous legacy channels still need review.
- The class-based prototype marks its discharge formula as unfinished and omits time integration. It is not a validated alternative method.
- Provisional fits do not establish delivered salt quantity, complete tracer recovery, mixing, clock alignment, background/tail windows or calibration uncertainty. The DI-stock ionic-background correction has not been implemented.

The mass runner uses the saved pairings and exact fitted K, actual elapsed seconds, signed excess conductivity and a pre/post background. Gaps or missing cells inside used windows block calculation. Relative-injectate discharge and tail extrapolation remain outside this runner. [Results](results/README.md) separate calculated proposals from blocked releases.
