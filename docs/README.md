# SAD2XS documentation

This folder contains the project documentation for SAD2XS.

The documentation defines the structure, assumptions, and development conventions used by the project. It makes converter changes easier to review, and helps keep new behaviour consistent with the architecture.

These pages describe what the converter does today. Planned work lives in the [GitHub issue tracker](https://github.com/JPTS2/sad2xs/issues), not here.

## Testing philosophy

SAD2XS tests from the ground up: the test suite first verifies what SAD itself does, then verifies that the converter mirrors it exactly. Converter logic is written to match SAD's actual runtime behaviour, not an interpretation of its documentation — the tests are the specification. This is why `tests/sad/` exists: to machine-verify which parameters each element type accepts or rejects before any conversion code is written or changed.

## Contents

### Design and structure

- [Architecture](architecture.md): package layout, subsystem responsibilities, and boundaries between parser, converter, writer, and SAD helper code.
- [Conversion model](conversion-model.md): the SAD-to-Xsuite conversion pipeline and the decision to treat the converted Xsuite model as the canonical representation.
- [Design decisions](design-decisions.md): project-level decisions that guide future development.

### Subsystems

- [SAD helpers](sad-helpers.md): Python wrappers around external SAD calculations, including entry points, subprocess handling, timeouts, optionality target, and current limitations.
- [Xsuite helpers](xsuite-helpers.md): Python utilities operating purely on an `xt.Line`, independent of SAD — currently reference-energy bookkeeping for accelerating lines.

### Reference

- [SAD behaviour notes](sad-behaviour.md): empirically-established facts about how SAD itself behaves — physics conventions, quirks, and limitations discovered while building and testing the converter, independent of any SAD2XS decision made in response.
- [Line reversals](line-reversals.md): the sign conventions, empirical verifications, and design decisions behind the line-transformation flags (`reverse_element_order`, `reverse_charge_sign`, `reverse_survey_horizontal`, `reverse_survey_vertical`) and the reference-particle `CHARGE` handling they interact with.

### Process

- [Testing](testing.md): public test policy, regression workflow, CI structure (master and per-folder workflows), known failure groups, and SAD dependency handling.
- [Contributing](contributing.md): branch naming, pull request expectations, release workflow, and public issue policy.
- [Releasing](releasing.md): the step-by-step procedure for publishing a release, covering version bumps, citation metadata, package build checks, tagging, the Zenodo archive, and PyPI upload.

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
