"""Central mapping of tests that document open GitHub issues."""

KNOWN_ISSUE_TESTS = {
    # Parser and expression handling.
    "tests/parser/test_functions.py::test_sad_function_definition_is_preserved": 32,
    "tests/parser/test_functions.py::test_sad_function_definition_with_module_body_is_preserved": 32,
    "tests/parser/test_functions.py::test_sad_function_call_in_deferred_expression_converts": 32,
    "tests/parser/test_functions.py::test_sad_function_call_in_element_expression_converts": 32,
    "tests/parser/test_functions.py::test_nested_sad_function_call_in_deferred_expression_converts": 32,

    # Conversion behaviour and physics comparisons.
    "tests/conversion/elements/test_mult.py::test_mult_conversion_matches_sad_twiss_for_combined_orders": 33,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_thin_kick": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_rotated_kicks": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_element_offsets": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_thin_kick": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_rotated_kicks": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_element_offsets": 55,
    "tests/conversion/pipeline/test_offset_markers.py::test_pipeline_offset_marker_symbolic_expression_resolves_to_computed_s_position": 22,
    "tests/conversion/pipeline/test_reverse_charge.py::test_pipeline_reverse_charge_negates_positive_q0": 59,
    "tests/conversion/pipeline/test_reverse_charge.py::test_pipeline_reverse_charge_negates_negative_q0": 59,
    "tests/conversion/pipeline/test_reverse_charge.py::test_pipeline_reverse_charge_does_not_affect_p0c_or_mass0": 59,
}


PARTIAL_KNOWN_ISSUES = (
    # (test node prefix, parameter-id fragment, issue number)
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_twiss_for_element_offsets", "[0.001-0.0]", 55),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_twiss_for_element_offsets", "[0.001--0.001]", 55),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_tracking_for_element_offsets", "[0.001-0.0]", 55),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_tracking_for_element_offsets", "[0.001--0.001]", 55),
    ("tests/conversion/elements/test_sol.py::test_sol_optics_matches_sad_twiss_at_end", "[-0.1]", 58),
    ("tests/conversion/elements/test_sol.py::test_sol_optics_matches_sad_twiss_at_end", "[0.1]", 58),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_horizontal_kicks", "[-0.1]", 55),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_horizontal_kicks", "[0.1]", 55),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_horizontal_kicks", "[-0.1]", 55),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_horizontal_kicks", "[0.1]", 55),
    ("tests/conversion/elements/test_sol.py::test_sol_reference_transform_restores_design_orbit_at_end", "[out-dxdy]", 58),
    ("tests/conversion/elements/test_sol.py::test_sol_reference_transform_restores_design_orbit_at_end", "[out-dxdy_dpx_dpy]", 58),
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
