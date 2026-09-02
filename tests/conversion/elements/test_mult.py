"""
================================================================================
Tests for SAD MULT conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-08-29
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import logging
import os

import numpy as np
import pytest
import sad2xs as s2x
import xtrack as xt

from sad2xs.config import Config
from sad2xs.converter._004_element_converter import convert_elements, convert_multipoles
from sad2xs.sad_helpers import track_sad, transfer_matrix_sad
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
from tests.support.coupled_optics import (
    edwards_teng_optics_at,
    linear_transfer_matrix_4d)
from tests.support.diagnostics import (
    diagnostic_report_path,
    write_tracking_failure_report,
    write_twiss_failure_report)
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
    x_init     = np.array([0.0, 1E-4, 0.0, 1E-4, -1E-4])
    px_init    = np.array([0.0, 0.0, 1E-4, 0.0, -1E-4])
    y_init     = np.array([0.0, 0.0, 1E-4, 1E-4, -1E-4])
    py_init    = np.array([0.0, 1E-4, 0.0, -1E-4, 1E-4])
    zeta_init  = np.zeros_like(x_init)
    delta_init = np.zeros_like(x_init)
    return x_init, px_init, y_init, py_init, zeta_init, delta_init

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

def _mult_xsuite_twiss_values(twiss, element_name):
    """
    Pack Xsuite optics in SAD's coupled beta/alpha convention.
    """
    edwards_teng = edwards_teng_optics_at(twiss, element_name)
    values = _mult_twiss_values(twiss, element_name)
    for key in ["betx", "bety", "alfx", "alfy"]:
        values[key] = edwards_teng[key]
    return values

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

def test_mult_converter_warns_when_dipole_multipole_simplifies_to_bend(
        xsuite_environment,
        assert_environment_element,
        caplog):
    """
    Auto-simplified K0/SK0 MULT elements should warn about the fringe model.
    """
    caplog.set_level(
        logging.DEBUG,
        logger = "sad2xs.converter._004_element_converter")

    convert_multipoles(
        parsed_elements = {
            "mult": {
                "mx": {"l": 0.5, "k0": 0.05},
                "my": {"l": 0.5, "sk0": 0.05},
            },
        },
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = _mult_config(simplify = True))

    assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "mx",
        element_type    = xt.Bend)
    assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "my",
        element_type    = xt.Bend)

    warnings = [
        record for record in caplog.records
        if "MULT dipole fringe convention" in record.getMessage()]
    assert len(warnings) == 1, (
        "Dipole-only MULT simplification should emit one warning per "
        "conversion, not one warning per element.")
    debug_details = [
        record.getMessage() for record in caplog.records
        if record.levelno == logging.DEBUG
        and "Dipole-only MULT elements" in record.getMessage()]
    assert debug_details == [
        "Dipole-only MULT elements converted to Bend/corrector elements: mx, my"
    ], "Debug logging should name the MULT elements behind the summary warning."

@pytest.mark.parametrize(
    "element_variables, expected_k0, expected_rotation",
    [
        ({"l": 0.5, "k0": 0.1, "rotate": +np.pi / 2}, -0.2, np.pi / 2),
        ({"l": 0.5, "k0": 0.1, "rotate": -np.pi / 2}, +0.2, np.pi / 2),
        ({"l": 0.5, "k0": 0.1, "rotate": +np.pi},     -0.2, 0.0),
        ({"l": 0.5, "sk0": 0.1},                       -0.2, np.pi / 2),
    ])
def test_mult_converter_canonicalizes_auto_simplified_dipole_rotations(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables,
        expected_k0,
        expected_rotation):
    """
    Auto-simplified dipole-only MULT elements should use canonical Bend fields.
    """
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type        = "mult",
            element_name        = "test_mult",
            element_variables   = element_variables),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = _mult_config(simplify = True))

    bend = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_mult",
        element_type    = xt.Bend)

    assert bend.k0 == pytest.approx(expected_k0), (
        "Auto-simplified MULT dipole k0 should include the canonical field sign.")
    assert bend.rot_s_rad == pytest.approx(expected_rotation), (
        "Auto-simplified MULT dipole should use canonical Xsuite rotation.")

@pytest.mark.parametrize(
    "user_multipole_replacements, simplify",
    [
        (None,               True),
        ({"test": "Bend"},   False),
    ])
@pytest.mark.parametrize(
    "element_variables, extra_env_vars, expected_k0, expected_rotation",
    [
        ({"l": 0.5, "k0": "k0_var", "sk0": "sk0_var"},
         {"k0_var": 0.1, "sk0_var": 0.05},
         np.sqrt(0.1**2 + 0.05**2) / 0.5,
         np.arctan2(-0.05, 0.1)),
        ({"l": 0.5, "sk0": "sk0_var", "rotate": "rot_var"},
         {"sk0_var": 0.05, "rot_var": 0.2},
         0.05 / 0.5,
         -0.2 - np.pi / 2),
    ])
def test_mult_converter_combines_deferred_k0_sk0(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables,
        extra_env_vars,
        expected_k0,
        expected_rotation,
        user_multipole_replacements,
        simplify):
    """
    Combined-order and SK0-only dipole-only MULT elements with deferred K0,
    SK0, and/or ROTATE should combine without crashing and resolve to the
    same fields as the equivalent numeric case, for both auto-simplification
    and user Bend replacement.
    """
    for var_name, value in extra_env_vars.items():
        xsuite_environment[var_name] = value

    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type        = "mult",
            element_name        = "test_mult",
            element_variables   = element_variables),
        environment                 = xsuite_environment,
        user_multipole_replacements = user_multipole_replacements,
        config                      = _mult_config(simplify = simplify))

    bend = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_mult",
        element_type    = xt.Bend)

    assert bend.k0 == pytest.approx(expected_k0), (
        "Deferred K0/SK0/ROTATE should resolve to the numeric-equivalent "
        "magnitude.")
    assert bend.rot_s_rad == pytest.approx(expected_rotation), (
        "Deferred K0/SK0/ROTATE should resolve to the numeric-equivalent "
        "rotation.")

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
    "element_variables, expected_k0, expected_rotation",
    [
        ({"l": 0.5, "k0": 0.1, "rotate": +np.pi / 2}, -0.2, np.pi / 2),
        ({"l": 0.5, "k0": 0.1, "rotate": -np.pi / 2}, +0.2, np.pi / 2),
        ({"l": 0.5, "k0": 0.1, "rotate": +np.pi},     -0.2, 0.0),
        ({"l": 0.5, "sk0": 0.1},                       -0.2, np.pi / 2),
    ])
def test_mult_converter_canonicalizes_bend_user_replacement_rotations(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables,
        expected_k0,
        expected_rotation):
    """
    User Bend replacement of dipole-only MULT should use canonical Bend fields.
    """
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type        = "mult",
            element_name        = "test_mult",
            element_variables   = element_variables),
        environment                 = xsuite_environment,
        user_multipole_replacements = {"test": "Bend"},
        config                      = _mult_config(simplify = False))

    bend = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_mult",
        element_type    = xt.Bend)

    assert bend.k0 == pytest.approx(expected_k0), (
        "Bend replacement k0 should include the canonical field sign.")
    assert bend.rot_s_rad == pytest.approx(expected_rotation), (
        "Bend replacement should use canonical Xsuite rotation.")

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

########################################
# RF Handling
########################################
@pytest.mark.parametrize(
    "element_variables",
    [
        {"volt": 1.0E6, "freq": 5.0E8, "phi": 0.0},
        {"l": 0.0, "volt": 1.0E6, "freq": 5.0E8, "k1": 0.2},
    ])
def test_mult_converter_creates_thin_rf_compound(
        parsed_elements,
        xsuite_environment,
        element_variables):
    """
    A thin (L=0) MULT carrying VOLT should convert to a single thin
    Multipole/Cavity pair, regardless of whether Kn is also present.
    """
    xsuite_environment["fshift"] = 0.0

    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type      = "mult",
            element_name      = "test_mult",
            element_variables = element_variables),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = _mult_config())

    assert xsuite_environment.lines["test_mult"].element_names == [
        "test_mult_mult_0", "test_mult_cavi_0"], (
        "Thin RF MULT should produce exactly one Multipole/Cavity pair.")

    multipole = xsuite_environment["test_mult_mult_0"]
    cavity    = xsuite_environment["test_mult_cavi_0"]
    assert isinstance(multipole, xt.Multipole)
    assert isinstance(cavity, xt.Cavity)
    assert cavity.voltage == pytest.approx(1.0E6), (
        "Thin RF MULT should preserve VOLT on the Cavity slice.")
    assert cavity.frequency == pytest.approx(5.0E8), (
        "Thin RF MULT should preserve FREQ on the Cavity slice.")

def test_mult_converter_creates_thick_rf_compound_with_interleaved_slices(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    A thick MULT carrying both K1 and VOLT should slice into
    N_SLICES_MULT_RF interleaved Multipole/Cavity pairs, with per-slice
    knl/length/voltage summing back to the declared totals.
    """
    xsuite_environment["fshift"] = 0.0
    config = _mult_config()

    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type      = "mult",
            element_name      = "test_mult",
            element_variables = {
                "l":    2.0,
                "k1":   0.3,
                "volt": 9.0E5,
                "freq": 5.0E8,
                "phi":  0.0,
            }),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = config)

    n_slices = config.N_SLICES_MULT_RF
    expected_names = []
    for i in range(n_slices):
        expected_names += [f"test_mult_mult_{i}", f"test_mult_cavi_{i}"]
    assert xsuite_environment.lines["test_mult"].element_names == expected_names, (
        "Thick RF MULT should interleave Multipole/Cavity slices in order.")

    total_knl1 = 0.0
    total_len  = 0.0
    total_volt = 0.0
    for i in range(n_slices):
        multipole = assert_environment_element(
            environment  = xsuite_environment,
            element_name = f"test_mult_mult_{i}",
            element_type = xt.Multipole)
        cavity = assert_environment_element(
            environment  = xsuite_environment,
            element_name = f"test_mult_cavi_{i}",
            element_type = xt.Cavity)
        total_knl1 += multipole.knl[1]
        total_len  += multipole.length
        total_volt += cavity.voltage

    assert total_knl1 == pytest.approx(0.3), (
        "Sliced knl[1] should sum back to the declared integrated K1.")
    assert total_len == pytest.approx(2.0), (
        "Sliced Multipole lengths should sum back to the declared length.")
    assert total_volt == pytest.approx(9.0E5), (
        "Sliced Cavity voltages should sum back to the declared VOLT.")

def test_mult_converter_slices_deferred_rf_expressions(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    A thick RF MULT with L/K1/VOLT given as deferred SAD variable
    references (not literals) should slice without raising, using
    divide_integrated_strength's string-expression fallback the same way
    every other strength division in this file does.
    """
    xsuite_environment["fshift"]  = 0.0
    xsuite_environment["l_var"]   = 2.0
    xsuite_environment["k1_var"]  = 0.3
    xsuite_environment["volt_var"] = 9.0E5

    config = _mult_config()
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type      = "mult",
            element_name      = "test_mult",
            element_variables = {
                "l":    "l_var",
                "k1":   "k1_var",
                "volt": "volt_var",
                "freq": 5.0E8,
            }),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = config)

    n_slices  = config.N_SLICES_MULT_RF
    multipole = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_mult_mult_0",
        element_type = xt.Multipole)
    cavity = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_mult_cavi_0",
        element_type = xt.Cavity)
    assert multipole.length == pytest.approx(2.0 / n_slices), (
        "Deferred L should still divide correctly across slices.")
    assert multipole.knl[1] == pytest.approx(0.3 / n_slices), (
        "Deferred K1 should still divide correctly across slices.")
    assert cavity.voltage == pytest.approx(9.0E5 / n_slices), (
        "Deferred VOLT should still divide correctly across slices.")

def test_mult_converter_ignores_user_replacements_for_rf_elements(
        parsed_elements,
        xsuite_environment):
    """
    A MULT matching a user_multipole_replacements entry that also carries
    RF parameters should ignore the requested replacement and take the RF
    path instead, the same way SIMPLIFY_MULTIPOLES is already silently
    superseded by RF parameters -- RF-carrying elements are never a
    candidate for single-purpose-element replacement.
    """
    xsuite_environment["fshift"] = 0.0

    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type      = "mult",
            element_name      = "test_mult",
            element_variables = {"k1": 0.2, "volt": 1.0E5}),
        environment                 = xsuite_environment,
        user_multipole_replacements = {"test_mult": "Quadrupole"},
        config                      = _mult_config())

    assert "test_mult" not in xsuite_environment.element_dict, (
        "RF-carrying MULT should not be replaced with a Quadrupole.")
    assert xsuite_environment.lines["test_mult"].element_names == [
        "test_mult_mult_0", "test_mult_cavi_0"], (
        "RF-carrying MULT should take the RF slicing path, ignoring "
        "user_multipole_replacements.")

def test_mult_converter_rejects_ambiguous_short_rf_length(
        parsed_elements,
        xsuite_environment):
    """
    A concrete nonzero RF-MULT length below the configured precision is
    neither silently treated as thin nor sliced as a thick element.
    """
    xsuite_environment["fshift"] = 0.0

    with pytest.raises(
            ValueError,
            match = r"MULT element 'test_mult'.*below MAGNET_LENGTH_PRECISION"):
        convert_elements(
            parsed_lattice_data = {
                "elements": parsed_elements(
                    element_type      = "mult",
                    element_name      = "test_mult",
                    element_variables = {
                        "l": 1.0E-14, "k1": 0.2,
                        "volt": 1.0E5, "freq": 5.0E8}),
            },
            environment                 = xsuite_environment,
            user_multipole_replacements = None,
            config                      = _mult_config())

def test_mult_converter_uses_harmonic_when_harmonic_is_supplied(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    SAD MULT HARM should map to Xsuite harmonic with zero frequency on the
    sliced Cavity elements, mirroring CAVI's mutual-exclusivity rule.
    """
    xsuite_environment["fshift"] = 0.0

    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type      = "mult",
            element_name      = "test_mult",
            element_variables = {
                "volt": 1.0E6,
                "harm": 400.0,
                "phi":  0.0,
            }),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = _mult_config())

    cavity = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_mult_cavi_0",
        element_type = xt.Cavity)
    assert cavity.harmonic == pytest.approx(400.0), (
        "Harmonic-driven RF MULT should set Xsuite harmonic directly.")
    assert cavity.frequency == pytest.approx(0.0), (
        "Harmonic-driven RF MULT should not also set Xsuite frequency.")

def test_mult_rf_triggers_cavity_focusing_warning(caplog):
    """
    Any Cavity element ending up in the converted line -- including via
    RF-MULT slicing -- should trigger the RF-focusing limitation warning
    exactly once (sad2xs's Xsuite Cavity does not model the transverse
    RF-focusing kick SAD applies whenever RFSW is on and VOLT != 0).
    """
    caplog.set_level(
        logging.WARNING,
        logger = "sad2xs.converter._004_element_converter")

    environment = xt.Environment()
    environment["fshift"] = 0.0

    convert_elements(
        parsed_lattice_data = {
            "elements": {
                "mult": {
                    "test_mult": {
                        "l": 1.0, "k1": 0.1, "volt": 1.0E5, "freq": 5.0E8},
                },
            },
        },
        environment                 = environment,
        user_multipole_replacements = None,
        config                      = _mult_config())

    warnings = [
        record for record in caplog.records
        if "do not model SAD's transverse RF-focusing kick" in record.getMessage()]
    assert len(warnings) == 1, (
        "Any Cavity ending up in the line should trigger exactly one "
        "RF-focusing limitation warning, regardless of how many Cavity "
        "slices were created.")

def test_mult_rf_pipeline_removes_notimplementederror_guard(write_lattice):
    """
    Full conversion of a combined K1+VOLT SAD MULT should succeed end to
    end (the former NotImplementedError guard is gone) and produce
    interleaved Multipole/Cavity elements.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MULT        TEST_MULT   = (
            L       = 1.0
            K1      = 0.3
            VOLT    = 1.0E6
            FREQ    = 5.0E8
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_MULT END);
        """,
        filename = "mult_rf_pipeline_removes_guard.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    mult_names = [n for n in line.element_names if n.startswith("test_mult_mult_")]
    cavi_names = [n for n in line.element_names if n.startswith("test_mult_cavi_")]
    assert len(mult_names) == len(cavi_names) == Config().N_SLICES_MULT_RF, (
        "Pipeline conversion should slice the RF MULT into the configured "
        "number of interleaved Multipole/Cavity pairs.")
    assert isinstance(line[mult_names[0]], xt.Multipole)
    assert isinstance(line[cavi_names[0]], xt.Cavity)

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
        xsuite_values = _mult_xsuite_twiss_values(tw_xs, "end")
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
            "Xsuite beta/alpha values use SAD's Edwards-Teng convention; "
            "see docs/helpers/sad-helpers.md.",
        ])

########################################
# Single-Order Optics (isolates which order, if any, disagrees with SAD)
########################################
@pytest.mark.parametrize(
    "order_name, mult_definition, parameters",
    [
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
    tests/README.md and docs/reference/sad-behaviour.md for what this found.
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
        xsuite_values = _mult_xsuite_twiss_values(tw_xs, "end")
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
            "Single-order MULT optics coverage — each order (K1-K3, SK1-SK3) "
            "in isolation, no combination with any other order.",
            "Xsuite beta/alpha values use SAD's Edwards-Teng convention; "
            "see docs/helpers/sad-helpers.md.",
        ])

########################################
# K0/SK0 Dipole-Fringe Difference (accepted limitation, locked in exactly)
########################################
@pytest.mark.parametrize(
    "order_name, mult_parameter, row, column",
    [
        ("k0",  "K0",  3, 2),
        ("sk0", "SK0", 1, 0),
    ])
def test_mult_k0_dipole_fringe_difference_is_theta_fourth_order(
        write_lattice,
        tmp_path,
        order_name,
        mult_parameter,
        row,
        column):
    """
    The K0/SK0 dipole-fringe map difference between SAD and Xsuite is real,
    exactly characterised, and fourth-order in the kick angle.
    """
    length          = 0.5
    theta_values    = [0.025, 0.05, 0.1]
    differences     = {}

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        for theta in theta_values:
            lattice_path = write_lattice(
                f"""\
                MOMENTUM    = 1.0 GEV;

                MULT        TEST_MULT   = (
                    L       = {length}
                    {mult_parameter}      = {theta}
                );

                MARK        START       = ()
                            END         = ();

                LINE        TEST_LINE   = (START TEST_MULT END);
                """,
                filename = f"mult_fringe_scaling_{order_name}_{theta}.sad")

            tm_sad = transfer_matrix_sad(
                lattice_filepath    = lattice_path.name,
                line_name           = "TEST_LINE")
            line = s2x.convert_sad_to_xsuite(
                sad_lattice_path    = str(lattice_path),
                output_directory    = "N/A",
                _verbose            = False,
                _test_mode          = True)
            tm_xsuite = linear_transfer_matrix_4d(line)

            sad_term    = tm_sad[row, column]
            xsuite_term = tm_xsuite[row, column]

            assert sad_term == pytest.approx(
                -theta**2 / length, abs = 1e-12), (
                f"SAD's {mult_parameter} dipole fringe term should be "
                "exactly -theta^2/L at every kick angle.")

            differences[theta] = xsuite_term - sad_term
    finally:
        os.chdir(cwd)

    for theta in theta_values:
        assert differences[theta] != 0.0, (
            "The SAD-vs-Xsuite dipole fringe terms should NOT be equal — "
            "the accepted limitation is a real map difference. If they now "
            "agree, a fringe model changed in one of the codes and this "
            "limitation (and its documentation) must be re-derived.")
        assert differences[theta] == pytest.approx(-theta**4, rel = 0.01), (
            "The dipole fringe difference should equal -theta^4 at leading "
            f"order (measured -1.0005..-1.008 x theta^4 over {theta_values}).")

    assert differences[0.05] / differences[0.025] == pytest.approx(
        16.0, rel = 0.01), (
        "Doubling theta should multiply the fringe difference by 2^4 = 16 "
        "— the difference scales as theta^4.")
    assert differences[0.1] / differences[0.05] == pytest.approx(
        16.0, rel = 0.01), (
        "Doubling theta should multiply the fringe difference by 2^4 = 16 "
        "— the difference scales as theta^4.")

########################################
# Tracking With Particle Offsets
########################################
def test_mult_conversion_matches_sad_tracking_for_combined_orders(
        write_lattice,
        tmp_path):
    """
    Converted combined-order SAD MULT elements should match SAD tracking.
    """
    x_init, px_init, y_init, py_init, zeta_init, delta_init = \
        _standard_five_particle_offsets()

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

        xs_particles = track_xsuite_particles(
            line, x_init, px_init, y_init, py_init, zeta_init, delta_init)
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
    x_init, px_init, y_init, py_init, zeta_init, delta_init = \
        _standard_five_particle_offsets()

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

        xs_particles = track_xsuite_particles(
            line, x_init, px_init, y_init, py_init, zeta_init, delta_init)
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

################################################################################
# Linear F1/F2 Fringe Import
################################################################################
def test_mult_linear_fringe_import_defaults_on_and_brackets_body(write_lattice):
    """An active thick MULT fringe should bracket the unchanged body by default."""
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        MULT M1 = (L=0.5 K1=0.1 F1=0.02 F2=0.01 FRINGE=3 DISFRIN=1);
        MARK START=() END=();
        LINE TEST=(START M1 END);
        """,
        filename = "mult_linear_fringe_default.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.element_names == [
        "m1_fringe_in", "m1", "m1_fringe_out"]
    assert isinstance(line["m1"], xt.Quadrupole)
    assert isinstance(line["m1_fringe_in"], xt.SecondOrderTaylorMap)
    assert isinstance(line["m1_fringe_out"], xt.SecondOrderTaylorMap)


def test_mult_linear_fringe_coefficients_square_f1_and_include_sk1(
        parsed_elements, xsuite_environment):
    """MULT uses |K1+iSK1| and F1 squared, as established against SAD."""
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type      = "mult",
            element_name      = "m1",
            element_variables = {
                "l": 0.5, "k1": 0.03, "sk1": 0.04,
                "f1k1f": -0.02, "f2k1f": 0.01, "fringe": 1.0}),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = _mult_config(simplify = False))

    fringe = xsuite_environment["m1_fringe_in"]
    magnitude = np.hypot(0.03, 0.04) / 0.5
    expected_a = -magnitude * (-0.02)**2 / 24.0
    expected_b = magnitude * 0.01
    expected_theta = 0.5 * np.arctan2(0.04 * 0.5, 0.03 * 0.5)
    assert fringe._sad_k1_fringe_a == pytest.approx(expected_a)
    assert fringe._sad_k1_fringe_b == pytest.approx(expected_b)
    assert fringe._sad_k1_fringe_frame_rotation == pytest.approx(expected_theta)
    assert "m1_fringe_out" not in xsuite_environment.element_dict


def test_mult_above_length_precision_remains_thick_with_fringe(write_lattice):
    """
    A MULT shorter than NumPy's default closeness tolerance but above the
    SAD2XS length precision is thick in SAD and retains its soft fringe.
    """
    length = 5 * Config().MAGNET_LENGTH_PRECISION
    lattice_path = write_lattice(
        f"""\
        MOMENTUM = 1.0 GEV;
        MULT M1 = (L={length} K1=1.0E-12 F1=0.02 FRINGE=1 DISFRIN=1);
        MARK START=() END=();
        LINE TEST_LINE=(START M1 END);
        """,
        filename = "mult_fringe_short_thick.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        _verbose              = False,
        _test_mode            = True,
        SIMPLIFY_MULTIPOLES   = False)

    assert line.element_names == ["m1_fringe_in", "m1"]
    assert isinstance(line["m1"], xt.Multipole)
    assert line["m1"].isthick, (
        "A resolved nonzero length above MAGNET_LENGTH_PRECISION must remain "
        "a thick Multipole.")
    assert line["m1"].length == pytest.approx(length)


def test_mult_linear_fringe_import_can_be_disabled(
        parsed_elements, xsuite_environment):
    """The hidden MULT-fringe flag should provide the same opt-out as QUAD."""
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type      = "mult",
            element_name      = "m1",
            element_variables = {
                "l": 0.5, "k1": 0.1, "f1": 0.02, "fringe": 3.0}),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = Config(
            _verbose = False, SIMPLIFY_MULTIPOLES = False,
            _import_sad_mult_fringes = False))

    assert "m1" in xsuite_environment.element_dict
    assert "m1_compound" not in xsuite_environment.lines
    assert not any("fringe" in name for name in xsuite_environment.element_dict)


def test_mult_linear_fringe_with_drot_warns_and_is_skipped(
        parsed_elements, xsuite_environment, caplog):
    """DROT must not be applied only to the fringe while the body ignores it."""
    caplog.set_level(logging.WARNING, logger = "sad2xs.converter._004_element_converter")
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type      = "mult",
            element_name      = "m1",
            element_variables = {
                "l": 0.5, "k1": 0.1, "f1": 0.02,
                "fringe": 3.0, "drot": 0.01}),
        environment                 = xsuite_environment,
        user_multipole_replacements = None,
        config                      = _mult_config(simplify = False))

    assert "m1_compound" not in xsuite_environment.lines
    assert "nonzero DROT" in caplog.text


def test_mult_linear_fringe_wraps_user_quadrupole_replacement(
        parsed_elements, xsuite_environment):
    """A K1-preserving user replacement should retain both fringe faces."""
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type = "mult", element_name = "m1",
            element_variables = {
                "l": 0.5, "k1": 0.1, "f1": 0.02, "fringe": 3.0}),
        environment = xsuite_environment,
        user_multipole_replacements = {"m1": "Quadrupole"},
        config = _mult_config(simplify = False))

    assert isinstance(xsuite_environment["m1"], xt.Quadrupole)
    assert xsuite_environment.lines["m1_compound"].element_names == [
        "m1_fringe_in", "m1", "m1_fringe_out"]


def test_mult_linear_fringe_is_skipped_when_user_replacement_discards_k1(
        parsed_elements, xsuite_environment, caplog):
    """A replacement that removes K1 must not retain a contradictory fringe."""
    caplog.set_level(logging.WARNING)
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type = "mult", element_name = "m1",
            element_variables = {
                "l": 0.5, "k1": 0.1, "k2": 0.2,
                "f1": 0.02, "fringe": 3.0}),
        environment = xsuite_environment,
        user_multipole_replacements = {"m1": "Sextupole"},
        config = _mult_config(simplify = False))

    assert isinstance(xsuite_environment["m1"], xt.Sextupole)
    assert "m1_compound" not in xsuite_environment.lines
    assert "replacement discards K1/SK1" in caplog.text


def test_mult_linear_fringe_wraps_complete_rf_sliced_body(
        parsed_elements, xsuite_environment):
    """RF slicing should remain inside, rather than replace, the fringe faces."""
    xsuite_environment["fshift"] = 0.0
    convert_multipoles(
        parsed_elements = parsed_elements(
            element_type = "mult", element_name = "m1",
            element_variables = {
                "l": 0.5, "k1": 0.1, "f1": 0.02, "fringe": 3.0,
                "volt": 1e6, "freq": 5e8, "phi": 0.0}),
        environment = xsuite_environment,
        user_multipole_replacements = None,
        config = _mult_config(simplify = False))

    names = xsuite_environment.lines["m1_compound"].element_names
    assert names[0] == "m1_fringe_in"
    assert names[-1] == "m1_fringe_out"
    assert any("m1_cavi_" in name for name in names)


def test_mult_linear_fringe_import_matches_sad_tracking(write_lattice, tmp_path):
    """The zero-BZ K1/SK1 map should preserve SAD transverse tracking."""
    initial = _standard_five_particle_offsets()
    lattice_text = """\
    MOMENTUM = 1.0 GEV;
    MULT M1 = (L=1.0 K1=0.03 SK1=0.04 K2=0.02
               F1=-0.02 F2=0.01 FRINGE=3 DISFRIN=1);
    MARK START=() END=();
    LINE TEST_LINE=(START M1 END);
    """
    lattice_path = write_lattice(
        lattice_text, filename = "mult_linear_fringe_tracking.sad")

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        sad_particles = track_sad(
            lattice_filepath       = lattice_path.name,
            line_name              = "TEST_LINE",
            x_init                 = initial[0],
            px_init                = initial[1],
            y_init                 = initial[2],
            py_init                = initial[3],
            zeta_init              = initial[4],
            delta_init             = initial[5],
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
            sad_lattice_path       = str(lattice_path),
            output_directory       = "N/A",
            _verbose               = False,
            _test_mode             = True,
            SIMPLIFY_MULTIPOLES    = False)
        xs_particles = track_xsuite_particles(line, *initial)
    finally:
        os.chdir(cwd)

    _assert_mult_tracking_matches_sad(
        test_name          = "test_mult_linear_fringe_import_matches_sad_tracking",
        lattice_text       = lattice_text,
        initial_coordinates = _mult_initial_coordinates(*initial),
        sad_coordinates    = {
            key: _mult_sad_coordinates(sad_particles)[key]
            for key in ("x", "px", "y", "py")},
        xsuite_coordinates = {
            key: _mult_xsuite_coordinates(xs_particles)[key]
            for key in ("x", "px", "y", "py")},
        parameters         = {
            "length": 1.0, "k1l": 0.03, "sk1l": 0.04,
            "k2l": 0.02, "f1": -0.02, "f2": 0.01},
        notes              = [
            "DISFRIN=1 suppresses the separate hard-edge model; this test "
            "targets the zero-BZ F1/F2 K1 soft-edge map."])
