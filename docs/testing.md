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
| `sad/` | Yes | Empirical SAD syntax assumption tests — machine-verified parameter acceptance and rejection per element type |
| `sad_helpers/` | Yes | Reusable helper APIs that call or prepare external SAD runs |
| `examples/` | Yes | Public example execution and example lattice checks |
| `installation/` | Yes | Installer and SAD executable behaviour |
| `packaging/` | No | Package metadata, import boundaries, and release metadata |
| `ci/` | No | Workflow configuration correctness |
| `observability/` | Mixed | Output suppression, quiet mode, and helper output policy |

Total collected: **1657 tests** (1638 pass, 19 currently failing) as of
this branch. See `tests/README.md` for the breakdown by failure group.

## SAD Syntax Assumption Tests

`tests/sad/` contains empirical tests that machine-verify which parameters each
SAD element type accepts or rejects at runtime. When the behaviour of any SAD
element, parameter, or reserved name is uncertain, a test is added here to
establish ground truth before any converter logic is written or changed. The
SAD runtime is the authoritative source — not documentation or assumption.

The accepted/rejected parameter matrix for all tested element types is in
`tests/sad/README.md`. The findings are consistent with direct confirmation from
K. Oide (SAD author, 2026-06-24) on typed-element parameter restrictions.

Reference: [SAD FFS command documentation](https://acc-physics.kek.jp/SAD/how-to-use-sad/sad-ffs-command-sad-script/)

## pytest Configuration

`pytest.ini` at the repository root sets `testpaths` as an explicit ordered
list (installation → sad\_helpers → sad → parser → conversion → writer →
examples → packaging → observability → ci). The order ensures SAD installation
is verified before SAD-dependent tests run.

`--import-mode=importlib` is also set in `pytest.ini`. It is required because
`tests/sad/` and `tests/conversion/elements/` share basenames (e.g.
`test_bend.py`). Without importlib mode pytest uses flat module names and
collects with errors. Any new test directory added to the suite must also be
added to `testpaths` in `pytest.ini`.

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

The suite contains **19 currently failing tests**, all linked to open GitHub
issues.

Tests associated with open issues receive the `known_issue` marker during
collection from `tests/support/known_issues.py`. They are not `xfail` tests:
they execute and report ordinary failures. CI runs unmarked tests as the
blocking regression gate and marked tests in a visible non-blocking job.

Local selections use:

```bash
pytest -m "not known_issue"  # blocking regression selection
pytest -m "known_issue"      # tests documenting open issues
```

The 19 failures are all in `conversion/elements/` (issues #33, #55). The
mapping is maintained in `tests/support/known_issues.py`. These tests must
not be modified to pass artificially — they are the record of what is broken
and what needs to be fixed.

`tests/conftest.py` fails collection loudly if a `PARTIAL_KNOWN_ISSUES`
parameter-id fragment matches nothing currently collected — e.g. a fragment
that stopped matching after a parametrize change. This is checked
automatically at collection time for whatever subset of the suite is being
run; it does not require a full-suite run to catch. This does not cover
`KNOWN_ISSUE_TESTS` (exact test names) — that would need to catch a renamed
test function, a scenario not yet observed, so it was left out rather than
added speculatively.

## Accepted Physics Limitations

Not every documented SAD-vs-Xsuite difference is an open bug. Some are
permanent, deliberate limitations — a physics effect SAD2XS does not and will
not model, with the divergence it causes locked in by a dedicated test that
asserts the divergence itself, rather than a bug to fix.

These tests are not added to `tests/support/known_issues.py` and do not carry
the `known_issue` marker — they are expected to pass, and a passing result
documents that the limitation still behaves as understood. If one of these
tests starts failing, or unexpectedly starts passing in the "matches"
direction, that is a signal the underlying assumption has changed and needs
re-examination — not a regression to silently fix.

Current example: `test_sol_disfrin_off_diverges_from_xsuite_in_tracking`
(`tests/conversion/elements/test_sol.py`) asserts that SAD and Xsuite
genuinely diverge for a solenoid without `DISFRIN=1`, since SAD2XS does not
model SAD's solenoid fringe kick. See `docs/design-decisions.md` for why, and
`docs/sad-helpers.md` for a related but distinct beta-function convention
note relevant to solenoid comparisons.

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
