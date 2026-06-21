"""
================================================================================
Tests for CI workflow checkout references and structural contracts
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
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
    with open(path, encoding = "utf-8") as fh:
        return yaml.safe_load(fh)


def _checkout_step(steps):
    """Return the first checkout step in a list of job steps, or None."""
    for step in steps:
        if step.get("uses", "").startswith("actions/checkout"):
            return step
    return None


def _triggers(data):
    """
    Return the triggers dict from a workflow, handling PyYAML's treatment of
    the YAML 1.1 reserved word 'on' as the boolean True rather than a string.
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
        "_test_template.yml must have a 'workflow_call' trigger so folder "
        "workflows can invoke it with 'uses:'.")


def test_ci_template_requires_test_files_input():
    """
    The test_files input must be marked required so a caller that omits it
    fails loudly rather than running with an empty test list.
    """
    data    = _load(TEMPLATE_PATH)
    inputs  = _triggers(data)["workflow_call"]["inputs"]
    assert "test_files" in inputs, (
        "_test_template.yml must declare a 'test_files' input.")
    assert inputs["test_files"].get("required") is True, (
        "The 'test_files' input in _test_template.yml must be required=true.")


################################################################################
# Template — discover job checkout
################################################################################
def test_ci_template_discover_job_uses_checkout_v4():
    """
    The discover job must use actions/checkout@v4. An older version risks
    incompatibility with the ubuntu-24.04 runner.
    """
    data  = _load(TEMPLATE_PATH)
    steps = data["jobs"]["discover"]["steps"]
    step  = _checkout_step(steps)
    assert step is not None, (
        "The 'discover' job in _test_template.yml should have a checkout step.")
    assert step["uses"] == "actions/checkout@v4", (
        f"Discover job should use actions/checkout@v4, got: {step['uses']!r}")


def test_ci_template_discover_job_checks_out_main():
    """
    The discover job must check out main. CI always validates the committed
    main state, not a transient PR branch. Changing this ref would cause CI to
    run tests that do not exist on main yet.
    """
    data  = _load(TEMPLATE_PATH)
    steps = data["jobs"]["discover"]["steps"]
    step  = _checkout_step(steps)
    assert step is not None, (
        "The 'discover' job should have a checkout step.")
    assert step.get("with", {}).get("ref") == "main", (
        "The 'discover' job checkout should reference 'main'. "
        f"Got: {step.get('with', {}).get('ref')!r}")


################################################################################
# Template — run job checkout
################################################################################
def test_ci_template_run_job_uses_checkout_v4():
    """
    The run job must use actions/checkout@v4.
    """
    data  = _load(TEMPLATE_PATH)
    steps = data["jobs"]["run"]["steps"]
    step  = _checkout_step(steps)
    assert step is not None, (
        "The 'run' job in _test_template.yml should have a checkout step.")
    assert step["uses"] == "actions/checkout@v4", (
        f"Run job should use actions/checkout@v4, got: {step['uses']!r}")


def test_ci_template_run_job_checks_out_main():
    """
    The run job must check out main for the same reason as the discover job.
    Both jobs must be consistent.
    """
    data  = _load(TEMPLATE_PATH)
    steps = data["jobs"]["run"]["steps"]
    step  = _checkout_step(steps)
    assert step is not None, (
        "The 'run' job should have a checkout step.")
    assert step.get("with", {}).get("ref") == "main", (
        "The 'run' job checkout should reference 'main'. "
        f"Got: {step.get('with', {}).get('ref')!r}")


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
        "The 'run' job matrix strategy should set fail-fast: false so all "
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
        f"{workflow_name} should have a 'workflow_dispatch' trigger for "
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
        f"'uses: ./.github/workflows/_test_template.yml'. Got: {uses!r}")


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
        f"{workflow_name} should pass 'pull_tag' to the template.")
    assert with_["pull_tag"], (
        f"{workflow_name} 'pull_tag' should be a non-empty string.")


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
        "run_tests.yml should have a 'pull_request' trigger.")


def test_ci_run_all_workflow_has_schedule_trigger():
    """
    run_tests.yml must have a schedule trigger for weekly runs that catch
    upstream breakage from new SAD or Xsuite releases independent of SAD2XS
    commits.
    """
    data = _load(RUN_ALL_PATH)
    assert "schedule" in _triggers(data), (
        "run_tests.yml should have a 'schedule' trigger for weekly runs.")


def test_ci_run_all_workflow_has_workflow_dispatch_trigger():
    """
    run_tests.yml must be manually triggerable so the full suite can be re-run
    on demand from the GitHub Actions UI.
    """
    data = _load(RUN_ALL_PATH)
    assert "workflow_dispatch" in _triggers(data), (
        "run_tests.yml should have a 'workflow_dispatch' trigger.")


################################################################################
# Docker build workflow
################################################################################
def test_ci_docker_build_workflow_name_is_stable():
    """
    The docker-build workflow's 'name:' field is documented here so that a
    rename is caught immediately. The name is referenced in external contexts
    (issue trackers, team runbooks) and should not change without review.
    """
    data = _load(DOCKER_PATH)
    assert data["name"] == DOCKER_BUILD_WORKFLOW_NAME, (
        f"docker-build.yml 'name' should be '{DOCKER_BUILD_WORKFLOW_NAME}'. "
        f"Update DOCKER_BUILD_WORKFLOW_NAME in this file if intentionally "
        f"renamed. Got: {data['name']!r}")


def test_ci_docker_build_triggers_on_push_to_main():
    """
    The Docker build must trigger on pushes to main so the SAD image stays
    current with the default branch.
    """
    data     = _load(DOCKER_PATH)
    push_on  = _triggers(data).get("push", {})
    branches = push_on.get("branches", [])
    assert "main" in branches, (
        f"docker-build.yml should trigger on push to 'main'. "
        f"Got branches: {branches}")


def test_ci_docker_build_has_workflow_dispatch_trigger():
    """
    The Docker build must be manually triggerable so the image can be rebuilt
    on demand without waiting for a push to main.
    """
    data = _load(DOCKER_PATH)
    assert "workflow_dispatch" in _triggers(data), (
        "docker-build.yml should have a 'workflow_dispatch' trigger.")


def test_ci_docker_build_uses_checkout_v4():
    """
    The Docker build job must use actions/checkout@v4.
    """
    data  = _load(DOCKER_PATH)
    jobs  = data["jobs"]
    job   = jobs[list(jobs.keys())[0]]
    step  = _checkout_step(job["steps"])
    assert step is not None, (
        "docker-build.yml should have a checkout step.")
    assert step["uses"] == "actions/checkout@v4", (
        f"docker-build.yml checkout should use actions/checkout@v4. "
        f"Got: {step['uses']!r}")
