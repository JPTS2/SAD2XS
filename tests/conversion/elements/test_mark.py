"""
================================================================================
Tests for SAD MARK conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import os

import numpy as np
import sad2xs as s2x
import xtrack as xt

from sad2xs.converter._004_element_converter import convert_markers
from tests.support.config import DELTA_S_ATOL, DELTA_S_RTOL
from sad2xs.sad_helpers import twiss_sad

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
def test_mark_converter_creates_xsuite_marker(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Parsed SAD MARK elements should become Xsuite Marker elements.
    """
    convert_markers(
        parsed_elements = parsed_elements(
            element_type        = "mark",
            element_name        = "test_mark",
            element_variables   = {}),
        environment     = xsuite_environment)

    assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_mark",
        element_type    = xt.Marker)

def test_mark_converter_creates_all_markers(
        xsuite_environment,
        assert_environment_element):
    """
    Multiple parsed SAD MARK elements should all be converted.
    """
    parsed_elements = {
        "mark": {
            "start": {},
            "mid":   {},
            "end":   {},
        },
    }

    convert_markers(
        parsed_elements = parsed_elements,
        environment     = xsuite_environment)

    assert set(xsuite_environment.element_dict) == {"start", "mid", "end"}, (
        "All parsed SAD MARK elements should be present in the environment.")
    for marker_name in ["start", "mid", "end"]:
        assert_environment_element(
            environment     = xsuite_environment,
            element_name    = marker_name,
            element_type    = xt.Marker)

def test_mark_converter_ignores_marker_parameters(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Current MARK conversion should ignore parsed marker parameters.
    """
    convert_markers(
        parsed_elements = parsed_elements(
            element_type        = "mark",
            element_name        = "test_mark",
            element_variables   = {"offset": 1.0, "dx": 2.0}),
        environment     = xsuite_environment)

    marker = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_mark",
        element_type    = xt.Marker)

    assert isinstance(marker, xt.Marker), (
        "Parsed MARK parameters should not change the converted element type.")

########################################
# Pipeline Behaviour
########################################
def test_mark_pipeline_preserves_marker_names(write_lattice):
    """
    Full conversion should preserve SAD MARK element names in the Xsuite line.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MARK        START       = ()
                    MID         = ()
                    END         = ();

        LINE        TEST_LINE   = (START MID END);
        """,
        filename = "mark_pipeline_preserves_names.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "mid", "end"], (
        "Converted MARK-only line should preserve marker order and names.")
    for marker_name in ["start", "mid", "end"]:
        assert isinstance(line[marker_name], xt.Marker), (
            f"Converted element '{marker_name}' should be an Xsuite Marker.")

################################################################################
# Physics Equivalence
################################################################################
########################################
# Zero-Length Marker Optics
########################################
def test_mark_conversion_matches_sad_zero_length_line(write_lattice, tmp_path):
    """
    A MARK-only line should remain zero length in SAD and Xsuite.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_path = write_lattice(
            """\
            MOMENTUM    = 1.0 GEV;

            MARK        START       = ()
                        END         = ();

            LINE        TEST_LINE   = (START END);
            """,
            filename = "mark_zero_length_line.sad")

        tw_sad = twiss_sad(
            lattice_filepath        = lattice_path.name,
            line_name               = "TEST_LINE",
            calc6d                  = False,
            closed                  = False,
            reverse_element_order   = False,
            reverse_bend_direction  = False,
            additional_commands     = "")

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path    = str(lattice_path),
            output_directory    = "N/A",
            _verbose            = False,
            _test_mode          = True)

        table = line.get_table()
        sad_final_s = tw_sad["s", "END"]
        xs_final_s = table["s", "end"]
    finally:
        os.chdir(cwd)

    assert np.isclose(
        sad_final_s,
        xs_final_s,
        rtol = DELTA_S_RTOL,
        atol = DELTA_S_ATOL), (
        "MARK-only conversion should preserve the zero-length SAD line.")
