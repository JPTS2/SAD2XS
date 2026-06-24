"""Central mapping of tests that document open GitHub issues."""

KNOWN_ISSUE_TESTS = {
    # Parser and expression handling.
    "tests/parser/test_errors.py::test_invalid_deferred_expression_syntax_raises_clear_error": 22,
    "tests/parser/test_errors.py::test_malformed_line_missing_equals_raises_clear_error": 22,
    "tests/parser/test_errors.py::test_malformed_line_missing_parentheses_raises_clear_error": 22,
    "tests/parser/test_errors.py::test_malformed_line_extra_closing_parenthesis_raises_clear_error": 22,
    "tests/parser/test_functions.py::test_sad_function_definition_is_preserved": 32,
    "tests/parser/test_functions.py::test_sad_function_definition_with_module_body_is_preserved": 32,
    "tests/parser/test_functions.py::test_sad_function_call_in_deferred_expression_converts": 32,
    "tests/parser/test_functions.py::test_sad_function_call_in_element_expression_converts": 32,
    "tests/parser/test_functions.py::test_nested_sad_function_call_in_deferred_expression_converts": 32,
    "tests/parser/test_element_expressions.py::test_element_expression_with_parentheses_is_preserved": 47,
    "tests/parser/test_element_expressions.py::test_element_expression_with_math_function_is_preserved": 47,
    "tests/parser/test_element_expressions.py::test_parenthesised_length_expression_can_be_evaluated_in_xsuite_environment": 47,
    "tests/parser/test_element_expressions.py::test_math_function_length_expression_can_be_evaluated_in_xsuite_environment": 47,
    "tests/conversion/pipeline/test_offset_markers.py::test_pipeline_offset_marker_symbolic_expression_resolves_to_computed_s_position": 47,
    "tests/parser/test_deferred_expressions.py::test_multiline_deferred_expression_converts": 48,
    "tests/parser/test_globals.py::test_global_name_prefix_collisions_remain_deferred_expressions": 49,
    "tests/parser/test_preprocessing.py::test_on_and_off_prefix_variable_names_are_not_removed": 49,
    "tests/parser/test_repeated_definitions.py::test_repeated_element_name_across_types_raises_clear_error": 51,
    "tests/parser/test_errors.py::test_protected_element_names_raise_clear_error": 53,

    # Conversion behaviour and physics comparisons.
    "tests/conversion/elements/test_mult.py::test_mult_conversion_matches_sad_twiss_for_combined_orders": 33,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_thin_kick": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_rotated_kicks": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_element_offsets": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_thin_kick": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_rotated_kicks": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_element_offsets": 55,
    "tests/conversion/pipeline/test_reverse_charge.py::test_pipeline_reverse_charge_negates_positive_q0": 59,
    "tests/conversion/pipeline/test_reverse_charge.py::test_pipeline_reverse_charge_negates_negative_q0": 59,
    "tests/conversion/pipeline/test_reverse_charge.py::test_pipeline_reverse_charge_does_not_affect_p0c_or_mass0": 59,
}


PARTIAL_KNOWN_ISSUES = (
    # (test node prefix, parameter-id fragment, issue number)
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_twiss_for_element_offsets", "[0.001-0.0]", 19),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_twiss_for_element_offsets", "[0.001--0.001]", 19),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_tracking_for_element_offsets", "[0.001-0.0]", 19),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_tracking_for_element_offsets", "[0.001--0.001]", 19),
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
