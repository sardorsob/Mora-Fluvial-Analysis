# Mount Rainier Fluvial Analysis

Tools and notebooks for salt-dilution discharge measurements and fluvial seismology at Mount Rainier National Park.

This repository currently contains the project layout and documentation only. Analysis scripts, notebooks, datasets, and completed runs have not been added.

## Research methods

- [Salt dilution](salt-dilution/README.md): conductivity-based stream-discharge analysis.
- [Fluvial seismology](fluvial-seismology/README.md): seismic processing and models of river flow and sediment transport.

## Layout

```text
mora-fluvial-analysis/
├── README.md
├── LICENSE
├── CITATION.cff
├── docs/
│   ├── getting-started.md
│   ├── research-methods.md
│   └── provenance.md
├── salt-dilution/
│   ├── README.md
│   ├── notebooks/
│   │   └── exploratory/
│   ├── scripts/
│   │   ├── processing/
│   │   ├── parsers/
│   │   └── experimental/
│   ├── config/
│   ├── data/
│   │   ├── README.md
│   │   ├── inventory.csv
│   │   ├── examples/
│   │   ├── raw/
│   │   └── processed/
│   └── results/
│       └── _template/
│           ├── figures/
│           ├── tables/
│           └── run-info.json
└── fluvial-seismology/
    ├── README.md
    ├── notebooks/
    │   ├── preparation/
    │   ├── instrument-calibration/
    │   ├── spectral-analysis/
    │   ├── modelling/
    │   └── exploratory/
    ├── scripts/
    │   ├── processing/
    │   └── models/
    ├── config/
    ├── data/
    │   ├── README.md
    │   ├── inventory.csv
    │   ├── examples/
    │   ├── raw/
    │   └── processed/
    └── results/
        └── _template/
            ├── figures/
            ├── tables/
            └── run-info.json
```

The `_template` folders describe future runs; they contain no analysis results. Empty folders contain `.gitkeep` files so the layout survives a Git clone.

## Working here

Start with [getting started](docs/getting-started.md), [research methods](docs/research-methods.md), and [source provenance](docs/provenance.md). Each method's README explains where its materials belong.

Code, documentation, configuration, and small documented examples belong in Git. Full field recordings, processed field datasets, and generated result runs are ignored by default. Preserve original measurements and record their source, units, and time zone when adding data.

The license and citation files are initial placeholders for completion when research materials and contributor details are added.
