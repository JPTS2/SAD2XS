# SAD2XS documentation

This folder contains the project documentation for SAD2XS.

The documentation defines the structure, assumptions, and development conventions used by the project. It makes converter changes easier to review, and helps keep new behaviour consistent with the architecture.

These pages describe what the converter does today. Planned work lives in the [GitHub issue tracker](https://github.com/JPTS2/sad2xs/issues), not here.

## Testing philosophy

SAD2XS tests from the ground up: the test suite first verifies what SAD itself does, then verifies that the converter mirrors it exactly. Converter logic is written to match SAD's actual runtime behaviour, not an interpretation of its documentation — the tests are the specification. This is why `tests/sad/` exists: to machine-verify which parameters each element type accepts or rejects before any conversion code is written or changed.

## Contents

Start with [Architecture](architecture.md) for a map of the whole repository.

### Using SAD2XS

- [Supported elements](usage/supported-elements.md): the two separate questions behind "is my element supported?" — what the converter reads, and what survives a write and reload.
- [Conversion options](usage/conversion-options.md): every option accepted by `convert_sad_to_xsuite`.
- [Limitations](usage/limitations.md): where a converted lattice does not reproduce SAD.

### The converter

- [Conversion model](converter/README.md): the SAD-to-Xsuite pipeline, and the decision to treat the converted Xsuite model as canonical.
- [Parsing and expressions](converter/parsing.md): how SAD text becomes structured data.
- [Element conversion](converter/elements.md): how each SAD element family is converted.
- [Fringe models](converter/fringes.md): bend and quadrupole fringe field import.
- [Solenoid conversion](converter/solenoids.md): solenoid regions, and how the SAD and Xsuite solenoid models differ.
- [Models and integrators](converter/models-integrators.md): the tracking model, integrator, and kick count chosen per element type.
- [Line reversals](converter/line-reversals.md): sign conventions behind the line-transformation flags and the reference-particle `CHARGE` handling they interact with.
- [Offset markers](converter/offset-markers.md): how offset markers are installed and what they are for.

### Output writer

- [Output writer](writer/README.md): how the converted Xsuite model is serialised into lattice and optics files.

### Helpers

- [SAD helpers](helpers/sad-helpers.md): Python wrappers around external SAD calculations, including entry points, subprocess handling, timeouts, and current limitations.
- [Xsuite helpers](helpers/xsuite-helpers.md): utilities operating purely on an `xt.Line`, independent of SAD.

### Reference

- [SAD behaviour notes](reference/sad-behaviour.md): empirically-established facts about how SAD itself behaves — physics conventions, quirks, and limitations discovered while building and testing the converter, independent of any SAD2XS decision made in response.

### Development

- [Design decisions](development/design-decisions.md): project-level decisions that guide future development.
- [Testing](development/testing.md): public test policy, regression workflow, CI structure, known failure groups, and SAD dependency handling.
- [Contributing](development/contributing.md): branch naming, pull request expectations, and public issue policy.
- [Releasing](development/releasing.md): the step-by-step release procedure, covering version bumps, citation metadata, package build checks, tagging, the Zenodo archive, and PyPI upload.

## Scope

These documents cover:

- converter architecture and responsibility boundaries;
- the role of Xsuite as the canonical intermediate model;
- SAD helper functionality and its subprocess model;
- empirically-established SAD behaviour, independent of SAD2XS's own decisions;
- line reversal and charge sign conventions;
- testing policy for public and private validation;
- contribution and release workflow;
- design decisions that affect converter, writer, and helper changes.

These documents do not cover:

- a complete user guide;
- generated API documentation;
- a complete reference for every supported SAD element;
- detailed examples for every conversion mode.

Installation and basic usage are in the [top-level README](../README.md).

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
