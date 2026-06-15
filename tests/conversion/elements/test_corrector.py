"""
================================================================================
Tests for SAD corrector conversion
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

from sad2xs.converter._004_element_converter import convert_correctors
from sad2xs.sad_helpers import track_sad
from tests.support.config import (
    DELTA_S_ATOL,
    DELTA_S_RTOL,
    DELTA_PX_ATOL,
    DELTA_PX_RTOL,
    DELTA_PY_ATOL,
    DELTA_PY_RTOL,
    DELTA_X_ATOL,
    DELTA_X_RTOL,
    DELTA_Y_ATOL,
    DELTA_Y_RTOL)
from tests.support.diagnostics import (
    diagnostic_report_path,
    write_twiss_failure_report,
    write_tracking_failure_report)
from sad2xs.sad_helpers import twiss_sad

################################################################################
# Diagnostic Helpers
################################################################################
CORRECTOR_ARTIFACT_CATEGORY = "conversion/elements/corrector"

def _corrector_tracking_tolerances():
    """
    Return coordinate tolerances used by corrector tracking comparisons.
    """
    return {
        "x":  (DELTA_X_ATOL, DELTA_X_RTOL),
        "px": (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":  (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py": (DELTA_PY_ATOL, DELTA_PY_RTOL),
    }

def _corrector_twiss_tolerances():
    """
    Return tolerances used by corrector optics comparisons.
    """
    return {
        "s":     (DELTA_S_ATOL, DELTA_S_RTOL),
        "x":     (DELTA_X_ATOL, DELTA_X_RTOL),
        "px":    (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":     (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py":    (DELTA_PY_ATOL, DELTA_PY_RTOL),
        "dx":    (DELTA_X_ATOL, DELTA_X_RTOL),
        "dpx":   (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "dy":    (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "dpy":   (DELTA_PY_ATOL, DELTA_PY_RTOL),
        "betx":  (1E-9, 1E-5),
        "bety":  (1E-9, 1E-5),
        "alfx":  (1E-9, 1E-5),
        "alfy":  (1E-9, 1E-5),
    }

def _corrector_twiss_values(twiss, element_name):
    """
    Pack optics values from a Twiss table for diagnostic reports.
    """
    return {
        "s":     twiss["s", element_name],
        "x":     twiss["x", element_name],
        "px":    twiss["px", element_name],
        "y":     twiss["y", element_name],
        "py":    twiss["py", element_name],
        "dx":    twiss["dx", element_name],
        "dpx":   twiss["dpx", element_name],
        "dy":    twiss["dy", element_name],
        "dpy":   twiss["dpy", element_name],
        "betx":  twiss["betx", element_name],
        "bety":  twiss["bety", element_name],
        "alfx":  twiss["alfx", element_name],
        "alfy":  twiss["alfy", element_name],
    }

def _corrector_initial_coordinates(
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

def _corrector_sad_coordinates(sad_particles):
    """
    Pack SAD tracking coordinates for diagnostic reports.
    """
    return {
        "x":  sad_particles["x"],
        "px": sad_particles["px"],
        "y":  sad_particles["y"],
        "py": sad_particles["py"],
    }

def _corrector_xsuite_coordinates(xs_particles):
    """
    Pack Xsuite tracking coordinates for diagnostic reports.
    """
    return {
        "x":  xs_particles.x,
        "px": xs_particles.px,
        "y":  xs_particles.y,
        "py": xs_particles.py,
    }

def _assert_corrector_tracking_matches_sad(
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
    tolerances = _corrector_tracking_tolerances()
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
            category        = CORRECTOR_ARTIFACT_CATEGORY,
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
            f"Converted corrector tracking should match SAD. "
            f"Failed coordinates: {failed_coordinates}. "
            f"Diagnostic report: {report_path}")

def _assert_corrector_twiss_matches_sad(
        test_name,
        lattice_text,
        sad_values,
        xsuite_values,
        parameters,
        notes = None):
    """
    Assert optics equivalence and write a Markdown report on failure.
    """
    tolerances = _corrector_twiss_tolerances()
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
            category        = CORRECTOR_ARTIFACT_CATEGORY,
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
            f"Converted corrector optics should match SAD. "
            f"Failed values: {failed_values}. "
            f"Diagnostic report: {report_path}")

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
@pytest.mark.parametrize(
    "k0l, expected_k0",
    [
        (0.0, 0.0),
        (0.1, 0.2),
        (-0.1, -0.2),
    ])
def test_corrector_converter_creates_xsuite_bend_corrector(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element,
        k0l,
        expected_k0):
    """
    SAD zero-angle BEND correctors should become Xsuite Bend elements.
    """
    convert_correctors(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_corr",
            element_variables   = {"l": 0.5, "angle": 0.0, "k0": k0l}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    corrector = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_corr",
        element_type    = xt.Bend)

    assert corrector.length == pytest.approx(0.5), (
        "Converted corrector should preserve the parsed SAD length.")
    assert corrector.k0 == pytest.approx(expected_k0), (
        "Converted corrector k0 should equal parsed integrated K0 divided by "
        "length.")
    assert corrector.k1 == pytest.approx(0.0), (
        "Converted correctors should not introduce quadrupole strength.")
    assert corrector.edge_entry_angle == pytest.approx(0.0), (
        "Converted correctors should not introduce entrance edge focusing.")
    assert corrector.edge_exit_angle == pytest.approx(0.0), (
        "Converted correctors should not introduce exit edge focusing.")

def test_corrector_converter_treats_missing_angle_as_corrector(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    SAD BEND entries without ANGLE should be treated as correctors.
    """
    convert_correctors(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_corr",
            element_variables   = {"l": 0.5, "k0": 0.1}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    corrector = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_corr",
        element_type    = xt.Bend)

    assert corrector.k0 == pytest.approx(0.2), (
        "Missing ANGLE corrector should preserve integrated K0 divided by "
        "length.")

def test_corrector_converter_creates_all_correctors(
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    Multiple parsed SAD correctors should all be converted.
    """
    parsed_elements = {
        "bend": {
            "ch": {"l": 0.5, "angle": 0.0, "k0": 0.1},
            "cv": {"l": 0.5, "angle": 0.0, "k0": -0.1, "rotate": np.pi / 2},
            "cz": {"l": 0.5, "angle": 0.0, "k0": 0.0},
        },
    }

    convert_correctors(
        parsed_elements = parsed_elements,
        environment     = xsuite_environment,
        config          = sad2xs_config)

    assert set(xsuite_environment.element_dict) == {"ch", "cv", "cz"}, (
        "All parsed SAD correctors should be present in the environment.")
    for corr_name, expected_k0 in [
            ("ch", 0.2),
            ("cv", -0.2),
            ("cz", 0.0)]:
        corrector = assert_environment_element(
            environment     = xsuite_environment,
            element_name    = corr_name,
            element_type    = xt.Bend)
        assert corrector.length == pytest.approx(0.5), (
            f"Converted corrector '{corr_name}' should preserve length.")
        assert corrector.k0 == pytest.approx(expected_k0), (
            f"Converted corrector '{corr_name}' should preserve integrated "
            "kick divided by length.")

########################################
# Defaults, Symbolics, and Errors
########################################
def test_corrector_converter_defaults_missing_k0_to_zero(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    A SAD corrector without K0 should convert as a zero-kick corrector.
    """
    convert_correctors(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_corr",
            element_variables   = {"l": 0.5, "angle": 0.0}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    corrector = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_corr",
        element_type    = xt.Bend)

    assert corrector.k0 == pytest.approx(0.0), (
        "Missing SAD corrector K0 should convert to zero bend strength.")

def test_corrector_converter_preserves_symbolic_strength_with_environment_variable(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    Symbolic SAD corrector strengths should resolve through Xsuite env vars.
    """
    xsuite_environment["kc"] = 0.1

    convert_correctors(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_corr",
            element_variables   = {"l": 0.5, "angle": 0.0, "k0": "kc"}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    corrector = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_corr",
        element_type    = xt.Bend)

    assert xsuite_environment["k0_test_corr"] == pytest.approx(0.2), (
        "Symbolic integrated K0 should be converted to a resolved k0 variable.")
    assert corrector.k0 == pytest.approx(0.2), (
        "Converted corrector should use the resolved symbolic k0 variable.")

def test_corrector_converter_supports_symbolic_length_and_strength(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    Symbolic SAD corrector lengths and strengths should resolve through vars.
    """
    xsuite_environment["lc"] = 0.5
    xsuite_environment["kc"] = 0.1

    convert_correctors(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_corr",
            element_variables   = {"l": "lc", "angle": 0.0, "k0": "kc"}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    corrector = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_corr",
        element_type    = xt.Bend)

    assert corrector.length == pytest.approx(0.5), (
        "Converted corrector should resolve the SAD symbolic length.")
    assert corrector.k0 == pytest.approx(0.2), (
        "Converted corrector should resolve symbolic integrated K0 divided "
        "by symbolic length.")

########################################
# Offsets and Rotations
########################################
def test_corrector_converter_preserves_offsets_and_rotation(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    SAD corrector DX, DY, and ROTATE should map to Xsuite element fields.
    """
    convert_correctors(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_corr",
            element_variables   = {
                "l":        0.5,
                "angle":    0.0,
                "k0":       0.1,
                "dx":       1.0E-3,
                "dy":       -2.0E-3,
                "rotate":   np.pi / 2,
            }),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    corrector = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_corr",
        element_type    = xt.Bend)

    assert corrector.shift_x == pytest.approx(1.0E-3), (
        "Converted corrector should preserve SAD DX as Xsuite shift_x.")
    assert corrector.shift_y == pytest.approx(-2.0E-3), (
        "Converted corrector should preserve SAD DY as Xsuite shift_y.")
    assert corrector.rot_s_rad == pytest.approx(-np.pi / 2), (
        "Converted corrector should apply the SAD-to-Xsuite rotation sign.")

def test_corrector_converter_missing_length_installs_marker(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    Current missing-length corrector policy installs a marker.
    """
    convert_correctors(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_corr",
            element_variables   = {"angle": 0.0, "k0": 0.1}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_corr",
        element_type    = xt.Marker)

########################################
# Pipeline Behaviour
########################################
def test_corrector_pipeline_preserves_names_order_lengths_and_kicks(write_lattice):
    """
    Full conversion should preserve corrector names, order, lengths, and kicks.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        CH          = (L = 0.5 ANGLE = 0.0 K0 = 0.1)
                    CV          = (L = 0.5 ANGLE = 0.0 K0 = -0.1 ROTATE = 90 DEG)
                    CZ          = (L = 0.5 ANGLE = 0.0 K0 = 0.0);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START CH CV CZ END);
        """,
        filename = "corrector_pipeline_preserves_names_order_lengths_kicks.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "ch", "cv", "cz", "end"], (
        "Converted line should preserve SAD corrector names and order.")
    for corr_name, expected_k0 in [
            ("ch", 0.2),
            ("cv", -0.2),
            ("cz", 0.0)]:
        assert isinstance(line[corr_name], xt.Bend), (
            f"Converted element '{corr_name}' should be an Xsuite Bend.")
        assert line[corr_name].length == pytest.approx(0.5), (
            f"Converted corrector '{corr_name}' should preserve length.")
        assert line[corr_name].k0 == pytest.approx(expected_k0), (
            f"Converted corrector '{corr_name}' should preserve integrated "
            "kick divided by length.")

def test_corrector_pipeline_preserves_offsets_and_rotation(write_lattice):
    """
    Full conversion should preserve corrector DX, DY, and ROTATE fields.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        COFF        = (
            L       = 0.5
            ANGLE   = 0.0
            K0      = 0.1
            DX      = 1.0E-3
            DY      = -2.0E-3
            ROTATE  = 90 DEG
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START COFF END);
        """,
        filename = "corrector_pipeline_preserves_offsets_rotation.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "coff", "end"], (
        "Converted line should preserve offset corrector order.")
    assert isinstance(line["coff"], xt.Bend), (
        "Converted offset corrector should be an Xsuite Bend.")
    assert line["coff"].shift_x == pytest.approx(1.0E-3), (
        "Converted corrector should preserve SAD DX as Xsuite shift_x.")
    assert line["coff"].shift_y == pytest.approx(-2.0E-3), (
        "Converted corrector should preserve SAD DY as Xsuite shift_y.")
    assert line["coff"].rot_s_rad == pytest.approx(-np.pi / 2), (
        "Converted corrector should apply the SAD-to-Xsuite rotation sign.")

################################################################################
# Physics Equivalence
################################################################################
########################################
# Default Kick Optics
########################################
@pytest.mark.parametrize(
    "k0l",
    [-0.1, 0.0, 0.1])
def test_corrector_conversion_matches_sad_twiss_for_horizontal_kicks(
        write_lattice,
        tmp_path,
        k0l):
    """
    Converted horizontal SAD correctors should match SAD optics and dispersion.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_CORR   = (L = 0.5 ANGLE = 0.0 K0 = {k0l});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_CORR END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"corrector_twiss_hkick_k0l_{k0l:+.3f}.sad")

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

        tw_xs = line.twiss4d(
            _continue_if_lost   = True,
            start               = xt.START,
            end                 = xt.END,
            betx                = 1,
            bety                = 1)

        sad_values = _corrector_twiss_values(tw_sad, "END")
        xsuite_values = _corrector_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_corrector_twiss_matches_sad(
        test_name       = (
            "test_corrector_conversion_matches_sad_twiss_for_horizontal_kicks"),
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {"k0l": k0l},
        notes           = [
            "Corrector optics coverage includes orbit and dispersion columns.",
        ])

########################################
# Thin Kick Optics
########################################
def test_corrector_conversion_matches_sad_twiss_for_thin_kick(
        write_lattice,
        tmp_path):
    """
    Converted thin SAD correctors should match SAD optics and dispersion.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = """\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_CORR   = (L = 0.0 ANGLE = 0.0 K0 = 0.1);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_CORR END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = "corrector_twiss_thin_k0l.sad")

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

        tw_xs = line.twiss4d(
            _continue_if_lost   = True,
            start               = xt.START,
            end                 = xt.END,
            betx                = 1,
            bety                = 1)

        sad_values = _corrector_twiss_values(tw_sad, "END")
        xsuite_values = _corrector_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_corrector_twiss_matches_sad(
        test_name       = (
            "test_corrector_conversion_matches_sad_twiss_for_thin_kick"),
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {"length": 0.0, "k0l": 0.1},
        notes           = [
            "Thin corrector coverage should lock down the SAD-to-Xsuite "
            "representation for integrated K0 without finite length.",
        ])

########################################
# Rotation Optics
########################################
@pytest.mark.parametrize(
    "rotation",
    [np.pi / 2, -np.pi / 2])
def test_corrector_conversion_matches_sad_twiss_for_rotated_kicks(
        write_lattice,
        tmp_path,
        rotation):
    """
    Converted rotated SAD correctors should match SAD optics and dispersion.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_CORR   = (
            L       = 0.5
            ANGLE   = 0.0
            K0      = 0.1
            ROTATE  = {rotation}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_CORR END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"corrector_twiss_rotate_{rotation:+.6f}.sad")

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

        tw_xs = line.twiss4d(
            _continue_if_lost   = True,
            start               = xt.START,
            end                 = xt.END,
            betx                = 1,
            bety                = 1)

        sad_values = _corrector_twiss_values(tw_sad, "END")
        xsuite_values = _corrector_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_corrector_twiss_matches_sad(
        test_name       = (
            "test_corrector_conversion_matches_sad_twiss_for_rotated_kicks"),
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {"rotation": rotation},
        notes           = [
            "Corrector rotations are represented as rotated Xsuite Bend "
            "elements with zero bend angle and non-zero k0.",
            "Optics coverage includes orbit and dispersion columns.",
        ])

########################################
# Offset Optics
########################################
@pytest.mark.parametrize(
    "dx, dy",
    [
        (1.0E-3, 0.0),
        (0.0, -1.0E-3),
        (1.0E-3, -1.0E-3),
    ])
def test_corrector_conversion_matches_sad_twiss_for_element_offsets(
        write_lattice,
        tmp_path,
        dx,
        dy):
    """
    Converted offset SAD correctors should match SAD optics and dispersion.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_CORR   = (
            L       = 0.5
            ANGLE   = 0.0
            K0      = 0.1
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_CORR END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"corrector_twiss_dx_{dx:+.3e}_dy_{dy:+.3e}.sad")

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

        tw_xs = line.twiss4d(
            _continue_if_lost   = True,
            start               = xt.START,
            end                 = xt.END,
            betx                = 1,
            bety                = 1)

        sad_values = _corrector_twiss_values(tw_sad, "END")
        xsuite_values = _corrector_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_corrector_twiss_matches_sad(
        test_name       = (
            "test_corrector_conversion_matches_sad_twiss_for_element_offsets"),
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {"dx": dx, "dy": dy},
        notes           = [
            "Offset corrector optics coverage includes orbit and dispersion "
            "columns.",
        ])

########################################
# Default Kick Tracking
########################################
@pytest.mark.parametrize(
    "k0l",
    [-0.1, 0.0, 0.1])
def test_corrector_conversion_matches_sad_tracking_for_horizontal_kicks(
        write_lattice,
        tmp_path,
        k0l):
    """
    Converted horizontal SAD correctors should match SAD tracking.
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

        BEND        TEST_CORR   = (L = 0.5 ANGLE = 0.0 K0 = {k0l});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_CORR END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"corrector_tracking_hkick_k0l_{k0l:+.3f}.sad")

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

    _assert_corrector_tracking_matches_sad(
        test_name               = (
            "test_corrector_conversion_matches_sad_tracking_for_horizontal_kicks"),
        lattice_text            = lattice_text,
        initial_coordinates     = _corrector_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _corrector_sad_coordinates(sad_particles),
        xsuite_coordinates      = _corrector_xsuite_coordinates(xs_particles),
        parameters              = {"k0l": k0l})

########################################
# Thin Kick Tracking
########################################
def test_corrector_conversion_matches_sad_tracking_for_thin_kick(
        write_lattice,
        tmp_path):
    """
    Converted thin SAD correctors should match SAD tracking.
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
        lattice_text = """\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_CORR   = (L = 0.0 ANGLE = 0.0 K0 = 0.1);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_CORR END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = "corrector_tracking_thin_k0l.sad")

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

    _assert_corrector_tracking_matches_sad(
        test_name               = (
            "test_corrector_conversion_matches_sad_tracking_for_thin_kick"),
        lattice_text            = lattice_text,
        initial_coordinates     = _corrector_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _corrector_sad_coordinates(sad_particles),
        xsuite_coordinates      = _corrector_xsuite_coordinates(xs_particles),
        parameters              = {"length": 0.0, "k0l": 0.1},
        notes                   = [
            "Thin corrector tracking should match SAD before the "
            "representation is accepted as production behaviour.",
        ])

########################################
# Rotation Tracking
########################################
@pytest.mark.parametrize(
    "rotation",
    [np.pi / 2, -np.pi / 2])
def test_corrector_conversion_matches_sad_tracking_for_rotated_kicks(
        write_lattice,
        tmp_path,
        rotation):
    """
    Converted rotated SAD correctors should match SAD tracking.
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

        BEND        TEST_CORR   = (
            L       = 0.5
            ANGLE   = 0.0
            K0      = 0.1
            ROTATE  = {rotation}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_CORR END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"corrector_tracking_rotate_{rotation:+.6f}.sad")

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

    _assert_corrector_tracking_matches_sad(
        test_name               = (
            "test_corrector_conversion_matches_sad_tracking_for_rotated_kicks"),
        lattice_text            = lattice_text,
        initial_coordinates     = _corrector_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _corrector_sad_coordinates(sad_particles),
        xsuite_coordinates      = _corrector_xsuite_coordinates(xs_particles),
        parameters              = {"rotation": rotation},
        notes                   = [
            "Corrector rotations are represented as rotated Xsuite Bend "
            "elements with zero bend angle and non-zero k0.",
        ])

########################################
# Offset Tracking
########################################
@pytest.mark.parametrize(
    "dx, dy",
    [
        (1.0E-3, 0.0),
        (0.0, -1.0E-3),
        (1.0E-3, -1.0E-3),
    ])
def test_corrector_conversion_matches_sad_tracking_for_element_offsets(
        write_lattice,
        tmp_path,
        dx,
        dy):
    """
    Converted offset SAD correctors should match SAD tracking.
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

        BEND        TEST_CORR   = (
            L       = 0.5
            ANGLE   = 0.0
            K0      = 0.1
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_CORR END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"corrector_tracking_dx_{dx:+.3e}_dy_{dy:+.3e}.sad")

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

    _assert_corrector_tracking_matches_sad(
        test_name               = (
            "test_corrector_conversion_matches_sad_tracking_for_element_offsets"),
        lattice_text            = lattice_text,
        initial_coordinates     = _corrector_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _corrector_sad_coordinates(sad_particles),
        xsuite_coordinates      = _corrector_xsuite_coordinates(xs_particles),
        parameters              = {"dx": dx, "dy": dy})
