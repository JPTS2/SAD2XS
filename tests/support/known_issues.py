"""Central mapping of tests that document open GitHub issues."""

KNOWN_ISSUE_TESTS = {
    # Conversion behaviour and physics comparisons.
    "tests/conversion/elements/test_mult.py::test_mult_conversion_matches_sad_twiss_for_combined_orders": 33,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_rotated_kicks": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_element_offsets": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_rotated_kicks": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_element_offsets": 55,
}


PARTIAL_KNOWN_ISSUES = (
    # (test node prefix, parameter-id fragment, issue number)
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_twiss_for_element_offsets", "[0.001-0.0]", 55),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_twiss_for_element_offsets", "[0.001--0.001]", 55),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_tracking_for_element_offsets", "[0.001-0.0]", 55),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_tracking_for_element_offsets", "[0.001--0.001]", 55),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_horizontal_kicks", "[-0.1]", 55),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_horizontal_kicks", "[0.1]", 55),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_horizontal_kicks", "[-0.1]", 55),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_horizontal_kicks", "[0.1]", 55),
)


def known_issue_for(nodeid):
    """Return the linked issue number for a collected node, if any."""
    unparametrized_nodeid = nodeid.split("[", 1)[0]
    issue = KNOWN_ISSUE_TESTS.get(unparametrized_nodeid)
    if issue is not None:
        return issue

    for node_prefix, parameter_fragment, issue in PARTIAL_KNOWN_ISSUES:
        if nodeid.startswith(node_prefix) and parameter_fragment in nodeid:
            return issue

    return None
