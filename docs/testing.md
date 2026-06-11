# Testing

Testing should protect converter behaviour while keeping the public repository
shareable and maintainable.

Run Python commands in an environment with the SAD2XS development dependencies
installed.

```bash
python -m pytest
```

The test tree itself is documented in `tests/README.md`.

## Public Test Policy

Public tests must use synthetic or publicly shareable inputs.

Private or non-shareable lattices can be used for local validation, but they
must not be required for public CI, public issues, or public regression tests.
If a private lattice reveals a bug, reduce it to a small synthetic SAD example
before adding a public test.

Public tests should not mention private lattice names or institution-specific
files unless those files are explicitly public and committed to the repository.

Public examples may use committed public lattices. Regression tests for bugs
found in private validation should use reduced synthetic inputs.

## Test Layers

Current status: the public test tree is organised into responsibility-based
folders:

- `parser/`: SAD text parsing and parser error handling.
- `conversion/elements/`: individual SAD element conversion.
- `conversion/features/`: cross-element conversion features.
- `conversion/pipeline/`: public conversion pipeline and options.
- `writer/`: generated lattice and optics writer behaviour.
- `roundtrip/`: generated file import and write/reload equivalence.
- `sad_helpers/`: reusable helper APIs that call or prepare external SAD runs.
- `examples/`: public example execution and example lattice checks.
- `installation/`: installer and installation helper behaviour.
- `packaging/`: package metadata, import boundaries, and release metadata.
- `ci/`: workflow configuration checks.
- `observability/`: output, quiet-mode, and logging behaviour.

Large end-to-end lattice tests are useful, but they should not be the only
protection. Small regression tests make failures easier to understand.

Next release target: keep useful larger checks while adding smaller, targeted
regression tests for each open converter issue.

## Regression Workflow

For converter bugs, prefer a failing-test-first workflow:

```text
1. Add a minimal public test that fails on the current code.
2. Confirm that the failure represents the issue.
3. Implement the fix.
4. Confirm that the new test passes.
5. Keep the test as the regression guard.
```

Tests should assert behaviour, not implementation details, unless the
implementation detail is part of the documented contract.

For parser fixes, asserting the parsed structure is appropriate. For converter
fixes, asserting on the Xsuite object model is usually better than asserting on
intermediate dictionaries.

## SAD Dependency

Tests that do not require external SAD should remain fast and independent.

Tests that require SAD should be marked and capable of being skipped when SAD
is unavailable. CI should run a dedicated SAD smoke or installation job before
running SAD-dependent conversion checks.

Do not rely on filename ordering to ensure that SAD installation tests run
before other tests. Use pytest markers and CI job dependencies instead.

## Temporary Files

Next release target: tests should use isolated temporary directories,
preferably pytest `tmp_path`, for generated SAD files, output files, and helper
scripts.

Tests should not write generated files into the repository root, `tests/`,
`examples/`, or committed output folders unless the test is explicitly updating
a tracked fixture.

Current status: some tests and helper utilities still write fixed temporary
files or output plots into repository paths. These should be cleaned up as each
test file is reviewed.

## Diagnostics

Diagnostics are useful, especially for physics comparisons, but they should not
make routine test runs noisy or leave uncontrolled output files.

Preferred approach:

- default tests assert with clear numerical error messages;
- detailed plots or tables are written only when an explicit diagnostic option
  or environment variable is enabled;
- diagnostic artifacts are written to a temporary or configured artifact
  directory, not to fixed repository paths.

## Physics Edge Cases

Edge cases should be tested when they protect real converter behaviour.

Examples include:

- unusual but valid angles and rotations;
- zero-length or thin elements;
- combined multipole components;
- reversed lines and reversed elements;
- aperture aliases and equivalent parameter forms;
- RF phase and harmonic conventions;
- generated lattice write/reload equivalence.

The default baseline tests should remain simple. Extreme values should be
isolated in targeted tests so they do not obscure unrelated failures.

## Naming

Use descriptive filenames for new tests. Existing numbered test names are
retained where they carry historical context, but test execution must not
depend on those numbers.

SAD element mnemonics may be used in element-specific filenames when they make
the converter contract clearer, for example `cavi`, `aper`, `moni`, and `sol`.

## Transitional Work

Current status: the test tree is being reorganised. Support files have been
moved under `tests/support/`, and fixtures under `tests/fixtures/`, but some
test files still import legacy support module names. Those imports should be
updated when each test file is reviewed.

The current placeholder files are intentional markers for planned coverage.
They should be filled or removed as the associated issues are tackled.

## CI Expectations

Next release target: CI should run the public test suite without private files
or local machine assumptions.

CI should test the commit or pull request under review, not a fixed branch.
External SAD-dependent tests should run in a job that clearly declares the
dependency and depends on a SAD smoke check.
