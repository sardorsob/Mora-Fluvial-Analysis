# Methodology references

This folder is the maintained methodology-reference layer for `mora-fluvial-analysis`.

Use it to keep the scientific sources and interpretation notes that directly constrain salt-dilution implementation, calibration, quality assurance, and later analysis. These references are methodological evidence; they do not prove that a particular Mount Rainier field trial followed every recommendation.

## Core references

### Moore 2004 - constant-rate injection

R.D. (Dan) Moore, *Introduction to Salt Dilution Gauging for Streamflow Measurement, Part 2: Constant-rate Injection*, Streamline Watershed Management Bulletin 8(1), 2004.

Project relevance:

- constant-rate tracer formulation and steady-state relative concentration;
- calibration of relative concentration against electrical conductivity;
- cumulative secondary-solution additions;
- fitting the RC-versus-EC relation to obtain `k`;
- lateral-mixing and measurement-reach requirements; and
- uncertainty from injection-rate, volume, background-EC, and mixing errors.

This is a related method reference. The current salt-dilution codebase is centered on slug injection rather than a maintained constant-rate workflow.

### Moore 2005 - slug injection using salt in solution

R.D. (Dan) Moore, *Introduction to Salt Dilution Gauging for Streamflow Measurement Part III: Slug Injection Using Salt in Solution*, Streamline Watershed Management Bulletin 8(2), 2005.

This is the primary conceptual reference for the historical solution-injection workflow.

Important implementation constraints include:

- discharge is based on the measured final volume of injected solution and the time-integrated calibrated breakthrough curve;
- the conductivity record must cover the salt wave through its return toward background;
- calibration uses the actual injection solution diluted into stream water;
- the calibration relation must cover the conductivity range observed during the salt wave;
- lateral mixing is a core validity requirement;
- probe placement in backwaters or strongly aerated locations can distort measurements; and
- changing background or a long stored-salt tail requires explicit treatment rather than silent truncation.

### Richardson 2015 - tracer-method refinement and uncertainty

Mark E. Richardson, *Refinement of tracer dilution methods for discharge measurements in steep mountain streams*, M.Sc. thesis, University of British Columbia, 2015. DOI: `10.14288/1.0166725`.

See [Richardson methodology notes](Richardson_2015_methodology_notes.md).

Richardson is especially relevant to the newer Mount Rainier paired-bank, attenuation/background, dry-calibration, and solution-calibration data because it:

- treats dry-salt and salt-in-solution slug injection as distinct methods;
- separates mass-based calibration from volume/relative-concentration calibration;
- recommends calibration near in-situ stream temperature when possible;
- recommends using the same conductivity probe for the discharge record and its calibration;
- shows that same-side probe agreement can falsely suggest adequate mixing;
- recommends opposite-bank measurements for confident lateral-mixing checks;
- documents measurement-location effects on breakthrough-curve shape and discharge precision; and
- decomposes discharge uncertainty into injected amount, breakthrough-curve area, and calibration-factor contributions.

## Project source-copy hashes

The user supplied these exact source copies for the project on 2026-10-01:

```text
ca4997afc4e1cf6ce5a95e475cff795c1696e8bb200f53a8e65c0f020b5405fa  Moore_2004b_constant_rate_injection.pdf
360fab1ab40abf4d774a4ac039c331ed61a0a7b55086e6b16fdb30fb23719d47  Moore_2005_Slug_salt_in_solution.pdf
32f0676856d597aae6fa3658b7ad994a0b90576cd3baf20ef896e8658c0d5cfd  RefinementOfTracerMethods_RichardsonThesis.pdf
```

The methodology notes in this folder were reviewed against those supplied copies.

## Binary-copy status

The browser GitHub connector used for this update writes UTF-8 repository content but does not directly upload arbitrary local PDF bytes. Therefore this folder currently preserves the reference index, source-copy hashes, and methodology notes; do not claim that the three PDF binaries are committed here unless the files are visibly present in this directory.

When the PDFs are added from a Git-capable environment, use the exact filenames above and verify their SHA-256 values against this page before committing.

## How to use these references when changing code

Before changing salt-dilution scientific logic:

1. read this index and the Richardson notes;
2. read [research methods](../research_methods.md);
3. read the salt-dilution README and the current calculation code;
4. identify whether the target trial is **solution injection** or **dry injection**;
5. identify the authoritative conductivity quantity and calibration schema;
6. preserve trial/probe/calibration/background associations explicitly;
7. distinguish code execution from scientific QA and staff acceptance; and
8. record any deliberate departure from the methodology sources.

Do not retrofit a method choice from file names alone. Field notes, calibration records, source metadata, and staff direction remain controlling evidence for a real trial.
