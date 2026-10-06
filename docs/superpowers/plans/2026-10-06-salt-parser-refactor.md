# Salt Parser Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three overlapping historical parser scripts with a small, reproducible parser layer for Aqua TROLL, General logger, and calibration-table inputs.

**Architecture:** Each source family gets one focused reader. `parse_data.py` is the single public dispatcher returning `(DataFrame, metadata_dict)`. Scientific calibration and discharge logic remain in `scripts/processing/`.

**Tech Stack:** Python 3.10+, pandas, openpyxl, xlrd, standard library `html.parser`, unittest.

**Spec:** `docs/superpowers/specs/2026-10-06-salt-parser-refactor-design.md`

## Global Constraints

- Preserve raw source files unchanged.
- Return a pandas DataFrame plus a plain metadata dictionary.
- Preserve full timestamps and keep actual versus specific conductivity distinct.
- Normalize only fields whose meaning is clear from source labels.
- Treat filename-derived metadata as provisional.
- Keep calibration/discharge mathematics out of the parser layer.
- No parser classes, registry, factory, or new framework.
- Comments only for vendor quirks, provenance, or non-obvious scientific distinctions.
- `read_data()` is read-only; CLI writes only when `--output` is explicit.
- CLI normalized outputs are one CSV plus one metadata JSON under the caller-selected processed-data directory.
- Support legacy General logger `.xls` files with `xlrd`.

## Review Focus

- Aqua TROLL CSV files with variable-length metadata blocks must find the real `Date Time`/measurement header.
- Aqua TROLL HTML with extra measurement columns must preserve those columns instead of dropping them.
- General logger date/time values must combine without losing the source timing.
- Unknown/legacy filenames must not make an otherwise readable file fail.
- Calibration CSVs that do not match a supported schema must fail clearly instead of being silently misclassified.

---

### Task 1: Filename metadata helper

**Files:**
- Create: `salt_dilution/scripts/parsers/filename_metadata.py`
- Create: `tests/test_salt_parsers.py`

**Interfaces:**
- Produces: `parse_filename(path) -> dict`

- [ ] Write tests for canonical date/time/source/site/bank parsing, legacy partial parsing, and unknown filenames returning partial/empty metadata.
- [ ] Run `python -m unittest tests.test_salt_parsers -v` and confirm the new tests fail because the helper does not exist.
- [ ] Implement the smallest regex-based helper that satisfies those cases.
- [ ] Run the parser tests and the full `python -m unittest discover -s tests -v`.
- [ ] Commit: `feat(parser): add filename metadata helper`

### Task 2: Aqua TROLL reader

**Files:**
- Create: `salt_dilution/scripts/parsers/aquatroll.py`
- Modify: `tests/test_salt_parsers.py`

**Interfaces:**
- Consumes: `parse_filename(path) -> dict`
- Produces: `read_aquatroll(path) -> tuple[pandas.DataFrame, dict]`

- [ ] Add failing tests using one tracked VuSitu HTML file and one tracked Aqua TROLL CSV/WRD CSV.
- [ ] Tests must assert full timestamp preservation, distinct normalized actual/specific conductivity columns, preservation of extra source columns, and metadata fields for source format/type plus embedded metadata when available.
- [ ] Implement HTML parsing with the standard library and CSV header detection by scanning for the measurement header instead of fixed skip rows.
- [ ] Normalize only `Date Time`, temperature, actual conductivity, and specific conductivity labels while retaining other columns.
- [ ] Run parser tests and the full unittest suite.
- [ ] Commit: `feat(parser): add Aqua TROLL reader`

### Task 3: General logger reader

**Files:**
- Create: `salt_dilution/scripts/parsers/general_logger.py`
- Modify: `requirements.txt`
- Modify: `tests/test_salt_parsers.py`

**Interfaces:**
- Consumes: `parse_filename(path) -> dict`
- Produces: `read_general_logger(path) -> tuple[pandas.DataFrame, dict]`

- [ ] Add `xlrd` to the project requirements for tracked legacy `.xls` files.
- [ ] Add failing tests for an `.xlsx` General logger source and a small temporary workbook that exercises Date + Time combination and channel value/unit preservation.
- [ ] Implement `pandas.read_excel` loading for `.xls`/`.xlsx`, combining source Date/Time fields when present.
- [ ] Do not relabel channel values as conductivity/temperature unless source labels or units explicitly support it.
- [ ] Run parser tests and the full unittest suite.
- [ ] Commit: `feat(parser): add General logger reader`

### Task 4: Calibration-table reader

**Files:**
- Create: `salt_dilution/scripts/parsers/calibration_table.py`
- Modify: `tests/test_salt_parsers.py`

**Interfaces:**
- Produces: `read_calibration_table(path) -> tuple[pandas.DataFrame, dict]`
- Metadata includes `calibration_type`.

- [ ] Add failing tests for the tracked solution-injection template/historical table, the tracked dry/mass template, and an unsupported schema.
- [ ] Implement schema detection using required column sets and clear errors for unsupported tables.
- [ ] Keep table values unchanged; do not calculate cumulative additions or correction factors here.
- [ ] Run parser tests and the full unittest suite.
- [ ] Commit: `feat(parser): add calibration table reader`

### Task 5: Dispatcher, CLI, and legacy parser removal

**Files:**
- Create: `salt_dilution/scripts/parsers/parse_data.py`
- Modify: `tests/test_salt_parsers.py`
- Modify: `tests/test_portability.py`
- Modify: `docs/getting_started.md`
- Modify: `salt_dilution/README.md`
- Delete: `salt_dilution/scripts/parsers/parse_aquatroll_filename_cli.py`
- Delete: `salt_dilution/scripts/parsers/parse_aquatroll_metadata_cli.py`
- Delete: `salt_dilution/scripts/parsers/parse_aquatroll_interactive.py`

**Interfaces:**
- Consumes: the three reader functions.
- Produces: `read_data(path) -> tuple[pandas.DataFrame, dict]`
- CLI: `python -m salt_dilution.scripts.parsers.parse_data <path> [--output <processed-dir>]`

- [ ] Add failing dispatch tests for HTML, Aqua TROLL CSV, General Excel, calibration CSV, and unsupported extensions.
- [ ] Implement simple suffix/content dispatch; no registry or parser classes.
- [ ] Keep CLI output minimal. Without `--output`, print source metadata plus a compact table summary and write nothing. With `--output`, write one normalized CSV and one metadata JSON using the source stem.
- [ ] Update the portability test to launch `parse_data --help` instead of the deleted parser modules.
- [ ] Update setup/method docs to describe the one parser entry point and processed-output boundary.
- [ ] Delete the three historical parser scripts after the replacement tests cover their required use cases.
- [ ] Run parser tests and the full unittest suite.
- [ ] Commit: `refactor(parser): replace legacy Aqua TROLL parsers`

### Task 6: Reproducibility verification and durable context

**Files:**
- Modify as needed only if verification reveals a documented gap.
- Update after verified implementation:
  `sardorsob/personal-work-life/04-fellowships-scholarships/placements/mount-rainier-geohazards-assistant/03-service/work-context/current-state-and-next-steps.md`
- Update:
  `sardorsob/personal-work-life/04-fellowships-scholarships/placements/mount-rainier-geohazards-assistant/03-service/projects/fluvial-seismology-and-salt-dilution.md`

**Interfaces:**
- Consumes the completed parser layer and its verification evidence.
- Produces a durable record of what was implemented, why the architecture was chosen, what formats were verified, and what remains outside parser scope.

- [ ] Run `python -m unittest discover -s tests -v` on Python 3.12 in a clean checkout with project requirements available.
- [ ] Exercise `parse_data` on representative tracked Aqua TROLL HTML, Aqua TROLL/WRD CSV, General logger Excel, and both calibration-table families.
- [ ] Confirm raw source files are unchanged and parser outputs preserve full timestamps plus conductivity distinctions.
- [ ] Record exact implementation/verification status in the Mount Rainier personal-work-life context without copying raw measurements or sensitive identifiers.
- [ ] Commit the personal-work-life documentation with the repository's required commit style.
