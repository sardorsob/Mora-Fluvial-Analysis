# Mount Rainier Fluvial Analysis

Tools and notebooks for salt-dilution discharge measurements and fluvial seismology at Mount Rainier National Park.

This repository brings two existing research codebases into one self-contained project. Scientific calculations are preserved; filenames, notebook titles, imports, input locations, and saved-result paths have been organized consistently. Some source workflows remain exploratory or incomplete.

## Start here

- [Getting started](docs/getting_started.md): dependencies, launching notebooks, and saving runs.
- [Salt dilution](salt_dilution/README.md): the July 24, 2025 discharge example, parsers, and exploratory alternatives.
- [Fluvial seismology](fluvial_seismology/README.md): waveform preparation, calibration, spectra, and Python/R models.
- [Naming conventions](docs/naming_conventions.md): rules for naming files.
- [Provenance](docs/provenance.md) and [source manifest](docs/source_manifest.csv): source revisions and every original-to-new filename.
- [Validation](docs/validation.md): what was checked and what remains unverified.

## Layout

```text
mora-fluvial-analysis/
├── README.md
├── LICENSE
├── CITATION.cff
├── project_paths.py                  Shared input and run-output paths
├── licenses/                         Preserved source license text
├── docs/                             Setup, methods, naming, and provenance
├── tests/                            Import and path checks
├── salt_dilution/
│   ├── notebooks/
│   │   └── exploratory/
│   ├── scripts/
│   │   ├── processing/
│   │   ├── parsers/
│   │   └── experimental/
│   ├── config/
│   ├── data/
│   │   ├── examples/
│   │   ├── raw/
│   │   └── processed/
│   └── results/
│       └── _template/
└── fluvial_seismology/
    ├── notebooks/
    │   ├── preparation/
    │   ├── instrument_calibration/
    │   ├── spectral_analysis/
    │   ├── modelling/
    │   └── exploratory/
    ├── scripts/
    │   ├── processing/
    │   └── models/
    ├── config/
    │   └── source_environments/
    ├── data/
    │   ├── examples/
    │   ├── raw/
    │   └── processed/
    └── results/
        └── _template/
```

Each run keeps its figures, tables, and `run_info.json` together. Raw field data, processed field data, and generated runs are ignored by Git. Small source examples and their inventory are tracked. Original instrument filenames are retained.

The archived source repositories remain independent and unchanged. See [LICENSE](LICENSE) for the scope of retained source notices; this import does not assign a new blanket license to the combined work.
