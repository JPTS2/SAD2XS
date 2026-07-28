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

## Subfolders

- `elements/`: serialisation per element family, one file per Xsuite element
  type. Covers every supported field, including strengths, offsets, rotations,
  skew components, and combined-function combinations, plus element-specific
  features such as RF parameters and offset marker output.
- `pipeline/`: whole-line writer contracts, file generation, reload behaviour,
  and the supported-element policy.

Start with element-level coverage, which isolates a failure by element type.
Then use the pipeline tests to verify whole-line behaviour.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
