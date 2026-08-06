"""
================================================================================
Tests for SAD corrector conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-29
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
    DELTA_DELTA_ATOL,
    DELTA_DELTA_RTOL,
    DELTA_S_ATOL,
    DELTA_S_RTOL,
    DELTA_PX_ATOL,
    DELTA_PX_RTOL,
    DELTA_PY_ATOL,
    DELTA_PY_RTOL,
    DELTA_X_ATOL,
    DELTA_X_RTOL,
    DELTA_Y_ATOL,
    DELTA_Y_RTOL,
    DELTA_ZETA_ATOL,
    DELTA_ZETA_RTOL)
from tests.support.diagnostics import (
    diagnostic_report_path,
    write_twiss_failure_report,
    write_tracking_failure_report)
from tests.support.tracking_helpers import track_xsuite_particles
from sad2xs.sad_helpers import twiss_sad

################################################################################
# Shared Tracking Coordinates
################################################################################
def _standard_five_particle_offsets():
    """
    Standard 5-particle probe reused by several tracking comparisons: a
    null particle plus one offset each in x, px, y, py.
    """
    x_init     = np.array([0.0, 1E-4, 0.0, 0.0, 1E-4])
    px_init    = np.array([0.0, 0.0, 1E-4, 0.0, -1E-4])
    y_init     = np.array([0.0, 0.0, 0.0, 1E-4, -1E-4])
    py_init    = np.array([0.0, 0.0, 0.0, 1E-4, 1E-4])
    zeta_init  = np.zeros_like(x_init)
    delta_init = np.zeros_like(x_init)
    return x_init, px_init, y_init, py_init, zeta_init, delta_init

################################################################################
# Diagnostic Helpers
################################################################################
CORRECTOR_ARTIFACT_CATEGORY = "conversion/elements/corrector"

def _corrector_tracking_tolerances():
    """
    Return coordinate tolerances used by corrector tracking comparisons.
    """
    return {
        "x":     (DELTA_X_ATOL, DELTA_X_RTOL),
        "px":    (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":     (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py":    (DELTA_PY_ATOL, DELTA_PY_RTOL),
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
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
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
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
        "zeta":  twiss["zeta", element_name],
        "delta": twiss["delta", element_name],
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
        "x":     sad_particles["x"],
        "px":    sad_particles["px"],
        "y":     sad_particles["y"],
        "py":    sad_particles["py"],
        "zeta":  sad_particles["zeta"],
        "delta": sad_particles["delta"],
    }

def _corrector_xsuite_coordinates(xs_particles):
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
            ("cv", 0.2),
            ("cz", 0.0)]:
        corrector = assert_environment_element(
            environment     = xsuite_environment,
            element_name    = corr_name,
            element_type    = xt.Bend)
        assert corrector.length == pytest.approx(0.5), (
            f"Converted corrector `{corr_name}` should preserve length.")
        assert corrector.k0 == pytest.approx(expected_k0), (
            f"Converted corrector `{corr_name}` should preserve integrated "
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
@pytest.mark.parametrize(
    "sad_rotation, expected_rotation, expected_sign",
    [
        (0.0,        0.0,       +1),
        (+np.pi,     0.0,       -1),
        (-np.pi,     0.0,       -1),
        (+np.pi / 2, np.pi / 2, -1),
        (-np.pi / 2, np.pi / 2, +1),
        (0.125,     -0.125,     +1),
    ])
def test_corrector_converter_canonicalizes_dipole_rotations(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element,
        sad_rotation,
        expected_rotation,
        expected_sign):
    """
    SAD corrector special rotations should map to canonical Xsuite Bend fields.
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
                "rotate":   sad_rotation,
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
    assert corrector.k0 == pytest.approx(expected_sign * 0.2), (
        "Canonicalized corrector k0 should include the dipole field sign.")
    assert corrector.rot_s_rad == pytest.approx(expected_rotation), (
        "Converted corrector should use the canonical Xsuite dipole rotation.")

@pytest.mark.parametrize(
    "sad_rotation, expected_rotation, expected_sign",
    [
        (0.0,        0.0,       +1),
        (+np.pi,     0.0,       -1),
        (-np.pi,     0.0,       -1),
        (+np.pi / 2, np.pi / 2, -1),
        (-np.pi / 2, np.pi / 2, +1),
        (0.125,     -0.125,     +1),
    ])
def test_corrector_converter_canonicalizes_thin_dipole_rotations(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element,
        sad_rotation,
        expected_rotation,
        expected_sign):
    """
    Thin SAD corrector rotations should canonicalize the dipole kick.
    """
    convert_correctors(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_corr",
            element_variables   = {
                "angle":    0.0,
                "k0":       0.1,
                "k1":       0.2,
                "rotate":   sad_rotation,
            }),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    ele = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_corr",
        element_type    = xt.Multipole)

    assert ele.knl[0] == pytest.approx(expected_sign * 0.1), (
        "Thin corrector knl[0] should include the canonical dipole field sign.")
    assert ele.knl[1] == pytest.approx(0.2), (
        "Thin corrector K1 should not be flipped by dipole canonicalization.")
    assert ele.rot_s_rad == pytest.approx(expected_rotation), (
        "Thin corrector should use the canonical Xsuite dipole rotation.")

def test_corrector_converter_without_length_creates_thin_multipole(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    A corrector with K0 and K1 but no L should convert to a thin Multipole.
    Both K0 and K1 are integrated strengths — both must appear in knl.
    """
    convert_correctors(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_corr",
            element_variables   = {"angle": 0.0, "k0": 0.1, "k1": 0.2}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    ele = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_corr",
        element_type    = xt.Multipole)
    assert ele.knl[0] == pytest.approx(0.1), (
        "Thin corrector without L should set knl[0] to the K0 value.")
    assert ele.knl[1] == pytest.approx(0.2), (
        "K1 in a thin corrector is integrated — must be preserved as knl[1].")

def test_corrector_converter_without_length_and_zero_kick_installs_multipole(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    A corrector with no L and zero K0/K1 still installs as a Multipole.
    No silent Marker conversions — thin elements are always Multipole.
    """
    convert_correctors(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_corr",
            element_variables   = {"angle": 0.0}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_corr",
        element_type    = xt.Multipole)

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
                    CV          = (L = 0.5 ANGLE = 0.0 K0 = -0.1)
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
            f"Converted element `{corr_name}` should be an Xsuite Bend.")
        assert line[corr_name].length == pytest.approx(0.5), (
            f"Converted corrector `{corr_name}` should preserve length.")
        assert line[corr_name].k0 == pytest.approx(expected_k0), (
            f"Converted corrector `{corr_name}` should preserve integrated "
            "kick divided by length.")

def test_corrector_pipeline_canonicalizes_offsets_and_rotation(write_lattice):
    """
    Full conversion should preserve corrector offsets and canonicalize ROTATE.
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
        filename = "corrector_pipeline_canonicalizes_offsets_rotation.sad")

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
    assert line["coff"].k0 == pytest.approx(-0.2), (
        "Converted corrector k0 should include the canonical dipole field sign.")
    assert line["coff"].rot_s_rad == pytest.approx(np.pi / 2), (
        "Converted corrector should use the canonical Xsuite vertical dipole rotation.")

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
    x_init, px_init, y_init, py_init, zeta_init, delta_init = \
        _standard_five_particle_offsets()

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

        xs_particles = track_xsuite_particles(
            line, x_init, px_init, y_init, py_init, zeta_init, delta_init)
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
    x_init, px_init, y_init, py_init, zeta_init, delta_init = \
        _standard_five_particle_offsets()

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

        xs_particles = track_xsuite_particles(
            line, x_init, px_init, y_init, py_init, zeta_init, delta_init)
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
    x_init, px_init, y_init, py_init, zeta_init, delta_init = \
        _standard_five_particle_offsets()

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

        xs_particles = track_xsuite_particles(
            line, x_init, px_init, y_init, py_init, zeta_init, delta_init)
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
    x_init, px_init, y_init, py_init, zeta_init, delta_init = \
        _standard_five_particle_offsets()

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

        xs_particles = track_xsuite_particles(
            line, x_init, px_init, y_init, py_init, zeta_init, delta_init)
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

################################################################################
# FB1/FB2 soft-edge fringe import (_import_sad_bend_fringes) -- same
# mechanism as test_bend.py's F1/FRINGE section; see docs/reference/sad-behaviour.md
################################################################################
def test_corrector_fringe_import_defaults_on(write_lattice, tmp_path):
    """
    _import_sad_bend_fringes defaults to True -- FB1/FB2/FRINGE on a
    K0-only corrector should populate edge_entry_fint/hgap without needing
    to pass the flag.
    """
    lattice_text = """\
    MOMENTUM    = 1.0 GEV;

    BEND        TEST_CORR   = (
        L       = 0.4
        K0      = 0.03
        FRINGE  = 1
        FB1     = 0.025
        FB2     = 0.018
    );

    MARK        START       = ()
                END         = ();

    LINE        TEST_LINE   = (START TEST_CORR END);
    """
    lattice_path = write_lattice(lattice_text, filename = "corrector_fringe_import_default_on.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    corrector = line["test_corr"]
    assert corrector.edge_entry_fint == pytest.approx(0.025) and corrector.edge_entry_hgap == pytest.approx(1 / 12), (
        "FB1/FB2/FRINGE should be imported by default "
        "(_import_sad_bend_fringes defaults to True).")

def test_corrector_fringe_import_explicit_off(write_lattice, tmp_path):
    """
    With _import_sad_bend_fringes explicitly disabled, FB1/FB2/FRINGE on a
    K0-only corrector should have no effect on the converted xt.Bend --
    edge_entry_fint/hgap stay at Xsuite's own defaults.
    """
    lattice_text = """\
    MOMENTUM    = 1.0 GEV;

    BEND        TEST_CORR   = (
        L       = 0.4
        K0      = 0.03
        FRINGE  = 1
        FB1     = 0.025
        FB2     = 0.018
    );

    MARK        START       = ()
                END         = ();

    LINE        TEST_LINE   = (START TEST_CORR END);
    """
    lattice_path = write_lattice(lattice_text, filename = "corrector_fringe_import_explicit_off.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path            = str(lattice_path),
        output_directory            = "N/A",
        _verbose                    = False,
        _test_mode                  = True,
        _import_sad_bend_fringes    = False)

    corrector = line["test_corr"]
    assert corrector.edge_entry_fint == 0.0 and corrector.edge_entry_hgap == 0.0, (
        "FB1/FB2/FRINGE should be ignored when _import_sad_bend_fringes is "
        "explicitly disabled.")

@pytest.mark.parametrize("fringe, entry_active, exit_active", [
    (0, False, False),
    (-1, True, False),
    (-2, False, True),
    (-3, False, False),
    (-4, False, False),
    (1, True, True),
    (2, True, True),
    (3, True, True)])
def test_corrector_fringe_import_fringe_gates_single_edge(
        write_lattice, tmp_path, fringe, entry_active, exit_active):
    """
    Same grid as test_bend.py's fringe_import_fringe_gates_single_edge,
    for a K0-only corrector -- see docs/reference/sad-behaviour.md.
    """
    lattice_text = f"""\
    MOMENTUM    = 1.0 GEV;

    BEND        TEST_CORR   = (
        L       = 0.5
        K0      = 0.05
        FB1     = 0.15
        FB2     = 0.08
        FRINGE  = {fringe}
    );

    MARK        START       = ()
                END         = ();

    LINE        TEST_LINE   = (START TEST_CORR END);
    """
    lattice_path = write_lattice(
        lattice_text, filename = f"corrector_fringe_import_fringe_{fringe}.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path            = str(lattice_path),
        output_directory            = "N/A",
        _verbose                    = False,
        _test_mode                  = True,
        _import_sad_bend_fringes    = True)

    corrector = line["test_corr"]
    if entry_active:
        assert corrector.edge_entry_fint != 0.0, (
            f"FRINGE={fringe} should activate the entry edge fringe.")
    else:
        assert corrector.edge_entry_fint == 0.0 and corrector.edge_entry_hgap == 0.0, (
            f"FRINGE={fringe} should leave the entry edge at Xsuite's own "
            "defaults.")
    if exit_active:
        assert corrector.edge_exit_fint != 0.0, (
            f"FRINGE={fringe} should activate the exit edge fringe.")
    else:
        assert corrector.edge_exit_fint == 0.0 and corrector.edge_exit_hgap == 0.0, (
            f"FRINGE={fringe} should leave the exit edge at Xsuite's own "
            "defaults.")

def test_corrector_fringe_import_matches_sad_on_momentum(write_lattice, tmp_path):
    """
    With _import_sad_bend_fringes=True, on-momentum (delta=0) tracking
    through a converted K0-only corrector should match SAD closely.
    """
    L, K0, FB1, FB2 = 0.4, 0.03, 0.025, 0.018
    y0 = 0.002
    x_init      = np.array([0.0])
    px_init     = np.array([0.0])
    y_init      = np.array([y0])
    py_init     = np.array([0.0])
    zeta_init   = np.array([0.0])
    delta_init  = np.array([0.0])

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_CORR   = (
            L       = {L}
            K0      = {K0}
            FRINGE  = 1
            FB1     = {FB1}
            FB2     = {FB2}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_CORR END);
        """
        lattice_path = write_lattice(
            lattice_text, filename = "corrector_fringe_import_on_momentum.sad")

        sad_particles = track_sad(
            lattice_filepath    = lattice_path.name,
            line_name           = "TEST_LINE",
            x_init               = x_init,
            px_init              = px_init,
            y_init               = y_init,
            py_init              = py_init,
            zeta_init            = zeta_init,
            delta_init           = delta_init,
            n_turns              = 1,
            rfsw                 = False,
            with_progress        = False)

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path            = str(lattice_path),
            output_directory            = "N/A",
            _verbose                    = False,
            _test_mode                  = True,
            _import_sad_bend_fringes    = True)

        xs_particles = track_xsuite_particles(
            line, x_init, px_init, y_init, py_init, zeta_init, delta_init)
    finally:
        os.chdir(cwd)

    np.testing.assert_allclose(
        xs_particles.py, sad_particles["py"], rtol = 1E-3, atol = 1E-12,
        err_msg = (
            "On-momentum, the fh=FB1/12, FB2/12 closed form should "
            "reproduce SAD's corrector fringe kick to a fraction of a "
            "percent."))

@pytest.mark.parametrize("delta", [0.03, -0.03])
def test_corrector_fringe_import_matches_sad_off_momentum(write_lattice, tmp_path, delta):
    """
    Off-momentum, the imported K0-only fringe matches SAD to 1e-4 relative.

    The corrector counterpart of
    `test_bend_fringe_import_matches_sad_off_momentum` in `test_bend.py`.
    """
    L, K0, FB1, FB2 = 0.4, 0.03, 0.025, 0.018
    y0 = 0.002
    x_init      = np.array([0.0])
    px_init     = np.array([0.0])
    y_init      = np.array([y0])
    py_init     = np.array([0.0])
    zeta_init   = np.array([0.0])
    delta_init  = np.array([delta])

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_CORR   = (
            L       = {L}
            K0      = {K0}
            FRINGE  = 1
            FB1     = {FB1}
            FB2     = {FB2}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_CORR END);
        """
        lattice_path = write_lattice(
            lattice_text, filename = f"corrector_fringe_import_off_momentum_{delta:+.3f}.sad")

        sad_particles = track_sad(
            lattice_filepath    = lattice_path.name,
            line_name           = "TEST_LINE",
            x_init               = x_init,
            px_init              = px_init,
            y_init               = y_init,
            py_init              = py_init,
            zeta_init            = zeta_init,
            delta_init           = delta_init,
            n_turns              = 1,
            rfsw                 = False,
            with_progress        = False)

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path            = str(lattice_path),
            output_directory            = "N/A",
            _verbose                    = False,
            _test_mode                  = True,
            _import_sad_bend_fringes    = True)

        xs_particles = track_xsuite_particles(
            line, x_init, px_init, y_init, py_init, zeta_init, delta_init)
    finally:
        os.chdir(cwd)

    # Measured agreement at this geometry: 2.4e-5, near-constant in delta
    # (2.7e-5 at delta = +-0.05). What remains is a small offset, not a
    # momentum-scaling error, so the bound does not need to grow with delta.
    np.testing.assert_allclose(
        xs_particles.py, sad_particles["py"], rtol = 1E-4, atol = 1E-12,
        err_msg = (
            f"Off-momentum (delta={delta}) corrector fringe import should "
            "match SAD to 1e-4 relative. A larger residual means Xsuite's "
            "native fringe momentum-scaling has regressed."))
