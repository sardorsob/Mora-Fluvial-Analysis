# Naming conventions

- Use lowercase `snake_case` for internal folders and filenames. Keep the GitHub repository name `mora-fluvial-analysis`.
- Keep conventional names such as `README.md`, `LICENSE`, `CITATION.cff`, and `.gitignore`. R source uses the `.R` extension.
- Name reusable modules by subject: `calibration.py`, `mass_slug.py`, `waveform_utils.py`.
- Name executable workflows by action and subject: `download_waveforms.py`, `screen_waveforms.ipynb`.
- Name notebooks for their analysis and use readable display titles inside. Number filenames only for an intentionally ordered sequence.
- Keep dates on measurement configurations and result runs: `2025-07-24_trial_01.ini`, `2026-09-28_turbulence_trial_01/`.
- Preserve original instrument-export filenames and document them in the data inventory. Do not rename measured quantities or CSV columns during filename cleanup.
- Use Git history for versions. Avoid `final2`, `new`, and `misc`; describe an experiment's purpose and document its status.
- Keep experimental alternatives clearly labelled. Use the maintained parser entry point rather than adding another source reader for a launch interface.

The initial reorganization retained source function and parameter names. Some historical helpers have since been retired; consult the method guides for current interfaces. The [source manifest](source_manifest.csv) maps every imported file to its original name and revision.
