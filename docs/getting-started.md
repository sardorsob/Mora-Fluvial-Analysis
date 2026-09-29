# Getting started

This is a directory scaffold. There is no runnable analysis or supported environment yet.

1. Choose [salt dilution](../salt-dilution/README.md) or [fluvial seismology](../fluvial-seismology/README.md).
2. When importing source materials, record their repository, branch, commit, original path, and new path in [provenance](provenance.md). Preserve authorship and license notices.
3. Place reusable code in `scripts/`, notebook workflows in `notebooks/`, and run settings in `config/`. Add dependency and launch instructions alongside the first runnable workflow.
4. Record datasets in the method's `data/inventory.csv`. Keep original observations in `data/raw/`, derived inputs in `data/processed/`, and small documented examples in `data/examples/`.
5. Use the method's `results/_template/` as the layout for a named run. Save figures, tables, and the run record together.

When source code is organized here, import and file-path changes should be reviewed separately from changes to scientific calculations.
