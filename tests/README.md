# SAD2XS Test Suite

This directory contains the public tests, test support modules, local test data,
and diagnostic artifacts for SAD2XS.

The suite is organised by responsibility. New tests should be placed in the
narrowest folder that describes the behaviour being protected.

## Requirements

The SAD2XS converter is validated against SAD, so the test suite is expected to
run in an environment where the SAD executable and the Python project
dependencies are available.

Some tests, especially parser and packaging tests, do not invoke SAD directly.
They still live inside the same SAD-capable suite so that local and CI runs use
one consistent environment.

## Folder Map

- `parser/`: SAD text parsing and parser-owned expression conversion.
- `conversion/`: SAD-to-Xsuite conversion behaviour.
- `conversion/elements/`: conversion tests for individual SAD element families.
- `conversion/pipeline/`: public conversion entry points and user options.
- `writer/`: generated lattice and optics writer behaviour.
- `writer/elements/`: element-specific serialisation.
- `writer/features/`: writer behaviour that crosses element families.
- `writer/pipeline/`: whole-writer entry points and supported-element policy.
- `sad_helpers/`: tests for `sad2xs.sad_helpers` command construction,
  temporary-file handling, SAD output parsing, and smoke behaviour.
- `examples/`: tests for public examples and example lattices.
- `installation/`: installer and installation helper tests, plus
  installation-specific SAD smoke-test input data.
- `packaging/`: package metadata, import boundary, and release metadata tests.
- `ci/`: tests for repository CI workflow configuration.
- `observability/`: tests for terminal output, quiet mode, and logging policy.
- `support/`: reusable test support modules. These are not test files.
- `artifacts/`: generated diagnostic Markdown reports from selected physics
  comparison tests.

## Naming

Use descriptive test filenames. Existing numbered names are retained where they
come from historical examples, but new tests should not rely on filename order
for execution.

Element-specific tests may use SAD element mnemonics when that is clearer for
the converter contract, for example `cavi`, `aper`, `moni`, and `sol`.

For large element families, a subfolder is acceptable, but do not add
per-element folders by default unless the test set is large enough to justify
the extra navigation.

## Diagnostic Artifacts

Physics comparison tests may write deterministic Markdown reports under
`tests/artifacts/`. These generated reports are ignored by Git, except for the
folder README. They are intended to make failures inspectable: they include the
SAD lattice, tested parameters, SAD and Xsuite values, and tolerance summaries.

Artifact paths should mirror the test area that produced them, for example
`tests/artifacts/conversion/elements/sol/`.

## Transitional Notes

The test tree is being reorganised. Placeholder files in incomplete folders are
intentional markers for planned coverage and should be filled or removed as the
associated issues are tackled.
