# Design decisions

This file is a lightweight decision log. It records project-level choices that should guide future changes.

Decisions about how specific SAD physics is modelled live with the feature they concern, in the [converter documentation](../converter/README.md): [fringe models](../converter/fringes.md), [solenoids](../converter/solenoids.md), [models and integrators](../converter/models-integrators.md), and [element conversion](../converter/elements.md).

**On this page:**

- [Xsuite is the canonical intermediate model](#xsuite-is-the-canonical-intermediate-model)
- [Public tests must be shareable](#public-tests-must-be-shareable)
- [SAD helpers are optional](#sad-helpers-are-optional)
- [Keep SAD2XS as one package for now](#keep-sad2xs-as-one-package-for-now)
- [Writer should become reusable](#writer-should-become-reusable)
- [Configuration must not change semantics accidentally](#configuration-must-not-change-semantics-accidentally)
- [Parser hardening is staged, not a full grammar rewrite](#parser-hardening-is-staged-not-a-full-grammar-rewrite)
- [SAD builds against the system toolchain, not a conda environment](#sad-builds-against-the-system-toolchain-not-a-conda-environment)
- [The installer never installs system dependencies](#the-installer-never-installs-system-dependencies)

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

Consequence: helper imports do not make core conversion imports fail. `sad_helpers` is imported lazily on first access (PEP 562), so the core converter loads without the helper dependencies. The public test suite itself is SAD-capable and requires SAD; `tests/packaging/test_import_boundaries.py` protects core imports from helper coupling.

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

## SAD builds against the system toolchain, not a conda environment

Decision: SAD is built with the system compilers and system glibc. The conda or mamba environment is for Python only. The installer sanitises the build environment so an active environment cannot leak into the build.

Reasoning: SAD2XS runs `sad` as a subprocess. If SAD's runtime libraries came from a conda environment, SAD would work only while that environment was active, and a different active environment would give a mismatched `libgfortran` at runtime rather than a clean failure. The two-layer split is already how the Dockerfile works: the builder stage compiles SAD with the system toolchain, and a separate stage creates the Python environment. Conda sysroots are also older than the host: their `bits/math-finite.h` declares `lgamma` in terms of `lgamma_r`, which SAD does not request, so a conda toolchain fails to compile `autos_.c` outright.

Consequence: each platform installer pins `PATH` to the platform's own directories for the build and clears the compiler, include, library, and linker variables conda activation exports. The dependency audit searches that same pinned `PATH`, so a command supplied only by conda is reported missing rather than disappearing once the build starts. On Linux a toolchain that resolves inside a conda environment is refused outright.

Root is not needed to build SAD. A user without root builds normally, provided the system toolchain and headers are already installed — which is the usual case on a managed shared machine. The limitation applies only when a required system package is absent and the user cannot have it installed. Building against a conda toolchain instead is unsupported and unverified, and this decision should be revisited if that case becomes common.

## The installer never installs system dependencies

Decision: `sad2xs-install-sad` never runs `sudo` and never runs a package manager. It probes for what the build needs, reports everything missing together with how to provide it, and exits before touching SAD. On macOS that is a Homebrew command. On Linux it is the package name for the detected distribution, not a privileged command.

Reasoning: SAD2XS is a lattice converter, not a system administration tool, and it has had no public security review. Asking for a password would ask users to trust it with far more than it needs. Reporting is also more honest across distributions: package names differ, and a machine where the user cannot become root is common on shared systems.

Consequence: distribution detection exists only to name packages accurately in a printed report. The report names the detected distribution family and the package that provides each missing dependency; it prints no command to run as root, and no automatic-confirmation flag. How those packages arrive is left to the user and whoever administers the machine. Source-level tests assert that no executable path in any installer module — the shared code included, since every platform runs it — can invoke a package manager. The clone, the build, the build logs, and the launcher are all owned by the user.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
