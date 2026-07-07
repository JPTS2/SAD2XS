"""Central mapping of tests that document open GitHub issues."""

KNOWN_ISSUES = (
    # (test node prefix, parameter-id fragment, issue number)
    # An empty fragment ("") matches every parametrisation of the test,
    # i.e. the whole test is the known issue, not just specific parameters.
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_twiss_for_element_offsets", "[0.001-0.0]", 103),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_twiss_for_element_offsets", "[0.001--0.001]", 103),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_tracking_for_element_offsets", "[0.001-0.0]", 103),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_tracking_for_element_offsets", "[0.001--0.001]", 103),
)


def known_issue_for(nodeid):
    """Return the linked issue number for a collected node, if any."""
    for node_prefix, parameter_fragment, issue in KNOWN_ISSUES:
        if nodeid.startswith(node_prefix) and parameter_fragment in nodeid:
            return issue

    return None
