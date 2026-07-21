"""
================================================================================
Central Mapping of Tests That Document Open GitHub Issues
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-21
================================================================================
"""

KNOWN_ISSUES = (
    # (test node prefix, parameter-id fragment, issue number)
    # An empty fragment ("") matches every parametrisation of the test,
    # i.e. the whole test is the known issue, not just specific parameters.
)


def known_issue_for(nodeid):
    """
    Return the linked issue number for a collected node, if any.
    """
    for node_prefix, parameter_fragment, issue in KNOWN_ISSUES:
        if nodeid.startswith(node_prefix) and parameter_fragment in nodeid:
            return issue

    return None
