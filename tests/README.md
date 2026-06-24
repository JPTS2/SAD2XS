# SAD2XS Test Suite

This directory contains the public tests, test support modules, local test
data, and diagnostic artifacts for SAD2XS.

The suite is organised by responsibility. New tests should be placed in the
narrowest folder that describes the behaviour being protected.

## Requirements

The SAD2XS converter is validated against SAD, so the test suite is expected to
run in an environment where the SAD executable and the Python project
dependencies (`xtrack`, `numpy`, `pyyaml`) are available.

Some tests — notably `parser/`, `writer/`, `packaging/`, `ci/`, and the
converter quiet-mode tests in `observability/` — do not invoke the SAD
executable. They still live inside the same environment so that local and CI
runs are consistent.

## Running Tests

`pytest.ini` at the repository root controls the full suite configuration:

- `testpaths` is an explicit ordered list: `installation → sad_helpers → sad → parser → conversion → writer → examples → packaging → observability → ci`. The order ensures SAD is verified before SAD-dependent tests run. **Any new test directory must be added to this list**, or it will not be collected.
- `-ra` prints a short summary of all non-passing tests at the end of the run.
- `--import-mode=importlib` is required because `tests/sad/` and `tests/conversion/elements/` share basenames (e.g. `test_bend.py`). Without this, pytest collection fails.

To run a single folder:

```
pytest tests/writer/ -v
pytest tests/conversion/elements/ -v
```

Deprecation warnings are shown by default. Do not suppress them — they often
signal upstream Xsuite or SAD API changes that require attention.

## CI

The master workflow runs the full suite in a single job in the order defined
by `pytest.ini` `testpaths`:

- `run_tests.yml` — master workflow. One job (`run-tests`) with two sequential
  steps. Step 1 runs `pytest -m "not known_issue" tests/` and is blocking —
  any failure blocks the PR. Step 2 runs `pytest -m "known_issue" tests/` with
  `continue-on-error: true` so known-bug failures are visible but never block a
  merge. The single job ensures `tests/sad/` (SAD syntax assumptions) always
  runs before `tests/conversion/` (conversion correctness), matching the
  `testpaths` order.

- Per-folder workflows — one workflow per test folder, all manually triggerable
  via `workflow_dispatch`. Allow targeted re-runs of one area without waiting
  for the full suite.

Both CI setups use the Docker image built by `docker-build.yml`, which packages
the SAD executable and all Python dependencies.

## Folder Map

| Folder | Requires SAD | Contents |
|--------|-------------|----------|
| `parser/` | No | SAD text parsing and expression conversion |
| `conversion/` | Yes | SAD-to-Xsuite conversion; element and pipeline sub-tests |
| `conversion/elements/` | Yes | Per-element-family conversion tests |
| `conversion/pipeline/` | Yes | Public conversion options and pipeline behaviour |
| `writer/` | No | Generated lattice and optics writer behaviour |
| `writer/elements/` | No | Per-element-family serialisation roundtrip tests |
| `writer/pipeline/` | No | Whole-writer entry points and supported-element policy |
| `sad/` | Yes | SAD syntax assumption tests — empirically verifies which parameters each SAD element type accepts or rejects |
| `sad_helpers/` | Yes | `sad2xs.sad_helpers` — command construction, output parsing, smoke tests |
| `examples/` | Yes | Public example lattice conversion, write+reload, and script contracts |
| `installation/` | Yes | macOS installer, SAD executable smoke test |
| `packaging/` | No | Package metadata format and public API surface |
| `ci/` | No | GitHub Actions workflow structural and target-path contracts |
| `observability/` | Mixed | Converter quiet mode (no SAD); helper output policy (SAD required) |
| `support/` | — | Reusable support modules — not test files |
| `artifacts/` | — | Generated Markdown diagnostic reports (git-ignored) |

## Naming

Use descriptive test filenames. Element-specific tests may use SAD element
mnemonics when that is clearer for the converter contract — for example
`cavi`, `aper`, `moni`, and `sol`.

For large element families, a subfolder is acceptable, but do not add
per-element subfolders by default unless the test set is large enough to
justify the extra navigation.

## Diagnostic Artifacts

Physics comparison tests may write deterministic Markdown reports under
`tests/artifacts/`. These generated reports are ignored by Git, except for the
folder README. They are intended to make failures inspectable without long test
logs: they include the SAD lattice, tested parameters, SAD and Xsuite values,
and tolerance summaries.

Artifact paths should mirror the test area that produced them, for example
`tests/artifacts/conversion/elements/sol/`.

## Test Counts

Total collected: **1404 tests** (1353 pass, 51 fail) as of the test run on
this branch. The breakdown by failure group is in the Known Failures section
below. Individual folder READMEs document per-file counts.

## Known Failures

The test suite contains currently failing tests that document known bugs.

Tests linked to open issues are marked during collection from the central
mapping in `tests/support/known_issues.py`. They remain ordinary failing tests;
the marker controls CI selection only and does not use `xfail`.

**51 failing tests** across `parser/`, `conversion/elements/`, and
`conversion/pipeline/` document known incorrect behaviour in the production
code. These tests are the spec for the fix work that follows. They must not be
modified to pass — they are the record of what is broken and what needs to be
done. All 51 are linked to open issues.

Never modify a failing test to make it pass artificially. Fix the root cause.
If you add a test that documents a known bug, record it in the relevant folder
README.
