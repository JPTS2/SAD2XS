"""
================================================================================
Tests for SAD MULT conversion
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
from sad2xs.converter._004_element_converter import convert_multipoles
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
MULT_ARTIFACT_CATEGORY = "conversion/elements/mult"

def _mult_config(simplify = False):
    """
    Return a quiet config with explicit multipole simplification control.
    """
    return Config(
        _verbose            = False,
        SIMPLIFY_MULTIPOLES = simplify)

def _mult_tracking_tolerances():
    """
    Return coordinate tolerances used by multipole tracking comparisons.
    """
    return {
        "x":     (DELTA_X_ATOL, DELTA_X_RTOL),
        "px":    (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":     (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py":    (DELTA_PY_ATOL, DELTA_PY_RTOL),
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
    }

def _mult_twiss_tolerances():
    """
    Return tolerances used by multipole optics comparisons.
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

def _mult_twiss_values(twiss, element_name):
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

def _mult_initial_coordinates(
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

def _mult_sad_coordinates(sad_particles):
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

def _mult_xsuite_coordinates(xs_particles):
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

def _assert_mult_tracking_matches_sad(
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
    tolerances = _mult_tracking_tolerances()
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
            category        = MULT_ARTIFACT_CATEGORY,
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
            f"Converted multipole tracking should match SAD. "
            f"Failed coordinates: {failed_coordinates}. "
            f"Diagnostic report: {report_path}")

def _assert_mult_twiss_matches_sad(
        test_name,
        lattice_text,
        sad_values,
        xsuite_values,
        parameters,
        notes = None):
    """
    Assert optics equivalence and write a Markdown report on failure.
    """
    tolerances = _mult_twiss_tolerances()
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
            category        = MULT_ARTIFACT_CATEGORY,
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
            f"Converted multipole optics should match SAD. "
            f"Failed values: {failed_values}. "
            f"Diagnostic report: {report_path}")

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
def test_mult_converter_creates_xsuite_multipole(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Parsed SAD MULT elements should become Xsuite Multipole elements.
    """
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type        = "mult",
            element_name        = "test_mult",
            element_variables   = {
                "l":    0.5,
                "k0":   0.01,
                "k1":   0.02,
                "k2":   0.03,
                "sk1":  -0.04,
            }),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = _mult_config(simplify = False))

    multipole = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_mult",
        element_type    = xt.Multipole)

    assert multipole.length == pytest.approx(0.5), (
        "Converted MULT should preserve the parsed SAD length.")
    assert multipole.knl[0] == pytest.approx(0.01), (
        "Converted MULT should preserve integrated K0 as knl[0].")
    assert multipole.knl[1] == pytest.approx(0.02), (
        "Converted MULT should preserve integrated K1 as knl[1].")
    assert multipole.knl[2] == pytest.approx(0.03), (
        "Converted MULT should preserve integrated K2 as knl[2].")
    assert multipole.ksl[1] == pytest.approx(-0.04), (
        "Converted MULT should preserve integrated SK1 as ksl[1].")

def test_mult_converter_creates_all_multipoles(
        xsuite_environment,
        assert_environment_element):
    """
    Multiple parsed SAD MULT elements should all be converted.
    """
    parsed_elements = {
        "mult": {
            "m1": {"l": 0.5, "k1": 0.1, "k2": 0.02},
            "m2": {"l": 0.5, "sk1": 0.1, "sk2": -0.02},
            "m3": {"l": 0.5, "k3": 0.1, "sk3": 0.02},
        },
    }

    convert_multipoles(
        parsed_elements              = parsed_elements,
        environment                  = xsuite_environment,
        user_multipole_replacements  = None,
        config                       = _mult_config(simplify = False))

    assert set(xsuite_environment.element_dict) == {"m1", "m2", "m3"}, (
        "All parsed SAD MULT elements should be present in the environment.")
    for mult_name in ["m1", "m2", "m3"]:
        assert_environment_element(
            environment     = xsuite_environment,
            element_name    = mult_name,
            element_type    = xt.Multipole)

########################################
# Thin Element Behaviour
########################################
@pytest.mark.parametrize(
    "element_variables, expected_knl",
    [
        ({"k1": 0.1}, [0.0, 0.1]),
        ({"l": 0.0, "k1": 0.1}, [0.0, 0.1]),
        ({"k0": 0.1, "k2": 0.2}, [0.1, 0.0, 0.2]),
    ])
def test_mult_converter_preserves_thin_multipoles_as_active_multipoles(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables,
        expected_knl):
    """
    Thin SAD MULT elements should remain active Xsuite Multipole kicks.
    """
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type        = "mult",
            element_name        = "test_mult",
            element_variables   = element_variables),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = _mult_config(simplify = False))

    multipole = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_mult",
        element_type    = xt.Multipole)

    assert multipole.length == pytest.approx(0.0), (
        "Thin MULT elements should have zero Xsuite length.")
    for order, expected_value in enumerate(expected_knl):
        assert multipole.knl[order] == pytest.approx(expected_value), (
            f"Thin MULT should preserve integrated K{order} as knl[{order}].")

########################################
# Offsets and Rotations
########################################
def test_mult_converter_preserves_offsets_and_rotation(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    SAD MULT DX, DY, and ROTATE should map to Xsuite element fields.
    """
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type        = "mult",
            element_name        = "test_mult",
            element_variables   = {
                "l":        0.5,
                "k1":       0.1,
                "k2":       0.02,
                "dx":       1.0E-3,
                "dy":       -2.0E-3,
                "rotate":   0.125,
            }),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = _mult_config(simplify = False))

    multipole = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_mult",
        element_type    = xt.Multipole)

    assert multipole.shift_x == pytest.approx(1.0E-3), (
        "Converted MULT should preserve SAD DX as Xsuite shift_x.")
    assert multipole.shift_y == pytest.approx(-2.0E-3), (
        "Converted MULT should preserve SAD DY as Xsuite shift_y.")
    assert multipole.rot_s_rad == pytest.approx(-0.125), (
        "Converted MULT should apply the SAD-to-Xsuite rotation sign.")

########################################
# Simplification Behaviour
########################################
@pytest.mark.parametrize(
    "element_variables, element_type, attr_name, expected_value",
    [
        ({"l": 0.5, "k1": 0.1}, xt.Quadrupole, "k1", 0.2),
        ({"l": 0.5, "k2": 0.1}, xt.Sextupole, "k2", 0.2),
        ({"l": 0.5, "k3": 0.1}, xt.Octupole, "k3", 0.2),
    ])
def test_mult_converter_simplifies_single_order_multipoles(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables,
        element_type,
        attr_name,
        expected_value):
    """
    Simple finite SAD MULT elements may simplify to equivalent thick elements.
    """
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type        = "mult",
            element_name        = "test_mult",
            element_variables   = element_variables),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = _mult_config(simplify = True))

    element = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_mult",
        element_type    = element_type)

    assert getattr(element, attr_name) == pytest.approx(expected_value), (
        "Simplified MULT strength should equal integrated strength divided by "
        "length.")

def test_mult_converter_keeps_combined_orders_as_multipole(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    SAD MULT elements with multiple powered orders should remain Multipoles.
    """
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type        = "mult",
            element_name        = "test_mult",
            element_variables   = {"l": 0.5, "k1": 0.1, "k2": 0.02}),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = _mult_config(simplify = True))

    multipole = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_mult",
        element_type    = xt.Multipole)

    assert multipole.knl[1] == pytest.approx(0.1), (
        "Combined-order MULT should preserve integrated K1.")
    assert multipole.knl[2] == pytest.approx(0.02), (
        "Combined-order MULT should preserve integrated K2.")

########################################
# User Replacement Behaviour
########################################
@pytest.mark.parametrize(
    "replacement, element_variables, element_type, attr_name, expected_value",
    [
        ("Quadrupole", {"l": 0.5, "k1": 0.1}, xt.Quadrupole, "k1", 0.2),
        ("Sextupole", {"l": 0.5, "k2": 0.1}, xt.Sextupole, "k2", 0.2),
        ("Octupole", {"l": 0.5, "k3": 0.1}, xt.Octupole, "k3", 0.2),
        ("Bend", {"l": 0.5, "k0": 0.1}, xt.Bend, "k0", 0.2),
    ])
def test_mult_converter_applies_user_replacements(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        replacement,
        element_variables,
        element_type,
        attr_name,
        expected_value):
    """
    User replacement rules should convert finite MULT elements explicitly.
    """
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type        = "mult",
            element_name        = "test_mult",
            element_variables   = element_variables),
        environment                 = xsuite_environment,
        user_multipole_replacements = {"test": replacement},
        config                      = _mult_config(simplify = False))

    element = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_mult",
        element_type    = element_type)

    assert getattr(element, attr_name) == pytest.approx(expected_value), (
        f"{replacement} replacement should divide integrated strength by length.")

@pytest.mark.parametrize(
    "element_variables",
    [
        {"k1": 0.01},
        {"l": 0.0, "k1": 0.01},
    ])
def test_mult_converter_rejects_thin_user_replacements(
        parsed_elements,
        xsuite_environment,
        element_variables):
    """
    Thin SAD MULT elements cannot be replaced by thick element types.
    """
    with pytest.raises(ValueError, match = "Cannot replace thin SAD multipole"):
        convert_multipoles(
            parsed_elements = parsed_elements(
                element_type        = "mult",
                element_name        = "test_mult",
                element_variables   = element_variables),
            environment                 = xsuite_environment,
            user_multipole_replacements = {"test": "Quadrupole"},
            config                      = _mult_config(simplify = False))

########################################
# Pipeline Behaviour
########################################
def test_mult_pipeline_preserves_combined_multipole(write_lattice):
    """
    Full conversion should preserve combined-order SAD MULT elements.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MULT        TEST_MULT   = (
            L       = 0.5
            K1      = 0.1
            K2      = 0.02
            SK1     = -0.03
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_MULT END);
        """,
        filename = "mult_pipeline_preserves_combined_multipole.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "test_mult", "end"], (
        "Converted line should preserve the SAD MULT element name and order.")
    assert isinstance(line["test_mult"], xt.Multipole), (
        "Combined-order SAD MULT should remain an Xsuite Multipole.")
    assert line["test_mult"].length == pytest.approx(0.5), (
        "Converted MULT should preserve length.")
    assert line["test_mult"].knl[1] == pytest.approx(0.1), (
        "Converted MULT should preserve K1 as integrated knl[1].")
    assert line["test_mult"].knl[2] == pytest.approx(0.02), (
        "Converted MULT should preserve K2 as integrated knl[2].")
    assert line["test_mult"].ksl[1] == pytest.approx(-0.03), (
        "Converted MULT should preserve SK1 as integrated ksl[1].")

################################################################################
# Physics Equivalence
################################################################################
########################################
# Default Multipole Optics
########################################
def test_mult_conversion_matches_sad_twiss_for_combined_orders(
        write_lattice,
        tmp_path):
    """
    Converted combined-order SAD MULT elements should match SAD optics.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = """\
        MOMENTUM    = 1.0 GEV;

        MULT        TEST_MULT   = (
            L       = 0.5
            K1      = 0.1
            K2      = 0.02
            SK1     = -0.03
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_MULT END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = "mult_twiss_combined_orders.sad")

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

        sad_values = _mult_twiss_values(tw_sad, "END")
        xsuite_values = _mult_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_mult_twiss_matches_sad(
        test_name       = (
            "test_mult_conversion_matches_sad_twiss_for_combined_orders"),
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {"k1l": 0.1, "k2l": 0.02, "sk1l": -0.03},
        notes           = [
            "Combined-order MULT optics coverage checks normal and skew "
            "components in a true Xsuite Multipole.",
        ])

########################################
# Single-Order Optics (isolates which order, if any, disagrees with SAD)
########################################
@pytest.mark.parametrize(
    "order_name, mult_definition, parameters",
    [
        ("k0",  "K0 = 0.05",  {"k0l": 0.05}),
        ("sk0", "SK0 = 0.05", {"sk0l": 0.05}),
        ("k1",  "K1 = 0.1",   {"k1l": 0.1}),
        ("sk1", "SK1 = -0.03", {"sk1l": -0.03}),
        ("k2",  "K2 = 0.02",  {"k2l": 0.02}),
        ("sk2", "SK2 = 0.02", {"sk2l": 0.02}),
        ("k3",  "K3 = 5.0",   {"k3l": 5.0}),
        ("sk3", "SK3 = 5.0",  {"sk3l": 5.0}),
    ])
def test_mult_conversion_matches_sad_twiss_for_single_order(
        write_lattice,
        tmp_path,
        order_name,
        mult_definition,
        parameters):
    """
    Converted single-order SAD MULT elements should match SAD optics.

    Isolates each order individually so a single-order discrepancy is not
    masked or amplified by combining it with other orders. See
    tests/README.md and docs/design-decisions.md for what this found.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        MULT        TEST_MULT   = (
            L       = 0.5
            {mult_definition}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_MULT END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"mult_twiss_single_order_{order_name}.sad")

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

        sad_values = _mult_twiss_values(tw_sad, "END")
        xsuite_values = _mult_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_mult_twiss_matches_sad(
        test_name       = (
            "test_mult_conversion_matches_sad_twiss_for_single_order"),
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = parameters,
        notes           = [
            "Single-order MULT optics coverage — each order (K0-K3, SK0-SK3) "
            "in isolation, no combination with any other order.",
        ])

########################################
# Tracking With Particle Offsets
########################################
def test_mult_conversion_matches_sad_tracking_for_combined_orders(
        write_lattice,
        tmp_path):
    """
    Converted combined-order SAD MULT elements should match SAD tracking.
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
        lattice_text = """\
        MOMENTUM    = 1.0 GEV;

        MULT        TEST_MULT   = (
            L       = 0.5
            K1      = 0.1
            K2      = 0.02
            SK1     = -0.03
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_MULT END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = "mult_tracking_combined_orders.sad")

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

    _assert_mult_tracking_matches_sad(
        test_name               = (
            "test_mult_conversion_matches_sad_tracking_for_combined_orders"),
        lattice_text            = lattice_text,
        initial_coordinates     = _mult_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _mult_sad_coordinates(sad_particles),
        xsuite_coordinates      = _mult_xsuite_coordinates(xs_particles),
        parameters              = {"k1l": 0.1, "k2l": 0.02, "sk1l": -0.03})

########################################
# Thin Multipole Tracking
########################################
def test_mult_conversion_matches_sad_tracking_for_thin_multipole(
        write_lattice,
        tmp_path):
    """
    Converted thin SAD MULT elements should match SAD tracking.
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
        lattice_text = """\
        MOMENTUM    = 1.0 GEV;

        MULT        TEST_MULT   = (L = 0.0 K1 = 0.1 K2 = 0.02);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_MULT END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = "mult_tracking_thin_multipole.sad")

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

    _assert_mult_tracking_matches_sad(
        test_name               = (
            "test_mult_conversion_matches_sad_tracking_for_thin_multipole"),
        lattice_text            = lattice_text,
        initial_coordinates     = _mult_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _mult_sad_coordinates(sad_particles),
        xsuite_coordinates      = _mult_xsuite_coordinates(xs_particles),
        parameters              = {"length": 0.0, "k1l": 0.1, "k2l": 0.02},
        notes                   = [
            "Thin MULT tracking should remain active and preserve integrated "
            "normal multipole strengths.",
        ])
