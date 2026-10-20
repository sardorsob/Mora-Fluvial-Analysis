# Normalized salt-data inputs

Updated locally on 2026-10-19 with the existing parser: **153 CSV tables and 153 metadata JSON files**. The October 16 baseline's 143 pairs were preserved; ten new pairs add 3,901 rows. Subdirectories mirror `data/raw/`; original source files are unchanged.

These are provisional normalized inputs. They include observation exports and calibration tables, and may contain overlapping exports of the same recording. Eleven retained tables have flagged timestamps. No discharge, correction factors, background models or weather joins were calculated.

The [October 19 run summary](../../../docs/parser_run_2026_10_19.md) and [local run bundle](../../results/2026-10-19_parser_ingestion/README.md) record the fourteen newly attempted inputs: ten live time-series exports and four supporting calibration/deployment reports without a recognized measurement table. All ten new series have actual and specific conductivity and clean source-local timestamp ordering. The current corpus has 349,543 retained rows; the older timestamp flags and two quarantines remain unresolved.

See the [versioned run summary](../../../docs/parser_run_2026_10_16.md), [local run report](../../results/2026-10-16_parser_ingestion/README.md) and [per-file manifest](../../results/2026-10-16_parser_ingestion/run_info.json) for exact lineage, hashes, row counts, warnings, 28 unprocessed candidates and two clock-only files quarantined outside this folder. The August 5 duplicate was additionally withheld after its date changed with the execution date; its previous output was preserved in the new run bundle. The [October 6 run](../../results/2026-10-06_parser_ingestion/README.md) remains the earlier cutoff with 144 retained pairs.

Resolve trial associations, units, time zones and timestamp flags before analysis. This README is versioned; generated stream tables, metadata and the older field-note staging bundle remain ignored. The small curated notebook tables and their retained source evidence are versioned in [records/](../records/README.md).
