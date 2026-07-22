"""
================================================================================
Tests for pytest.ini's testpaths completeness
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-22
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import subprocess
import sys
from pathlib import Path

################################################################################
# Paths
################################################################################
REPO_ROOT = Path(__file__).resolve().parents[2]

################################################################################
# Helpers
################################################################################
def _collect_node_ids(*args: str) -> set[str]:
    """
    Run `pytest --collect-only -q <args>` from REPO_ROOT and return the set
    of collected test node IDs.
    """
    result  = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *args],
        cwd = REPO_ROOT, capture_output = True, text = True)
    return {line for line in result.stdout.splitlines() if "::" in line}

################################################################################
# testpaths completeness
################################################################################
def test_testpaths_collects_every_test_under_the_tests_directory():
    """
    A bare `pytest` run (using pytest.ini's testpaths) must collect every
    test a full scan of tests/ finds -- otherwise a new test directory
    silently never runs, as tests/xsuite_helpers and tests/xtrack did for
    about two weeks after being added, undetected until now.
    """
    via_testpaths   = _collect_node_ids()
    via_full_scan   = _collect_node_ids("tests/")

    missing = via_full_scan - via_testpaths
    assert missing == set(), (
        f"{len(missing)} test(s) under tests/ aren't collected via "
        f"pytest.ini's testpaths -- add the missing directory: "
        f"{sorted(missing)[:10]}")

def test_testpaths_does_not_reference_stale_paths():
    """
    testpaths should not list a directory that no longer contributes any
    test collected by a full scan of tests/ -- e.g. a folder that was
    removed or renamed without updating pytest.ini.
    """
    via_testpaths   = _collect_node_ids()
    via_full_scan   = _collect_node_ids("tests/")

    stale = via_testpaths - via_full_scan
    assert stale == set(), (
        f"{len(stale)} test(s) are collected via pytest.ini's testpaths "
        f"but not by a full scan of tests/ -- testpaths may reference a "
        f"stale path: {sorted(stale)[:10]}")
