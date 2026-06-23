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

`pytest.ini` at the repository root sets `testpaths = tests` so that running
`pytest` from the root directory collects and runs the full suite without
arguments. The `-ra` flag is set by default, which prints a short summary of
all non-passing tests at the end of the run.

To run a single folder:

```
pytest tests/writer/ -v
pytest tests/conversion/elements/ -v
```

Deprecation warnings are shown by default. Do not suppress them — they often
signal upstream Xsuite or SAD API changes that require attention.

## CI

The master workflow separates merge-blocking regression coverage from visible
tests for open issues:

- `run_tests.yml` — master workflow. Its blocking `sad-free` and `sad-required`
  jobs run tests selected by `-m "not known_issue"`. A parallel, non-blocking
  `known-issues` job runs `-m "known_issue"` normally so full failure output
  remains visible without masking new regressions.

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

Total collected: **1218 tests** (1148 pass, 70 fail) as of the test run on
this branch. The breakdown by failure group is in the Known Failures section
below. Individual folder READMEs document per-file counts.

## Known Failures

The test suite contains currently failing tests that document known bugs. These fall into two groups:

Tests linked to open issues are marked during collection from the central
mapping in `tests/support/known_issues.py`. They remain ordinary failing tests;
the marker controls CI selection only and does not use `xfail`.

**Group A — Documented writer issues:** 8 tests (7 in `writer/elements/`, 1
in `writer/pipeline/`) that expose known writer bugs tracked as issues #62
(aperture dimensions not written as live expressions) and #63 (k1 not written
for combined-function bends). These tests must remain failing until the
corresponding issues are fixed.

**Group B — Exposing production bugs:** 62 tests across
`parser/`, `conversion/elements/`, and `conversion/pipeline/` that document
known incorrect behaviour in the production code. These tests are the spec for
the fix work that follows this PR. They must not be modified to pass — they are
the record of what is broken and what needs to be done.

All 70 currently failing instances are linked to open issues.

Never modify a failing test to make it pass artificially. Fix the root cause.
If you add a test that documents a known bug, record it in the relevant folder
README.
