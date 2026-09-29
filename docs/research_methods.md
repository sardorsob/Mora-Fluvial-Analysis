# Research methods

## Salt dilution

The imported workflow uses conductivity measurements and calibration information to estimate stream discharge following an injected salt solution. The supplied code background concerns slug injection. Constant-rate injection is a related reference method, not an implemented workflow in this repository.

Background reading supplied for the project:

- R. D. (Dan) Moore, 2004: *Introduction to Salt Dilution Gauging for Streamflow Measurement, Part 2: Constant-rate Injection*. Streamline Watershed Management Bulletin, 8(1), pp. 11–15.
- R. D. (Dan) Moore, 2005: *Introduction to Salt Dilution Gauging for Streamflow Measurement, Part III: Slug Injection Using Salt in Solution*. Streamline Watershed Management Bulletin, 8(2), pp. 1–6.

The original PDF attachments remain in the research archive; they are not included in this repository. The [salt-dilution README](../salt_dilution/README.md) records the current example, calibration choices, and source limitations.

## Fluvial seismology

The imported workflows include waveform preparation, instrument calibration, spectral analysis, and turbulence/bedload modelling. The source repository includes Python, R, and a notebook using rpy2 to access R from Python.

The relationship between measured discharge and seismic model outputs should be documented for each research analysis. The imported source contains exploratory models; the import does not establish validated findings or new completed scientific experiments.

See [provenance](provenance.md) for the source repositories.
