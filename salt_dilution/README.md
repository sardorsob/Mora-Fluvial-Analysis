# Salt-dilution discharge analysis

Start with [salt_dilution_discharge.ipynb](notebooks/salt_dilution_discharge.ipynb). It replays the original July 24, 2025 solution-injection example using [its configuration](config/2025-07-24_trial_01.ini) and eleven preserved [source CSVs](data/README.md).

## Workflows

| Location | Purpose and status |
| --- | --- |
| `notebooks/salt_dilution_discharge.ipynb` | Primary historical example; scientific review still required. |
| `notebooks/exploratory/explore_salt_dilution.ipynb` | Earlier interactive investigation with different calibration assumptions and index-based CSV selection. |
| `notebooks/exploratory/check_dilution_calculations.ipynb` | Historical checks; refers to missing source inputs and older function interfaces. |
| `scripts/processing/dilution_calculations.py` | Configuration loading, calibration, discharge calculations, and plotting. |
| `scripts/processing/convert_units.py` | Volume and mass conversion helpers. |
| `scripts/processing/datetime_utils.py` | Time-window and CSV helpers. |
| `scripts/parsers/` | Source readers for Aqua TROLL, General logger, calibration tables, filename metadata, and the single parser CLI. |
| `scripts/experimental/` | Unfinished class-based dilution implementation and its example launcher. |
| `config/dilution_draft.ini` | Incomplete historical configuration; not the primary example's settings. |

## Parsers

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

The three historical Aqua TROLL parser variants were replaced after their required source-reading behavior was covered by the focused readers and tests. Raw HTML/Excel source files remain unchanged.

## Known source limitations

These remain visible for scientific review; organizing files does not resolve them.

- The primary notebook uses hard-coded sample indices 230:500 for the injection interval even though the configuration also contains clock-time windows.
- `calibration_RC` multiplies each addition by its row index; its cumulative-volume calculation assumes equal increments and an initial zero row.
- `calculate_k` uses the endpoint range, while the calibration plot uses a linear regression.
- Actual and temperature-compensated conductivity labels are not consistently distinguished in the source.
- The exploratory check notebook refers to an absent configuration and `calibration.csv`, missing/older helper interfaces, and incomplete imports.
- The class-based prototype explicitly marks its discharge formula as unfinished and omits the required time integration. It is not a second validated method.

The main example saves figures, a discharge table, a configuration snapshot, and `run_info.json` under [results](results/README.md). Preserve raw observations, units, calibration records, time zones, and the reasoning behind any future change to these calculations.
