# Mount Rainier Fluvial Analysis

Tools for studying river flow and sediment movement at Mount Rainier National Park through salt-dilution measurements and fluvial seismology.

The salt workflow pairs conductivity recordings with calibration fits and estimates discharge from delivered salt mass or original solution volume. The seismic workflows explore how river flow and moving sediment appear in ground vibrations. The project combines two research repositories; [source provenance](docs/provenance.md) records their authors, revisions and licenses.

## Start here

1. [Understand the methods](docs/research_methods.md): what is measured and how the experiments connect.
2. [Set up and run the tools](docs/getting_started.md): dependencies and commands for calibration, discharge and review.
3. [Use the data](salt_dilution/data/records/README.md): salt tables, rock observations, identifiers and missing values.

## Current capabilities

| Workflow | Available work |
| --- | --- |
| Salt dilution | Instrument-file extraction, calibration fits, recording/K pairing, mass- and solution-slug calculations, and window and calibration diagnostics. |
| Rock trials | 331 tethered-rock observations, grouped by session, round, category and individual test. |
| Fluvial seismology | Imported Python/R scripts and notebooks for waveform preparation, spectra, turbulence and bedload models. |

The recovery calibration run has **59 provisional fits and 27 skipped series**. The [current discharge results and graphs](salt_dilution/results/README.md#graphs) combine five selected Nisqually estimates with **22 conditional working estimates**, covering 27 of 30 experimental Nisqually releases. Two unresolved stock recipes and one spilled dose still lack a chosen Q; two practice releases are excluded. Six selected Paradise estimates use a collaborator worksheet calibration and assume the nominal mass entered the river. The graphs retain separate instruments, channels and calibration attempts. All estimates await scientific acceptance. The seismic workflows require field recordings and have not been validated end to end here.

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
│   └── results/             Selected calibration, pairing and discharge results
└── fluvial_seismology/
    ├── scripts/             Waveform processing and models
    ├── notebooks/           Preparation, calibration, spectra and modelling
    ├── config/              Historical source environments
    ├── data/                Local waveform inputs and working copies
    └── results/             Local analysis runs
```

Small curated records, historical examples and selected calibration, pairing and discharge bundles are versioned. The discharge bundle includes figures and tables that can be read without raw recordings. Large normalized recordings, intermediate runs and seismic field inputs remain local. Links to local staging or run files require those files on the reader's machine; recovery calibration uses the tracked records and pinned calibration sources.

See [validation](docs/validation.md) for what has been checked, [references](docs/references/README.md) for the scientific sources, and [naming conventions](docs/naming_conventions.md) for file organization. [LICENSE](LICENSE) retains the source notices; no new blanket license is assigned. Follow [CITATION.cff](CITATION.cff) when citing the work.
