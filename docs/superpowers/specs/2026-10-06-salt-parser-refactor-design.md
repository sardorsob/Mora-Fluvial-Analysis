# Salt Parser Refactor Design

## Goal

Replace the three overlapping Aqua TROLL parser scripts with a small parser layer that reads the real MORA salt-dilution source formats into consistent pandas tables plus source metadata. Parsing must remain separate from calibration and discharge calculations.

## Scope

Create:

- `salt_dilution/scripts/parsers/aquatroll.py`
- `salt_dilution/scripts/parsers/general_logger.py`
- `salt_dilution/scripts/parsers/calibration_table.py`
- `salt_dilution/scripts/parsers/filename_metadata.py`
- `salt_dilution/scripts/parsers/parse_data.py`

Remove after replacement verification:

- `parse_aquatroll_filename_cli.py`
- `parse_aquatroll_metadata_cli.py`
- `parse_aquatroll_interactive.py`

The historical raw files are never rewritten.

## Responsibilities

### aquatroll.py

Read Aqua TROLL / VuSitu HTML and exported CSV files.

Preserve:

- full timestamps;
- temperature;
- actual conductivity;
- specific conductivity;
- other source columns;
- embedded metadata when available;
- original source column names/units for provenance.

Normalize only well-understood fields such as:

- `timestamp`
- `temperature_c`
- `actual_conductivity_us_cm`
- `specific_conductivity_us_cm`

Do not calculate background, calibration factors, breakthrough areas, or discharge.

### general_logger.py

Read General logger `.xls` and `.xlsx` files.

Preserve channel values and channel units. Combine source date/time columns into a full timestamp when the source provides them.

Do not guess that a channel is conductivity or temperature unless the file's recorded units/labels support that interpretation.

### calibration_table.py

Read and classify the known calibration table families.

Initial supported types:

- historical/solution-injection relative-concentration tables;
- mass/dry or stock-titration tables.

The parser identifies the table type and validates expected columns. Scientific calculations remain in `salt_dilution/scripts/processing/calibration.py`.

### filename_metadata.py

Extract candidate metadata from known filename patterns.

Candidate values may include date, time, source type, site/role, bank, and run/trial hints.

Filename metadata is provisional. It must not override embedded file metadata or field records, and unknown names should return partial/empty metadata rather than fail.

### parse_data.py

Provide the simple public entry point and CLI dispatch.

Primary interface:

```python
df, metadata = read_data(path)
```

It selects the correct reader from the file type/content and returns:

1. a pandas DataFrame;
2. a plain metadata dictionary.

No parser class hierarchy, registry, factory, or new dependency is required.

## Metadata contract

The metadata dictionary should stay simple and extensible:

```python
{
    "source_file": "...",
    "source_format": "html | csv | xls | xlsx",
    "source_type": "live_reading | log | general | calibration | unknown",
    "instrument_family": "aquatroll | general_logger | unknown",
    "filename_metadata": {...},
    "embedded_metadata": {...},
}
```

Only include fields supported by the source. Do not invent missing values.

## Provenance and data flow

The parser layer must preserve the distinction between:

- original Aqua TROLL HTML;
- browser-exported CSV from the same HTML recording;
- historical Python parser outputs;
- General logger Excel files;
- calibration tables;
- new normalized/processed outputs.

Raw inputs stay under `salt_dilution/data/raw/`. New normalized outputs, when written by the CLI, belong under `salt_dilution/data/processed/`.

HTML and exported CSV may represent the same physical recording. The parser reads either form but does not decide trial identity or deduplicate physical events.

## Error behavior

- Unsupported file types raise a clear `ValueError`.
- Missing required columns for a recognized schema raise a clear error.
- Unknown filename patterns do not fail parsing.
- The parser preserves extra source columns instead of silently dropping them.
- Raw input files are never modified.

## Testing

Use representative real source structures already in the repository.

Minimum parser checks:

- Aqua TROLL HTML loads and preserves full timestamp plus actual/specific conductivity.
- Aqua TROLL exported CSV loads through the same normalized contract.
- General logger Excel loads with timestamp plus channel values/units.
- Both known calibration-table schemas are recognized.
- Canonical and legacy filenames return candidate metadata without making it authoritative.
- Unknown filenames degrade safely.
- Existing repository tests remain green.

Keep tests focused and small. No broad parser framework or exhaustive test matrix is required before real data proves a need.

## Reproducibility

The code should be readable enough that another analyst can follow:

```text
raw source file
    -> parser
    -> normalized DataFrame + metadata
    -> calibration or slug processing
    -> scientific result
```

Comments should explain vendor quirks, provenance decisions, or non-obvious scientific distinctions only. Avoid comments that narrate ordinary Python.

## Out of scope

This refactor does not:

- calculate correction factors;
- select background windows;
- integrate breakthrough curves;
- calculate discharge;
- join weather data;
- infer which files belong to one physical trial;
- redesign the raw-data folder structure again;
- normalize every possible source column;
- build a general plugin/registry framework.
