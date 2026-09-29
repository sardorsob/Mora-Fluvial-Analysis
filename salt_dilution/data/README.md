# Salt-dilution data

Eleven CSVs from the archived dilution branch are included under `examples/`. Their original bytes, filenames, column names, and values are preserved. [inventory.csv](inventory.csv) records source locations and checksums.

These are historical source examples, not new field observations. Confirm measurement units, time zone, calibration matching, and scientific assumptions before using them for a research conclusion. The July 24 configuration explicitly pairs `20250724_162611_840058.csv` with `20250724_trial1_solution_injection_calibration.csv`; other pairings have not been inferred.

- `examples/`: tracked source examples. The July 15 calibration export contains a different multi-section structure from the simple measurement CSVs.
- `raw/`: original field observations, ignored by Git and kept unchanged.
- `processed/`: derived inputs and parser output, ignored by Git.

Add new datasets to the inventory with source/storage location, units, time zone, and relevant calibration. Ignoring a directory does not establish approval to store restricted material there.
