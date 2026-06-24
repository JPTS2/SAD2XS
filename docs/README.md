# SAD2XS documentation

This folder contains the project documentation for SAD2XS.

The documentation is intended to define the structure, assumptions, and development conventions used by the project. It should make converter changes easier to review and help ensure that new behaviour is consistent with the intended architecture.

Some sections describe current behaviour. Others describe agreed direction for upcoming work. Where this distinction matters, the relevant page should state it explicitly.

## Testing philosophy

SAD2XS tests from the ground up: the test suite first verifies what SAD itself does, then verifies that the converter mirrors it exactly. Converter logic is written to match SAD's actual runtime behaviour, not an interpretation of its documentation — the tests are the specification. This is why `tests/sad/` exists: to machine-verify which parameters each element type accepts or rejects before any conversion code is written or changed.

## Documentation convention

When a section describes behaviour that is not yet implemented, it should use one of these labels:

- `Current status`: what the code does today.
- `Next release target`: behaviour expected before the next release is complete.
- `Long-term direction`: design direction that is useful to record but not required for the next release.

Avoid describing target behaviour as if it already exists.

## Contents

- [Architecture](architecture.md): package layout, subsystem responsibilities, and boundaries between parser, converter, writer, and SAD helper code.
- [Conversion model](conversion-model.md): the SAD-to-Xsuite conversion pipeline and the decision to treat the converted Xsuite model as the canonical representation.
- [SAD helpers](sad-helpers.md): Python wrappers around external SAD calculations, including entry points, subprocess handling, timeouts, optionality target, and current limitations.
- [Testing](testing.md): public test policy, regression workflow, CI structure (master and per-folder workflows), known failure groups, and SAD dependency handling.
- [Contributing](contributing.md): branch naming, pull request expectations, release workflow, and public issue policy.
- [Design decisions](design-decisions.md): project-level decisions that should guide future development.

## Scope

These documents currently cover:

- converter architecture and responsibility boundaries;
- the role of Xsuite as the canonical intermediate model;
- SAD helper functionality and its current subprocess model;
- testing policy for public and private validation;
- contribution and release workflow for the current development cycle;
- design decisions that affect future converter, writer, and helper changes.

These documents do not yet cover:

- a complete user guide;
- full installation instructions;
- generated API documentation;
- a complete reference for every supported SAD element;
- detailed examples for every conversion mode.

Those sections should be added as the public API, docstrings, and supported conversion behaviours are stabilised.
