"""
================================================================================
Repository Structure Inventory
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-29
================================================================================
"""
################################################################################
# Required Packages
################################################################################
from pathlib import Path

################################################################################
# Paths
################################################################################
REPO_ROOT    = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
TESTS_DIR    = REPO_ROOT / "tests"
PYTEST_INI   = REPO_ROOT / "pytest.ini"


################################################################################
# Inventory
################################################################################
def testpath_folders() -> list[str]:
    """
    Read the `tests/<folder>` entries from `pytest.ini`'s testpaths block.

    Returns the folder names in their declared order, without the `tests/`
    prefix. The order is meaningful: it is the order pytest collects in.

    Returns
    -------
    list of str
        Folder names, for example ``["ci", "installation", ...]``.
    """
    folders     = []
    in_block    = False

    for line in PYTEST_INI.read_text().splitlines():
        stripped = line.strip()

        if stripped.startswith("testpaths"):
            in_block = True
            continue

        if in_block:
            if not stripped.startswith("tests/"):
                break
            folders.append(stripped.split("/", 1)[1])

    return folders


def folder_workflow_names() -> list[str]:
    """
    Expected per-folder workflow filename for every testpaths folder.

    Derived rather than hard-coded, so a folder added to `testpaths` without
    a matching workflow fails the CI tests instead of passing silently.

    Returns
    -------
    list of str
        Workflow filenames, for example ``["test_ci.yml", ...]``.
    """
    return [f"test_{folder}.yml" for folder in testpath_folders()]
