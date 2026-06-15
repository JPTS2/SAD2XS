# Writer Tests

This folder contains tests for generated lattice and optics writer behaviour.

Writer tests should assert on generated output structure, serialisation
choices, supported-element policy, and writer-specific features. They should
not own SAD parser rules or SAD-to-Xsuite conversion physics.

## Subfolders

- `elements/`: element-specific serialisation.
- `features/`: writer behaviour that crosses element families, such as RF,
  reference shifts, and offset markers.
- `pipeline/`: whole-writer entry points and supported-element policy.
