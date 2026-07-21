"""
================================================================================
Tests for CI workflow checkout references and structural contracts
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
from pathlib import Path

import pytest
import yaml

################################################################################
# Paths and constants
################################################################################
REPO_ROOT     = Path(__file__).resolve().parents[2]
WORKFLOW_DIR  = REPO_ROOT / ".github" / "workflows"
TEMPLATE_PATH = WORKFLOW_DIR / "_test_template.yml"
DOCKER_PATH   = WORKFLOW_DIR / "docker-build.yml"
RUN_ALL_PATH  = WORKFLOW_DIR / "run_tests.yml"

FOLDER_WORKFLOW_NAMES = [
    "test_packaging.yml",
    "test_ci.yml",
    "test_parser.yml",
    "test_writer.yml",
    "test_observability.yml",
    "test_sad.yml",
    "test_conversion.yml",
    "test_sad_helpers.yml",
    "test_examples.yml",
    "test_installation.yml",
]

DOCKER_BUILD_WORKFLOW_NAME = "SAD Docker Build"

################################################################################
# Helpers
################################################################################
def _load(path):
    """
    Parse a YAML workflow file into a dict.
    """
    with open(path, encoding = "utf-8") as fh:
        return yaml.safe_load(fh)


def _checkout_step(steps):
    """
    Return the first checkout step in a list of job steps, or None.
    """
    for step in steps:
        if step.get("uses", "").startswith("actions/checkout"):
            return step
    return None


def _job_run_text(data, job_name):
    """
    Return all shell commands configured for a workflow job.
    """
    job = data.get("jobs", {}).get(job_name, {})
    return "\n".join(
        step["run"] for step in job.get("steps", []) if "run" in step)


def _step_by_name(data, job_name, step_name):
    """
    Return a named workflow step, or None when it is absent.
    """
    for step in data.get("jobs", {}).get(job_name, {}).get("steps", []):
        if step.get("name") == step_name:
            return step
    return None


def _triggers(data):
    """
    Return the triggers dict from a workflow, handling PyYAML's treatment of
    the YAML 1.1 reserved word `on` as the boolean True rather than a string.
    """
    return data.get(True) or data.get("on") or {}


################################################################################
# Template — trigger
################################################################################
def test_ci_template_has_workflow_call_trigger():
    """
    The test template must be triggered via workflow_call so that per-folder
    workflows can call it with uses:. Removing workflow_call would silently
    break every folder workflow.
    """
    data = _load(TEMPLATE_PATH)
    assert "workflow_call" in _triggers(data), (
        "_test_template.yml must have a `workflow_call` trigger so folder "
        "workflows can invoke it with `uses:`.")


def test_ci_template_requires_test_files_input():
    """
    The test_files input must be marked required so a caller that omits it
    fails loudly rather than running with an empty test list.
    """
    data    = _load(TEMPLATE_PATH)
    inputs  = _triggers(data)["workflow_call"]["inputs"]
    assert "test_files" in inputs, (
        "_test_template.yml must declare a `test_files` input.")
    assert inputs["test_files"].get("required") is True, (
        "The `test_files` input in _test_template.yml must be required=true.")


################################################################################
# Template — discover job checkout
################################################################################
def test_ci_template_discover_job_uses_checkout_v7():
    """
    The discover job must use actions/checkout@v7. An older version risks
    incompatibility with the ubuntu-24.04 runner.
    """
    data  = _load(TEMPLATE_PATH)
    steps = data["jobs"]["discover"]["steps"]
    step  = _checkout_step(steps)
    assert step is not None, (
        "The `discover` job in _test_template.yml should have a checkout step.")
    assert step["uses"] == "actions/checkout@v7", (
        f"""Discover job should use actions/checkout@v7, got: {step["uses"]!r}""")


def test_ci_template_discover_job_does_not_override_checkout_ref():
    """
    The discover job must not set an explicit ref on the checkout step. Without
    an override, actions/checkout uses the commit that triggered the workflow —
    the required behaviour for PR and branch validation. An explicit ref
    (e.g. `main`) would cause CI to test a different commit than the one that
    triggered the run.
    """
    data  = _load(TEMPLATE_PATH)
    steps = data["jobs"]["discover"]["steps"]
    step  = _checkout_step(steps)
    assert step is not None, (
        "The `discover` job should have a checkout step.")
    ref = step.get("with", {}).get("ref")
    assert ref is None, (
        "The `discover` job checkout should not override the ref. "
        f"Got: {ref!r}")


################################################################################
# Template — run job checkout
################################################################################
def test_ci_template_run_job_uses_checkout_v7():
    """
    The run job must use actions/checkout@v7.
    """
    data  = _load(TEMPLATE_PATH)
    steps = data["jobs"]["run"]["steps"]
    step  = _checkout_step(steps)
    assert step is not None, (
        "The `run` job in _test_template.yml should have a checkout step.")
    assert step["uses"] == "actions/checkout@v7", (
        f"""Run job should use actions/checkout@v7, got: {step["uses"]!r}""")


def test_ci_template_run_job_does_not_override_checkout_ref():
    """
    The run job must not set an explicit ref on the checkout step, for the same
    reason as the discover job. Both jobs must be consistent.
    """
    data  = _load(TEMPLATE_PATH)
    steps = data["jobs"]["run"]["steps"]
    step  = _checkout_step(steps)
    assert step is not None, (
        "The `run` job should have a checkout step.")
    ref = step.get("with", {}).get("ref")
    assert ref is None, (
        "The `run` job checkout should not override the ref. "
        f"Got: {ref!r}")


################################################################################
# Template — matrix strategy
################################################################################
def test_ci_template_run_job_matrix_does_not_fail_fast():
    """
    The matrix strategy must have fail-fast=false so that a single failing test
    file does not cancel the remaining matrix legs and hide other failures.
    """
    data     = _load(TEMPLATE_PATH)
    strategy = data["jobs"]["run"].get("strategy", {})
    assert strategy.get("fail-fast") is False, (
        "The `run` job matrix strategy should set fail-fast: false so all "
        "test files run independently.")


################################################################################
# Per-folder workflows — triggers
################################################################################
@pytest.mark.parametrize("workflow_name", FOLDER_WORKFLOW_NAMES)
def test_ci_folder_workflow_has_workflow_dispatch_trigger(workflow_name):
    """
    Each per-folder workflow must have a workflow_dispatch trigger so it can be
    run manually from the GitHub Actions UI for targeted re-runs.
    """
    data = _load(WORKFLOW_DIR / workflow_name)
    assert "workflow_dispatch" in _triggers(data), (
        f"{workflow_name} should have a `workflow_dispatch` trigger for "
        f"manual re-runs.")


################################################################################
# Per-folder workflows — template usage
################################################################################
@pytest.mark.parametrize("workflow_name", FOLDER_WORKFLOW_NAMES)
def test_ci_folder_workflow_uses_shared_template(workflow_name):
    """
    Each per-folder workflow must delegate to the shared _test_template.yml via
    uses:. Direct job definitions would bypass the consistent Docker pull and
    test matrix logic.
    """
    data     = _load(WORKFLOW_DIR / workflow_name)
    jobs     = data["jobs"]
    job_name = list(jobs.keys())[0]
    uses     = jobs[job_name].get("uses", "")
    assert uses == "./.github/workflows/_test_template.yml", (
        f"{workflow_name} should call the shared template via "
        f"`uses: ./.github/workflows/_test_template.yml`. Got: {uses!r}")


@pytest.mark.parametrize("workflow_name", FOLDER_WORKFLOW_NAMES)
def test_ci_folder_workflow_sets_pull_tag(workflow_name):
    """
    Each per-folder workflow must pass a pull_tag to the template so the Docker
    image tag is always explicit and auditable.
    """
    data     = _load(WORKFLOW_DIR / workflow_name)
    jobs     = data["jobs"]
    job_name = list(jobs.keys())[0]
    with_    = jobs[job_name].get("with", {})
    assert "pull_tag" in with_, (
        f"{workflow_name} should pass `pull_tag` to the template.")
    assert with_["pull_tag"], (
        f"{workflow_name} `pull_tag` should be a non-empty string.")


################################################################################
# Run-all workflow — triggers
################################################################################
def test_ci_run_all_workflow_has_pull_request_trigger():
    """
    run_tests.yml must trigger on pull_request so regressions are caught before
    any merge to main or a release branch.
    """
    data = _load(RUN_ALL_PATH)
    assert "pull_request" in _triggers(data), (
        "run_tests.yml should have a `pull_request` trigger.")


def test_ci_run_all_workflow_has_schedule_trigger():
    """
    run_tests.yml must have a schedule trigger for weekly runs that catch
    upstream breakage from new SAD or Xsuite releases independent of SAD2XS
    commits.
    """
    data = _load(RUN_ALL_PATH)
    assert "schedule" in _triggers(data), (
        "run_tests.yml should have a `schedule` trigger for weekly runs.")


def test_ci_run_all_workflow_has_workflow_dispatch_trigger():
    """
    run_tests.yml must be manually triggerable so the full suite can be re-run
    on demand from the GitHub Actions UI.
    """
    data = _load(RUN_ALL_PATH)
    assert "workflow_dispatch" in _triggers(data), (
        "run_tests.yml should have a `workflow_dispatch` trigger.")


################################################################################
# Run-all workflow — regression gate and known issues
################################################################################
def test_ci_regression_step_excludes_known_issues():
    """
    The `Run regression tests` step must exclude known_issue-marked tests
    via a `not known_issue` pytest filter, after (re)installing the
    package in editable mode.
    """
    data = _load(RUN_ALL_PATH)
    step = _step_by_name(data, "run-tests", "Run regression tests")
    assert step is not None, "run-tests job must have a `Run regression tests` step."
    assert "not known_issue" in step["run"]
    assert "pip install --no-cache-dir -e ." in step["run"]


def test_ci_known_issues_step_selects_only_known_issues():
    """
    The `Run known-issue tests` step must select only known_issue-marked
    tests (not also apply the regression step's `not known_issue`
    exclusion), after (re)installing the package in editable mode.
    """
    data = _load(RUN_ALL_PATH)
    step = _step_by_name(data, "run-tests", "Run known-issue tests")
    assert step is not None, "run-tests job must have a `Run known-issue tests` step."
    assert "known_issue" in step["run"]
    assert "not known_issue" not in step["run"]
    assert "pip install --no-cache-dir -e ." in step["run"]


def test_ci_known_issues_step_is_non_blocking():
    """
    The `Run known-issue tests` step must set continue-on-error: true
    (a known failure shouldn't fail the job), while the run-tests job
    itself stays blocking.
    """
    data = _load(RUN_ALL_PATH)
    assert not data["jobs"]["run-tests"].get("continue-on-error", False), (
        "The run-tests job itself must not be continue-on-error.")
    step = _step_by_name(data, "run-tests", "Run known-issue tests")
    assert step is not None
    assert step.get("continue-on-error") is True, (
        "`Run known-issue tests` step must have continue-on-error: true.")


def test_ci_regression_job_is_blocking():
    """
    The run-tests job itself must not be continue-on-error, so a genuine
    regression still fails the CI run.
    """
    data = _load(RUN_ALL_PATH)
    assert not data["jobs"]["run-tests"].get("continue-on-error", False), (
        "run-tests job must be blocking (no continue-on-error on the job).")


def test_ci_run_all_job_does_not_override_checkout_ref():
    """
    The run-tests job's checkout step must not override ref, for the same
    reason as the per-folder template jobs: CI should test the commit
    that triggered the run.
    """
    data = _load(RUN_ALL_PATH)
    step = _checkout_step(data["jobs"]["run-tests"]["steps"])
    assert step is not None
    assert step.get("with", {}).get("ref") is None


################################################################################
# Docker build workflow
################################################################################
def test_ci_docker_build_workflow_name_is_stable():
    """
    The docker-build workflow's `name:` field is documented here so that a
    rename is caught immediately. The name is referenced in external contexts
    (issue trackers, team runbooks) and should not change without review.
    """
    data = _load(DOCKER_PATH)
    assert data["name"] == DOCKER_BUILD_WORKFLOW_NAME, (
        f"docker-build.yml `name` should be `{DOCKER_BUILD_WORKFLOW_NAME}`. "
        f"Update DOCKER_BUILD_WORKFLOW_NAME in this file if intentionally "
        f"""renamed. Got: {data["name"]!r}""")


def test_ci_docker_build_triggers_on_push_to_main():
    """
    The Docker build must trigger on pushes to main so the SAD image stays
    current with the default branch.
    """
    data     = _load(DOCKER_PATH)
    push_on  = _triggers(data).get("push", {})
    branches = push_on.get("branches", [])
    assert "main" in branches, (
        f"docker-build.yml should trigger on push to `main`. "
        f"Got branches: {branches}")


def test_ci_docker_build_has_workflow_dispatch_trigger():
    """
    The Docker build must be manually triggerable so the image can be rebuilt
    on demand without waiting for a push to main.
    """
    data = _load(DOCKER_PATH)
    assert "workflow_dispatch" in _triggers(data), (
        "docker-build.yml should have a `workflow_dispatch` trigger.")


def test_ci_docker_build_uses_checkout_v7():
    """
    The Docker build job must use actions/checkout@v7.
    """
    data  = _load(DOCKER_PATH)
    jobs  = data["jobs"]
    job   = jobs[list(jobs.keys())[0]]
    step  = _checkout_step(job["steps"])
    assert step is not None, (
        "docker-build.yml should have a checkout step.")
    assert step["uses"] == "actions/checkout@v7", (
        f"docker-build.yml checkout should use actions/checkout@v7. "
        f"""Got: {step["uses"]!r}""")
