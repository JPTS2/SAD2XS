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

Consequence: helper imports should not make core conversion imports fail. The public test suite itself is SAD-capable and requires SAD, but package import-boundary tests should still protect core imports from unnecessary helper coupling.

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

## Parser hardening is staged, not a full grammar rewrite

Decision: `_001_parser.py` keeps its ad-hoc string-splitting approach for now. Parser errors cite the source line number (`"line N: ..."`) via line-tracked sections, and SAD's `:=` function-definition syntax is rejected with a clear error instead of being silently misparsed into a garbage deferred-expression key. A token-level/grammar-based rewrite is deliberately deferred to a future release.

Reasoning: `parsed_lattice_data` (the parser's `globals`/`elements`/`lines`/`expressions` output) is consumed by seven downstream converter files, so a grammar rewrite's risk is spread far wider than its benefit. The current ad-hoc parser also encodes a number of empirically-discovered SAD quirks (e.g. SAD's own parser silently drops comma-separated trailing parameters in element bodies — matched on purpose, not a bug to fix) that a from-scratch grammar risks re-deriving one at a time. The existing parser is not rated defective: 99% of parser tests pass, and an independent codebase review called the ad-hoc string handling "stylistic, not risky." Line numbers and explicit-rejection errors deliver most of the remaining hardening value without that risk.

Consequence: SAD user-defined functions (`f[x_] := expr`) are explicitly out of scope for now rather than silently half-supported — closer to how Xtrack deliberately does not parse MAD-X files containing expressions. When a full grammar-based parser is eventually built, build its parse tree in parallel with the current parser first and validate its output matches `parsed_lattice_data`'s shape byte-for-byte against the full `tests/sad/` ground-truth corpus before any cutover.
