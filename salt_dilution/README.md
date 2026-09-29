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
| `scripts/experimental/` | Unfinished class-based dilution implementation and its example launcher. |
| `config/dilution_draft.ini` | Incomplete historical configuration; not the primary example's settings. |

## Parsers

All three source variants are retained separately:

- `parse_aquatroll_filename_cli.py`: batch HTML parser whose output names use the source filename plus instrument metadata.
- `parse_aquatroll_metadata_cli.py`: batch parser that also reads HTML meta tags, including exported CSV names.
- `parse_aquatroll_interactive.py`: prompts for a single input file and output directory. Its metadata filename is fixed and can be overwritten by another input in the same destination.

Parser calculations and extraction behavior are unchanged. The metadata variant's original `--dry-run` flag is not forwarded to its writer. Use separate destinations and inspect outputs when selecting a parser. Launch instructions are in [getting started](../docs/getting_started.md).

## Known source limitations

These remain visible for scientific review; organizing files does not resolve them.

- The primary notebook uses hard-coded sample indices 230:500 for the injection interval even though the configuration also contains clock-time windows.
- `calibration_RC` multiplies each addition by its row index; its cumulative-volume calculation assumes equal increments and an initial zero row.
- `calculate_k` uses the endpoint range, while the calibration plot uses a linear regression.
- Actual and temperature-compensated conductivity labels are not consistently distinguished in the source.
- The exploratory check notebook refers to an absent configuration and `calibration.csv`, missing/older helper interfaces, and incomplete imports.
- The class-based prototype explicitly marks its discharge formula as unfinished and omits the required time integration. It is not a second validated method.

The main example saves figures, a discharge table, a configuration snapshot, and `run_info.json` under [results](results/README.md). Preserve raw observations, units, calibration records, time zones, and the reasoning behind any future change to these calculations.
