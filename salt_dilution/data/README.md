# Salt-dilution data

Eleven CSVs from the archived dilution branch are included under `examples/`. Their original bytes, filenames, column names, and values are preserved. [inventory.csv](inventory.csv) records source locations and checksums.

These are historical source examples, not new field observations. Confirm measurement units, time zone, calibration matching, and scientific assumptions before using them for a research conclusion. The July 24 configuration explicitly pairs `20250724_162611_840058.csv` with `20250724_trial1_solution_injection_calibration.csv`; other pairings have not been inferred.

- `examples/`: tracked source examples. The July 15 calibration export contains a different multi-section structure from the simple measurement CSVs.
- `raw/`: original field observations. Date folders keep `LiveReadings/` and `Logs/` directly under the date when those source folders exist; the redundant intermediate `raw_data/` / `raw data/` layer from older workstation layouts is flattened in this repository. Source files themselves remain unchanged.
- `processed/`: derived inputs and parser output, ignored by Git.
- `records/`: the [four curated salt tables](records/README.md), populated from the saved notebook transcription using the compact trial/calibration/point/association schema. These small CSVs and their provenance, manifest and validation report are versioned. Large normalized stream readings and their metadata stay ignored under `processed/`.

Handwritten calibration, injection, sediment and impact observations have a preserved local [field-note bundle index](processed/field_notes/README.md). This broader transcription is staging evidence; `records/` is the current compact salt interface. The [field-data schema](../../docs/field_data_schema.md) documents both layers, their units, source locators and review states. Both use the normalized parser's actual/specific conductivity names. The compact association table references processed stream paths directly; the original recording inventory remains provenance. The bundle's `discharge/`, `sediment/` and `seismic/` folders keep distinct measurements readable without moving existing raw exports or duplicating logger observations.

Keep the historical inventory unchanged when assigning identities to new field records. The curated provenance registry records new dataset identities, checksums, source locations and unresolved clock/calibration checks. Ignoring a directory does not establish approval to store restricted material there.
