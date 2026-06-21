"""Central mapping of tests that document open GitHub issues."""

KNOWN_ISSUE_TESTS = {
    # Writer issues.
    "tests/writer/elements/test_oct_writer.py::test_oct_writer_preserves_knl_combined_multipole_component": 17,
    "tests/writer/elements/test_oct_writer.py::test_oct_writer_preserves_ksl_combined_multipole_component": 17,
    "tests/writer/elements/test_oct_writer.py::test_oct_writer_preserves_knl_and_ksl_components_simultaneously": 17,
    "tests/writer/elements/test_quad_writer.py::test_quad_writer_preserves_knl_combined_multipole_component": 17,
    "tests/writer/elements/test_quad_writer.py::test_quad_writer_preserves_ksl_combined_multipole_component": 17,
    "tests/writer/elements/test_quad_writer.py::test_quad_writer_preserves_knl_and_ksl_components_simultaneously": 17,
    "tests/writer/elements/test_sext_writer.py::test_sext_writer_preserves_knl_combined_multipole_component": 17,
    "tests/writer/elements/test_sext_writer.py::test_sext_writer_preserves_ksl_combined_multipole_component": 17,
    "tests/writer/elements/test_sext_writer.py::test_sext_writer_preserves_knl_and_ksl_components_simultaneously": 17,
    "tests/writer/elements/test_aper_writer.py::test_aper_writer_limitellipse_a_is_accessible_as_optics_variable": 62,
    "tests/writer/elements/test_aper_writer.py::test_aper_writer_limitellipse_b_is_accessible_as_optics_variable": 62,
    "tests/writer/elements/test_aper_writer.py::test_aper_writer_limitellipse_a_is_tunable_via_optics_variable": 62,
    "tests/writer/elements/test_aper_writer.py::test_aper_writer_limitrect_min_x_is_accessible_as_optics_variable": 62,
    "tests/writer/elements/test_aper_writer.py::test_aper_writer_limitrect_max_x_is_accessible_as_optics_variable": 62,
    "tests/writer/elements/test_aper_writer.py::test_aper_writer_limitrect_min_x_is_tunable_via_optics_variable": 62,
    "tests/writer/elements/test_bend_writer.py::test_bend_writer_k1_is_preserved_for_combined_function_magnet": 63,
    "tests/writer/pipeline/test_line_roundtrip.py::test_writer_roundtrip_preserves_supported_line_contract": 63,

    # Thin elements and current Xsuite API migration.
    "tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_twiss_for_thin_bend": 18,
    "tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_tracking_for_thin_bend": 18,
    "tests/conversion/elements/test_oct.py::test_oct_converter_converts_thin_octupole_to_multipole": 18,
    "tests/conversion/elements/test_quad.py::test_quad_converter_converts_thin_quadrupole_to_multipole": 18,
    "tests/conversion/elements/test_sext.py::test_sext_converter_converts_thin_sextupole_to_multipole": 18,
    "tests/conversion/elements/test_bend.py::test_bend_converter_creates_xsuite_bend": 19,
    "tests/conversion/elements/test_bend.py::test_bend_converter_creates_all_bends": 19,
    "tests/conversion/elements/test_cavi.py::test_cavi_converter_uses_phase_not_lag": 19,
    "tests/conversion/elements/test_cavi.py::test_cavi_converter_preserves_symbolic_phase_with_environment_variable": 19,
    "tests/conversion/elements/test_cavi.py::test_cavi_converter_uses_harmonic_when_harmonic_is_supplied": 19,
    "tests/conversion/elements/test_cavi.py::test_cavi_pipeline_preserves_names_order_and_rf_settings": 19,
    "tests/conversion/elements/test_cavi.py::test_cavi_pipeline_preserves_harmonic_rf_setting": 19,

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
    "tests/parser/test_line_names.py::test_line_name_containing_line_is_preserved": 45,
    "tests/parser/test_line_names.py::test_line_reference_containing_line_is_preserved": 45,
    "tests/parser/test_line_names.py::test_reversed_line_reference_containing_line_is_preserved": 45,
    "tests/conversion/pipeline/test_convert_sad_to_xsuite.py::test_pipeline_line_name_selects_requested_line": 46,
    "tests/parser/test_element_expressions.py::test_element_expression_with_parentheses_is_preserved": 47,
    "tests/parser/test_element_expressions.py::test_element_expression_with_math_function_is_preserved": 47,
    "tests/parser/test_element_expressions.py::test_parenthesised_length_expression_can_be_evaluated_in_xsuite_environment": 47,
    "tests/parser/test_element_expressions.py::test_math_function_length_expression_can_be_evaluated_in_xsuite_environment": 47,
    "tests/conversion/pipeline/test_offset_markers.py::test_pipeline_offset_marker_symbolic_expression_resolves_to_computed_s_position": 47,
    "tests/parser/test_deferred_expressions.py::test_multiline_deferred_expression_converts": 48,
    "tests/parser/test_globals.py::test_global_name_prefix_collisions_remain_deferred_expressions": 49,
    "tests/parser/test_preprocessing.py::test_on_and_off_prefix_variable_names_are_not_removed": 49,
    "tests/parser/test_units.py::test_radian_angle_units_parse_as_radians": 50,
    "tests/parser/test_repeated_definitions.py::test_repeated_element_name_across_types_raises_clear_error": 51,
    "tests/parser/test_errors.py::test_protected_element_names_raise_clear_error": 53,

    # Conversion behavior and physics comparisons.
    "tests/conversion/elements/test_aper.py::test_aper_converter_preserves_rectangle_rotation": 33,
    "tests/conversion/elements/test_aper.py::test_aper_converter_preserves_combined_rectangular_and_elliptical_limits": 66,
    "tests/conversion/elements/test_aper.py::test_aper_pipeline_preserves_rectangle_rotation": 33,
    "tests/conversion/elements/test_aper.py::test_aper_rotated_limitrect_grid_loss_matches_sad_boundary": 33,
    "tests/conversion/elements/test_mult.py::test_mult_conversion_matches_sad_twiss_for_combined_orders": 33,
    "tests/conversion/elements/test_mult.py::test_mult_conversion_matches_sad_tracking_for_combined_orders": 33,
    "tests/conversion/elements/test_bend.py::test_bend_converter_supports_symbolic_length_and_angle": 52,
    "tests/conversion/elements/test_drift.py::test_drift_converter_creates_all_drifts": 52,
    "tests/conversion/elements/test_oct.py::test_oct_converter_supports_symbolic_length_and_strength": 52,
    "tests/conversion/elements/test_quad.py::test_quad_converter_supports_symbolic_length_and_strength": 52,
    "tests/conversion/elements/test_sext.py::test_sext_converter_supports_symbolic_length_and_strength": 52,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_thin_kick": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_rotated_kicks": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_element_offsets": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_thin_kick": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_rotated_kicks": 55,
    "tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_element_offsets": 55,
    "tests/conversion/elements/test_sol.py::test_sol_reference_transform_restores_design_orbit_at_end": 58,
    "tests/conversion/elements/test_sol.py::test_sol_reference_transform_restores_orbit_with_interior_kicks": 58,
    "tests/conversion/elements/test_sol.py::test_sol_powered_reference_shift_orbit_matches_sad_at_end": 58,
    "tests/conversion/pipeline/test_reverse_charge.py::test_pipeline_reverse_charge_negates_positive_q0": 59,
    "tests/conversion/pipeline/test_reverse_charge.py::test_pipeline_reverse_charge_negates_negative_q0": 59,
    "tests/conversion/pipeline/test_reverse_charge.py::test_pipeline_reverse_charge_does_not_affect_p0c_or_mass0": 59,
}


PARTIAL_KNOWN_ISSUES = (
    # (test node prefix, parameter-id fragment, issue number)
    ("tests/conversion/elements/test_drift.py::test_drift_converter_creates_xsuite_drift", "[l_drift]", 52),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_twiss_for_element_offsets", "[0.001-0.0]", 19),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_twiss_for_element_offsets", "[0.001--0.001]", 19),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_tracking_for_element_offsets", "[0.001-0.0]", 19),
    ("tests/conversion/elements/test_bend.py::test_bend_conversion_matches_sad_tracking_for_element_offsets", "[0.001--0.001]", 19),
    ("tests/conversion/elements/test_sol.py::test_sol_optics_matches_sad_twiss_at_end", "[-0.1]", 58),
    ("tests/conversion/elements/test_sol.py::test_sol_optics_matches_sad_twiss_at_end", "[0.1]", 58),
    ("tests/conversion/elements/test_quad.py::test_quad_conversion_matches_sad_tracking_for_element_rotation", "[0.7853981633974483]", 54),
    ("tests/conversion/elements/test_quad.py::test_quad_conversion_matches_sad_tracking_for_element_rotation", "[-0.7853981633974483]", 54),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_horizontal_kicks", "[-0.1]", 55),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_twiss_for_horizontal_kicks", "[0.1]", 55),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_horizontal_kicks", "[-0.1]", 55),
    ("tests/conversion/elements/test_corrector.py::test_corrector_conversion_matches_sad_tracking_for_horizontal_kicks", "[0.1]", 55),
    ("tests/conversion/elements/test_sol.py::test_sol_reference_transform_orbit_matches_sad_twiss", "-geo_out-dxdy]", 58),
    ("tests/conversion/elements/test_sol.py::test_sol_reference_transform_orbit_matches_sad_twiss", "-geo_out-dpx]", 58),
    ("tests/conversion/elements/test_sol.py::test_sol_reference_transform_orbit_matches_sad_twiss", "-geo_out-dpy]", 58),
    ("tests/conversion/elements/test_sol.py::test_sol_reference_transform_orbit_matches_sad_twiss", "-geo_out-dxdy_dpx_dpy]", 58),
    ("tests/conversion/elements/test_sol.py::test_sol_reference_transform_orbit_matches_sad_twiss", "-geo_out-dxdy_chi1_chi2]", 58),
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
