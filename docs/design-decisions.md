# Design decisions

This file is a lightweight decision log. It records project-level choices that should guide future changes.

## Xsuite is the canonical intermediate model

Decision: after SAD input is parsed and converted, Xsuite objects are the source of truth.

Reasoning: SAD input may not represent the final converted model after reversals, substitutions, offsets, apertures, solenoid handling, or user rematching. Writing outputs from the Xsuite model keeps the writer aligned with what the converter actually built.

Consequence: new converter features should assert on the Xsuite model where possible. Writer changes should avoid depending on raw SAD text unless there is a documented reason.

## Public tests must be shareable

Decision: public tests must use synthetic or publicly shareable inputs.

Reasoning: the repository and CI should be usable by contributors who do not have access to private lattices.

Consequence: private validation can still be used locally, but public bugs should be reduced to small synthetic reproductions before tests or issues are added.

## SAD helpers are optional

Decision: external SAD helper functionality should remain optional for the core converter.

Reasoning: helper functions are useful for validation and comparison, but they depend on an external SAD installation. Users should be able to import and use the converter without setting up every helper dependency.

Consequence: helper imports should not make core conversion imports fail. Tests that require external SAD should skip cleanly when SAD is unavailable.

Current status: this is not fully implemented. The top-level package still re-exports `sad_helpers`, so import-time coupling should be reduced in a future packaging change.

## Keep SAD2XS as one package for now

Decision: do not split the project into separate SAD helper and SAD-to-Xsuite packages during the current release cycle.

Reasoning: the current priority is converter correctness, public tests, and writer clarity. A package split would add release and dependency complexity before the internal boundaries are stable.

Consequence: keep boundaries clear inside the current package. If the SAD helper layer becomes independently useful and testable, a future package split can be reconsidered.

## Writer should become reusable

Decision: the long-term writer direction is a reusable Xsuite serializer.

Reasoning: users may want to convert a SAD lattice, rematch or modify it in Xsuite, then regenerate readable lattice and optics files. That workflow should not require the original SAD input to remain the authoritative source.

Consequence: writer APIs should move toward accepting complete Xsuite lines or environments. The current writer already accepts an `xt.Line` for lattice output, but it still carries SAD2XS-specific assumptions that need to be documented and reduced.

## Configuration must not change semantics accidentally

Decision: diagnostic options such as verbosity should affect logging only, unless a setting is explicitly documented as changing conversion behaviour.

Reasoning: users need repeatable conversion results. A flag intended for observability should not silently enable or disable conversion steps.

Consequence: behaviour-affecting settings must be documented and tested. Logging settings should be tested to ensure they do not alter the converted Xsuite model.
