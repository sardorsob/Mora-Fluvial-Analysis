# Research methods

The project compares physical river measurements with seismic signals to study water flow and sediment movement. Salt dilution measures the water passing through a reach. Rock trials provide observations of particle movement. Seismic recordings offer a way to investigate both processes from outside the river.

## Salt dilution: measuring water discharge

A slug test releases a known amount of salt and records the downstream conductivity pulse. Calibration converts the conductivity rise above river background into added salt concentration.

For a mass-based test, conservation of salt gives:

```text
Delta_C(t) = K × (EC(t) − EC_background(t))
Q = M_delivered / integral(Delta_C(t) dt)
```

`EC` is conductivity in µS/cm, `K` converts conductivity to concentration, and `Delta_C` is excess salt concentration in mg/L. `M_delivered` is the salt mass that entered the river, in mg. Integrating concentration over elapsed seconds gives mg·s/L, so `Q` is water discharge in L/s.

For the same salt mass, a higher discharge produces a smaller concentration–time integral. This calculation assumes sufficiently steady discharge during passage, adequate mixing, tracer recovery and a suitable river background. It requires the full pulse, including its tail; peak height alone is insufficient.

The maintained code extracts recordings and [fits calibration curves](calibration.md). Event matching, reviewed integration windows and discharge calculation are still unfinished. Historical solution-slug calibrations use relative injectate concentration and require the corresponding injectate quantity; their coefficients cannot be substituted into the mass equation above.

Moore (2004) covers constant-rate injection; Moore (2005) covers solution-slug injection. Richardson (2015) and Richardson et al. (2017) develop mass-stock calibration and uncertainty. See [references](references/README.md) and the [instrument guide](salt_dilution_instruments.md). Constant-rate injection is background methodology, not an implemented workflow here.

## Rock trials: observing particle movement

The tethered trials repeat releases across five ordered categories: `38.5mm`, `54.5mm`, `D50`, `79mm` and `119mm`. Individual tests are grouped into rounds, often following a salt measurement. Repeats capture variation within a category and under changing river conditions.

The [rock table](../salt_dilution/data/records/README.md#rock-observations) preserves measured apparatus distances and field notes. Its 60-second working duration is a stated protocol convention. Tether tension, snags and release position affect the observations; the distance definition still needs confirmation before calculating physical particle speed. These tests do not directly measure natural bedload flux. Associating a round with Q also requires timing and reach checks.

## Fluvial seismology: relating signals to the river

Water turbulence and moving sediment contribute to ground vibration. The imported workflows prepare waveforms, inspect spectra and explore turbulence, bedload and inversion models. Physical flow and sediment observations are needed to evaluate those models; no validated discharge–seismic relationship has been established here.

Model water depth (`h_w`), sediment flux (`q_s`) and water discharge (`Q`) are different quantities. Comparisons must state their units, time coverage and assumptions. The R experiments use installed `eseis` through rpy2; local R files are not loaded automatically. See the [seismic guide](../fluvial_seismology/README.md) for inputs and inherited limitations, and [source provenance](provenance.md) for authorship and licensing.
