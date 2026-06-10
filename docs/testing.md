# Testing

Testing should protect converter behaviour while keeping the public repository shareable and maintainable.

Run Python commands in an environment with the SAD2XS development dependencies installed. If using the repository conda environment file, create and activate that environment first.

```bash
pytest
```

## Public test policy

Public tests must use synthetic or publicly shareable inputs.

Private or non-shareable lattices can be used for local validation, but they must not be required for public CI, public issues, or public regression tests. If a private lattice reveals a bug, reduce it to a small synthetic SAD example before adding a public test.

Public tests should not mention private lattice names or institution-specific files unless those files are explicitly public and committed to the repository.

Public examples may use committed public lattices. Regression tests for bugs found in private validation should use reduced synthetic inputs.

## Test layers

Next release target: the test suite should cover several layers:

- Parser tests for comments, section splitting, line syntax, expressions, globals, and functions.
- Element conversion tests for one SAD element or one feature at a time.
- Line construction tests for line composition, repeated elements, and reversed lines.
- Writer tests that verify generated outputs compile and rebuild the intended Xsuite model.
- SAD helper tests that are optional or clearly skipped when an external SAD installation is unavailable.

Large end-to-end lattice tests are useful, but they should not be the only protection. Small regression tests make failures easier to understand.

Current status: the test suite includes several larger conversion checks and some placeholder files.

Next release target: keep the useful larger checks while adding smaller, more targeted regression tests.

## Temporary files

Next release target: tests should use isolated temporary directories, preferably pytest `tmp_path`, for generated SAD files, output files, and helper scripts.

Tests should not write generated files into the repository root, `tests/`, `examples/`, or committed output folders unless the test is explicitly updating a tracked fixture.

Current status: some tests and helper utilities still write fixed temporary files or output plots into repository paths.

## Physics edge cases

Edge cases should be tested when they protect real converter behaviour.

Examples include:

- unusual but valid angles and rotations;
- zero-length or thin elements;
- combined multipole components;
- reversed lines and reversed elements;
- aperture aliases and equivalent parameter forms;
- RF phase and harmonic conventions.

The default baseline tests should remain simple. Extreme values should be isolated in targeted tests so they do not obscure unrelated failures.

## Regression test rule

Next release target: every converter bug fix should add or update a test unless there is a clear reason not to.

The preferred pattern is:

```text
1. Add a minimal synthetic SAD input that reproduces the issue.
2. Convert it through the public API.
3. Assert on the Xsuite object model.
4. If relevant, write and reload the generated output.
```

Tests should assert behaviour, not implementation details, unless the implementation detail is itself part of the documented contract.

For parser fixes, asserting the parsed structure is appropriate. For converter fixes, asserting on the Xsuite objects is usually better than asserting on intermediate dictionaries.

## CI expectations

Next release target: CI should run the public test suite without private files or local machine assumptions.

External SAD-dependent tests should either be skipped when SAD is unavailable or run in a separate job that clearly declares the dependency.
