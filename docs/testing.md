# Testing

Testing protects converter behaviour while keeping the public repository
shareable and maintainable.

Run the full suite from the repository root (the `pytest.ini` sets `testpaths`
and `-ra` automatically):

```bash
pytest
```

To run a single area:

```bash
pytest tests/conversion/elements/ -v
pytest tests/parser/ -v
```

The test tree is documented in full in `tests/README.md`.

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

The public test tree is organised into responsibility-based folders. Each folder
has its own README with per-file coverage tables and known-failure documentation.

| Folder | Requires SAD | Responsibility |
|--------|-------------|----------------|
| `parser/` | No | SAD text parsing and parser error handling |
| `conversion/elements/` | Yes | Individual SAD element conversion |
| `conversion/pipeline/` | Yes | Public conversion options and pipeline behaviour |
| `writer/` | No | Generated lattice and optics writer behaviour |
| `sad_helpers/` | Yes | Reusable helper APIs that call or prepare external SAD runs |
| `examples/` | Yes | Public example execution and example lattice checks |
| `installation/` | Yes | Installer and SAD executable behaviour |
| `packaging/` | No | Package metadata, import boundaries, and release metadata |
| `ci/` | No | Workflow configuration correctness |
| `observability/` | Mixed | Output suppression, quiet mode, and helper output policy |

Total collected: **1184 tests** (1041 pass, 143 currently failing) as of
this branch. See `tests/README.md` for the breakdown by failure group.

Large end-to-end lattice tests are useful, but they should not be the only
protection. Small, targeted regression tests make failures easier to understand
and diagnose.

## Regression Workflow

For converter bugs, use a failing-test-first workflow:

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

## Known Failures

The suite contains 143 currently failing tests, split into two groups:

Tests associated with open issues receive the `known_issue` marker during
collection from `tests/support/known_issues.py`. They are not `xfail` tests:
they execute and report ordinary failures. CI runs unmarked tests as the
blocking regression gate and marked tests in a visible non-blocking job.

Local selections use:

```bash
pytest -m "not known_issue"  # blocking regression selection
pytest -m "known_issue"      # tests documenting open issues
```

**Group A (17 tests)** — known writer bugs, tracked as open issues:
- Issue #17: `knl`/`ksl` not written for quad, sext, and oct elements
- Issue #62: aperture dimensions written as literal numbers rather than live expressions
- Issue #63: `k1` not written for combined-function bends

**Group B (126 tests)** — converter and parser bugs documented by the tests.
These tests are the spec for the fix work that follows. They must not be
modified to pass artificially — they are the record of what is broken and what
needs to be done.

All 143 currently failing instances are linked to open issues; combined
rectangular-and-elliptical aperture conversion is tracked by issue #66.

## SAD Dependency

The test suite requires SAD for conversion and helper tests. Parser, writer,
packaging, CI, and converter quiet-mode tests do not invoke the SAD executable.

CI uses two blocking regression jobs and one non-blocking known-issues job.
`sad-free` runs first; `sad-required` follows only when that regression gate
passes. The known-issues job runs independently and retains full failure output.

Do not rely on filename ordering to ensure that SAD installation tests run
before other tests. The explicit job dependency in `run_tests.yml` handles this.

## Temporary Files

Tests use `pytest`'s `tmp_path` fixture for generated SAD files, output files,
and helper scripts. Tests do not write into the repository root, `tests/`,
`examples/`, or committed output folders.

Physics comparison tests may write deterministic Markdown diagnostic reports
under `tests/artifacts/`. These are git-ignored and are written only on
failure, to make comparisons inspectable without long test logs.

## Diagnostics

Physics comparison tests assert with clear numerical error messages by default.
When a test fails, a Markdown report is written to `tests/artifacts/` with
the SAD lattice, tested parameters, SAD and Xsuite values, and tolerance
summaries. The artifact path mirrors the test area that produced it.

## CI

Three layers of CI run the test suite automatically:

**`run_tests.yml`** — master workflow. Triggered on pull requests to `main` and
`release/**`, and on a weekly schedule. Runs `sad-free` followed by
`sad-required`. Both jobs pull the SAD Docker image and run pytest inside it.

**Per-folder workflows** (`test_parser.yml`, `test_conversion.yml`, etc.) —
one workflow per test folder, all manually triggerable via `workflow_dispatch`.
These allow targeted re-runs of one area without waiting for the full suite.

**`docker-build.yml`** — builds the SAD Docker image on push to `main` and on
demand. The SAD image packages the SAD executable and all Python dependencies.

## Physics Edge Cases

Edge cases should be tested when they protect real converter behaviour.
Examples include:

- unusual but valid angles and rotations
- zero-length or thin elements embedded in a physical lattice
- combined multipole components
- reversed lines and reversed elements
- aperture aliases and equivalent parameter forms
- RF phase and harmonic conventions
- generated lattice write/reload equivalence

The default baseline tests should remain simple. Extreme values should be
isolated in targeted tests so they do not obscure unrelated failures.

When a test calls the SAD executable, ensure the lattice is physically valid —
a line composed entirely of zero-length elements is degenerate and will cause
SAD to abort. Embed zero-length elements in a lattice with at least one
physical element.

## Naming

Use descriptive filenames. SAD element mnemonics may be used in
element-specific filenames when they make the converter contract clearer — for
example `cavi`, `aper`, `moni`, and `sol`.

For large element families a subfolder is acceptable, but do not add
per-element subfolders by default unless the test set is large enough to
justify the extra navigation.
