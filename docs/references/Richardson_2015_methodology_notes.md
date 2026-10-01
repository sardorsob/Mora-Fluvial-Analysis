# Richardson 2015 methodology notes

Source: Mark E. Richardson (2015), *Refinement of tracer dilution methods for discharge measurements in steep mountain streams*, M.Sc. thesis, University of British Columbia. DOI: `10.14288/1.0166725`.

Reviewed against the project-supplied PDF on 2026-10-01.

These are implementation-oriented notes, not a substitute for the thesis.

## Distinguish the two salt slug methods

Richardson treats two slug-injection pathways separately.

### Dry salt injection

Conceptually:

`Q = M / (CFT * A)`

where:

- `M` is injected salt mass;
- `CFT` is a mass-concentration-to-temperature-corrected-conductivity calibration factor; and
- `A` is the area under the background-subtracted breakthrough curve.

The calibration table therefore contains mass/concentration semantics.

### Salt-in-solution injection

Conceptually:

`Q = V / (kT * A)`

where:

- `V` is the measured volume of primary/injection solution actually injected;
- `kT` is the solution-volume/relative-concentration calibration slope; and
- `A` is the breakthrough-curve area.

The live code must not route dry-injection `g/mL` concentration into the solution-injection relative-concentration equations merely because the tables share conductivity and volume columns.

## Conductivity basis and temperature

Richardson expresses the field and calibration workflow using temperature-corrected electrical conductivity.

The thesis also found a meaningful calibration difference between calibration near in-situ stream temperature and calibration at room temperature even when instruments applied temperature compensation.

For this project:

- preserve actual and specific/temperature-corrected conductivity as separate source quantities;
- select one authoritative quantity for a given method/trial;
- use it consistently for background, BTC, calibration, plotting, and final Q; and
- record the selected basis in result provenance.

Do not silently substitute one conductivity column for another.

## Match the calibration probe to the measurement probe

Richardson recommends using the same conductivity probe for the discharge measurement and the calibration.

Even similar devices can show systematic differences in calibration factor.

The normalized data model should therefore keep probe identity associated with both the field recording and calibration. A mismatched-probe calibration should be flagged unless staff explicitly accepts it.

## Opposite-bank probe agreement is strong mixing evidence

One of Richardson's most important findings for the Mount Rainier data is that same-side probes can agree even when the tracer is not fully mixed across the stream.

The thesis recommends opposite-side probes for confident verification of adequate lateral mixing.

This directly supports treating paired `river_left` and `river_right` recordings as a scientific QA relationship rather than duplicate files.

A future QA path can compare:

- independently calculated Q;
- calibrated BTC integrals;
- arrival times;
- peak response; and
- tail behavior.

Agreement can support a mixing decision. Disagreement should trigger investigation or qualification; do not simply average the two records.

## A smooth breakthrough curve does not prove complete mixing

Richardson found that probe location strongly affects BTC shape.

Fast-flowing, non-aerated locations generally produced smoother BTCs, while side pools, backwaters, obstructions, and aerated water could create noisy or choppy responses.

However, a smooth BTC alone does not establish complete cross-channel mixing.

Signal-shape metrics may be useful diagnostics, but they should not become an automatic mixing pass/fail rule without spatial evidence and field context.

## Reach length and lateral water exchange matter

Adequate mixing length was reach dependent.

Richardson also documented cases where calculated discharge increased downstream, consistent with gaining water or other surface-subsurface exchange.

For repeated measurements and QA, preserve when available:

- injection-to-probe distance;
- wetted width;
- reach gradient/morphology;
- probe bank/side;
- local flow character; and
- whether the reach is known or suspected to gain or lose water.

Use the shortest reach that confidently achieves complete mixing to reduce the influence of lateral inputs.

Do not assume all downstream disagreement is caused solely by incomplete mixing.

## Probe-placement documentation is scientific metadata

Richardson recommends detailed descriptions and/or photographs of measurement locations.

This supports the local download SOP requirement to retain contextual installation photographs, sketch maps, recording start/stop times, injection time, and travel-time notes.

The analysis repository should store safe references/identifiers to those records rather than embedding sensitive field photographs or restricted coordinates in Git.

## Calibration procedure implications

For dry calibration, Richardson discusses a correction when a secondary solution uses water whose background conductivity differs from the stream sample, such as distilled water.

That correction belongs to the dry-calibration method and should sit behind an explicit method choice.

Do not apply dry-calibration corrections automatically to Moore-style solution-injection relative-concentration calibration.

## Uncertainty should remain decomposable

Richardson separates uncertainty contributions from:

1. injected amount;
2. breakthrough-curve area/background/noise; and
3. calibration factor.

The first code repair does not need a complete uncertainty-propagation framework, but each run should preserve enough intermediate values that uncertainty can later be computed without reconstructing the analysis from final Q alone.

## Practical code requirements derived from the thesis

The maintained implementation should eventually be able to:

- identify `calibration_type` / method explicitly;
- validate required fields by method;
- preserve calibration-device and measurement-device identity;
- preserve complete timestamps and actual integration spacing;
- calculate paired-bank QA without collapsing recordings too early;
- store field/probe/reach metadata references;
- save calibration fit diagnostics;
- save background selection/model details;
- flag incomplete tail/background recovery;
- preserve BTC area as an explicit intermediate value; and
- distinguish execution success, scientific QA status, and staff acceptance.

## Source-copy hash

The exact project-supplied PDF reviewed for these notes:

`32f0676856d597aae6fa3658b7ad994a0b90576cd3baf20ef896e8658c0d5cfd`
