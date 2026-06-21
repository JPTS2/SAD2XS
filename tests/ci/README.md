# CI Tests

This folder contains tests for the repository's GitHub Actions workflow
configuration.

These tests parse the YAML workflow files directly and assert on their
structural and behavioural contracts. They are the canary for CI
misconfigurations: a broken checkout ref, a missing trigger, or a stale test
path will be caught here before it silently affects a real CI run.

## What Belongs Here

- Template structural contracts (`workflow_call` trigger, required inputs,
  checkout version, checkout ref, fail-fast policy).
- Per-folder workflow contracts (`workflow_dispatch` trigger, template
  delegation, non-empty `pull_tag`).
- Master workflow trigger contracts (pull_request, schedule, workflow_dispatch
  for `run_tests.yml`).
- Test path validation (paths listed in per-folder workflows exist in the repo).
- Docker build workflow trigger and naming contracts.

## What Does Not Belong Here

- Converter physics, parser rules, or writer correctness.
- Installation or package metadata.
- Anything that requires running a workflow — these tests are pure YAML analysis.

## Notes

Both files use `pyyaml` (`import yaml`). GitHub Actions YAML uses `on:` as a
top-level key, which PyYAML 5+ parses as the boolean `True` rather than the
string `"on"`. All trigger access uses a `_triggers(data)` helper that checks
`data.get(True)` first to handle this.

## Coverage

### `test_workflow_checkout_refs.py` — 17 test functions, ~45 instances, all expected to pass

**Template tests (7, not parametrised):**
- Template has `workflow_call` trigger (required for per-folder delegation)
- Template `test_files` input is marked `required: true`
- Discover job uses `actions/checkout@v4` and checks out `main`
- Run job uses `actions/checkout@v4` and checks out `main`
- Run job matrix strategy has `fail-fast: false`

**Per-folder workflow tests (3 functions × 9 workflows = 27 instances):**

Parametrised over all 9 per-folder workflows (`test_packaging.yml`,
`test_ci.yml`, `test_parser.yml`, `test_writer.yml`, `test_observability.yml`,
`test_conversion.yml`, `test_sad_helpers.yml`, `test_examples.yml`,
`test_installation.yml`).

- Each workflow has a `workflow_dispatch` trigger for manual re-runs
- Each workflow delegates to `_test_template.yml` via `uses:`
- Each workflow passes a non-empty `pull_tag`

**Run-all workflow tests (3, not parametrised):**
- `run_tests.yml` has a `pull_request` trigger (catches regressions before merge)
- `run_tests.yml` has a `schedule` trigger (weekly runs for upstream breakage)
- `run_tests.yml` has a `workflow_dispatch` trigger (manual re-runs)

**Docker build tests (4, not parametrised):**
- `docker-build.yml` name is stable and documented
- Triggers on push to `main`
- Has `workflow_dispatch` trigger
- Uses `actions/checkout@v4`

### `test_workflow_test_targets.py` — 3 test functions × 9 workflows = 27 instances, all expected to pass

Parametrised over the same 9 per-folder workflows. Parses each workflow's
`test_files:` block (stripping blank lines and comment lines, matching the
template's own normalisation logic).

| Test | Expected result | What it checks |
|------|----------------|----------------|
| `test_ci_folder_workflow_lists_at_least_one_test_target` | 9 PASS | Each workflow has a non-empty `test_files:` block |
| `test_ci_folder_workflow_test_targets_all_exist` | 9 PASS | Each listed path (`tests/<folder>`) exists as a directory |
| `test_ci_folder_workflow_test_targets_are_under_tests_directory` | 9 PASS | All paths start with `tests/` |
