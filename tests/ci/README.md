# CI Tests

This folder contains tests for the repository's test-running configuration:
the GitHub Actions workflows and `pytest.ini`.

Most of these tests parse the YAML workflow files directly and assert on
their structural and behavioural contracts; one parses `pytest.ini` and
cross-checks it against a real collection of `tests/`. They are the canary
for test-configuration misconfigurations: a broken checkout ref, a missing
trigger, a stale test path, or a test directory silently absent from
`testpaths` will be caught here before it silently affects a real run.

This folder runs first (see `pytest.ini`'s `testpaths`), so a misconfigured
`testpaths` list is caught before anything else runs, not after.

## What Belongs Here

- Template structural contracts (`workflow_call` trigger, required inputs,
  checkout version, checkout ref, fail-fast policy).
- Per-folder workflow contracts (`workflow_dispatch` trigger, template
  delegation, non-empty `pull_tag`).
- Master workflow trigger contracts (pull_request, schedule, workflow_dispatch
  for `run_tests.yml`).
- Test path validation (paths listed in per-folder workflows exist in the repo).
- Docker build workflow trigger and naming contracts.
- `pytest.ini`'s `testpaths` completeness (every test collected by a full
  scan of `tests/` is also collected via `testpaths`, and vice versa).

## What Does Not Belong Here

- Converter physics, parser rules, or writer correctness.
- Installation or package metadata.
- Anything that requires actually running a workflow or the full test suite
  for its own sake — these are static configuration checks.

## Notes

Both files use `pyyaml` (`import yaml`). GitHub Actions YAML uses `on:` as a
top-level key, which PyYAML 5+ parses as the boolean `True` rather than the
string `"on"`. All trigger access uses a `_triggers(data)` helper that checks
`data.get(True)` first to handle this.

## Coverage

### `test_workflow_checkout_refs.py` — 49 tests, all expected to pass

**Template tests (7, not parametrised):**
- Template has `workflow_call` trigger (required for per-folder delegation)
- Template `test_files` input is marked `required: true`
- Discover job uses `actions/checkout@v7` with no `ref` override (checks out triggering commit)
- Run job uses `actions/checkout@v7` with no `ref` override (checks out triggering commit)
- Run job matrix strategy has `fail-fast: false`

**Per-folder workflow tests (3 functions × 10 workflows = 30 instances):**

Parametrised over all 10 per-folder workflows (`test_packaging.yml`,
`test_ci.yml`, `test_parser.yml`, `test_writer.yml`, `test_observability.yml`,
`test_sad.yml`, `test_conversion.yml`, `test_sad_helpers.yml`,
`test_examples.yml`, `test_installation.yml`).

- Each workflow has a `workflow_dispatch` trigger for manual re-runs
- Each workflow delegates to `_test_template.yml` via `uses:`
- Each workflow passes a non-empty `pull_tag`

**Run-all workflow tests (3, not parametrised):**
- `run_tests.yml` has a `pull_request` trigger (catches regressions before merge)
- `run_tests.yml` has a `schedule` trigger (weekly runs for upstream breakage)
- `run_tests.yml` has a `workflow_dispatch` trigger (manual re-runs)

**Regression-gate tests (5 functions, 5 instances):**
- The `Run regression tests` step in the single `run-tests` job selects `not known_issue`
- The `Run known-issue tests` step selects `known_issue` only and is non-blocking (`continue-on-error: true`)
- The `run-tests` job itself remains blocking
- The `run-tests` job checks out the triggering commit without a `ref` override

**Docker build tests (4, not parametrised):**
- `docker-build.yml` name is stable and documented
- Triggers on push to `main`
- Has `workflow_dispatch` trigger
- Uses `actions/checkout@v7`

### `test_workflow_test_targets.py` — 30 tests (3 functions x 10 workflows), all expected to pass

Parametrised over the same 10 per-folder workflows. Parses each workflow's
`test_files:` block (stripping blank lines and comment lines, matching the
template's own normalisation logic).

| Test | Expected result | What it checks |
|------|----------------|----------------|
| `test_ci_folder_workflow_lists_at_least_one_test_target` | 10 PASS | Each workflow has a non-empty `test_files:` block |
| `test_ci_folder_workflow_test_targets_all_exist` | 10 PASS | Each listed path (`tests/<folder>`) exists as a directory |
| `test_ci_folder_workflow_test_targets_are_under_tests_directory` | 10 PASS | All paths start with `tests/` |

### `test_pytest_ini_testpaths.py` — 2 tests, all expected to pass

Runs `pytest --collect-only` as a subprocess twice (once bare, using
`pytest.ini`'s `testpaths`; once against `tests/` directly) and compares the
collected test node ID sets.

| Test | Expected result | What it checks |
|------|----------------|----------------|
| `test_testpaths_collects_every_test_under_the_tests_directory` | PASS | Every test found by a full scan of `tests/` is also collected via `testpaths` |
| `test_testpaths_does_not_reference_stale_paths` | PASS | `testpaths` does not list a directory contributing no test a full scan finds |

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
