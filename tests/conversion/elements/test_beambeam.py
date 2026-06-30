"""
================================================================================
Tests for SAD BEAMBEAM conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

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

from sad2xs.converter._004_element_converter import convert_beam_beam
from tests.support.config import DELTA_S_ATOL, DELTA_S_RTOL
from sad2xs.sad_helpers import twiss_sad

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
def test_beambeam_converter_creates_xsuite_marker(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Parsed SAD BEAMBEAM elements should currently become Xsuite Marker elements.
    """
    convert_beam_beam(
        parsed_elements = parsed_elements(
            element_type        = "beambeam",
            element_name        = "test_beambeam",
            element_variables   = {}),
        environment     = xsuite_environment)

    assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_beambeam",
        element_type    = xt.Marker)

def test_beambeam_converter_creates_all_beambeam_markers(
        xsuite_environment,
        assert_environment_element):
    """
    Multiple parsed SAD BEAMBEAM elements should all be converted.
    """
    parsed_elements = {
        "beambeam": {
            "bb_1": {},
            "bb_2": {},
            "bb_3": {},
        },
    }

    convert_beam_beam(
        parsed_elements = parsed_elements,
        environment     = xsuite_environment)

    assert set(xsuite_environment.element_dict) == {"bb_1", "bb_2", "bb_3"}, (
        "All parsed SAD BEAMBEAM elements should be present in the environment.")
    for beambeam_name in ["bb_1", "bb_2", "bb_3"]:
        assert_environment_element(
            environment     = xsuite_environment,
            element_name    = beambeam_name,
            element_type    = xt.Marker)

def test_beambeam_converter_ignores_beambeam_parameters(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Current BEAMBEAM conversion should ignore parsed beam-beam parameters.
    """
    convert_beam_beam(
        parsed_elements = parsed_elements(
            element_type        = "beambeam",
            element_name        = "test_beambeam",
            element_variables   = {"offset": 1.0, "strength": 2.0}),
        environment     = xsuite_environment)

    beambeam = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_beambeam",
        element_type    = xt.Marker)

    assert isinstance(beambeam, xt.Marker), (
        "Parsed BEAMBEAM parameters should not change the converted element "
        "type.")

########################################
# Pipeline Behaviour
########################################
def test_beambeam_pipeline_preserves_beambeam_names(write_lattice):
    """
    Full conversion should preserve SAD BEAMBEAM element names in the Xsuite line.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEAMBEAM    BB_1        = ()
                    BB_2        = ()
                    BB_3        = ();

        LINE        TEST_LINE   = (BB_1 BB_2 BB_3);
        """,
        filename = "beambeam_pipeline_preserves_names.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["bb_1", "bb_2", "bb_3"], (
        "Converted BEAMBEAM-only line should preserve element order and names.")
    for beambeam_name in ["bb_1", "bb_2", "bb_3"]:
        assert isinstance(line[beambeam_name], xt.Marker), (
            f"Converted element '{beambeam_name}' should be an Xsuite Marker.")

################################################################################
# Physics Equivalence
################################################################################
########################################
# Zero-Length Beam-Beam Optics
########################################
def test_beambeam_conversion_matches_sad_zero_length_line(
        write_lattice,
        tmp_path):
    """
    BEAMBEAM elements should contribute zero length — SAD and Xsuite should
    agree on the total line length, which equals only the drift length.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_path = write_lattice(
            """\
            MOMENTUM    = 1.0 GEV;

            DRIFT       D1          = (L = 1.0);
            BEAMBEAM    BB_1        = ()
                        BB_2        = ();
            MARK        START       = ()
                        END         = ();

            LINE        TEST_LINE   = (START BB_1 D1 BB_2 END);
            """,
            filename = "beambeam_zero_length_line.sad")

        tw_sad = twiss_sad(
            lattice_filepath        = lattice_path.name,
            line_name               = "TEST_LINE",
            calc6d                  = False,
            closed                  = False,
            reverse_element_order   = False,
            reverse_survey_horizontal  = False,
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
        "BEAMBEAM elements should contribute zero length — SAD and Xsuite "
        "total line lengths should agree.")
