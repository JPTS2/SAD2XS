"""
================================================================================
Shared pytest configuration
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
import logging
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


@pytest.fixture(autouse = True)
def _restore_sad2xs_log_level():
    """
    Restore the sad2xs logger level after every test. _verbose=True (and
    set_log_level) change the level process-wide; without this fixture one
    verbose test would raise the verbosity of every test that follows it.
    """
    sad2xs_logger = logging.getLogger("sad2xs")
    level = sad2xs_logger.level
    yield
    sad2xs_logger.setLevel(level)


def pytest_itemcollected(item):
    """
    Mark known-failure tests before pytest evaluates marker selections.
    """
    tracker_id = known_issue_for(item.nodeid)
    if tracker_id is not None:
        item.add_marker(pytest.mark.known_issue(tracker_id))


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

    for node_prefix, parameter_fragment, tracker_id in KNOWN_ISSUES:
        matching_prefix = [
            nodeid for nodeid in collected_nodeids
            if nodeid.startswith(node_prefix)]
        if matching_prefix and not any(
                parameter_fragment in nodeid for nodeid in matching_prefix):
            stale_entries.append(
                f"KNOWN_ISSUES entry for tracker id {tracker_id} "
                f"({node_prefix!r}, {parameter_fragment!r}) matched the test "
                "function but none of its collected parametrisations.")

    if stale_entries:
        raise pytest.UsageError(
            "Stale tests/support/known_issues.py entries (rename, fix, or "
            "remove them):\n" + "\n".join(f"- {msg}" for msg in stale_entries))
