# Mount Rainier Fluvial Analysis

Tools for studying river flow and sediment movement at Mount Rainier National Park through salt-dilution measurements and fluvial seismology.

The salt workflow reads conductivity recordings and fits calibration curves that convert conductivity changes into added salt concentration. The seismic workflows explore how river flow and moving sediment appear in ground vibrations. The project combines two research repositories; [source provenance](docs/provenance.md) records their authors, revisions and licenses.

## Start here

1. [Understand the methods](docs/research_methods.md): what is measured and how the experiments connect.
2. [Set up and run the tools](docs/getting_started.md): dependencies, parser and calibration commands.
3. [Use the data](salt_dilution/data/records/README.md): salt tables, rock observations, identifiers and missing values.

## Current capabilities

| Workflow | Available work |
| --- | --- |
| Salt dilution | Instrument-file extraction and provisional calibration fits, with diagnostics and skip reasons. |
| Rock trials | 331 tethered-rock observations, grouped by session, round, category and individual test. |
| Fluvial seismology | Imported Python/R scripts and notebooks for waveform preparation, spectra, turbulence and bedload models. |

The [reviewed calibration results](salt_dilution/results/calibrations/2026-10-26_probe_review/README.md) contain **49 provisional fits and 37 skipped series**. The maintained workflow does not yet calculate discharge, Q. The seismic workflows require field recordings and have not been validated end to end here.

Use the [salt guide](salt_dilution/README.md) or [seismic guide](fluvial_seismology/README.md) for the available scripts and notebooks. Historical dilution notebooks use retired helpers.

## Project layout

```text
mora-fluvial-analysis/
├── docs/                    Setup, methods, data schema and provenance
├── project_paths.py         Shared input and result paths
├── tests/                   Parser, calibration, records and portability checks
├── salt_dilution/
│   ├── scripts/             Parsers, processing and experimental code
│   ├── notebooks/           Historical dilution calculations
│   ├── config/              Procedure definitions and historical settings
│   ├── data/                Examples, raw exports, curated records and processed data
│   └── results/             Calibration bundles and local runs
└── fluvial_seismology/
    ├── scripts/             Waveform processing and models
    ├── notebooks/           Preparation, calibration, spectra and modelling
    ├── config/              Historical source environments
    ├── data/                Local waveform inputs and working copies
    └── results/             Local analysis runs
```

Small curated records, historical examples and selected calibration bundles are versioned. Large normalized recordings, other generated runs and seismic field inputs remain local. Links to local staging or run files require those files on the reader's machine; fitting calibration curves needs only the tracked tables.

See [validation](docs/validation.md) for what has been checked, [references](docs/references/README.md) for the scientific sources, and [naming conventions](docs/naming_conventions.md) for file organization. [LICENSE](LICENSE) retains the source notices; no new blanket license is assigned. Follow [CITATION.cff](CITATION.cff) when citing the work.
