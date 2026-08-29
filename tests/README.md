# SAD2XS Test Suite

This directory contains the public tests, test support modules, local test
data, and diagnostic artifacts for SAD2XS.

The suite is organised by responsibility. New tests should be placed in the
narrowest folder that describes the behaviour being protected.

## Requirements

The full suite expects an environment with the SAD executable and the Python
project dependencies (`xsuite`, `numpy`, `scipy`, `pyyaml`) available, even though not
every folder invokes SAD (see the Folder Map's Requires SAD column) — this
keeps local and CI runs consistent.

## Running Tests

```
pytest tests/writer/ -v
pytest tests/conversion/elements/ -v
```

See `docs/development/testing.md` for `pytest.ini`'s configuration (`testpaths` order,
`--import-mode=importlib`) and why it matters.

Deprecation warnings are shown by default. Do not suppress them — they often
signal upstream Xsuite or SAD API changes that require attention.

## CI

`run_tests.yml` (one job, two sequential steps: blocking regression, then
non-blocking known-issue) plus per-folder `workflow_dispatch` workflows for
targeted re-runs — see `docs/development/testing.md`'s CI section for the full
description.

## Suite Total

**2383 tests**, counted as instances collected by pytest, so each
parametrisation counts separately.

| Folder | Tests |
|--------|-------|
| `conversion/elements/` | 605 |
| `sad/` | 473 |
| `writer/elements/` | 345 |
| `conversion/pipeline/` | 163 |
| `parser/` | 140 |
| `conversion/` (top level) | 85 |
| `sad_helpers/` | 83 |
| `ci/` | 103 |
| `writer/pipeline/` | 61 |
| `xsuite_helpers/` | 58 |
| `observability/` | 18 |
| `packaging/` | 22 |
| `examples/` | 17 |
| `installation/` | 187 |
| `xtrack/` | 9 |
| `docs/` | 14 |
| **Total** | **2383** |

Each folder README gives the per-file breakdown, and those per-file counts sum
to the folder totals above. Reproduce any of these with
`pytest --collect-only -q`.

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
| `xtrack/` | No | Xsuite ground-truth tests — empirically verifies `xtrack` library behaviour that sad2xs relies on or documents |
| `xsuite_helpers/` | No | `sad2xs.xsuite_helpers` — utilities operating purely on an `xt.Line`, independent of SAD |
| `examples/` | Yes | Public example lattice conversion, write+reload, and script contracts |
| `installation/` | Yes | macOS installer, SAD executable smoke test |
| `packaging/` | No | Package metadata format and public API surface |
| `ci/` | No | GitHub Actions workflow structural and target-path contracts |
| `docs/` | No | Documentation consistency with the codebase — links, cited sections, config tables, test counts |
| `observability/` | Mixed | Converter quiet mode (no SAD); helper output policy (SAD required) |
| `support/` | — | Reusable support modules — not test files |
| `artifacts/` | — | Generated Markdown diagnostic reports (git-ignored) |

See `docs/development/testing.md` for filename conventions.

## Diagnostic Artifacts

Physics comparison tests may write deterministic Markdown reports under
`tests/artifacts/`. These generated reports are ignored by Git, except for the
folder README. They are intended to make failures inspectable without long test
logs: they include the SAD lattice, tested parameters, SAD and Xsuite values,
and tolerance summaries.

Artifact paths should mirror the test area that produced them, for example
`tests/artifacts/conversion/elements/sol/`.

## Known Failures

`KNOWN_ISSUES` in `tests/support/known_issues.py` is the live source of truth
for what is currently known-failing (it is empty as often as not) — see
`docs/development/testing.md`'s Known Failures section for the marker mechanism and CI
routing. Never modify a failing test to make it pass artificially; fix the
root cause. If you add a test that documents a known bug, record it in the
relevant folder README.

Most discrepancies found so far have, on investigation, turned out to be
either a converter bug (fixed) or a fully characterised, documented, and
quantified difference rather than an open bug — see `docs/development/testing.md`'s
Accepted Physics Limitations section for that pattern and the current list
of examples, and `docs/reference/sad-behaviour.md` for the underlying SAD physics and
convention notes behind each one (solenoid `DISFRIN` fringe kick, `MULT`
`K0`/`SK0` dipole fringe, bend element-offset reference-orbit convention,
Edwards-Teng/Mais-Ripken twiss conventions in coupled regions).

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
