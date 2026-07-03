# Conversion model

The core SAD2XS design choice is that Xsuite is the canonical intermediate representation.

SAD input is parsed and converted into Xsuite objects.

Next release target: after conversion, the Xsuite `Environment`, `Line`, and element objects should be the source of truth for writer output and later processing.

## Why Xsuite is canonical

Raw SAD definitions are not always authoritative after conversion.

Reasons include:

- SAD line reversals may require derived or transformed Xsuite elements.
- Conversion may expand one SAD concept into several Xsuite elements or helper markers.
- Offsets, apertures, and solenoid handling may require Xsuite-specific structures.
- Users may later rematch or modify the Xsuite lattice and still want readable regenerated outputs.
- Current Xsuite APIs can change, so the converter must target the active Xsuite object model rather than preserve stale SAD syntax.

For these reasons, SAD2XS should not treat parsed SAD text as the primary model once conversion has happened.

## Conversion pipeline

```text
1. Read SAD file content.
2. Normalize names and simple whitespace.
3. Parse constants, globals, elements, and lines.
4. Exclude user-requested elements.
5. Optionally convert aperture elements to markers.
6. Create an Xsuite Environment and populate variables.
7. Create the Xsuite reference particle.
8. Convert supported SAD elements to Xsuite elements.
9. Convert SAD line definitions to Xsuite lines.
10. Select the requested line, or the longest available line.
11. Apply solenoid-specific corrections.
12. Configure models, integrators, and bend edge handling.
13. Apply requested line order, bend direction, and charge reversals.
14. Install offset markers.
15. Write lattice and optics files from the Xsuite model.
16. Reload the generated files and return the rebuilt Xsuite line.
```

This describes the current high-level orchestration. Some individual steps need cleanup to fully satisfy the design decisions in this documentation.

## Parser expectations

Next release target: the parser should turn SAD text into structured data without losing information that later conversion stages need.

Important parser expectations for the next release include:

- comments should not affect semicolon-based section splitting;
- globals and expressions should be available to later element conversion;
- SAD user-defined function definitions (`f[x_] := expr`) are explicitly rejected with a clear error rather than silently misparsed — see the parser-hardening decision in `docs/design-decisions.md`;
- parse errors cite the source line number of the offending statement;
- line definitions should support supported SAD syntax variants, including comma-separated components;
- arithmetic in element parameters should not depend on fragile whitespace handling.

## Element conversion expectations

Next release target: element conversion should preserve the physics information that Xsuite can represent.

Important cases for the next release include:

- RF cavities should use the current Xsuite phase and harmonic conventions.
- Coordinate transforms should use current Xsuite transform elements such as translations, rotations, and time delays.
- Thin and zero-length magnetic elements need a documented policy, likely using `xt.Multipole` where appropriate.
- Combined multipole components should be preserved when a base element includes higher-order corrections.
- Aperture conversion should support equivalent SAD aperture parameter forms where the meaning is clear.
- Solenoid-region conversion should follow SAD's inserted-element rules: between
  SOL boundary elements, SAD supports DRIFT, straight BEND, QUAD, and MULT.
  Direct SEXT and OCT elements should not be treated as supported inserted
  elements in that region; higher-order content should be represented through
  MULT where appropriate.

Unsupported cases should fail clearly. Silent loss of physics information is worse than a loud error.

## Writer expectations

Next release target: the writer should serialize the Xsuite model that SAD2XS actually built.

This means:

- writer output should reflect converted and reversed Xsuite elements;
- writer output should not require the original SAD text to remain authoritative;
- regenerated lattices should compile and reproduce the intended Xsuite model;

Long-term direction: the writer should accept a general Xsuite line or environment, not only a direct SAD2XS conversion result.

## Boundaries

SAD2XS is not expected to preserve every SAD syntax detail. It is expected to preserve the accelerator model within the limits of supported Xsuite elements and documented conversion rules.

Where SAD and Xsuite have different physics models or naming conventions, the converter should document the choice and test the expected behaviour with synthetic examples.

One concrete case of this: SAD's solenoid fringe kick (a nonlinear hard-edge term, distinct from the solenoid's main linear field) has no Xsuite equivalent and is not modelled — every converted solenoid behaves as if fringe kicks were disabled, regardless of the source file. This is a documented, accepted boundary rather than an open bug — see `docs/design-decisions.md`. The converter warns once per lattice when a solenoid's source parameters don't match that assumption.
