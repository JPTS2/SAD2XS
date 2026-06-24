"""
================================================================================
Tests for CI workflow test file targets
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-24
================================================================================
"""
################################################################################
# Required Packages
################################################################################
from pathlib import Path

import pytest
import yaml

################################################################################
# Paths
################################################################################
REPO_ROOT    = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

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

################################################################################
# Helpers
################################################################################
def _load(path):
    with open(path, encoding = "utf-8") as fh:
        return yaml.safe_load(fh)


def _extract_test_targets(workflow_data):
    """
    Extract the list of test paths from a workflow's test_files: input,
    stripping blank lines and comment lines (matching the template's own
    normalisation logic).
    """
    jobs     = workflow_data["jobs"]
    job_name = list(jobs.keys())[0]
    raw      = jobs[job_name]["with"]["test_files"]
    return [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")]


################################################################################
# test_files — non-empty
################################################################################
@pytest.mark.parametrize("workflow_name", FOLDER_WORKFLOW_NAMES)
def test_ci_folder_workflow_lists_at_least_one_test_target(workflow_name):
    """
    Each per-folder workflow must list at least one path in its test_files:
    block. An empty list causes the matrix to produce zero jobs and CI passes
    vacuously without running anything.
    """
    data    = _load(WORKFLOW_DIR / workflow_name)
    targets = _extract_test_targets(data)
    assert len(targets) > 0, (
        f"{workflow_name} should list at least one path in test_files. "
        f"An empty list causes CI to pass without running any tests.")


################################################################################
# test_files — paths exist in the repository
################################################################################
@pytest.mark.parametrize("workflow_name", FOLDER_WORKFLOW_NAMES)
def test_ci_folder_workflow_test_targets_all_exist(workflow_name):
    """
    Every path listed in a workflow's test_files: block must exist in the
    repository. A path that does not exist causes the pytest invocation inside
    Docker to fail with a collection error rather than a clean test failure,
    making CI harder to diagnose.
    """
    data    = _load(WORKFLOW_DIR / workflow_name)
    targets = _extract_test_targets(data)
    missing = [t for t in targets if not (REPO_ROOT / t).exists()]
    assert missing == [], (
        f"{workflow_name} references paths that do not exist in the "
        f"repository.\nMissing: {missing}")


################################################################################
# test_files — paths are under tests/
################################################################################
@pytest.mark.parametrize("workflow_name", FOLDER_WORKFLOW_NAMES)
def test_ci_folder_workflow_test_targets_are_under_tests_directory(workflow_name):
    """
    All paths in test_files: should be rooted under the tests/ directory. A
    path outside tests/ suggests a configuration error.
    """
    data    = _load(WORKFLOW_DIR / workflow_name)
    targets = _extract_test_targets(data)
    bad     = [t for t in targets if not t.startswith("tests/")]
    assert bad == [], (
        f"{workflow_name} lists paths outside the tests/ directory: {bad}")
