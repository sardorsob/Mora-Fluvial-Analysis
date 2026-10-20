# Salt-dilution discharge analysis

Historical notebooks are preserved for provenance, but they are no longer the maintained processing path and may reference retired helper functions. New work starts with the normalized parser output and will move through `scripts/processing/calibration.py` and `scripts/processing/mass_slug.py` as those modules are implemented and validated.

## Workflows

| Location | Purpose and status |
| --- | --- |
| `notebooks/salt_dilution_discharge.ipynb` | Historical July 24 example; preserved for provenance and not expected to run against the retired helper API. |
| `notebooks/exploratory/explore_salt_dilution.ipynb` | Historical interactive investigation with older calibration assumptions and index-based selection. |
| `notebooks/exploratory/check_dilution_calculations.ipynb` | Historical checks using older helper interfaces and incomplete source inputs. |
| `scripts/processing/calibration.py` | Reserved for the maintained calibration implementation; intentionally not implemented yet. |
| `scripts/processing/mass_slug.py` | Reserved for the maintained mass-based slug-discharge implementation; intentionally not implemented yet. |
| `scripts/parsers/` | Source readers for Aqua TROLL, General logger, calibration tables, filename metadata, and the single parser CLI. |
| `scripts/experimental/` | Unfinished class-based dilution implementation and its example launcher. |
| `config/dilution_draft.ini` | Incomplete historical configuration; not the primary example's settings. |

## Parsers

The [four curated salt tables](data/records/README.md) hold physical releases, calibration preparations, observed points and candidate recording associations. The [field-data schema](../docs/field_data_schema.md) defines that compact interface and the preserved [broader transcription bundles](data/processed/field_notes/README.md), which also contain sediment and controlled seismic-source records. The populated tables need scientific review; file associations, units, clocks and calibration inputs must be checked before calculations.

The [October 20 reconciliation](../docs/salt_record_reconciliation_2026_10_20.md) repairs four duplicate preparation IDs and 16 point references while preserving reviewed values. There are now 48 linked rows across 31 recordings; 11 placeholders remain unresolved. Known files and probes are distinct from accepted calibration fits and integration windows. All inputs remain `needs_review`.

The parser layer has one public entry point:

```python
from salt_dilution.scripts.parsers.parse_data import read_data

df, metadata = read_data(path)
```

The focused readers are:

- `aquatroll.py`: Aqua TROLL/VuSitu HTML and metadata-prefixed CSV exports;
- `general_logger.py`: General logger XLS/XLSX files;
- `calibration_table.py`: known solution-injection and mass/stock calibration-table schemas; and
- `filename_metadata.py`: provisional hints from known filename patterns.

`read_data()` is read-only. The CLI writes normalized CSV plus metadata JSON only when `--output` is supplied, and those files belong under `data/processed/`. The parser preserves full timestamps, keeps actual and specific conductivity distinct, retains extra source columns, and does not perform calibration or discharge calculations.

For single-file and recursive folder commands, filters, metadata/UTC behavior,
overwrite protection and the per-file manifest, see [reusable salt-data extraction](../docs/parser_ingestion.md).
The same CLI now accepts directories; no separate PowerShell wrapper is required.

```sh
python -m salt_dilution.scripts.parsers.parse_data salt_dilution/data/raw --recursive --output salt_dilution/data/processed/new_run
```

Use a fresh output directory. Supporting deployment/instrument reports are
identified and logged as skips, while malformed measurements are failures.
The new inline VuSitu metadata layout is supported. Source clocks are retained;
UTC is added only from explicit offsets. Source-only time values without dates
are rejected, and separate temperature sensors remain separate channels.

The three historical Aqua TROLL parser variants were replaced after their required source-reading behavior was covered by the focused readers and tests. Raw HTML/Excel source files remain unchanged.

## Known source limitations

These remain visible for scientific review; organizing files does not resolve them.

- The historical primary notebook uses hard-coded sample indices for the injection interval and calls helper functions that have now been retired.
- The retired processing code assumed equal calibration increments in places and used inconsistent definitions of the calibration relationship; those assumptions must not be carried into the maintained implementation.
- Actual and temperature-compensated conductivity labels were not consistently distinguished in the historical workflow; the parser now keeps those channels separate.
- The exploratory notebooks refer to older helper interfaces and incomplete or missing source inputs, so they should be read as provenance rather than executed as the maintained workflow.
- The class-based prototype explicitly marks its discharge formula as unfinished and omits the required time integration. It is not a second validated method.

Future maintained processing should consume normalized parser tables rather than reopen source files or recreate timestamp/file-selection helpers. Preserve raw observations, units, calibration records, time zones, and the reasoning behind any scientific calculation.
