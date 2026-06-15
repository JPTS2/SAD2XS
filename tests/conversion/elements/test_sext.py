"""
================================================================================
Tests for SAD SEXT conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-12
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

from sad2xs.converter._004_element_converter import convert_sextupoles
from sad2xs.sad_helpers import track_sad
from tests.support.config import (
    DELTA_PX_ATOL,
    DELTA_PX_RTOL,
    DELTA_PY_ATOL,
    DELTA_PY_RTOL,
    DELTA_S_ATOL,
    DELTA_S_RTOL,
    DELTA_X_ATOL,
    DELTA_X_RTOL,
    DELTA_Y_ATOL,
    DELTA_Y_RTOL)
from tests.support.diagnostics import (
    diagnostic_report_path,
    write_tracking_failure_report,
    write_twiss_failure_report)
from tests.support.sad_helpers import twiss_sad

################################################################################
# Diagnostic Helpers
################################################################################
SEXT_ARTIFACT_CATEGORY = "conversion/elements/sext"

def _sext_tracking_tolerances():
    """
    Return coordinate tolerances used by sextupole tracking comparisons.
    """
    return {
        "x":  (DELTA_X_ATOL, DELTA_X_RTOL),
        "px": (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":  (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py": (DELTA_PY_ATOL, DELTA_PY_RTOL),
    }

def _sext_twiss_tolerances():
    """
    Return coordinate tolerances used by sextupole Twiss comparisons.
    """
    return {
        "s":     (1E-9, 1E-5),
        "betx":  (1E-9, 1E-5),
        "bety":  (1E-9, 1E-5),
        "alfx":  (1E-9, 1E-5),
        "alfy":  (1E-9, 1E-5),
    }

def _sext_initial_coordinates(
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

def _sext_sad_coordinates(sad_particles):
    """
    Pack SAD tracking coordinates for diagnostic reports.
    """
    return {
        "x":  sad_particles["x"],
        "px": sad_particles["px"],
        "y":  sad_particles["y"],
        "py": sad_particles["py"],
    }

def _sext_xsuite_coordinates(xs_particles):
    """
    Pack Xsuite tracking coordinates for diagnostic reports.
    """
    return {
        "x":  xs_particles.x,
        "px": xs_particles.px,
        "y":  xs_particles.y,
        "py": xs_particles.py,
    }

def _assert_sext_tracking_matches_sad(
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
    tolerances = _sext_tracking_tolerances()
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
            category        = SEXT_ARTIFACT_CATEGORY,
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
            f"Converted sextupole tracking should match SAD. "
            f"Failed coordinates: {failed_coordinates}. "
            f"Diagnostic report: {report_path}")

def _assert_sext_twiss_matches_sad(
        test_name,
        lattice_text,
        sad_values,
        xsuite_values,
        parameters,
        notes = None):
    """
    Assert Twiss equivalence and write a Markdown report on failure.
    """
    tolerances = _sext_twiss_tolerances()
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
            category        = SEXT_ARTIFACT_CATEGORY,
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
            f"Converted sextupole Twiss should match SAD. "
            f"Failed values: {failed_values}. "
            f"Diagnostic report: {report_path}")

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
@pytest.mark.parametrize(
    "k2l, expected_k2",
    [
        (0.0, 0.0),
        (0.1, 0.2),
        (-0.1, -0.2),
    ])
def test_sext_converter_creates_xsuite_sextupole(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        k2l,
        expected_k2):
    """
    Parsed SAD SEXT elements should become Xsuite Sextupole elements.
    """
    convert_sextupoles(
        parsed_elements = parsed_elements(
            element_type        = "sext",
            element_name        = "test_sext",
            element_variables   = {"l": 0.5, "k2": k2l}),
        environment     = xsuite_environment)

    sext = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_sext",
        element_type    = xt.Sextupole)

    assert sext.length == pytest.approx(0.5), (
        "Converted sextupole should preserve the parsed SAD length.")
    assert sext.k2 == pytest.approx(expected_k2), (
        "Converted sextupole k2 should equal parsed integrated K2 divided by "
        "length.")
    assert sext.k2s == pytest.approx(0.0), (
        "Unrotated SAD sextupoles should have zero skew sextupole strength.")

def test_sext_converter_creates_all_sextupoles(
        xsuite_environment,
        assert_environment_element):
    """
    Multiple parsed SAD SEXT elements should all be converted.
    """
    parsed_elements = {
        "sext": {
            "sf": {"l": 0.5, "k2": 0.1},
            "sd": {"l": 0.5, "k2": -0.1},
            "sz": {"l": 0.5, "k2": 0.0},
        },
    }

    convert_sextupoles(
        parsed_elements = parsed_elements,
        environment     = xsuite_environment)

    assert set(xsuite_environment.element_dict) == {"sf", "sd", "sz"}, (
        "All parsed SAD SEXT elements should be present in the environment.")
    for sext_name, expected_k2 in [
            ("sf", 0.2),
            ("sd", -0.2),
            ("sz", 0.0)]:
        sext = assert_environment_element(
            environment     = xsuite_environment,
            element_name    = sext_name,
            element_type    = xt.Sextupole)
        assert sext.length == pytest.approx(0.5), (
            f"Converted sextupole '{sext_name}' should preserve length.")
        assert sext.k2 == pytest.approx(expected_k2), (
            f"Converted sextupole '{sext_name}' should preserve integrated "
            "strength divided by length.")

########################################
# Defaults and Symbolic Parameters
########################################
def test_sext_converter_defaults_missing_k2_to_zero(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    A SAD SEXT without K2 should convert as a zero-strength sextupole.
    """
    convert_sextupoles(
        parsed_elements = parsed_elements(
            element_type        = "sext",
            element_name        = "test_sext",
            element_variables   = {"l": 0.5}),
        environment     = xsuite_environment)

    sext = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_sext",
        element_type    = xt.Sextupole)

    assert sext.k2 == pytest.approx(0.0), (
        "Missing SAD SEXT K2 should convert to zero sextupole strength.")

def test_sext_converter_preserves_symbolic_strength_with_environment_variable(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Symbolic SAD SEXT strengths should resolve through Xsuite environment vars.
    """
    xsuite_environment["ks"] = 0.1

    convert_sextupoles(
        parsed_elements = parsed_elements(
            element_type        = "sext",
            element_name        = "test_sext",
            element_variables   = {"l": 0.5, "k2": "ks"}),
        environment     = xsuite_environment)

    sext = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_sext",
        element_type    = xt.Sextupole)

    assert xsuite_environment["k2_test_sext"] == pytest.approx(0.2), (
        "Symbolic integrated K2 should be converted to a resolved k2 variable.")
    assert sext.k2 == pytest.approx(0.2), (
        "Converted sextupole should use the resolved symbolic k2 variable.")

########################################
# Offsets and Rotations
########################################
def test_sext_converter_preserves_offsets_and_rotation(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    SAD SEXT DX, DY, and ROTATE should map to Xsuite element fields.
    """
    convert_sextupoles(
        parsed_elements = parsed_elements(
            element_type        = "sext",
            element_name        = "test_sext",
            element_variables   = {
                "l":        0.5,
                "k2":       0.1,
                "dx":       1.0E-3,
                "dy":       -2.0E-3,
                "rotate":   0.125,
            }),
        environment     = xsuite_environment)

    sext = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_sext",
        element_type    = xt.Sextupole)

    assert sext.shift_x == pytest.approx(1.0E-3), (
        "Converted sextupole should preserve SAD DX as Xsuite shift_x.")
    assert sext.shift_y == pytest.approx(-2.0E-3), (
        "Converted sextupole should preserve SAD DY as Xsuite shift_y.")
    assert sext.rot_s_rad == pytest.approx(-0.125), (
        "Converted sextupole should apply the SAD-to-Xsuite rotation sign.")

########################################
# Special Rotation Mapping
########################################
@pytest.mark.parametrize(
    "sad_rotation, expected_k2, expected_k2s",
    [
        (+np.pi / 6, 0.0, +0.2),
        (-np.pi / 6, 0.0, -0.2),
    ])
def test_sext_converter_maps_30_degree_rotations_to_skew_strength(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        sad_rotation,
        expected_k2,
        expected_k2s):
    """
    30 degree SAD SEXT rotations should convert to pure skew sextupoles.
    """
    convert_sextupoles(
        parsed_elements = parsed_elements(
            element_type        = "sext",
            element_name        = "test_sext",
            element_variables   = {
                "l":        0.5,
                "k2":       0.1,
                "rotate":   sad_rotation,
            }),
        environment     = xsuite_environment)

    sext = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_sext",
        element_type    = xt.Sextupole)

    assert sext.k2 == pytest.approx(expected_k2), (
        "30 degree rotated sextupoles should not retain normal k2 strength.")
    assert sext.k2s == pytest.approx(expected_k2s), (
        "30 degree rotated sextupoles should map integrated K2 to k2s.")
    assert sext.rot_s_rad == pytest.approx(0.0), (
        "Pure skew sextupole conversion should remove the residual rotation.")

@pytest.mark.parametrize(
    "sad_rotation",
    [
        +np.pi / 6 - 0.01,
        +np.pi / 6 + 0.01,
        -np.pi / 6 - 0.01,
        -np.pi / 6 + 0.01,
    ])
def test_sext_converter_near_30_degree_rotations_remain_explicit_rotations(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        sad_rotation):
    """
    Near-30-degree SAD SEXT rotations should not trigger the skew shortcut.
    """
    convert_sextupoles(
        parsed_elements = parsed_elements(
            element_type        = "sext",
            element_name        = "test_sext",
            element_variables   = {
                "l":        0.5,
                "k2":       0.1,
                "rotate":   sad_rotation,
            }),
        environment     = xsuite_environment)

    sext = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_sext",
        element_type    = xt.Sextupole)

    assert sext.k2 == pytest.approx(0.2), (
        "Near-30-degree rotations should retain normal sextupole strength.")
    assert sext.k2s == pytest.approx(0.0), (
        "Near-30-degree rotations should not be rewritten as pure skew.")
    assert sext.rot_s_rad == pytest.approx(-sad_rotation), (
        "Near-30-degree rotations should remain explicit Xsuite rotations.")

def test_sext_converter_supports_symbolic_length_and_strength(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Symbolic SAD SEXT lengths and strengths should resolve through Xsuite vars.
    """
    xsuite_environment["ls"] = 0.5
    xsuite_environment["ks"] = 0.1

    convert_sextupoles(
        parsed_elements = parsed_elements(
            element_type        = "sext",
            element_name        = "test_sext",
            element_variables   = {"l": "ls", "k2": "ks"}),
        environment     = xsuite_environment)

    sext = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_sext",
        element_type    = xt.Sextupole)

    assert sext.length == pytest.approx(0.5), (
        "Converted sextupole should resolve the SAD symbolic length.")
    assert sext.k2 == pytest.approx(0.2), (
        "Converted sextupole should resolve symbolic integrated K2 divided "
        "by symbolic length.")

########################################
# Thin Element Behaviour
########################################
@pytest.mark.parametrize(
    "element_variables",
    [
        {"k2": 0.1},
        {"l": 0.0, "k2": 0.1},
    ])
def test_sext_converter_converts_thin_sextupole_to_multipole(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables):
    """
    Thin SAD SEXT elements should become active Xsuite Multipole kicks.
    """
    convert_sextupoles(
        parsed_elements = parsed_elements(
            element_type        = "sext",
            element_name        = "test_sext",
            element_variables   = element_variables),
        environment     = xsuite_environment)

    multipole = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_sext",
        element_type    = xt.Multipole)

    assert multipole.knl[2] == pytest.approx(0.1), (
        "Thin SEXT K2 should be preserved as integrated knl[2].")

########################################
# Pipeline Behaviour
########################################
def test_sext_pipeline_preserves_names_order_lengths_and_strengths(write_lattice):
    """
    Full conversion should preserve SAD SEXT names, order, lengths, and strengths.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        SEXT        SF          = (L = 0.5 K2 = 0.1)
                    SD          = (L = 0.5 K2 = -0.1)
                    SZ          = (L = 0.5 K2 = 0.0);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START SF SD SZ END);
        """,
        filename = "sext_pipeline_preserves_names_order_lengths_strengths.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "sf", "sd", "sz", "end"], (
        "Converted line should preserve SAD element names and order.")
    for sext_name, expected_k2 in [
            ("sf", 0.2),
            ("sd", -0.2),
            ("sz", 0.0)]:
        assert isinstance(line[sext_name], xt.Sextupole), (
            f"Converted element '{sext_name}' should be an Xsuite Sextupole.")
        assert line[sext_name].length == pytest.approx(0.5), (
            f"Converted sextupole '{sext_name}' should preserve length.")
        assert line[sext_name].k2 == pytest.approx(expected_k2), (
            f"Converted sextupole '{sext_name}' should preserve integrated "
            "strength divided by length.")

def test_sext_pipeline_preserves_offsets_and_rotation(write_lattice):
    """
    Full conversion should preserve SAD SEXT DX, DY, and ROTATE fields.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        SEXT        SOFF        = (
            L       = 0.5
            K2      = 0.1
            DX      = 1.0E-3
            DY      = -2.0E-3
            ROTATE  = 0.125
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START SOFF END);
        """,
        filename = "sext_pipeline_preserves_offsets_rotation.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "soff", "end"], (
        "Converted line should preserve offset sextupole order.")
    assert isinstance(line["soff"], xt.Sextupole), (
        "Converted offset sextupole should be an Xsuite Sextupole.")
    assert line["soff"].shift_x == pytest.approx(1.0E-3), (
        "Converted sextupole should preserve SAD DX as Xsuite shift_x.")
    assert line["soff"].shift_y == pytest.approx(-2.0E-3), (
        "Converted sextupole should preserve SAD DY as Xsuite shift_y.")
    assert line["soff"].rot_s_rad == pytest.approx(-0.125), (
        "Converted sextupole should apply the SAD-to-Xsuite rotation sign.")

################################################################################
# Physics Equivalence
################################################################################
########################################
# Default Sextupole Optics
########################################
@pytest.mark.parametrize(
    "k2l",
    [-0.1, 0.0, 0.1])
def test_sext_conversion_matches_sad_twiss(write_lattice, tmp_path, k2l):
    """
    Converted SAD SEXT elements should match SAD 4D Twiss propagation.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        SEXT        TEST_SEXT   = (L = 0.5 K2 = {k2l});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_SEXT END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"sext_twiss_k2l_{k2l:+.3f}.sad")

        tw_sad = twiss_sad(
            lattice_filename        = lattice_path.name,
            line_name               = "TEST_LINE",
            method                  = "4d",
            closed                  = False,
            reverse_element_order   = False,
            reverse_bend_direction  = False,
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
        }
        xs_values = {
            "s":     tw_xs["s", "end"],
            "betx":  tw_xs["betx", "end"],
            "bety":  tw_xs["bety", "end"],
            "alfx":  tw_xs["alfx", "end"],
            "alfy":  tw_xs["alfy", "end"],
        }
    finally:
        os.chdir(cwd)

    _assert_sext_twiss_matches_sad(
        test_name       = "test_sext_conversion_matches_sad_twiss",
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xs_values,
        parameters      = {"k2l": k2l})

########################################
# Tracking With Particle Offsets
########################################
@pytest.mark.parametrize(
    "k2l",
    [-0.1, 0.0, 0.1])
def test_sext_conversion_matches_sad_tracking_for_transverse_offsets(
        write_lattice,
        tmp_path,
        k2l):
    """
    Converted SAD SEXT elements should match SAD tracking for offset particles.
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

        SEXT        TEST_SEXT   = (L = 0.5 K2 = {k2l});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_SEXT END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"sext_tracking_k2l_{k2l:+.3f}.sad")

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
            rfsw                   = False,
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
            p0c     = 1.0E9,
            mass0   = xt.ELECTRON_MASS_EV,
            q0      = 1,
            x       = x_init.copy(),
            px      = px_init.copy(),
            y       = y_init.copy(),
            py      = py_init.copy(),
            zeta    = zeta_init.copy(),
            delta   = delta_init.copy())

        line.track(xs_particles, num_turns = 1)
    finally:
        os.chdir(cwd)

    _assert_sext_tracking_matches_sad(
        test_name               = (
            "test_sext_conversion_matches_sad_tracking_for_transverse_offsets"),
        lattice_text            = lattice_text,
        initial_coordinates     = _sext_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _sext_sad_coordinates(sad_particles),
        xsuite_coordinates      = _sext_xsuite_coordinates(xs_particles),
        parameters              = {"k2l": k2l})

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
def test_sext_conversion_matches_sad_tracking_for_element_offsets(
        write_lattice,
        tmp_path,
        dx,
        dy):
    """
    Converted offset SAD SEXT elements should match SAD tracking.
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

        SEXT        TEST_SEXT   = (
            L       = 0.5
            K2      = 0.1
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_SEXT END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"sext_tracking_dx_{dx:+.3e}_dy_{dy:+.3e}.sad")

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
            rfsw                   = False,
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
            p0c     = 1.0E9,
            mass0   = xt.ELECTRON_MASS_EV,
            q0      = 1,
            x       = x_init.copy(),
            px      = px_init.copy(),
            y       = y_init.copy(),
            py      = py_init.copy(),
            zeta    = zeta_init.copy(),
            delta   = delta_init.copy())

        line.track(xs_particles, num_turns = 1)
    finally:
        os.chdir(cwd)

    _assert_sext_tracking_matches_sad(
        test_name               = (
            "test_sext_conversion_matches_sad_tracking_for_element_offsets"),
        lattice_text            = lattice_text,
        initial_coordinates     = _sext_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _sext_sad_coordinates(sad_particles),
        xsuite_coordinates      = _sext_xsuite_coordinates(xs_particles),
        parameters              = {"dx": dx, "dy": dy})

########################################
# Tracking With Element Rotations
########################################
@pytest.mark.parametrize(
    "rotation",
    [
        0.125,
        +np.pi / 6 - 0.01,
        +np.pi / 6,
        +np.pi / 6 + 0.01,
        -np.pi / 6 - 0.01,
        -np.pi / 6,
        -np.pi / 6 + 0.01,
    ])
def test_sext_conversion_matches_sad_tracking_for_element_rotation(
        write_lattice,
        tmp_path,
        rotation):
    """
    Converted rotated SAD SEXT elements should match SAD tracking.
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

        SEXT        TEST_SEXT   = (
            L       = 0.5
            K2      = 0.1
            ROTATE  = {rotation}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_SEXT END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"sext_tracking_rotate_{rotation:+.6f}.sad")

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
            rfsw                   = False,
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
            p0c     = 1.0E9,
            mass0   = xt.ELECTRON_MASS_EV,
            q0      = 1,
            x       = x_init.copy(),
            px      = px_init.copy(),
            y       = y_init.copy(),
            py      = py_init.copy(),
            zeta    = zeta_init.copy(),
            delta   = delta_init.copy())

        line.track(xs_particles, num_turns = 1)
    finally:
        os.chdir(cwd)

    _assert_sext_tracking_matches_sad(
        test_name               = (
            "test_sext_conversion_matches_sad_tracking_for_element_rotation"),
        lattice_text            = lattice_text,
        initial_coordinates     = _sext_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _sext_sad_coordinates(sad_particles),
        xsuite_coordinates      = _sext_xsuite_coordinates(xs_particles),
        parameters              = {"rotation": rotation},
        notes                   = [
            "If signs differ only at +/- pi/6, check the SAD-to-Xsuite skew "
            "sextupole convention.",
            "For +/- pi/6, SAD2XS currently rewrites the rotated sextupole "
            "as a pure skew sextupole.",
        ])
