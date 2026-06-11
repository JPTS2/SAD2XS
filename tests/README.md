# Test Suite Layout

This directory contains public tests and test support files for SAD2XS.

The test suite is organised by responsibility. New tests should be placed in
the narrowest folder that describes the behaviour being protected.

## Folder Map

- `parser/`: SAD text parsing tests. These should assert parsed dictionaries
  or parser errors and should not run external SAD.
- `conversion/elements/`: conversion tests for individual SAD element
  families.
- `conversion/features/`: conversion tests for behaviour that crosses element
  families, such as reversal, rotations, reference shifts, RF, thin elements,
  and combined multipoles.
- `conversion/pipeline/`: tests for the public conversion pipeline and user
  options.
- `writer/`: output writer tests. `writer/elements/` covers element-specific
  serialisation, `writer/features/` covers cross-cutting writer behaviour, and
  `writer/pipeline/` covers whole writer entry points.
- `roundtrip/`: generated file import and write/reload equivalence tests.
- `sad_helpers/`: tests for `sad2xs.sad_helpers` behaviour.
- `examples/`: tests for public examples and example lattices.
- `installation/`: installer and installation helper tests.
- `packaging/`: package metadata, import boundary, and release metadata tests.
- `ci/`: tests for repository CI workflow configuration.
- `observability/`: tests for terminal output, quiet mode, and logging policy.
- `support/`: reusable support modules for tests. These are not test files.
- `fixtures/`: committed fixture files used by tests.

## Naming

Use descriptive test filenames. Existing numbered names are retained where they
come from the historical element test order, but new tests should not rely on
filename order for execution.

Element-specific tests may use SAD element mnemonics when that is clearer for
the converter contract, for example `cavi`, `aper`, `moni`, and `sol`.

For large element families, a subfolder is acceptable. Solenoid tests currently
use `conversion/elements/test_007_sol/` because the cases are large and split
by geometry and reference-shift combinations. Do not add per-element folders by
default unless the test set is large enough to justify it.

## Test Dependencies

Tests that require an external SAD executable should be marked and structured
so they can be skipped or run in a dedicated CI job. Tests that do not need SAD
should remain fast and independent.

## Transitional Notes

The test tree is currently being reorganised. Some moved tests still import
legacy support module names such as `_config` and `_sad_helpers`. Update those
imports when each file is reviewed.
