# Research methods

The project compares physical river measurements with seismic signals to study water flow and sediment movement. Salt dilution measures the water passing through a reach. Rock trials provide observations of particle movement. Seismic recordings offer a way to investigate both processes from outside the river.

## Salt dilution: measuring water discharge

A slug test releases a known quantity of tracer and records the downstream conductivity pulse. Let `I` be the signed integral of conductivity above river background over elapsed seconds, in µS·s/cm.

| Route | Delivered quantity | Calibration slope | Discharge in m³/s |
| --- | --- | --- | --- |
| Salt mass | `M` in g | `K_m` in (mg/L)/(µS/cm) | `M / (K_m × I)` |
| Original solution | `V` in mL | `K_r` in (mL/mL)/(µS/cm) | `(V / 10⁶) / (K_r × I)` |

The mass slope converts excess conductivity to added salt concentration. The relative slope converts it to the volume fraction of the original injectate. `V` is the original solution that entered the stream. If source evidence supports treating reported injected volume as delivered, the result carries that assumption.

For a given delivered quantity and calibration slope, greater discharge produces a smaller integral. The calculation assumes sufficiently steady flow, adequate mixing, a suitable background and capture of the full tracer passage. Native elapsed times drive trapezoidal integration. The standard background varies linearly between the means of selected pre- and post-pulse windows. An observed pre-pulse background can precede a recording pause when the evidence establishes that the pause was before injection and that the background still applies. A gap within the tracer passage prevents a full-pulse estimate.

The [calibration fits](calibration.md) are preparation- and channel-specific. Actual and specific conductivity retain their own coefficients. The recovery workflow records compatible trial-specific fits, including alternate worksheet recipes where supported, with their source qualifications. Dilute NaCl references are conditional diagnostics under stated chemistry and compensation assumptions. Calculated discharge uses the fitted coefficient. Pressure and depth comparisons describe changes within a recording placement, where that placement remained stable.

The [numerical review](getting_started.md#review-the-saved-release-estimates) recomputes saved estimates and compares plausible windows and background choices. Those ranges and fit standard errors cover individual uncertainty components. Full uncertainty also depends on delivered quantity, recipe, mixing and tracer recovery. Where the source supports a conditional observed-interval scenario, the review records the capture and background assumptions in a separate table. All current estimates await field acceptance. See [the results](../salt_dilution/results/discharge_analysis/README.md).

Moore (2004) covers constant-rate injection as background methodology. Moore (2005) covers solution-slug injection. Richardson (2015) and Richardson et al. (2017) develop mass-stock calibration and uncertainty. See [references](references/README.md) and the [instrument guide](salt_dilution_instruments.md).

## Rock trials: observing particle movement

The tethered trials repeat releases across five ordered categories: `38.5mm`, `54.5mm`, `D50`, `79mm` and `119mm`. Individual tests are grouped into rounds, often following a salt measurement. Repeats capture variation within a category and under changing river conditions.

The [rock table](../salt_dilution/data/records/README.md#rock-observations) preserves measured apparatus distances and field notes. Its 60-second working duration is a stated protocol convention. Tether tension, snags and release position affect the observations; the distance definition still needs confirmation before calculating physical particle speed. These tests do not directly measure natural bedload flux. Associating a round with Q also requires timing and reach checks.

## Fluvial seismology: relating signals to the river

Water turbulence and moving sediment contribute to ground vibration. The imported workflows prepare waveforms, inspect spectra and explore turbulence, bedload and inversion models. Physical flow and sediment observations are needed to evaluate those models; no validated discharge–seismic relationship has been established here.

Model water depth (`h_w`), sediment flux (`q_s`) and water discharge (`Q`) are different quantities. Comparisons must state their units, time coverage and assumptions. The R experiments use installed `eseis` through rpy2; local R files are not loaded automatically. See the [seismic guide](../fluvial_seismology/README.md) for inputs and inherited limitations, and [source provenance](provenance.md) for authorship and licensing.
