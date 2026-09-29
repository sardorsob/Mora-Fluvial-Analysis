# Source provenance

Imported on 2026-09-28 from two archived snapshots:

| Method | Source | Branch | Commit |
| --- | --- | --- | --- |
| Fluvial seismology | [taylor-kenyon/FluvialSeismology_Analysis](https://github.com/taylor-kenyon/FluvialSeismology_Analysis) | `main` | `2764f9454916b0162f98b7221883d75ca742c646` |
| Salt dilution | [rjost1/FluvialSeismology_Analysis](https://github.com/rjost1/FluvialSeismology_Analysis/tree/dilution/Dilution) | `dilution` | `fce22815c02abd61bebdff692fd49c128feb5f3a` |

The [source manifest](source_manifest.csv) records all 53 imported source files, original paths, destinations, commits, and original SHA-256 hashes. Original repositories and histories were left unchanged. Source `.gitignore` files and macOS `.DS_Store` files were not imported.

## Changes

- Normalized internal names to snake_case and organized files by method and purpose.
- Updated Python imports while retaining original local aliases and function interfaces.
- Replaced machine-specific Windows paths with project-relative inputs or per-run output paths.
- Resolved the main dilution configuration's inputs relative to the configuration file.
- Added notebook setup cells, descriptive titles, source-cell indices, and result export cells for the main dilution example. Cleared historical outputs and execution counts.
- Removed embedded and commented source credentials. Acquisition now reads optional MORA_IRIS_USERNAME and MORA_IRIS_PASSWORD environment variables; public access is used when neither is supplied.
- Added missing import/setup statements where needed, routed two existing R-only cells through `%%R`, and moved the inline R-package installation instruction into setup documentation.
- Kept scientific expressions, constants, station/time selections, and known source limitations. R source files received whitespace-only formatting.
- Preserved eleven source CSVs byte for byte. Source environment exports were normalized to UTF-8 and had installation prefixes removed; their dependency lists were retained.

The original dilution notes remain in [dilution_utils.txt](source_notes/dilution_utils.txt) and [aquatroll_cli.txt](source_notes/aquatroll_cli.txt). These are historical records; use current READMEs for filenames and launch instructions.

## Attribution and licensing

The Taylor repository's [Apache 2.0 license text](../licenses/taylor_kenyon_apache_2_0.txt) is retained. Source authorship comments, including Michael Dietze's R function documentation, remain in the files. The archived dilution branch has no standalone license file. No new blanket license is assigned to this combined repository.

The Python/R notebook imports the installed `eseis` package; storing R files here does not make the notebook use those local copies. Record actual R/package versions and any explicit `source()` calls when conducting research runs.
