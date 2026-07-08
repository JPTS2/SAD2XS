"""
================================================================================
Tests for SAD QUAD conversion
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

from sad2xs.converter._004_element_converter import convert_quadrupoles
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
QUAD_ARTIFACT_CATEGORY = "conversion/elements/quad"

def _quad_tracking_tolerances():
    """
    Return coordinate tolerances used by quadrupole tracking comparisons.
    """
    return {
        "x":     (DELTA_X_ATOL, DELTA_X_RTOL),
        "px":    (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":     (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py":    (DELTA_PY_ATOL, DELTA_PY_RTOL),
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
    }

def _quad_twiss_tolerances():
    """
    Return coordinate tolerances used by quadrupole Twiss comparisons.
    """
    return {
        "s":     (1E-9, 1E-5),
        "betx":  (1E-9, 1E-5),
        "bety":  (1E-9, 1E-5),
        "alfx":  (1E-9, 1E-5),
        "alfy":  (1E-9, 1E-5),
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
    }

def _quad_initial_coordinates(
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
        "x":      x_init,
        "px":     px_init,
        "y":      y_init,
        "py":     py_init,
        "zeta":   zeta_init,
        "delta":  delta_init,
    }

def _quad_sad_coordinates(sad_particles):
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

def _quad_xsuite_coordinates(xs_particles):
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

def _assert_quad_tracking_matches_sad(
        test_name,
        lattice_text,
        initial_coordinates,
        sad_coordinates,
        xsuite_coordinates,
        parameters,
        notes = None):
    """
    Assert tracking equivalence and write a Markdown report on failure.
    """
    tolerances = _quad_tracking_tolerances()
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
            test_name       = test_name,
            category        = QUAD_ARTIFACT_CATEGORY,
            parameters      = parameters)
        write_tracking_failure_report(
            report_path             = report_path,
            title                   = f"{test_name} failure",
            lattice_text            = lattice_text,
            initial_coordinates     = initial_coordinates,
            sad_coordinates         = sad_coordinates,
            xsuite_coordinates      = xsuite_coordinates,
            tolerances              = tolerances,
            parameters              = parameters,
            notes                   = notes)
        pytest.fail(
            f"Converted quadrupole tracking should match SAD. "
            f"Failed coordinates: {failed_coordinates}. "
            f"Diagnostic report: {report_path}")

def _assert_quad_twiss_matches_sad(
        test_name,
        lattice_text,
        sad_values,
        xsuite_values,
        parameters,
        notes = None):
    """
    Assert Twiss equivalence and write a Markdown report on failure.
    """
    tolerances = _quad_twiss_tolerances()
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
            test_name       = test_name,
            category        = QUAD_ARTIFACT_CATEGORY,
            parameters      = parameters)
        write_twiss_failure_report(
            report_path     = report_path,
            title           = f"{test_name} failure",
            lattice_text    = lattice_text,
            sad_values      = sad_values,
            xsuite_values   = xsuite_values,
            tolerances      = tolerances,
            parameters      = parameters,
            notes           = notes)
        pytest.fail(
            f"Converted quadrupole Twiss should match SAD. "
            f"Failed values: {failed_values}. "
            f"Diagnostic report: {report_path}")

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
@pytest.mark.parametrize(
    "k1l, expected_k1",
    [
        (0.0, 0.0),
        (0.1, 0.2),
        (-0.1, -0.2),
    ])
def test_quad_converter_creates_xsuite_quadrupole(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        k1l,
        expected_k1):
    """
    Parsed SAD QUAD elements should become Xsuite Quadrupole elements.
    """
    convert_quadrupoles(
        parsed_elements = parsed_elements(
            element_type        = "quad",
            element_name        = "test_quad",
            element_variables   = {"l": 0.5, "k1": k1l}),
        environment     = xsuite_environment)

    quad = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_quad",
        element_type    = xt.Quadrupole)

    assert quad.length == pytest.approx(0.5), (
        "Converted quadrupole should preserve the parsed SAD length.")
    assert quad.k1 == pytest.approx(expected_k1), (
        "Converted quadrupole k1 should equal parsed integrated K1 divided by "
        "length.")
    assert quad.k1s == pytest.approx(0.0), (
        "Unrotated SAD quadrupoles should have zero skew quadrupole strength.")

def test_quad_converter_creates_all_quadrupoles(
        xsuite_environment,
        assert_environment_element):
    """
    Multiple parsed SAD QUAD elements should all be converted.
    """
    parsed_elements = {
        "quad": {
            "qf": {"l": 0.5, "k1": 0.1},
            "qd": {"l": 0.5, "k1": -0.1},
            "q0": {"l": 0.5, "k1": 0.0},
        },
    }

    convert_quadrupoles(
        parsed_elements = parsed_elements,
        environment     = xsuite_environment)

    assert set(xsuite_environment.element_dict) == {"qf", "qd", "q0"}, (
        "All parsed SAD QUAD elements should be present in the environment.")
    for quad_name, expected_k1 in [
            ("qf", 0.2),
            ("qd", -0.2),
            ("q0", 0.0)]:
        quad = assert_environment_element(
            environment     = xsuite_environment,
            element_name    = quad_name,
            element_type    = xt.Quadrupole)
        assert quad.length == pytest.approx(0.5), (
            f"Converted quadrupole '{quad_name}' should preserve length.")
        assert quad.k1 == pytest.approx(expected_k1), (
            f"Converted quadrupole '{quad_name}' should preserve integrated "
            "strength divided by length.")

########################################
# Defaults and Symbolic Parameters
########################################
def test_quad_converter_defaults_missing_k1_to_zero(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    A SAD QUAD without K1 should convert as a zero-strength quadrupole.
    """
    convert_quadrupoles(
        parsed_elements = parsed_elements(
            element_type        = "quad",
            element_name        = "test_quad",
            element_variables   = {"l": 0.5}),
        environment     = xsuite_environment)

    quad = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_quad",
        element_type    = xt.Quadrupole)

    assert quad.k1 == pytest.approx(0.0), (
        "Missing SAD QUAD K1 should convert to zero quadrupole strength.")

def test_quad_converter_preserves_symbolic_strength_with_environment_variable(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Symbolic SAD QUAD strengths should resolve through Xsuite environment vars.
    """
    xsuite_environment["kq"] = 0.1

    convert_quadrupoles(
        parsed_elements = parsed_elements(
            element_type        = "quad",
            element_name        = "test_quad",
            element_variables   = {"l": 0.5, "k1": "kq"}),
        environment     = xsuite_environment)

    quad = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_quad",
        element_type    = xt.Quadrupole)

    assert xsuite_environment["k1_test_quad"] == pytest.approx(0.2), (
        "Symbolic integrated K1 should be converted to a resolved k1 variable.")
    assert quad.k1 == pytest.approx(0.2), (
        "Converted quadrupole should use the resolved symbolic k1 variable.")

########################################
# Offsets and Rotations
########################################
def test_quad_converter_preserves_offsets_and_rotation(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    SAD QUAD DX, DY, and ROTATE should map to Xsuite element fields.
    """
    convert_quadrupoles(
        parsed_elements = parsed_elements(
            element_type        = "quad",
            element_name        = "test_quad",
            element_variables   = {
                "l":        0.5,
                "k1":       0.1,
                "dx":       1.0E-3,
                "dy":       -2.0E-3,
                "rotate":   0.125,
            }),
        environment     = xsuite_environment)

    quad = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_quad",
        element_type    = xt.Quadrupole)

    assert quad.shift_x == pytest.approx(1.0E-3), (
        "Converted quadrupole should preserve SAD DX as Xsuite shift_x.")
    assert quad.shift_y == pytest.approx(-2.0E-3), (
        "Converted quadrupole should preserve SAD DY as Xsuite shift_y.")
    assert quad.rot_s_rad == pytest.approx(-0.125), (
        "Converted quadrupole should apply the SAD-to-Xsuite rotation sign.")

########################################
# Special Rotation Mapping
########################################
@pytest.mark.parametrize(
    "sad_rotation, expected_k1, expected_k1s",
    [
        (+np.pi / 4, 0.0, +0.2),
        (-np.pi / 4, 0.0, -0.2),
    ])
def test_quad_converter_maps_45_degree_rotations_to_skew_strength(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        sad_rotation,
        expected_k1,
        expected_k1s):
    """
    45 degree SAD QUAD rotations should convert to pure skew quadrupoles.
    """
    convert_quadrupoles(
        parsed_elements = parsed_elements(
            element_type        = "quad",
            element_name        = "test_quad",
            element_variables   = {
                "l":        0.5,
                "k1":       0.1,
                "rotate":   sad_rotation,
            }),
        environment     = xsuite_environment)

    quad = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_quad",
        element_type    = xt.Quadrupole)

    assert quad.k1 == pytest.approx(expected_k1), (
        "45 degree rotated quadrupoles should not retain normal k1 strength.")
    assert quad.k1s == pytest.approx(expected_k1s), (
        "45 degree rotated quadrupoles should map integrated K1 to k1s.")
    assert quad.rot_s_rad == pytest.approx(0.0), (
        "Pure skew quadrupole conversion should remove the residual rotation.")

@pytest.mark.parametrize(
    "sad_rotation",
    [
        +np.pi / 4 - 0.01,
        +np.pi / 4 + 0.01,
        -np.pi / 4 - 0.01,
        -np.pi / 4 + 0.01,
    ])
def test_quad_converter_near_45_degree_rotations_remain_explicit_rotations(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        sad_rotation):
    """
    Near-45-degree SAD QUAD rotations should not trigger the skew shortcut.
    """
    convert_quadrupoles(
        parsed_elements = parsed_elements(
            element_type        = "quad",
            element_name        = "test_quad",
            element_variables   = {
                "l":        0.5,
                "k1":       0.1,
                "rotate":   sad_rotation,
            }),
        environment     = xsuite_environment)

    quad = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_quad",
        element_type    = xt.Quadrupole)

    assert quad.k1 == pytest.approx(0.2), (
        "Near-45-degree rotations should retain normal quadrupole strength.")
    assert quad.k1s == pytest.approx(0.0), (
        "Near-45-degree rotations should not be rewritten as pure skew.")
    assert quad.rot_s_rad == pytest.approx(-sad_rotation), (
        "Near-45-degree rotations should remain explicit Xsuite rotations.")

def test_quad_converter_supports_symbolic_length_and_strength(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Symbolic SAD QUAD lengths and strengths should resolve through Xsuite vars.
    """
    xsuite_environment["lq"] = 0.5
    xsuite_environment["kq"] = 0.1

    convert_quadrupoles(
        parsed_elements = parsed_elements(
            element_type        = "quad",
            element_name        = "test_quad",
            element_variables   = {"l": "lq", "k1": "kq"}),
        environment     = xsuite_environment)

    quad = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_quad",
        element_type    = xt.Quadrupole)

    assert quad.length == pytest.approx(0.5), (
        "Converted quadrupole should resolve the SAD symbolic length.")
    assert quad.k1 == pytest.approx(0.2), (
        "Converted quadrupole should resolve symbolic integrated K1 divided "
        "by symbolic length.")

########################################
# Thin Element Behaviour
########################################
@pytest.mark.parametrize(
    "element_variables",
    [
        {"k1": 0.1},
        {"l": 0.0, "k1": 0.1},
    ])
def test_quad_converter_converts_thin_quadrupole_to_multipole(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables):
    """
    Thin SAD QUAD elements should become active Xsuite Multipole kicks.
    """
    convert_quadrupoles(
        parsed_elements = parsed_elements(
            element_type        = "quad",
            element_name        = "test_quad",
            element_variables   = element_variables),
        environment     = xsuite_environment)

    multipole = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_quad",
        element_type    = xt.Multipole)

    assert multipole.knl[1] == pytest.approx(0.1), (
        "Thin QUAD K1 should be preserved as integrated knl[1].")

def test_quad_converter_thin_element_preserves_offsets_and_rotation(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Thin SAD QUAD DX, DY, and ROTATE should map to Xsuite Multipole fields.
    """
    convert_quadrupoles(
        parsed_elements = parsed_elements(
            element_type        = "quad",
            element_name        = "test_quad",
            element_variables   = {
                "k1":       0.1,
                "dx":       1.0E-3,
                "dy":       -2.0E-3,
                "rotate":   0.125,
            }),
        environment     = xsuite_environment)

    multipole = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_quad",
        element_type    = xt.Multipole)

    assert multipole.shift_x == pytest.approx(1.0E-3), (
        "Thin QUAD DX should be preserved as Xsuite shift_x.")
    assert multipole.shift_y == pytest.approx(-2.0E-3), (
        "Thin QUAD DY should be preserved as Xsuite shift_y.")
    assert multipole.rot_s_rad == pytest.approx(-0.125), (
        "Thin QUAD ROTATE should apply the SAD-to-Xsuite rotation sign.")

@pytest.mark.parametrize(
    "sad_rotation, expected_knl1, expected_ksl1",
    [
        (+np.pi / 4, 0.0, +0.1),
        (-np.pi / 4, 0.0, -0.1),
    ])
def test_quad_converter_thin_element_maps_45_degree_rotations_to_skew_strength(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        sad_rotation,
        expected_knl1,
        expected_ksl1):
    """
    45 degree rotated thin SAD QUAD elements should convert to pure skew kicks.
    """
    convert_quadrupoles(
        parsed_elements = parsed_elements(
            element_type        = "quad",
            element_name        = "test_quad",
            element_variables   = {
                "k1":       0.1,
                "rotate":   sad_rotation,
            }),
        environment     = xsuite_environment)

    multipole = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_quad",
        element_type    = xt.Multipole)

    assert multipole.knl[1] == pytest.approx(expected_knl1), (
        "45 degree rotated thin QUAD should not retain normal knl[1] kick.")
    assert multipole.ksl[1] == pytest.approx(expected_ksl1), (
        "45 degree rotated thin QUAD should map K1 to integrated ksl[1].")
    assert multipole.rot_s_rad == pytest.approx(0.0), (
        "Pure skew thin QUAD conversion should remove the residual rotation.")

@pytest.mark.parametrize(
    "sad_rotation",
    [
        +np.pi / 4 - 0.01,
        +np.pi / 4 + 0.01,
        -np.pi / 4 - 0.01,
        -np.pi / 4 + 0.01,
    ])
def test_quad_converter_thin_element_near_45_degree_rotations_remain_explicit_rotations(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        sad_rotation):
    """
    Near-45-degree rotated thin SAD QUAD should not trigger the skew shortcut.
    """
    convert_quadrupoles(
        parsed_elements = parsed_elements(
            element_type        = "quad",
            element_name        = "test_quad",
            element_variables   = {
                "k1":       0.1,
                "rotate":   sad_rotation,
            }),
        environment     = xsuite_environment)

    multipole = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_quad",
        element_type    = xt.Multipole)

    assert multipole.knl[1] == pytest.approx(0.1), (
        "Near-45-degree thin QUAD should retain normal integrated kick.")
    assert multipole.ksl[1] == pytest.approx(0.0), (
        "Near-45-degree thin QUAD should not be rewritten as pure skew.")
    assert multipole.rot_s_rad == pytest.approx(-sad_rotation), (
        "Near-45-degree thin QUAD should remain an explicit Xsuite rotation.")

########################################
# Pipeline Behaviour
########################################
def test_quad_pipeline_preserves_names_order_lengths_and_strengths(write_lattice):
    """
    Full conversion should preserve SAD QUAD names, order, lengths, and strengths.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        QUAD        QF          = (L = 0.5 K1 = 0.1)
                    QD          = (L = 0.5 K1 = -0.1)
                    QZ          = (L = 0.5 K1 = 0.0);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START QF QD QZ END);
        """,
        filename = "quad_pipeline_preserves_names_order_lengths_strengths.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "qf", "qd", "qz", "end"], (
        "Converted line should preserve SAD element names and order.")
    for quad_name, expected_k1 in [
            ("qf", 0.2),
            ("qd", -0.2),
            ("qz", 0.0)]:
        assert isinstance(line[quad_name], xt.Quadrupole), (
            f"Converted element '{quad_name}' should be an Xsuite Quadrupole.")
        assert line[quad_name].length == pytest.approx(0.5), (
            f"Converted quadrupole '{quad_name}' should preserve length.")
        assert line[quad_name].k1 == pytest.approx(expected_k1), (
            f"Converted quadrupole '{quad_name}' should preserve integrated "
            "strength divided by length.")

def test_quad_pipeline_preserves_offsets_and_rotation(write_lattice):
    """
    Full conversion should preserve SAD QUAD DX, DY, and ROTATE fields.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        QUAD        QOFF        = (
            L       = 0.5
            K1      = 0.1
            DX      = 1.0E-3
            DY      = -2.0E-3
            ROTATE  = 0.125
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START QOFF END);
        """,
        filename = "quad_pipeline_preserves_offsets_rotation.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "qoff", "end"], (
        "Converted line should preserve offset quadrupole order.")
    assert isinstance(line["qoff"], xt.Quadrupole), (
        "Converted offset quadrupole should be an Xsuite Quadrupole.")
    assert line["qoff"].shift_x == pytest.approx(1.0E-3), (
        "Converted quadrupole should preserve SAD DX as Xsuite shift_x.")
    assert line["qoff"].shift_y == pytest.approx(-2.0E-3), (
        "Converted quadrupole should preserve SAD DY as Xsuite shift_y.")
    assert line["qoff"].rot_s_rad == pytest.approx(-0.125), (
        "Converted quadrupole should apply the SAD-to-Xsuite rotation sign.")

################################################################################
# Physics Equivalence
################################################################################
########################################
# Default Quadrupole Optics
########################################
@pytest.mark.parametrize(
    "k1l",
    [-0.1, 0.0, 0.1])
def test_quad_conversion_matches_sad_twiss(write_lattice, tmp_path, k1l):
    """
    Converted SAD QUAD elements should match SAD 4D Twiss propagation.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        QUAD        TEST_QUAD   = (L = 0.5 K1 = {k1l});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_QUAD END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"quad_twiss_k1l_{k1l:+.3f}.sad")

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
            sad_lattice_path    = str(lattice_path),
            output_directory    = "N/A",
            _verbose            = False,
            _test_mode          = True)

        tw_xs = line.twiss4d(
            _continue_if_lost   = True,
            start               = xt.START,
            end                 = xt.END,
            betx                = 1,
            bety                = 1)

        sad_values = {
            "s":     tw_sad["s", "END"],
            "betx":  tw_sad["betx", "END"],
            "bety":  tw_sad["bety", "END"],
            "alfx":  tw_sad["alfx", "END"],
            "alfy":  tw_sad["alfy", "END"],
            "zeta":  tw_sad["zeta", "END"],
            "delta": tw_sad["delta", "END"],
        }
        xs_values = {
            "s":     tw_xs["s", "end"],
            "betx":  tw_xs["betx", "end"],
            "bety":  tw_xs["bety", "end"],
            "alfx":  tw_xs["alfx", "end"],
            "alfy":  tw_xs["alfy", "end"],
            "zeta":  tw_xs["zeta", "end"],
            "delta": tw_xs["delta", "end"],
        }
    finally:
        os.chdir(cwd)

    _assert_quad_twiss_matches_sad(
        test_name       = "test_quad_conversion_matches_sad_twiss",
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xs_values,
        parameters      = {"k1l": k1l})

########################################
# Tracking With Particle Offsets
########################################
@pytest.mark.parametrize(
    "k1l",
    [-0.1, 0.0, 0.1])
def test_quad_conversion_matches_sad_tracking_for_transverse_offsets(
        write_lattice,
        tmp_path,
        k1l):
    """
    Converted SAD QUAD elements should match SAD tracking for offset particles.
    """
    x_init     = np.array([0.0, 1E-4, 0.0, 0.0, 1E-4])
    px_init    = np.array([0.0, 0.0, 1E-4, 0.0, -1E-4])
    y_init     = np.array([0.0, 0.0, 0.0, 1E-4, -1E-4])
    py_init    = np.array([0.0, 0.0, 0.0, 1E-4, 1E-4])
    zeta_init  = np.zeros_like(x_init)
    delta_init = np.zeros_like(x_init)

    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        QUAD        TEST_QUAD   = (L = 0.5 K1 = {k1l});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_QUAD END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"quad_tracking_k1l_{k1l:+.3f}.sad")

        sad_particles = track_sad(
            lattice_filepath       = lattice_path.name,
            line_name              = "TEST_LINE",
            x_init                 = x_init,
            px_init                = px_init,
            y_init                 = y_init,
            py_init                = py_init,
            zeta_init              = zeta_init,
            delta_init             = delta_init,
            n_turns                = 1,
            rfsw                   = True,
            rad                    = False,
            fluc                   = False,
            radcod                 = False,
            radtaper               = False,
            turn_by_turn_monitor   = False,
            with_progress          = False,
            wall_time              = 30)

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path    = str(lattice_path),
            output_directory    = "N/A",
            _verbose            = False,
            _test_mode          = True)

        xs_particles = xt.Particles(
            "positron",
            p0c     = 1.0E9,
            x       = x_init.copy(),
            px      = px_init.copy(),
            y       = y_init.copy(),
            py      = py_init.copy(),
            zeta    = zeta_init.copy(),
            delta   = delta_init.copy())

        line.track(xs_particles, num_turns = 1)
    finally:
        os.chdir(cwd)

    _assert_quad_tracking_matches_sad(
        test_name               = (
            "test_quad_conversion_matches_sad_tracking_for_transverse_offsets"),
        lattice_text            = lattice_text,
        initial_coordinates     = _quad_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _quad_sad_coordinates(sad_particles),
        xsuite_coordinates      = _quad_xsuite_coordinates(xs_particles),
        parameters              = {"k1l": k1l})

########################################
# Tracking With Element Offsets
########################################
@pytest.mark.parametrize(
    "dx, dy",
    [
        (1.0E-3, 0.0),
        (0.0, -1.0E-3),
        (1.0E-3, -1.0E-3),
    ])
def test_quad_conversion_matches_sad_tracking_for_element_offsets(
        write_lattice,
        tmp_path,
        dx,
        dy):
    """
    Converted offset SAD QUAD elements should match SAD tracking.
    """
    x_init     = np.array([0.0, 1E-4, 0.0, 0.0, 1E-4])
    px_init    = np.array([0.0, 0.0, 1E-4, 0.0, -1E-4])
    y_init     = np.array([0.0, 0.0, 0.0, 1E-4, -1E-4])
    py_init    = np.array([0.0, 0.0, 0.0, 1E-4, 1E-4])
    zeta_init  = np.zeros_like(x_init)
    delta_init = np.zeros_like(x_init)

    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        QUAD        TEST_QUAD   = (
            L       = 0.5
            K1      = 0.1
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_QUAD END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"quad_tracking_dx_{dx:+.3e}_dy_{dy:+.3e}.sad")

        sad_particles = track_sad(
            lattice_filepath       = lattice_path.name,
            line_name              = "TEST_LINE",
            x_init                 = x_init,
            px_init                = px_init,
            y_init                 = y_init,
            py_init                = py_init,
            zeta_init              = zeta_init,
            delta_init             = delta_init,
            n_turns                = 1,
            rfsw                   = True,
            rad                    = False,
            fluc                   = False,
            radcod                 = False,
            radtaper               = False,
            turn_by_turn_monitor   = False,
            with_progress          = False,
            wall_time              = 30)

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path    = str(lattice_path),
            output_directory    = "N/A",
            _verbose            = False,
            _test_mode          = True)

        xs_particles = xt.Particles(
            "positron",
            p0c     = 1.0E9,
            x       = x_init.copy(),
            px      = px_init.copy(),
            y       = y_init.copy(),
            py      = py_init.copy(),
            zeta    = zeta_init.copy(),
            delta   = delta_init.copy())

        line.track(xs_particles, num_turns = 1)
    finally:
        os.chdir(cwd)

    _assert_quad_tracking_matches_sad(
        test_name               = (
            "test_quad_conversion_matches_sad_tracking_for_element_offsets"),
        lattice_text            = lattice_text,
        initial_coordinates     = _quad_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _quad_sad_coordinates(sad_particles),
        xsuite_coordinates      = _quad_xsuite_coordinates(xs_particles),
        parameters              = {"dx": dx, "dy": dy})

########################################
# Tracking With Element Rotations
########################################
@pytest.mark.parametrize(
    "rotation",
    [
        0.125,
        +np.pi / 4 - 0.01,
        +np.pi / 4,
        +np.pi / 4 + 0.01,
        -np.pi / 4 - 0.01,
        -np.pi / 4,
        -np.pi / 4 + 0.01,
    ])
def test_quad_conversion_matches_sad_tracking_for_element_rotation(
        write_lattice,
        tmp_path,
        rotation):
    """
    Converted rotated SAD QUAD elements should match SAD tracking.
    """
    x_init     = np.array([0.0, 1E-4, 0.0, 0.0, 1E-4])
    px_init    = np.array([0.0, 0.0, 1E-4, 0.0, -1E-4])
    y_init     = np.array([0.0, 0.0, 0.0, 1E-4, -1E-4])
    py_init    = np.array([0.0, 0.0, 0.0, 1E-4, 1E-4])
    zeta_init  = np.zeros_like(x_init)
    delta_init = np.zeros_like(x_init)

    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        QUAD        TEST_QUAD   = (
            L       = 0.5
            K1      = 0.1
            ROTATE  = {rotation}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_QUAD END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"quad_tracking_rotate_{rotation:+.6f}.sad")

        sad_particles = track_sad(
            lattice_filepath       = lattice_path.name,
            line_name              = "TEST_LINE",
            x_init                 = x_init,
            px_init                = px_init,
            y_init                 = y_init,
            py_init                = py_init,
            zeta_init              = zeta_init,
            delta_init             = delta_init,
            n_turns                = 1,
            rfsw                   = True,
            rad                    = False,
            fluc                   = False,
            radcod                 = False,
            radtaper               = False,
            turn_by_turn_monitor   = False,
            with_progress          = False,
            wall_time              = 30)

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path    = str(lattice_path),
            output_directory    = "N/A",
            _verbose            = False,
            _test_mode          = True)

        xs_particles = xt.Particles(
            "positron",
            p0c     = 1.0E9,
            x       = x_init.copy(),
            px      = px_init.copy(),
            y       = y_init.copy(),
            py      = py_init.copy(),
            zeta    = zeta_init.copy(),
            delta   = delta_init.copy())

        line.track(xs_particles, num_turns = 1)
    finally:
        os.chdir(cwd)

    _assert_quad_tracking_matches_sad(
        test_name               = (
            "test_quad_conversion_matches_sad_tracking_for_element_rotation"),
        lattice_text            = lattice_text,
        initial_coordinates     = _quad_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _quad_sad_coordinates(sad_particles),
        xsuite_coordinates      = _quad_xsuite_coordinates(xs_particles),
        parameters              = {"rotation": rotation},
        notes                   = [
            "If the sign of px/py differs, check the SAD-to-Xsuite skew "
            "quadrupole sign convention.",
            "If x/y response is swapped, check the rotation convention.",
            "For +/- pi/4, SAD2XS currently rewrites the rotated quadrupole "
            "as a pure skew quadrupole.",
        ])
