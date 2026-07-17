"""
================================================================================
Tests for SAD MAP conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-17
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import os

import numpy as np
import pytest
import sad2xs as s2x
import xtrack as xt

from sad2xs.converter._004_element_converter import convert_maps
from tests.support.config import DELTA_S_ATOL, DELTA_S_RTOL
from sad2xs.sad_helpers import twiss_sad

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
def test_map_converter_creates_xsuite_marker(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Parsed SAD MAP elements with no parameters should become Xsuite Marker
    elements.
    """
    convert_maps(
        parsed_elements = parsed_elements(
            element_type        = "map",
            element_name        = "test_map",
            element_variables   = {}),
        environment     = xsuite_environment)

    assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_map",
        element_type    = xt.Marker)

def test_map_converter_creates_all_maps(
        xsuite_environment,
        assert_environment_element):
    """
    Multiple parsed SAD MAP elements should all be converted.
    """
    parsed_elements = {
        "map": {
            "jbc1p": {},
            "jbh0e": {},
            "jbhd0": {},
        },
    }

    convert_maps(
        parsed_elements = parsed_elements,
        environment     = xsuite_environment)

    assert set(xsuite_environment.element_dict) == {"jbc1p", "jbh0e", "jbhd0"}, (
        "All parsed SAD MAP elements should be present in the environment.")
    for map_name in ["jbc1p", "jbh0e", "jbhd0"]:
        assert_environment_element(
            environment     = xsuite_environment,
            element_name    = map_name,
            element_type    = xt.Marker)

def test_map_converter_rejects_parametrised_map(
        parsed_elements,
        xsuite_environment):
    """
    A MAP element with any parameters is not understood and must raise,
    rather than being silently converted or having its parameters ignored.
    """
    with pytest.raises(ValueError, match = "test_map"):
        convert_maps(
            parsed_elements = parsed_elements(
                element_type        = "map",
                element_name        = "test_map",
                element_variables   = {"dx": 1.0}),
            environment     = xsuite_environment)

########################################
# Pipeline Behaviour
########################################
def test_map_pipeline_preserves_map_names(write_lattice):
    """
    Full conversion should preserve SAD MAP element names in the Xsuite line.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MAP         JBC1P       = ()
                    JBH0E       = ()
                    JBHD0       = ();

        LINE        TEST_LINE   = (JBC1P JBH0E JBHD0);
        """,
        filename = "map_pipeline_preserves_names.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["jbc1p", "jbh0e", "jbhd0"], (
        "Converted MAP-only line should preserve map order and names.")
    for map_name in ["jbc1p", "jbh0e", "jbhd0"]:
        assert isinstance(line[map_name], xt.Marker), (
            f"Converted element '{map_name}' should be an Xsuite Marker.")

def test_map_pipeline_rejects_parametrised_map(write_lattice):
    """
    A MAP element with a parameter should raise during full conversion, not
    just when the converter function is called directly.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MAP         JBC1P       = (DX = 1.0);

        LINE        TEST_LINE   = (JBC1P);
        """,
        filename = "map_pipeline_rejects_parametrised.sad")

    with pytest.raises(ValueError, match = "jbc1p"):
        s2x.convert_sad_to_xsuite(
            sad_lattice_path    = str(lattice_path),
            output_directory    = "N/A",
            _verbose            = False,
            _test_mode          = True)

################################################################################
# Physics Equivalence
################################################################################
########################################
# Zero-Length Map Optics
########################################
def test_map_conversion_matches_sad_zero_length_line(write_lattice, tmp_path):
    """
    MAP elements should contribute zero length — SAD and Xsuite should agree
    on the total line length, which equals only the drift length.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_path = write_lattice(
            """\
            MOMENTUM    = 1.0 GEV;

            DRIFT       D1          = (L = 1.0);
            MAP         JBC1P       = ()
                        JBH0E       = ();
            MARK        START       = ()
                        END         = ();

            LINE        TEST_LINE   = (START JBC1P D1 JBH0E END);
            """,
            filename = "map_zero_length_line.sad")

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
        "MAP elements should contribute zero length — SAD and Xsuite total "
        "line lengths should agree.")
