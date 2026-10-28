# Mount Rainier Fluvial Analysis

Tools for studying river flow and sediment movement at Mount Rainier National Park using salt-dilution measurements and fluvial seismology.

The maintained salt workflow reads instrument exports and fits calibration curves that relate electrical conductivity to added salt concentration. The seismic workflows provide waveform preparation, spectra, and exploratory turbulence and bedload models. They came from two research repositories; [provenance](docs/provenance.md) identifies the source revisions and retained licenses.

## What works now

| Work | Current capability | Important limit |
| --- | --- | --- |
| Salt-data extraction | Read Aqua TROLL HTML/CSV, General logger spreadsheets and recognized calibration CSVs; save normalized readings and metadata. | Parsing does not resolve field clocks, choose an event or establish measurement quality. |
| Salt calibration | Fit the curated preparation/point tables separately by probe and conductivity channel; save coefficients, residuals, figures and skip reasons. | Fits are provisional. Discharge processing is not implemented in the maintained workflow. |
| Fluvial seismology | Imported Python/R scripts and notebooks for preparation, instrument comparisons, spectra and models. | No waveform data are bundled; these workflows have not been validated end to end here. |

The [reviewed calibration bundle](salt_dilution/results/calibrations/2026-10-26_probe_review/README.md) contains **49 provisional fits and 37 skipped series**. It resolves probe identities for 13 preparations without changing the earlier numerical fits. Twelve fitted series still lack probe identities. No accepted discharge estimate, Q, has been produced by the maintained workflow.

## Start here

1. Follow [getting started](docs/getting_started.md) to install dependencies and run the parser or calibration script.
2. Read the [calibration method](docs/calibration.md), [curated records guide](salt_dilution/data/records/README.md) and [instrument catalog](docs/salt_dilution_instruments.md) before applying a coefficient to stream data.
3. Use the [salt-dilution guide](salt_dilution/README.md) or [seismic guide](fluvial_seismology/README.md) to choose a workflow. Historical dilution notebooks use retired helpers and are reference material.

For the scientific background, see [research methods](docs/research_methods.md) and [references](docs/references/README.md). [Validation](docs/validation.md) distinguishes numerical checks from scientific acceptance. [Naming conventions](docs/naming_conventions.md) and the [source manifest](docs/source_manifest.csv) describe file organization and original names.

## Layout

```text
mora-fluvial-analysis/
├── docs/                    Setup, methods, data schema and provenance
├── project_paths.py         Shared input and run-output paths
├── tests/                   Parser, calibration, records and portability checks
├── salt_dilution/
│   ├── scripts/             parsers/, processing/ and experimental/
│   ├── notebooks/           Historical dilution calculations
│   ├── config/              Procedure definitions and historical settings
│   ├── data/                examples/, raw/, records/ and processed/
│   └── results/             Calibration bundles and local runs
└── fluvial_seismology/
    ├── scripts/             processing/ and models/
    ├── notebooks/           Preparation, calibration, spectra and modelling
    ├── config/              Historical source environments
    ├── data/                Local waveform inputs and working copies
    └── results/             Local analysis runs
```

Small curated salt records, their provenance, historical examples and selected calibration bundles are versioned. Original salt exports already in Git retain their instrument filenames. Large normalized readings, other generated runs and seismic field inputs stay local under the existing ignore rules. Local field-note staging and parser-run links require those files on the reader's machine; calibration fitting works from the tracked tables alone.

See [LICENSE](LICENSE) for the retained source notices. The combined repository has no new blanket license. Cite the methods and original authors, and record the revision used as described in [CITATION.cff](CITATION.cff).
