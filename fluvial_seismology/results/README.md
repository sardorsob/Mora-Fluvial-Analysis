# Analysis results

No validated seismic result is bundled. Keep each waveform, spectral or model analysis in a named run directory with its inputs, station/channel/time interval, settings, units and outcome recorded.

`_template/` provides `figures/`, `tables/` and `run_info.json`; it contains no scientific result. Add model files only when an analysis produces them. Generated runs are ignored; this guide and the template are tracked.

The Python `result_path` helper uses `MORA_RUN_ID` or a UTC timestamp and creates an initial record with status `started`. Complete its input references, configuration, Git revision and outcome. Functions that display plots do not necessarily export them; see the [seismic guide](../README.md) for saving selected figures and for workflow limitations.
