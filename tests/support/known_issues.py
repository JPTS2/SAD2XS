"""
Central mapping of tests that document open GitHub issues.
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
