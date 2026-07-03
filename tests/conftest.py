"""
================================================================================
Shared pytest configuration
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import sys
from pathlib import Path

import pytest

################################################################################
# Test Import Path
################################################################################
REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.support.known_issues import KNOWN_ISSUES, known_issue_for


def pytest_itemcollected(item):
    """Mark issue-linked tests before pytest evaluates marker selections."""
    issue = known_issue_for(item.nodeid)
    if issue is not None:
        item.add_marker(pytest.mark.known_issue(issue))


def pytest_collection_modifyitems(session, config, items):
    """
    Fail collection if a KNOWN_ISSUES entry matches nothing collected.

    A parameter-id fragment (or, for a whole-test entry, the test itself)
    that stops matching after a parametrize change (e.g. a decorator added
    or reordered, changing the bracket structure) would otherwise silently
    stop applying with no error at all. Only flags entries whose target
    function *was* part of this collection run, so running a subset of the
    suite does not raise false positives for unrelated files.
    """
    collected_nodeids = [item.nodeid for item in items]
    stale_entries = []

    for node_prefix, parameter_fragment, issue in KNOWN_ISSUES:
        matching_prefix = [
            nodeid for nodeid in collected_nodeids
            if nodeid.startswith(node_prefix)]
        if matching_prefix and not any(
                parameter_fragment in nodeid for nodeid in matching_prefix):
            stale_entries.append(
                f"KNOWN_ISSUES entry for issue #{issue} "
                f"({node_prefix!r}, {parameter_fragment!r}) matched the test "
                "function but none of its collected parametrisations.")

    if stale_entries:
        raise pytest.UsageError(
            "Stale tests/support/known_issues.py entries (rename, fix, or "
            "remove them):\n" + "\n".join(f"- {msg}" for msg in stale_entries))
