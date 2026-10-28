# Research methods

The project brings salt-dilution flow measurements and fluvial seismology into one analysis repository. The intended comparison is between measured river conditions and seismic signals/models of water flow and sediment movement. Each analysis still needs a documented site, time interval, units and comparison method; the repository does not yet establish a validated discharge–seismic relationship.

## Salt dilution

A slug measurement releases a known tracer quantity and records the downstream conductivity pulse. Calibration relates added tracer concentration to electrical conductivity. Discharge then depends on the delivered quantity and the time integral of excess tracer concentration, subject to mixing, tracer recovery, background and timing assumptions.

Two calibration bases are retained: relative concentration of the original injectate solution and salt mass concentration. They have different K units and require different delivered-input quantities. The maintained [calibration runner](calibration.md) implements preparation concentrations and separate actual/specific EC fits. Stream-event selection and discharge integration remain unimplemented. Constant-rate injection is background methodology, not an implemented workflow here.

The supplied background papers are Moore's 2004 constant-rate introduction and 2005 solution-slug method. Richardson's 2015 thesis and the 2017 calibration paper add mass-stock calibration and uncertainty context. See the [reference index](references/README.md) for citations and the [instrument guide](salt_dilution_instruments.md) for channel, temperature and same-instrument requirements. Published error ranges are not an uncertainty estimate for these field records.

## Fluvial seismology

The imported workflows cover waveform acquisition/preparation, instrument comparisons, spectral analysis, turbulence/bedload models and inversion. Python notebooks use ObsPy and, for the R experiments, installed `eseis` through rpy2. Checked-in R functions do not automatically replace the installed package's functions.

Model water depth (`h_w`), sediment flux (`q_s`) and salt-dilution water discharge are distinct quantities. A comparison must state how they relate, their units, temporal coverage and model assumptions. The [seismic guide](../fluvial_seismology/README.md) describes inherited limitations and missing inputs; these exploratory workflows have not been validated end to end here.

See [source provenance](provenance.md) for the original code repositories and licensing.
