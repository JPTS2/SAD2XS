"""
================================================================================
Tests for SAD COORD conversion
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
import pytest
import sad2xs as s2x
import xtrack as xt

from sad2xs.config import Config
from sad2xs.converter._004_element_converter import convert_coordinate_transformations
from sad2xs.sad_helpers import track_sad
from tests.support.config import (
    DELTA_DELTA_ATOL,
    DELTA_DELTA_RTOL,
    DELTA_PX_ATOL,
    DELTA_PX_RTOL,
    DELTA_PY_ATOL,
    DELTA_PY_RTOL,
    DELTA_S_ATOL,
    DELTA_S_RTOL,
    DELTA_X_ATOL,
    DELTA_X_RTOL,
    DELTA_Y_ATOL,
    DELTA_Y_RTOL,
    DELTA_ZETA_ATOL,
    DELTA_ZETA_RTOL)
from tests.support.diagnostics import (
    diagnostic_report_path,
    write_tracking_failure_report,
    write_twiss_failure_report)
from sad2xs.sad_helpers import twiss_sad

################################################################################
# Diagnostic Helpers
################################################################################
COORD_ARTIFACT_CATEGORY = "conversion/elements/coord"

def _coord_config():
    """
    Return a quiet config for deterministic COORD conversion tests.
    """
    return Config(_verbose = False)

def _coord_tracking_tolerances():
    """
    Return coordinate tolerances used by COORD tracking comparisons.
    """
    return {
        "x":     (DELTA_X_ATOL, DELTA_X_RTOL),
        "px":    (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":     (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py":    (DELTA_PY_ATOL, DELTA_PY_RTOL),
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
    }

def _coord_twiss_tolerances():
    """
    Return tolerances used by COORD optics comparisons.
    """
    return {
        "s":     (DELTA_S_ATOL, DELTA_S_RTOL),
        "x":     (DELTA_X_ATOL, DELTA_X_RTOL),
        "px":    (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":     (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py":    (DELTA_PY_ATOL, DELTA_PY_RTOL),
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
    }

def _coord_twiss_values(twiss, element_name):
    """
    Pack COORD Twiss values for diagnostic reports.
    """
    return {
        "s":     twiss["s", element_name],
        "x":     twiss["x", element_name],
        "px":    twiss["px", element_name],
        "y":     twiss["y", element_name],
        "py":    twiss["py", element_name],
        "zeta":  twiss["zeta", element_name],
        "delta": twiss["delta", element_name],
    }

def _coord_initial_coordinates(
        x_init,
        px_init,
        y_init,
        py_init,
        zeta_init,
        delta_init):
    """
    Pack initial particle coordinates for diagnostic reports.
    """
    return {
        "x":     x_init,
        "px":    px_init,
        "y":     y_init,
        "py":    py_init,
        "zeta":  zeta_init,
        "delta": delta_init,
    }

def _coord_sad_coordinates(sad_particles):
    """
    Pack SAD tracking coordinates for diagnostic reports.
    """
    return {
        "x":     sad_particles["x"],
        "px":    sad_particles["px"],
        "y":     sad_particles["y"],
        "py":    sad_particles["py"],
        "zeta":  sad_particles["zeta"],
        "delta": sad_particles["delta"],
    }

def _coord_xsuite_coordinates(xs_particles):
    """
    Pack Xsuite tracking coordinates for diagnostic reports.
    """
    return {
        "x":     xs_particles.x,
        "px":    xs_particles.px,
        "y":     xs_particles.y,
        "py":    xs_particles.py,
        "zeta":  xs_particles.zeta,
        "delta": xs_particles.delta,
    }

def _assert_coord_twiss_matches_sad(
        test_name,
        lattice_text,
        sad_values,
        xsuite_values,
        parameters,
        notes = None):
    """
    Assert COORD optics equivalence and write a Markdown report on failure.
    """
    tolerances = _coord_twiss_tolerances()
    failed_values = []

    for name, xs_value in xsuite_values.items():
        atol, rtol = tolerances[name]
        if not np.isclose(
                sad_values[name],
                xs_value,
                rtol = rtol,
                atol = atol):
            failed_values.append(name)

    if failed_values:
        report_path = diagnostic_report_path(
            test_name  = test_name,
            category   = COORD_ARTIFACT_CATEGORY,
            parameters = parameters)
        write_twiss_failure_report(
            report_path   = report_path,
            title         = f"{test_name} failure",
            lattice_text  = lattice_text,
            sad_values    = sad_values,
            xsuite_values = xsuite_values,
            tolerances    = tolerances,
            parameters    = parameters,
            notes         = notes)
        pytest.fail(
            f"Converted COORD optics should match SAD. "
            f"Failed values: {failed_values}. "
            f"Diagnostic report: {report_path}")

def _assert_coord_tracking_matches_sad(
        test_name,
        lattice_text,
        initial_coordinates,
        sad_coordinates,
        xsuite_coordinates,
        parameters,
        notes = None):
    """
    Assert COORD tracking equivalence and write a Markdown report on failure.
    """
    tolerances = _coord_tracking_tolerances()
    failed_coordinates = []

    for coord, xs_values in xsuite_coordinates.items():
        atol, rtol = tolerances[coord]
        if not np.all(np.isclose(
                sad_coordinates[coord],
                xs_values,
                rtol = rtol,
                atol = atol)):
            failed_coordinates.append(coord)

    if failed_coordinates:
        report_path = diagnostic_report_path(
            test_name  = test_name,
            category   = COORD_ARTIFACT_CATEGORY,
            parameters = parameters)
        write_tracking_failure_report(
            report_path         = report_path,
            title               = f"{test_name} failure",
            lattice_text        = lattice_text,
            initial_coordinates = initial_coordinates,
            sad_coordinates     = sad_coordinates,
            xsuite_coordinates  = xsuite_coordinates,
            tolerances          = tolerances,
            parameters          = parameters,
            notes               = notes)
        pytest.fail(
            f"Converted COORD tracking should match SAD. "
            f"Failed coordinates: {failed_coordinates}. "
            f"Diagnostic report: {report_path}")

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
@pytest.mark.parametrize(
    "element_variables, expected_dx, expected_dy",
    [
        ({"dx": 1.0E-3}, 1.0E-3, 0.0),
        ({"dy": -2.0E-3}, 0.0, -2.0E-3),
        ({"dx": 1.0E-3, "dy": -2.0E-3}, 1.0E-3, -2.0E-3),
    ])
def test_coord_converter_creates_xsuite_translation(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables,
        expected_dx,
        expected_dy):
    """
    SAD COORD transverse shifts should become current Xsuite Translation elements.
    """
    convert_coordinate_transformations(
        parsed_elements = parsed_elements(
            element_type      = "coord",
            element_name      = "test_coord",
            element_variables = element_variables),
        environment     = xsuite_environment,
        config          = _coord_config())

    translation = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_coord",
        element_type = xt.Translation)

    assert translation.shift_x == pytest.approx(expected_dx), (
        "Converted COORD should preserve SAD DX with the current sign convention.")
    assert translation.shift_y == pytest.approx(expected_dy), (
        "Converted COORD should preserve SAD DY with the current sign convention.")

@pytest.mark.parametrize(
    "element_variables, expected_field, expected_value",
    [
        ({"chi1": 0.125}, "rot_y_rad", -0.125),
        ({"chi2": 0.125}, "rot_x_rad",  0.125),
        ({"chi3": 0.125}, "rot_s_rad", -0.125),
    ])
def test_coord_converter_creates_xsuite_rotations(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables,
        expected_field,
        expected_value):
    """
    SAD COORD rotations should become current Xsuite Rotation elements.
    """
    convert_coordinate_transformations(
        parsed_elements = parsed_elements(
            element_type      = "coord",
            element_name      = "test_coord",
            element_variables = element_variables),
        environment     = xsuite_environment,
        config          = _coord_config())

    rotation = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_coord",
        element_type = xt.Rotation)

    assert getattr(rotation, expected_field) == pytest.approx(expected_value), (
        "Converted COORD rotation should store radians with the current "
        "SAD-to-Xsuite sign convention.")

def test_coord_converter_creates_marker_like_translation_for_empty_transform(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Empty COORD elements install a zero Translation placeholder.
    """
    convert_coordinate_transformations(
        parsed_elements = parsed_elements(
            element_type      = "coord",
            element_name      = "test_coord",
            element_variables = {}),
        environment     = xsuite_environment,
        config          = _coord_config())

    translation = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_coord",
        element_type = xt.Translation)

    assert translation.shift_x == pytest.approx(0.0), (
        "Empty COORD placeholder should have zero horizontal shift.")
    assert translation.shift_y == pytest.approx(0.0), (
        "Empty COORD placeholder should have zero vertical shift.")

########################################
# Compound Coordinate Transforms
########################################
def test_coord_converter_creates_compound_transform_line(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    COORD elements with shifts and rotations should become generated sub-lines.
    """
    convert_coordinate_transformations(
        parsed_elements = parsed_elements(
            element_type      = "coord",
            element_name      = "test_coord",
            element_variables = {
                "dx":   1.0E-3,
                "dy":   -2.0E-3,
                "chi1": 0.125,
                "chi2": -0.25,
                "chi3": 0.5,
            }),
        environment     = xsuite_environment,
        config          = _coord_config())

    assert "test_coord" in xsuite_environment.lines, (
        "Compound COORD should be installed as an Xsuite environment line.")
    assert xsuite_environment.lines["test_coord"].element_names == [
        "test_coord_dxy",
        "test_coord_chi1",
        "test_coord_chi2",
        "test_coord_chi3",
    ], (
        "Compound COORD should preserve the current shift-then-rotation order.")

    translation = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_coord_dxy",
        element_type = xt.Translation)
    chi1 = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_coord_chi1",
        element_type = xt.Rotation)
    chi2 = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_coord_chi2",
        element_type = xt.Rotation)
    chi3 = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_coord_chi3",
        element_type = xt.Rotation)

    assert translation.shift_x == pytest.approx(1.0E-3), (
        "Compound COORD should preserve SAD DX.")
    assert translation.shift_y == pytest.approx(-2.0E-3), (
        "Compound COORD should preserve SAD DY.")
    assert chi1.rot_y_rad == pytest.approx(-0.125), (
        "Compound COORD should preserve the CHI1 sign convention.")
    assert chi2.rot_x_rad == pytest.approx(-0.25), (
        "Compound COORD should preserve the CHI2 sign convention.")
    assert chi3.rot_s_rad == pytest.approx(-0.5), (
        "Compound COORD should preserve the CHI3 sign convention.")

########################################
# Reversed Coordinate Transforms
########################################
def test_coord_converter_applies_dir_signs_and_order(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    DIR should apply the current reversed-COORD signs and transform ordering.
    """
    convert_coordinate_transformations(
        parsed_elements = parsed_elements(
            element_type      = "coord",
            element_name      = "test_coord",
            element_variables = {
                "dir":  1.0,
                "dx":   1.0E-3,
                "dy":   -2.0E-3,
                "chi1": 0.125,
                "chi2": -0.25,
                "chi3": 0.5,
            }),
        environment     = xsuite_environment,
        config          = _coord_config())

    assert xsuite_environment.lines["test_coord"].element_names == [
        "test_coord_chi1",
        "test_coord_chi2",
        "test_coord_chi3",
        "test_coord_dxy",
    ], (
        "DIR COORD should preserve the current rotation-then-shift order.")

    chi1 = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_coord_chi1",
        element_type = xt.Rotation)
    chi2 = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_coord_chi2",
        element_type = xt.Rotation)
    chi3 = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_coord_chi3",
        element_type = xt.Rotation)
    translation = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_coord_dxy",
        element_type = xt.Translation)

    assert translation.shift_x == pytest.approx(-1.0E-3), (
        "DIR COORD should reverse the current DX convention.")
    assert translation.shift_y == pytest.approx(-2.0E-3), (
        "DIR COORD should preserve the current DY convention.")
    assert chi1.rot_y_rad == pytest.approx(-0.125), (
        "DIR COORD should preserve the current CHI1 convention.")
    assert chi2.rot_x_rad == pytest.approx(0.25), (
        "DIR COORD should reverse the current CHI2 convention.")
    assert chi3.rot_s_rad == pytest.approx(-0.5), (
        "DIR COORD should preserve the current CHI3 convention.")

################################################################################
# Pipeline Behaviour
################################################################################
########################################
# Full Conversion
########################################
def test_coord_pipeline_preserves_single_shift(write_lattice):
    """
    Full conversion should preserve single COORD shift elements in the line.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        COORD       TEST_COORD  = (DX = 0.001 DY = -0.002);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_COORD END);
        """,
        filename = "coord_pipeline_preserves_single_shift.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.element_names == ["start", "test_coord", "end"], (
        "Converted COORD line should preserve marker and COORD order.")
    assert isinstance(line["test_coord"], xt.Translation), (
        "Single DX/DY COORD should remain an Xsuite Translation in the line.")
    assert line["test_coord"].shift_x == pytest.approx(1.0E-3), (
        "Pipeline conversion should preserve SAD DX.")
    assert line["test_coord"].shift_y == pytest.approx(-2.0E-3), (
        "Pipeline conversion should preserve SAD DY.")

def test_coord_pipeline_expands_compound_transform(write_lattice):
    """
    Full conversion should expand compound COORD sub-lines into the final line.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        COORD       TEST_COORD  = (
            DX      = 0.001
            DY      = -0.002
            CHI1    = 0.125
            CHI2    = -0.25
            CHI3    = 0.5
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_COORD END);
        """,
        filename = "coord_pipeline_expands_compound_transform.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    expected_names = [
        "start",
        "test_coord_dxy",
        "test_coord_chi1",
        "test_coord_chi2",
        "test_coord_chi3",
        "end",
    ]
    assert line.element_names == expected_names, (
        "Compound COORD should expand to its generated child elements in order.")
    assert isinstance(line["test_coord_dxy"], xt.Translation), (
        "Compound COORD should include an Xsuite Translation child.")
    assert isinstance(line["test_coord_chi1"], xt.Rotation), (
        "Compound COORD should include an Xsuite Rotation child for CHI1.")
    assert isinstance(line["test_coord_chi2"], xt.Rotation), (
        "Compound COORD should include an Xsuite Rotation child for CHI2.")
    assert isinstance(line["test_coord_chi3"], xt.Rotation), (
        "Compound COORD should include an Xsuite Rotation child for CHI3.")

def test_coord_pipeline_preserves_reversed_compound_transform(write_lattice):
    """
    Full conversion should preserve reversed generated COORD sub-line behaviour.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        COORD       TEST_COORD  = (
            DX      = 0.001
            DY      = -0.002
            CHI1    = 0.125
            CHI2    = -0.25
            CHI3    = 0.5
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START -TEST_COORD END);
        """,
        filename = "coord_pipeline_preserves_reversed_compound_transform.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    expected_names = [
        "start",
        "-test_coord_dxy",
        "-test_coord_chi1",
        "-test_coord_chi2",
        "-test_coord_chi3",
        "end",
    ]
    assert line.element_names == expected_names, (
        "Reversed generated COORD sub-lines should preserve current cloned "
        "child-element naming.")
    assert isinstance(line["-test_coord_dxy"], xt.Translation), (
        "Reversed COORD shift should remain a current Xsuite Translation clone.")
    assert isinstance(line["-test_coord_chi1"], xt.Rotation), (
        "Reversed COORD CHI1 should remain a current Xsuite Rotation clone.")
    assert isinstance(line["-test_coord_chi2"], xt.Rotation), (
        "Reversed COORD CHI2 should remain a current Xsuite Rotation clone.")
    assert isinstance(line["-test_coord_chi3"], xt.Rotation), (
        "Reversed COORD CHI3 should remain a current Xsuite Rotation clone.")

################################################################################
# Physics Equivalence
################################################################################
########################################
# Coordinate Transform Optics
########################################
@pytest.mark.parametrize(
    "coord_definition, parameters",
    [
        ("DX = 0.001 DY = -0.002", {"dx": 1.0E-3, "dy": -2.0E-3}),
        ("CHI1 = 0.125", {"chi1": 0.125}),
        ("CHI2 = -0.125", {"chi2": -0.125}),
        ("CHI3 = 0.125", {"chi3": 0.125}),
        (
            "DX = 0.001 DY = -0.002 CHI1 = 0.125 CHI2 = -0.125 CHI3 = 0.25",
            {
                "dx":   1.0E-3,
                "dy":   -2.0E-3,
                "chi1": 0.125,
                "chi2": -0.125,
                "chi3": 0.25,
            },
        ),
    ])
def test_coord_conversion_matches_sad_twiss(
        write_lattice,
        tmp_path,
        coord_definition,
        parameters):
    """
    Converted SAD COORD transformations should match SAD optics.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        COORD       TEST_COORD  = ({coord_definition});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_COORD END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = "coord_twiss.sad")

        tw_sad = twiss_sad(
            lattice_filepath        = lattice_path.name,
            line_name               = "TEST_LINE",
            calc6d                  = False,
            closed                  = False,
            reverse_element_order   = False,
            reverse_survey_horizontal  = False,
            rfsw                    = True,
            additional_commands     = "")

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path = str(lattice_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)

        tw_xs = line.twiss4d(
            _continue_if_lost = True,
            start             = xt.START,
            end               = xt.END,
            betx              = 1,
            bety              = 1)

        sad_values = _coord_twiss_values(tw_sad, "END")
        xsuite_values = _coord_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_coord_twiss_matches_sad(
        test_name     = "test_coord_conversion_matches_sad_twiss",
        lattice_text  = lattice_text,
        sad_values    = sad_values,
        xsuite_values = xsuite_values,
        parameters    = parameters,
        notes         = [
            "COORD tests intentionally assert the current Xsuite reference "
            "element API. Migration to xt.Translation/xt.Rotation should update "
            "the converter compatibility notes and these tests together.",
        ])

########################################
# Coordinate Transform Tracking
########################################
@pytest.mark.parametrize(
    "coord_definition, parameters",
    [
        ("DX = 0.001 DY = -0.002", {"dx": 1.0E-3, "dy": -2.0E-3}),
        ("CHI1 = 0.125", {"chi1": 0.125}),
        ("CHI2 = -0.125", {"chi2": -0.125}),
        ("CHI3 = 0.125", {"chi3": 0.125}),
        (
            "DX = 0.001 DY = -0.002 CHI1 = 0.125 CHI2 = -0.125 CHI3 = 0.25",
            {
                "dx":   1.0E-3,
                "dy":   -2.0E-3,
                "chi1": 0.125,
                "chi2": -0.125,
                "chi3": 0.25,
            },
        ),
    ])
def test_coord_conversion_matches_sad_tracking(
        write_lattice,
        tmp_path,
        coord_definition,
        parameters):
    """
    Converted SAD COORD transformations should match SAD tracking.
    """
    x_init     = np.array([0.0, 1E-4, 0.0, 1E-4, -1E-4])
    px_init    = np.array([0.0, 0.0, 1E-4, 0.0, -1E-4])
    y_init     = np.array([0.0, 0.0, 1E-4, 1E-4, -1E-4])
    py_init    = np.array([0.0, 1E-4, 0.0, -1E-4, 1E-4])
    zeta_init  = np.zeros_like(x_init)
    delta_init = np.zeros_like(x_init)

    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        COORD       TEST_COORD  = ({coord_definition});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_COORD END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = "coord_tracking.sad")

        sad_particles = track_sad(
            lattice_filepath     = lattice_path.name,
            line_name            = "TEST_LINE",
            x_init               = x_init,
            px_init              = px_init,
            y_init               = y_init,
            py_init              = py_init,
            zeta_init            = zeta_init,
            delta_init           = delta_init,
            n_turns              = 1,
            rfsw                 = True,
            rad                  = False,
            fluc                 = False,
            radcod               = False,
            radtaper             = False,
            turn_by_turn_monitor = False,
            with_progress        = False,
            wall_time            = 30)

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path = str(lattice_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)

        xs_particles = xt.Particles(
            p0c   = 1.0E9,
            mass0 = xt.ELECTRON_MASS_EV,
            q0    = 1,
            x     = x_init.copy(),
            px    = px_init.copy(),
            y     = y_init.copy(),
            py    = py_init.copy(),
            zeta  = zeta_init.copy(),
            delta = delta_init.copy())

        line.track(xs_particles, num_turns = 1)
    finally:
        os.chdir(cwd)

    _assert_coord_tracking_matches_sad(
        test_name           = "test_coord_conversion_matches_sad_tracking",
        lattice_text        = lattice_text,
        initial_coordinates = _coord_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates     = _coord_sad_coordinates(sad_particles),
        xsuite_coordinates  = _coord_xsuite_coordinates(xs_particles),
        parameters          = parameters,
        notes               = [
            "COORD tests intentionally assert the current Xsuite reference "
            "element API. Migration to xt.Translation/xt.Rotation should update "
            "the converter compatibility notes and these tests together.",
        ])
