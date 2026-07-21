"""
================================================================================
Tests for SAD MONI conversion
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

from sad2xs.converter._004_element_converter import convert_monitors
from tests.support.config import DELTA_S_ATOL, DELTA_S_RTOL
from sad2xs.sad_helpers import twiss_sad

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
def test_moni_converter_creates_xsuite_marker(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Parsed SAD MONI elements should currently become Xsuite Marker elements.
    """
    convert_monitors(
        parsed_elements = parsed_elements(
            element_type        = "moni",
            element_name        = "test_moni",
            element_variables   = {}),
        environment     = xsuite_environment)

    assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_moni",
        element_type    = xt.Marker)

def test_moni_converter_creates_all_monitors(
        xsuite_environment,
        assert_environment_element):
    """
    Multiple parsed SAD MONI elements should all be converted.
    """
    parsed_elements = {
        "moni": {
            "bpm_1": {},
            "bpm_2": {},
            "bpm_3": {},
        },
    }

    convert_monitors(
        parsed_elements = parsed_elements,
        environment     = xsuite_environment)

    assert set(xsuite_environment.element_dict) == {"bpm_1", "bpm_2", "bpm_3"}, (
        "All parsed SAD MONI elements should be present in the environment.")
    for monitor_name in ["bpm_1", "bpm_2", "bpm_3"]:
        assert_environment_element(
            environment     = xsuite_environment,
            element_name    = monitor_name,
            element_type    = xt.Marker)

def test_moni_converter_ignores_monitor_parameters(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Current MONI conversion should ignore parsed monitor parameters.
    """
    convert_monitors(
        parsed_elements = parsed_elements(
            element_type        = "moni",
            element_name        = "test_moni",
            element_variables   = {"offset": 1.0, "dx": 2.0}),
        environment     = xsuite_environment)

    monitor = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_moni",
        element_type    = xt.Marker)

    assert isinstance(monitor, xt.Marker), (
        "Parsed MONI parameters should not change the converted element type.")

########################################
# Pipeline Behaviour
########################################
def test_moni_pipeline_preserves_monitor_names(write_lattice):
    """
    Full conversion should preserve SAD MONI element names in the Xsuite line.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MONI        BPM_1       = ()
                    BPM_2       = ()
                    BPM_3       = ();

        LINE        TEST_LINE   = (BPM_1 BPM_2 BPM_3);
        """,
        filename = "moni_pipeline_preserves_names.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["bpm_1", "bpm_2", "bpm_3"], (
        "Converted MONI-only line should preserve monitor order and names.")
    for monitor_name in ["bpm_1", "bpm_2", "bpm_3"]:
        assert isinstance(line[monitor_name], xt.Marker), (
            f"Converted element `{monitor_name}` should be an Xsuite Marker.")

################################################################################
# Physics Equivalence
################################################################################
########################################
# Zero-Length Monitor Optics
########################################
def test_moni_conversion_matches_sad_zero_length_line(write_lattice, tmp_path):
    """
    MONI elements should contribute zero length — SAD and Xsuite should agree
    on the total line length, which equals only the drift length.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_path = write_lattice(
            """\
            MOMENTUM    = 1.0 GEV;

            DRIFT       D1          = (L = 1.0);
            MONI        BPM_1       = ()
                        BPM_2       = ();
            MARK        START       = ()
                        END         = ();

            LINE        TEST_LINE   = (START BPM_1 D1 BPM_2 END);
            """,
            filename = "moni_zero_length_line.sad")

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
        "MONI elements should contribute zero length — SAD and Xsuite total "
        "line lengths should agree.")
