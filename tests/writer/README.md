# Writer Tests

This folder contains tests for generated lattice and optics writer behaviour.

Writer tests should assert on generated output structure, serialisation
choices, supported-element policy, and writer-specific features. They should
not own SAD parser rules or SAD-to-Xsuite conversion physics.

The writer is tested as an independent public capability. Tests should build
Xsuite lines directly, write them with `sad2xs.write_lattice` and
`sad2xs.write_optics`, reload the generated files in a clean Xsuite
environment, and compare the original and reloaded lines. A writer test should
not assume that the input line was produced by `convert_sad_to_xsuite`.

## Core Contract

The primary writer contract is:

`xt.Line` input -> generated lattice/optics Python files -> reloaded `xt.Line`.

The reloaded line should preserve the writer-supported parts of the input:

- element order and element names;
- element classes;
- reference particle;
- supported element fields, such as lengths, strengths, RF parameters,
  apertures, shifts, rotations, and solenoid fields;
- generated-file importability in a fresh Xsuite environment.

Assertion messages should name the element and field being compared so CI
failures are useful without inspecting generated files.

## Test Layers

- `pipeline/`: whole-line writer contracts, file generation, reload behaviour,
  and supported-element policy.
- `elements/`: focused serialisation tests per element family. One file per
  Xsuite element type, covering all supported fields including strengths,
  offsets, rotations, skew components, combined-function combinations, and
  element-specific features such as RF parameters and offset marker output.

Start with element-level coverage to isolate failures by element type, then
use pipeline tests to verify whole-line behaviour.

## Subfolders

- `elements/`: element-specific serialisation, one file per element family.
- `pipeline/`: whole-writer entry points and supported-element policy.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
