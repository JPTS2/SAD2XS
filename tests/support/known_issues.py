"""
================================================================================
Central Mapping of Tests That Document Open GitHub Issues
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-24
================================================================================
"""

KNOWN_ISSUES = (
    # (test node prefix, parameter-id fragment, issue number)
    # An empty fragment ("") matches every parametrisation of the test,
    # i.e. the whole test is the known issue, not just specific parameters.

    # xt.SecondOrderTaylorMap is not yet in the shipping xtrack release
    # (dev-only); these tests require it to build/reload a line.
    ("tests/writer/elements/test_taylor_maps_writer.py::test_second_order_taylor_map_writer_reloads_as_xsuite_second_order_taylor_map", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_second_order_taylor_map_writer_preserves_element_name", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_second_order_taylor_map_writer_preserves_length", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_second_order_taylor_map_writer_preserves_k", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_second_order_taylor_map_writer_preserves_r", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_second_order_taylor_map_writer_preserves_t", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_second_order_taylor_map_writer_preserves_full_double_precision", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_second_order_taylor_map_writer_preserves_sad_quad_fringe_metadata_when_present", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_second_order_taylor_map_writer_omits_sad_quad_fringe_metadata_when_absent", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_second_order_taylor_map_writer_strips_minus_sign_without_matching_root", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_second_order_taylor_map_writer_keeps_minus_sign_with_matching_root", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_taylor_maps_writer_preserves_multiple_maps_independently", "", 117),
    ("tests/writer/elements/test_taylor_maps_writer.py::test_taylor_maps_writer_preserves_element_order", "", 117),
    ("tests/writer/pipeline/test_supported_elements.py::test_supported_elements_writer_handles_second_order_taylor_map", "", 117),
)


def known_issue_for(nodeid):
    """
    Return the linked issue number for a collected node, if any.
    """
    for node_prefix, parameter_fragment, issue in KNOWN_ISSUES:
        if nodeid.startswith(node_prefix) and parameter_fragment in nodeid:
            return issue

    return None
