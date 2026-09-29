# Source environment exports

These four exports are preserved for provenance. None includes a complete R/rpy2/eseis setup, and none has been validated here as a portable installation.

| File | Original name | Source Python |
| --- | --- | --- |
| `obspy_python_3_10_19.yml` | `obspy.yaml` | 3.10.19 |
| `obspy_python_3_10_10.yml` | `obspy_env.yml` | 3.10.10 |
| `obspy_python_3_11_9_windows.yml` | `obspy.yml` | 3.11.9 |
| `obspy_python_3_10_10_windows.yml` | `obspy_env_new.yml` | 3.10.10 |

Windows exports contain platform/build-specific dependencies. Their machine-specific `prefix` entries were removed and UTF-16 was converted to UTF-8 where needed. Dependency versions and build specifications were retained.

Use these records when establishing the team's supported environment; do not treat all four as interchangeable setup choices.
