# Naming conventions

- Use lowercase `snake_case` for internal folders and filenames. Keep the GitHub repository name `mora-fluvial-analysis`.
- Keep conventional names such as `README.md`, `LICENSE`, `CITATION.cff`, and `.gitignore`. R source uses the `.R` extension.
- Name reusable modules by subject: `calibration.py`, `mass_slug.py`, `waveform_utils.py`.
- Name executable workflows by action and subject: `download_waveforms.py`, `screen_waveforms.ipynb`.
- Keep implementation code in `scripts/` and analysis notebooks in `notebooks/`. Do not copy code into result folders or create a `results/.../code/` directory. Tests remain in `tests/`.
- Name notebooks for their analysis and use readable display titles inside. Number filenames only for an intentionally ordered sequence.
- Use a stable, purpose-based folder for published results: `salt_dilution/results/discharge_analysis/`. Organize it into `tables/`, `figures/`, `settings/` and `provenance/`, with its README, navigation and run metadata at the root. Do not add a date-prefixed wrapper around the published analysis.
- Keep measurement dates in source filenames, trial identifiers, measurement configurations and run metadata. Preserve historical source-run paths and checksums in provenance; a layout cleanup must not rewrite the history of a numerical calculation.
- Preserve original instrument-export filenames and document them in the data inventory. Do not rename measured quantities or CSV columns during filename cleanup.
- Use Git history for versions. Avoid `final2`, `new`, and `misc`; describe an experiment's purpose and document its status. Existing historical calibration and matching bundles remain referenced by their recorded identities.
- Keep experimental alternatives clearly labelled and separate from the published analysis. Use the maintained parser entry point rather than adding another source reader for a launch interface.

The initial reorganization retained source function and parameter names. Some historical helpers have since been retired; consult the method guides for current interfaces. The [source manifest](source_manifest.csv) maps every imported file to its original name and revision.
