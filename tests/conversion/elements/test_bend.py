"""
================================================================================
Tests for SAD BEND conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-14
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
from sad2xs.converter._004_element_converter import convert_bends
from sad2xs.sad_helpers import track_sad
from tests.support.coupled_optics import edwards_teng_optics_at
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
BEND_ARTIFACT_CATEGORY = "conversion/elements/bend"

def _bend_tracking_tolerances():
    """
    Return coordinate tolerances used by bend tracking comparisons.
    """
    return {
        "x":     (DELTA_X_ATOL, DELTA_X_RTOL),
        "px":    (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":     (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py":    (DELTA_PY_ATOL, DELTA_PY_RTOL),
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
    }

def _bend_twiss_tolerances():
    """
    Return tolerances used by bend optics comparisons.
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

def _bend_twiss_values(twiss, element_name):
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

def _bend_initial_coordinates(
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

def _bend_sad_coordinates(sad_particles):
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

def _bend_xsuite_coordinates(xs_particles):
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

def _assert_bend_tracking_matches_sad(
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
    tolerances = _bend_tracking_tolerances()
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
            category        = BEND_ARTIFACT_CATEGORY,
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
            f"Converted bend tracking should match SAD. "
            f"Failed coordinates: {failed_coordinates}. "
            f"Diagnostic report: {report_path}")

def _assert_bend_tracking_matches_or_diverges(
        test_name,
        lattice_text,
        initial_coordinates,
        sad_coordinates,
        xsuite_coordinates,
        parameters,
        diverging_coordinates,
        notes = None):
    """
    Like _assert_bend_tracking_matches_sad, except every coordinate named
    in diverging_coordinates is asserted to diverge beyond tolerance
    instead of match -- the accepted-limitation coordinates of a
    documented SAD-side reference-orbit artifact (docs/sad-behaviour.md).
    """
    tolerances = _bend_tracking_tolerances()
    failed_coordinates = []

    for coord, xs_values in xsuite_coordinates.items():
        atol, rtol = tolerances[coord]
        close = np.all(np.isclose(
            sad_coordinates[coord],
            xs_values,
            rtol = rtol,
            atol = atol))
        should_match = coord not in diverging_coordinates
        if close != should_match:
            failed_coordinates.append(coord)

    if failed_coordinates:
        report_path = diagnostic_report_path(
            test_name       = test_name,
            category        = BEND_ARTIFACT_CATEGORY,
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
            f"Converted bend tracking should match SAD except for the "
            f"documented diverging coordinates {sorted(diverging_coordinates)}. "
            f"Coordinates with an unexpected result: {failed_coordinates}. "
            f"Diagnostic report: {report_path}")

def _assert_bend_twiss_matches_sad(
        test_name,
        lattice_text,
        sad_values,
        xsuite_values,
        parameters,
        notes = None):
    """
    Assert optics equivalence and write a Markdown report on failure.
    """
    tolerances = _bend_twiss_tolerances()
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
            category        = BEND_ARTIFACT_CATEGORY,
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
            f"Converted bend optics should match SAD. "
            f"Failed values: {failed_values}. "
            f"Diagnostic report: {report_path}")

def _assert_bend_twiss_matches_or_diverges(
        test_name,
        lattice_text,
        sad_values,
        xsuite_values,
        parameters,
        diverging_columns,
        notes = None):
    """
    Like _assert_bend_twiss_matches_sad, except every column named in
    diverging_columns is asserted to diverge beyond tolerance instead of
    match -- the accepted-limitation columns of a documented SAD-side
    reference-orbit/coupling artifact (docs/sad-behaviour.md). A column
    that unexpectedly matches is just as much a failure here as one that
    unexpectedly diverges: either means the accepted limitation's shape
    has changed and docs/sad-behaviour.md needs review.
    """
    tolerances = _bend_twiss_tolerances()
    failed_values = []

    for name, xs_value in xsuite_values.items():
        atol, rtol = tolerances[name]
        close = np.isclose(
            sad_values[name],
            xs_value,
            rtol = rtol,
            atol = atol)
        should_match = name not in diverging_columns
        if close != should_match:
            failed_values.append(name)

    if failed_values:
        report_path = diagnostic_report_path(
            test_name       = test_name,
            category        = BEND_ARTIFACT_CATEGORY,
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
            f"Converted bend optics should match SAD except for the "
            f"documented diverging columns {sorted(diverging_columns)}. "
            f"Columns with an unexpected result: {failed_values}. "
            f"Diagnostic report: {report_path}")

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
@pytest.mark.parametrize(
    "angle, expected_k0",
    [
        (0.1, 0.2),
        (-0.1, -0.2),
    ])
def test_bend_converter_creates_xsuite_bend(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element,
        angle,
        expected_k0):
    """
    Parsed non-zero-angle SAD BEND elements should become Xsuite Bend elements.
    """
    convert_bends(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_bend",
            element_variables   = {"l": 0.5, "angle": angle}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    bend = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_bend",
        element_type    = xt.Bend)

    assert bend.length == pytest.approx(0.5), (
        "Converted bend should preserve the parsed SAD length.")
    assert bend.k0 == pytest.approx(expected_k0), (
        "Converted bend k0 should equal parsed ANGLE divided by length.")
    assert bend.angle == pytest.approx(angle), (
        "Converted bend angle should preserve the parsed SAD ANGLE.")
    assert bend.k1 == pytest.approx(0.0), (
        "Bends without SAD K1 should have zero quadrupole component.")

def test_bend_converter_preserves_integrated_k1_component(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    SAD BEND K1 should map to the Xsuite bend k1 field, not multipole knl.
    """
    convert_bends(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_bend",
            element_variables   = {"l": 0.5, "angle": 0.1, "k1": 0.05}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    bend = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_bend",
        element_type    = xt.Bend)

    assert bend.k1 == pytest.approx(0.1), (
        "Converted bend k1 should equal parsed integrated K1 divided by "
        "length.")

def test_bend_converter_preserves_edge_terms(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    SAD BEND E1/E2/AE1/AE2 should map to Xsuite bend edge angles.
    """
    convert_bends(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_bend",
            element_variables   = {
                "l":        0.5,
                "angle":    0.1,
                "e1":       0.5,
                "e2":       0.25,
                "ae1":      0.01,
                "ae2":      -0.02,
            }),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    bend = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_bend",
        element_type    = xt.Bend)

    assert bend.edge_entry_angle == pytest.approx(0.06), (
        "Converted bend entry edge should be E1*ANGLE + AE1.")
    assert bend.edge_exit_angle == pytest.approx(0.005), (
        "Converted bend exit edge should be E2*ANGLE + AE2.")

def test_bend_converter_creates_all_bends(
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    Multiple parsed SAD BEND elements should all be converted.
    """
    parsed_elements = {
        "bend": {
            "bf": {"l": 0.5, "angle": 0.1},
            "bd": {"l": 0.5, "angle": -0.1},
            "bq": {"l": 0.5, "angle": 0.1, "k1": 0.05},
        },
    }

    convert_bends(
        parsed_elements = parsed_elements,
        environment     = xsuite_environment,
        config          = sad2xs_config)

    assert set(xsuite_environment.element_dict) == {"bf", "bd", "bq"}, (
        "All parsed non-zero-angle SAD BEND elements should be present.")
    for bend_name, expected_k0, expected_k1 in [
            ("bf", 0.2, 0.0),
            ("bd", -0.2, 0.0),
            ("bq", 0.2, 0.1)]:
        bend = assert_environment_element(
            environment     = xsuite_environment,
            element_name    = bend_name,
            element_type    = xt.Bend)
        assert bend.k0 == pytest.approx(expected_k0), (
            f"Converted bend '{bend_name}' should preserve angle/length.")
        assert bend.k1 == pytest.approx(expected_k1), (
            f"Converted bend '{bend_name}' should preserve integrated K1/length.")

########################################
# Element-Offset Warning
########################################
def test_bend_converter_warns_once_for_lattice_with_offset_angled_bends(
        xsuite_environment,
        sad2xs_config,
        caplog):
    """
    Converting a lattice with angled bends offset by DX/DY should warn
    exactly once for the whole lattice, not once per non-compliant element.
    """
    caplog.set_level(
        logging.DEBUG,
        logger = "sad2xs.converter._004_element_converter")

    convert_bends(
        parsed_elements = {
            "bend": {
                "b_offset_a": {"l": 0.5, "angle": 0.1, "dx": 0.001},
                "b_offset_b": {"l": 0.5, "angle": -0.1, "dy": -0.002},
                "b_clean":    {"l": 0.5, "angle": 0.1},
            },
        },
        environment = xsuite_environment,
        config      = sad2xs_config)

    offset_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "reference-orbit" in r.getMessage()]
    assert len(offset_warnings) == 1, (
        "Converting a lattice with offset angled bends should warn exactly "
        f"once. Got: {[r.getMessage() for r in caplog.records]!r}")
    debug_details = [
        record.getMessage() for record in caplog.records
        if record.levelno == logging.DEBUG
        and "Offset bends" in record.getMessage()]
    assert debug_details == [
        "Offset bends: b_offset_a, b_offset_b"
    ], "Debug logging should name the bends behind the summary warning."

def test_bend_converter_does_not_warn_for_unoffset_bends_or_correctors(
        xsuite_environment,
        sad2xs_config,
        caplog):
    """
    Angled bends without an offset, and zero-angle correctors with an
    offset, should not trigger the element-offset warning.
    """
    convert_bends(
        parsed_elements = {
            "bend": {
                "b_clean":     {"l": 0.5, "angle": 0.1},
                "b_corrector": {"l": 0.5, "angle": 0.0, "k0": 0.1, "dx": 0.001},
            },
        },
        environment = xsuite_environment,
        config      = sad2xs_config)

    offset_warnings = [
        r for r in caplog.records if "reference-orbit" in r.getMessage()]
    assert offset_warnings == [], (
        "Angled bends without an offset and zero-angle correctors with an "
        "offset should not trigger the offset warning. Got: "
        f"{[r.getMessage() for r in offset_warnings]!r}")

@pytest.mark.parametrize("verbose", [False, True])
def test_bend_converter_offset_warning_is_not_gated_by_verbosity(
        xsuite_environment,
        caplog,
        verbose):
    """
    The element-offset warning is emitted unconditionally, regardless of
    Config._verbose: convert_bends never reads that flag at all (only the
    main.py pipeline entry point does, and only to raise the logger's
    level for INFO/DEBUG progress narrative -- WARNING/ERROR records are
    always shown regardless, per Config._verbose's own docstring in
    sad2xs/config.py). This locks in that guarantee directly by checking
    both settings produce the identical warning, rather than the previous
    "visible in quiet mode" test, which used the same config as the tests
    above it and so never actually contrasted anything.
    """
    convert_bends(
        parsed_elements = {
            "bend": {
                "b_offset": {"l": 0.5, "angle": 0.1, "dx": 0.001},
            },
        },
        environment = xsuite_environment,
        config      = Config(_verbose = verbose))

    offset_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "reference-orbit" in r.getMessage()]
    assert len(offset_warnings) == 1, (
        "The element-offset warning should be emitted regardless of "
        f"Config._verbose (verbose={verbose}). Got records: "
        f"{[r.getMessage() for r in caplog.records]!r}")

########################################
# Corrector Handoff and Error Handling
########################################
def test_bend_converter_ignores_zero_angle_bends_for_corrector_pass(
        parsed_elements,
        xsuite_environment,
        sad2xs_config):
    """
    Zero-angle SAD BEND elements are handled by the corrector converter pass.
    """
    convert_bends(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_corr",
            element_variables   = {"l": 0.5, "angle": 0.0, "k0": 0.1}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    assert "test_corr" not in xsuite_environment.element_dict, (
        "Zero-angle BEND entries should be skipped by convert_bends.")

########################################
# Symbolic Parameters
########################################
def test_bend_converter_preserves_symbolic_angle_with_environment_variable(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    Symbolic SAD BEND angles should resolve through Xsuite environment vars.
    """
    xsuite_environment["theta"] = 0.1

    convert_bends(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_bend",
            element_variables   = {"l": 0.5, "angle": "theta"}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    bend = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_bend",
        element_type    = xt.Bend)

    assert xsuite_environment["k0_test_bend"] == pytest.approx(0.2), (
        "Symbolic ANGLE should be converted to resolved k0.")
    assert bend.angle == pytest.approx(0.1), (
        "Converted bend should use the resolved symbolic ANGLE.")

def test_bend_converter_supports_symbolic_length_and_angle(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    Symbolic SAD BEND lengths and angles should resolve through Xsuite vars.
    """
    xsuite_environment["lb"] = 0.5
    xsuite_environment["theta"] = 0.1

    convert_bends(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_bend",
            element_variables   = {"l": "lb", "angle": "theta"}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    bend = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_bend",
        element_type    = xt.Bend)

    assert bend.length == pytest.approx(0.5), (
        "Converted bend should resolve the SAD symbolic length.")
    assert bend.k0 == pytest.approx(0.2), (
        "Converted bend should resolve symbolic ANGLE divided by symbolic length.")

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
def test_bend_converter_canonicalizes_dipole_rotations(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element,
        sad_rotation,
        expected_rotation,
        expected_sign):
    """
    SAD BEND special rotations should map to canonical Xsuite Bend fields.
    """
    convert_bends(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_bend",
            element_variables   = {
                "l":        0.5,
                "angle":    0.1,
                "dx":       1.0E-3,
                "dy":       -2.0E-3,
                "rotate":   sad_rotation,
                "e1":       0.5,
                "e2":       0.25,
                "ae1":      0.01,
                "ae2":      -0.02,
            }),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    bend = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_bend",
        element_type    = xt.Bend)

    assert bend.shift_x == pytest.approx(1.0E-3), (
        "Converted bend should preserve SAD DX as Xsuite shift_x.")
    assert bend.shift_y == pytest.approx(-2.0E-3), (
        "Converted bend should preserve SAD DY as Xsuite shift_y.")
    assert bend.angle == pytest.approx(expected_sign * 0.1), (
        "Canonicalized bend angle should include the dipole field sign.")
    assert bend.k0 == pytest.approx(expected_sign * 0.2), (
        "Canonicalized bend k0 should include the dipole field sign.")
    assert bend.edge_entry_angle == pytest.approx(expected_sign * 0.06), (
        "Canonicalized bend edge_entry_angle should include the dipole field sign.")
    assert bend.edge_exit_angle == pytest.approx(expected_sign * 0.005), (
        "Canonicalized bend edge_exit_angle should include the dipole field sign.")
    assert bend.rot_s_rad == pytest.approx(expected_rotation), (
        "Converted bend should use the canonical Xsuite dipole rotation.")

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
def test_bend_converter_canonicalizes_thin_dipole_rotations(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element,
        sad_rotation,
        expected_rotation,
        expected_sign):
    """
    Thin SAD BEND rotations should canonicalize the dipole kick and hxl.
    """
    convert_bends(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_bend",
            element_variables   = {
                "angle":    0.1,
                "k1":       0.5,
                "rotate":   sad_rotation,
            }),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    ele = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_bend",
        element_type    = xt.Multipole)

    assert ele.knl[0] == pytest.approx(expected_sign * 0.1), (
        "Thin BEND knl[0] should include the canonical dipole field sign.")
    assert ele.hxl == pytest.approx(expected_sign * 0.1), (
        "Thin BEND hxl should include the canonical dipole field sign.")
    assert ele.knl[1] == pytest.approx(0.5), (
        "Thin BEND K1 should not be flipped by dipole canonicalization.")
    assert ele.rot_s_rad == pytest.approx(expected_rotation), (
        "Thin BEND should use the canonical Xsuite dipole rotation.")

def test_bend_converter_without_length_creates_thin_multipole(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    A SAD BEND with a non-zero ANGLE but no L should convert to a thin
    Multipole with hxl set — matching SAD's own treatment of this case.
    """
    convert_bends(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_bend",
            element_variables   = {"angle": 0.1}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    ele = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_bend",
        element_type    = xt.Multipole)
    assert ele.knl[0] == pytest.approx(0.1), (
        "Thin BEND without L should set knl[0] to the ANGLE value.")
    assert ele.hxl == pytest.approx(0.1), (
        "Thin BEND without L must set hxl to model reference-orbit bending.")

def test_bend_converter_without_length_preserves_k1_in_knl(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    K1 in a no-L SAD BEND is an integrated quadrupole strength and must appear
    in knl[1] of the resulting Multipole. Verified against SAD tracking.
    """
    convert_bends(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_bend",
            element_variables   = {"angle": 0.1, "k1": 0.5}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    ele = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_bend",
        element_type    = xt.Multipole)
    assert ele.knl[0] == pytest.approx(0.1), (
        "Thin BEND without L should set knl[0] to the ANGLE value.")
    assert ele.knl[1] == pytest.approx(0.5), (
        "K1 in a no-L BEND is integrated — must be preserved as knl[1].")
    assert ele.hxl == pytest.approx(0.1), (
        "Thin BEND without L must set hxl.")

def test_bend_converter_zero_length_preserves_k1_in_knl(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    K1 in an explicit L=0 SAD BEND is also integrated and must appear in knl[1].
    """
    convert_bends(
        parsed_elements = parsed_elements(
            element_type        = "bend",
            element_name        = "test_bend",
            element_variables   = {"angle": 0.1, "k1": 0.5, "l": 0.0}),
        environment     = xsuite_environment,
        config          = sad2xs_config)

    ele = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_bend",
        element_type    = xt.Multipole)
    assert ele.knl[1] == pytest.approx(0.5), (
        "K1 in an explicit L=0 BEND is integrated — must be preserved as knl[1].")

########################################
# Pipeline Behaviour
########################################
def test_bend_pipeline_preserves_names_order_lengths_angles_and_strengths(
        write_lattice):
    """
    Full conversion should preserve BEND names, order, lengths, angles, and K1.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        BF          = (L = 0.5 ANGLE = 0.1)
                    BD          = (L = 0.5 ANGLE = -0.1)
                    BQ          = (L = 0.5 ANGLE = 0.1 K1 = 0.05);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START BF BD BQ END);
        """,
        filename = "bend_pipeline_preserves_names_order_lengths_angles.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "bf", "bd", "bq", "end"], (
        "Converted line should preserve SAD bend names and order.")
    for bend_name, expected_angle, expected_k1 in [
            ("bf", 0.1, 0.0),
            ("bd", -0.1, 0.0),
            ("bq", 0.1, 0.1)]:
        assert isinstance(line[bend_name], xt.Bend), (
            f"Converted element '{bend_name}' should be an Xsuite Bend.")
        assert line[bend_name].length == pytest.approx(0.5), (
            f"Converted bend '{bend_name}' should preserve length.")
        assert line[bend_name].angle == pytest.approx(expected_angle), (
            f"Converted bend '{bend_name}' should preserve angle.")
        assert line[bend_name].k1 == pytest.approx(expected_k1), (
            f"Converted bend '{bend_name}' should preserve integrated K1/length.")

def test_bend_pipeline_canonicalizes_edges_offsets_and_rotation(write_lattice):
    """
    Full conversion should preserve offsets and canonicalize BEND edge terms
    and rotation.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        BOFF        = (
            L       = 0.5
            ANGLE   = 0.1
            E1      = 0.5
            E2      = 0.25
            AE1     = 0.01
            AE2     = -0.02
            DX      = 1.0E-3
            DY      = -2.0E-3
            ROTATE  = 90 DEG
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START BOFF END);
        """,
        filename = "bend_pipeline_canonicalizes_edges_offsets_rotation.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "boff", "end"], (
        "Converted line should preserve offset bend order.")
    assert isinstance(line["boff"], xt.Bend), (
        "Converted offset bend should be an Xsuite Bend.")
    assert line["boff"].angle == pytest.approx(-0.1), (
        "Converted bend angle should include the canonical dipole field sign.")
    assert line["boff"].k0 == pytest.approx(-0.2), (
        "Converted bend k0 should include the canonical dipole field sign.")
    assert line["boff"].edge_entry_angle == pytest.approx(-0.06), (
        "Converted bend edge_entry_angle should include the canonical dipole field sign.")
    assert line["boff"].edge_exit_angle == pytest.approx(-0.005), (
        "Converted bend edge_exit_angle should include the canonical dipole field sign.")
    assert line["boff"].shift_x == pytest.approx(1.0E-3), (
        "Converted bend should preserve SAD DX as Xsuite shift_x.")
    assert line["boff"].shift_y == pytest.approx(-2.0E-3), (
        "Converted bend should preserve SAD DY as Xsuite shift_y.")
    assert line["boff"].rot_s_rad == pytest.approx(np.pi / 2), (
        "Converted bend should use the canonical Xsuite vertical dipole rotation.")

################################################################################
# Physics Equivalence
################################################################################
########################################
# Default Bend Optics
########################################
@pytest.mark.parametrize(
    "angle",
    [-0.1, 0.1])
def test_bend_conversion_matches_sad_twiss_for_angles(
        write_lattice,
        tmp_path,
        angle):
    """
    Converted SAD BEND elements should match SAD optics and dispersion.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_BEND   = (L = 0.5 ANGLE = {angle});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_twiss_angle_{angle:+.3f}.sad")

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

        sad_values = _bend_twiss_values(tw_sad, "END")
        xsuite_values = _bend_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_bend_twiss_matches_sad(
        test_name       = "test_bend_conversion_matches_sad_twiss_for_angles",
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {"angle": angle},
        notes           = [
            "Bend optics coverage includes orbit and dispersion columns.",
        ])

########################################
# Thin Bend Optics
########################################
def test_bend_conversion_matches_sad_twiss_for_thin_bend(
        write_lattice,
        tmp_path):
    """
    Converted thin SAD BEND elements should match SAD optics and dispersion.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = """\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_BEND   = (L = 0.0 ANGLE = 0.1);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = "bend_twiss_thin_angle.sad")

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

        sad_values = _bend_twiss_values(tw_sad, "END")
        xsuite_values = _bend_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_bend_twiss_matches_sad(
        test_name       = "test_bend_conversion_matches_sad_twiss_for_thin_bend",
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {"length": 0.0, "angle": 0.1},
        notes           = [
            "Thin BEND coverage should lock down the SAD-to-Xsuite "
            "representation for integrated bend angle without finite length.",
        ])

########################################
# Thin Bend Offset Optics
########################################
def test_bend_conversion_matches_sad_twiss_for_thin_bend_element_offsets(
        write_lattice,
        tmp_path):
    """
    A thin, offset SAD BEND element should match SAD optics and dispersion
    when the offset is purely out of the bending plane (DY only).

    A DX offset on a thin bend is not tested here: it reproduces the same
    reference-orbit-convention residual as the thick case (see
    docs/sad-behaviour.md), locked in as a passing, quantified test by
    test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order
    rather than as a "should match" failure.
    """
    dx, dy = 0.0, -1.0E-3
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_BEND   = (
            L       = 0.0
            ANGLE   = 0.1
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_twiss_thin_dx_{dx:+.3e}_dy_{dy:+.3e}.sad")

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

        sad_values = _bend_twiss_values(tw_sad, "END")
        xsuite_values = _bend_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_bend_twiss_matches_sad(
        test_name       = "test_bend_conversion_matches_sad_twiss_for_thin_bend_element_offsets",
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {"length": 0.0, "dx": dx, "dy": dy},
        notes           = [
            "Offset out of the bending plane (DY only) should match SAD "
            "exactly for a thin bend, same as the thick case.",
        ])

########################################
# Thin Bend Offset Reference-Orbit Residual (Accepted Limitation)
########################################
@pytest.mark.parametrize(
    "dx, dy",
    [(1.0E-3, 0.0), (1.0E-3, -1.0E-3)])
def test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order(
        write_lattice,
        tmp_path,
        dx,
        dy):
    """
    The thin-bend counterpart of
    test_bend_offset_orbit_residual_is_angle_squared_order
    (docs/sad-behaviour.md): the same reference-orbit residual shows up
    in the dispersion (dx) column instead of the orbit (x) column, since a
    thin bend carries no separate orbit column of its own at zero length.
    Xsuite reproduces none of it; SAD's dx scales as ANGLE^2, matching
    -DX*(1-cos(ANGLE)) even more tightly than the thick case (opposite sign
    to the thick-bend orbit residual: dx is a dispersion, not an orbit, and
    there is no a priori reason the two share a sign convention). Confirmed
    at DX=0 that a thin bend alone (no offset) gives dx=0 exactly in both
    codes, so this is not fringe-model contamination.

    The second (dx, dy) parametrisation adds a DY component: confirmed
    empirically that DY contributes nothing of its own here (a thin bend's
    DY-only residual is zero to numerical noise on every column), so the
    combined-offset case is indistinguishable from the DX-only one and
    needs no separate formula -- this closes the combined-offset coverage
    gap directly rather than leaving it untested.

    zeta also diverges alongside dx (the same reference-orbit effect
    surfacing on a second column); it is asserted here only to be genuinely
    nonzero and beyond tolerance at every angle, not to a quantified
    formula, since dx is the primary quantity of interest.
    """
    angles      = [0.025, 0.05, 0.1]
    dx_diffs    = []
    zeta_diffs  = []

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        for angle in angles:
            lattice_path = write_lattice(
                f"""\
                MOMENTUM    = 1.0 GEV;

                BEND        TEST_BEND   = (
                    L       = 0.0
                    ANGLE   = {angle}
                    DX      = {dx}
                    DY      = {dy}
                );

                MARK        START       = ()
                            END         = ();

                LINE        TEST_LINE   = (START TEST_BEND END);
                """,
                filename = f"bend_offset_thin_residual_scaling_{angle}_{dx:+.3e}_{dy:+.3e}.sad")

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

            dx_sad   = tw_sad["dx", "END"]
            dx_xs    = tw_xs["dx", "end"]
            zeta_sad = tw_sad["zeta", "END"]
            zeta_xs  = tw_xs["zeta", "end"]

            assert dx_xs == pytest.approx(0.0, abs = 1E-8), (
                "Xsuite should not reproduce any of SAD's offset thin-bend "
                f"dispersion shift. Got dx={dx_xs:.3e} at angle={angle}.")

            dx_diffs.append(dx_sad - dx_xs)
            zeta_diffs.append(zeta_sad - zeta_xs)
    finally:
        os.chdir(cwd)

    for angle, diff, zeta_diff in zip(angles, dx_diffs, zeta_diffs):
        assert diff != 0.0, (
            "The SAD-vs-Xsuite offset thin-bend dispersion residual should "
            "NOT be zero -- the accepted limitation is a real dispersion "
            "difference. If this now matches, the reference-orbit "
            "convention changed in one of the codes and "
            "docs/sad-behaviour.md needs review.")
        assert diff == pytest.approx(
                -dx * (1 - np.cos(angle)), rel = 0.01), (
            "The offset thin-bend dispersion residual should equal "
            "-DX*(1-cos(ANGLE)) at leading order (opposite sign to the "
            "thick-bend orbit residual: dx is a dispersion, not an orbit).")
        assert zeta_diff != 0.0, (
            "zeta should also diverge from SAD alongside dx for a thin "
            "offset bend -- the same reference-orbit effect surfaces on "
            "both columns. If this now matches, docs/sad-behaviour.md "
            "needs review.")

    assert dx_diffs[1] / dx_diffs[0] == pytest.approx(4.0, rel = 0.01), (
        "Doubling ANGLE should multiply the dispersion residual by "
        "2^2 = 4 -- the residual scales as ANGLE^2.")
    assert dx_diffs[2] / dx_diffs[1] == pytest.approx(4.0, rel = 0.01), (
        "Doubling ANGLE should multiply the dispersion residual by "
        "2^2 = 4 -- the residual scales as ANGLE^2.")

########################################
# Combined-Function K1 Optics
########################################
@pytest.mark.parametrize(
    "k1l",
    [-0.05, 0.0, 0.05])
def test_bend_conversion_matches_sad_twiss_for_k1_components(
        write_lattice,
        tmp_path,
        k1l):
    """
    Converted combined-function SAD BEND K1 should match SAD optics.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_BEND   = (L = 0.5 ANGLE = 0.1 K1 = {k1l});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_twiss_k1l_{k1l:+.3f}.sad")

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

        sad_values = _bend_twiss_values(tw_sad, "END")
        xsuite_values = _bend_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_bend_twiss_matches_sad(
        test_name       = (
            "test_bend_conversion_matches_sad_twiss_for_k1_components"),
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {"k1l": k1l},
        notes           = [
            "SAD BEND K1 is stored in the Xsuite Bend k1 field, not knl.",
        ])

########################################
# Edge Optics
########################################
@pytest.mark.parametrize(
    "e1, e2, ae1, ae2",
    [
        (0.0, 0.0, 0.0, 0.0),
        (0.5, 0.5, 0.0, 0.0),
        (0.5, 0.25, 0.01, -0.02),
    ])
def test_bend_conversion_matches_sad_twiss_for_edge_terms(
        write_lattice,
        tmp_path,
        e1,
        e2,
        ae1,
        ae2):
    """
    Converted SAD BEND edge terms should match SAD optics and dispersion.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_BEND   = (
            L       = 0.5
            ANGLE   = 0.1
            E1      = {e1}
            E2      = {e2}
            AE1     = {ae1}
            AE2     = {ae2}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = (
                f"bend_twiss_edges_e1_{e1:+.3f}_e2_{e2:+.3f}"
                f"_ae1_{ae1:+.3f}_ae2_{ae2:+.3f}.sad"))

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

        sad_values = _bend_twiss_values(tw_sad, "END")
        xsuite_values = _bend_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_bend_twiss_matches_sad(
        test_name       = "test_bend_conversion_matches_sad_twiss_for_edge_terms",
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {
            "e1": e1,
            "e2": e2,
            "ae1": ae1,
            "ae2": ae2,
        },
        notes           = [
            "BEND edge coverage checks the E1/E2 fractional bend-edge terms "
            "and AE1/AE2 absolute edge-angle terms.",
        ])

########################################
# Rotation Optics
########################################
@pytest.mark.parametrize(
    "rotation",
    [np.pi / 2, -np.pi / 2])
def test_bend_conversion_matches_sad_twiss_for_rotated_bends(
        write_lattice,
        tmp_path,
        rotation):
    """
    Converted rotated SAD BEND elements should match SAD optics and dispersion.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_BEND   = (
            L       = 0.5
            ANGLE   = 0.1
            ROTATE  = {rotation}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_twiss_rotate_{rotation:+.6f}.sad")

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

        sad_values = _bend_twiss_values(tw_sad, "END")
        xsuite_values = _bend_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_bend_twiss_matches_sad(
        test_name       = "test_bend_conversion_matches_sad_twiss_for_rotated_bends",
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {"rotation": rotation},
        notes           = [
            "Rotated BEND optics coverage includes orbit and dispersion columns.",
        ])

########################################
# Offset Optics
########################################
def test_bend_conversion_matches_sad_twiss_for_element_offsets(
        write_lattice,
        tmp_path):
    """
    An offset SAD BEND element should match SAD optics and dispersion when
    the offset is purely out of the bending plane (DY only).

    A DX offset (or combined DX+DY) is not tested here: it reproduces a
    real, quantified reference-orbit-convention residual (see
    docs/sad-behaviour.md), locked in as a passing test by
    test_bend_offset_orbit_residual_is_angle_squared_order rather than as a
    "should match" failure. A rotated bend with an offset is covered
    separately by test_bend_conversion_matches_sad_twiss_for_rotated_element_offsets
    and test_bend_offset_rotated_coupling_is_a_sad_side_artifact, since
    ROTATE changes which axis is physically in the bending plane and
    introduces a further, separate SAD-side artifact of its own.
    """
    dx, dy = 0.0, -1.0E-3
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_BEND   = (
            L       = 0.5
            ANGLE   = 0.1
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_twiss_dx_{dx:+.3e}_dy_{dy:+.3e}.sad")

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

        sad_values = _bend_twiss_values(tw_sad, "END")
        xsuite_values = _bend_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_bend_twiss_matches_sad(
        test_name       = "test_bend_conversion_matches_sad_twiss_for_element_offsets",
        lattice_text    = lattice_text,
        sad_values      = sad_values,
        xsuite_values   = xsuite_values,
        parameters      = {"dx": dx, "dy": dy},
        notes           = [
            "Offset BEND optics coverage includes orbit and dispersion columns.",
        ])

########################################
# Offset Reference-Orbit Residual (Accepted Limitation)
########################################
@pytest.mark.parametrize(
    "dx, dy",
    [(1.0E-3, 0.0), (1.0E-3, -1.0E-3)])
def test_bend_offset_orbit_residual_is_angle_squared_order(
        write_lattice,
        tmp_path,
        dx,
        dy):
    """
    The DX-offset reference-orbit residual (docs/sad-behaviour.md) is
    real, reproducible, and quantified: SAD's orbit shows a nonzero shift
    that scales as ANGLE^2 (matching DX*(1-cos(ANGLE)) to ~1%), while Xsuite
    reproduces none of it (h stays fixed to the unshifted design orbit).

    This locks in the accepted limitation as a passing test, the same way
    test_mult_k0_dipole_fringe_difference_is_theta_fourth_order locks in the
    MULT K0/SK0 fringe residual. If this now fails, either a fringe/model
    change made the codes agree (good news, but the design decision needs
    revisiting) or the residual's character changed (needs investigation).

    The second (dx, dy) parametrisation adds a DY component: confirmed
    empirically that the combined-offset residual on every column is a
    pure superposition of the DX-only residual (DY's own contribution is
    zero to numerical noise), so this closes the combined-offset coverage
    gap without a second formula.

    zeta, dx (dispersion), betx, bety, alfx, and alfy also diverge
    alongside x for this element at every angle tested here (confirmed
    empirically); they are asserted only to genuinely diverge beyond
    tolerance, not to a quantified formula, since x is the primary
    quantity with an established closed form.

    px and dy are deliberately excluded from the per-column check below,
    not asserted either way: px diverges (ANGLE^4 scaling) but only
    clears tolerance at 0.05/0.1, not at 0.025, so it cannot be classed as
    a reliable per-angle "always diverges" column; dy carries a tiny
    (~1e-9) genuine cross-term in the combined-offset parametrisation that
    only clears tolerance at the largest angle tested. Both are real but
    angle-dependent right at the edge of the comparison tolerance.

    px's divergence is specifically the offset residual, not a symptom of
    the separate, already-documented Xsuite-bend-edge ANGLE^2+ANGLE^4 vs
    SAD's ANGLE^2-only fringe-order mismatch (see the MULT K0/SK0 fringe
    entry in docs/sad-behaviour.md for that unrelated effect): confirmed
    empirically that a DX=DY=0 bend at these same three angles matches
    SAD on all 15 columns with no divergence anywhere, so nothing here is
    conflating the two effects -- an unambiguous, angle-independent
    classification is only available for
    the seven columns actually checked here.
    """
    angles              = [0.025, 0.05, 0.1]
    diverging_columns   = {"x", "zeta", "dx", "betx", "bety", "alfx", "alfy"}
    ignored_columns     = {"px", "dy"}
    x_diffs             = []

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        for angle in angles:
            lattice_text = f"""\
                MOMENTUM    = 1.0 GEV;

                BEND        TEST_BEND   = (
                    L       = 0.5
                    ANGLE   = {angle}
                    DX      = {dx}
                    DY      = {dy}
                );

                MARK        START       = ()
                            END         = ();

                LINE        TEST_LINE   = (START TEST_BEND END);
                """
            lattice_path = write_lattice(
                lattice_text,
                filename = f"bend_offset_residual_scaling_{angle}_{dx:+.3e}_{dy:+.3e}.sad")

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

            sad_values      = _bend_twiss_values(tw_sad, "END")
            xsuite_values   = _bend_twiss_values(tw_xs, "end")

            assert xsuite_values["x"] == pytest.approx(0.0, abs = 1E-8), (
                "Xsuite should not reproduce any of SAD's offset-bend orbit "
                f"shift (h stays fixed to the design orbit). Got "
                f"x={xsuite_values['x']:.3e} at angle={angle}.")

            x_diffs.append(sad_values["x"] - xsuite_values["x"])

            checked_columns = set(xsuite_values.keys()) - ignored_columns
            _assert_bend_twiss_matches_or_diverges(
                test_name           = "test_bend_offset_orbit_residual_is_angle_squared_order",
                lattice_text        = lattice_text,
                sad_values          = {k: v for k, v in sad_values.items() if k in checked_columns},
                xsuite_values       = {k: v for k, v in xsuite_values.items() if k in checked_columns},
                parameters          = {"angle": angle, "dx": dx, "dy": dy},
                diverging_columns   = diverging_columns,
                notes               = [
                    "zeta, dx, betx, bety, alfx, alfy diverge alongside x "
                    "for an offset curved bend (docs/sad-behaviour.md); "
                    "s, y, py, delta, dpx, dpy should still match at this "
                    "angle. px and dy are excluded from this check "
                    "entirely (see docstring): both are real but only "
                    "clear tolerance at specific angles/parametrisations.",
                ])
    finally:
        os.chdir(cwd)

    for angle, diff in zip(angles, x_diffs):
        assert diff != 0.0, (
            "The SAD-vs-Xsuite offset-bend orbit residual should NOT be "
            "zero -- the accepted limitation is a real orbit difference. If "
            "this now matches, the reference-orbit convention changed in "
            "one of the codes and docs/sad-behaviour.md needs review.")
        assert diff == pytest.approx(
                dx * (1 - np.cos(angle)), rel = 0.01), (
            "The offset-bend orbit residual should equal DX*(1-cos(ANGLE)) "
            "at leading order.")

    assert x_diffs[1] / x_diffs[0] == pytest.approx(4.0, rel = 0.01), (
        "Doubling ANGLE should multiply the orbit residual by 2^2 = 4 -- "
        "the residual scales as ANGLE^2.")
    assert x_diffs[2] / x_diffs[1] == pytest.approx(4.0, rel = 0.01), (
        "Doubling ANGLE should multiply the orbit residual by 2^2 = 4 -- "
        "the residual scales as ANGLE^2.")

########################################
# Default Bend Tracking
########################################
@pytest.mark.parametrize(
    "angle",
    [-0.1, 0.1])
def test_bend_conversion_matches_sad_tracking_for_angles(
        write_lattice,
        tmp_path,
        angle):
    """
    Converted SAD BEND elements should match SAD tracking.
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

        BEND        TEST_BEND   = (L = 0.5 ANGLE = {angle});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_tracking_angle_{angle:+.3f}.sad")

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

    _assert_bend_tracking_matches_sad(
        test_name               = "test_bend_conversion_matches_sad_tracking_for_angles",
        lattice_text            = lattice_text,
        initial_coordinates     = _bend_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _bend_sad_coordinates(sad_particles),
        xsuite_coordinates      = _bend_xsuite_coordinates(xs_particles),
        parameters              = {"angle": angle})

########################################
# Thin Bend Tracking
########################################
def test_bend_conversion_matches_sad_tracking_for_thin_bend(
        write_lattice,
        tmp_path):
    """
    Converted thin SAD BEND elements should match SAD tracking.
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

        BEND        TEST_BEND   = (L = 0.0 ANGLE = 0.1);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = "bend_tracking_thin_angle.sad")

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

    _assert_bend_tracking_matches_sad(
        test_name               = (
            "test_bend_conversion_matches_sad_tracking_for_thin_bend"),
        lattice_text            = lattice_text,
        initial_coordinates     = _bend_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _bend_sad_coordinates(sad_particles),
        xsuite_coordinates      = _bend_xsuite_coordinates(xs_particles),
        parameters              = {"length": 0.0, "angle": 0.1},
        notes                   = [
            "Thin BEND tracking should match SAD before the representation "
            "is accepted as production behaviour.",
        ])

########################################
# Thin Bend Offset Tracking
########################################
def test_bend_conversion_matches_sad_tracking_for_thin_bend_element_offsets(
        write_lattice,
        tmp_path):
    """
    A thin, offset SAD BEND element should match SAD tracking when the
    offset is purely out of the bending plane (DY only).

    A DX offset (or combined DX+DY) is not tested here: see
    test_bend_offset_thin_bend_dispersion_residual_diverges_in_tracking
    for the tracking-mode divergence lock-in, and
    test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order
    for the quantified twiss-side residual (docs/sad-behaviour.md).
    """
    dx, dy = 0.0, -1.0E-3
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

        BEND        TEST_BEND   = (
            L       = 0.0
            ANGLE   = 0.1
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_tracking_thin_dx_{dx:+.3e}_dy_{dy:+.3e}.sad")

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

    _assert_bend_tracking_matches_sad(
        test_name               = (
            "test_bend_conversion_matches_sad_tracking_for_thin_bend_element_offsets"),
        lattice_text            = lattice_text,
        initial_coordinates     = _bend_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _bend_sad_coordinates(sad_particles),
        xsuite_coordinates      = _bend_xsuite_coordinates(xs_particles),
        parameters              = {"dx": dx, "dy": dy},
        notes                   = [
            "Offset out of the bending plane (DY only) should match SAD "
            "exactly for a thin bend, same as the thick case.",
        ])

@pytest.mark.parametrize(
    "dx, dy",
    [(1.0E-3, 0.0), (1.0E-3, -1.0E-3)])
def test_bend_offset_thin_bend_dispersion_residual_diverges_in_tracking(
        write_lattice,
        tmp_path,
        dx,
        dy):
    """
    The tracking-mode counterpart of
    test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order:
    a DX-offset (or combined DX+DY) thin bend diverges from SAD in
    tracking on x, y, and zeta -- x and y by a small, uniform rigid shift
    (~1e-8, the same size for every particle regardless of its own initial
    coordinates) and zeta by a much larger amount (~1e-4), the reference-
    orbit residual surfacing directly in the time-of-flight coordinate for
    a zero-length element. px, py, and delta still match (confirmed
    empirically for both parametrisations, so DY again contributes nothing
    of its own). This is a coarse divergence lock-in (no quantified
    formula), the same style as
    test_sol_disfrin_off_diverges_from_xsuite_in_tracking.
    """
    diverging_coordinates = {"x", "y", "zeta"}

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

        BEND        TEST_BEND   = (
            L       = 0.0
            ANGLE   = 0.1
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_offset_thin_residual_tracking_{dx:+.3e}_{dy:+.3e}.sad")

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

    _assert_bend_tracking_matches_or_diverges(
        test_name               = (
            "test_bend_offset_thin_bend_dispersion_residual_diverges_in_tracking"),
        lattice_text            = lattice_text,
        initial_coordinates     = _bend_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _bend_sad_coordinates(sad_particles),
        xsuite_coordinates      = _bend_xsuite_coordinates(xs_particles),
        parameters              = {"dx": dx, "dy": dy},
        diverging_coordinates   = diverging_coordinates,
        notes                   = [
            "The thin-bend dispersion residual (docs/sad-behaviour.md) "
            "surfaces in tracking as a divergence on x/y/zeta; px/py/delta "
            "still match.",
        ])

########################################
# Combined-Function K1 Tracking
########################################
@pytest.mark.parametrize(
    "k1l",
    [-0.05, 0.0, 0.05])
def test_bend_conversion_matches_sad_tracking_for_k1_components(
        write_lattice,
        tmp_path,
        k1l):
    """
    Converted combined-function SAD BEND K1 should match SAD tracking.
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

        BEND        TEST_BEND   = (L = 0.5 ANGLE = 0.1 K1 = {k1l});

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_tracking_k1l_{k1l:+.3f}.sad")

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

    _assert_bend_tracking_matches_sad(
        test_name               = (
            "test_bend_conversion_matches_sad_tracking_for_k1_components"),
        lattice_text            = lattice_text,
        initial_coordinates     = _bend_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _bend_sad_coordinates(sad_particles),
        xsuite_coordinates      = _bend_xsuite_coordinates(xs_particles),
        parameters              = {"k1l": k1l},
        notes                   = [
            "SAD BEND K1 is stored in the Xsuite Bend k1 field, not knl.",
        ])

########################################
# Edge Tracking
########################################
@pytest.mark.parametrize(
    "e1, e2, ae1, ae2",
    [
        (0.0, 0.0, 0.0, 0.0),
        (0.5, 0.5, 0.0, 0.0),
        (0.5, 0.25, 0.01, -0.02),
    ])
def test_bend_conversion_matches_sad_tracking_for_edge_terms(
        write_lattice,
        tmp_path,
        e1,
        e2,
        ae1,
        ae2):
    """
    Converted SAD BEND edge terms should match SAD tracking.
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

        BEND        TEST_BEND   = (
            L       = 0.5
            ANGLE   = 0.1
            E1      = {e1}
            E2      = {e2}
            AE1     = {ae1}
            AE2     = {ae2}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = (
                f"bend_tracking_edges_e1_{e1:+.3f}_e2_{e2:+.3f}"
                f"_ae1_{ae1:+.3f}_ae2_{ae2:+.3f}.sad"))

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

    _assert_bend_tracking_matches_sad(
        test_name               = (
            "test_bend_conversion_matches_sad_tracking_for_edge_terms"),
        lattice_text            = lattice_text,
        initial_coordinates     = _bend_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _bend_sad_coordinates(sad_particles),
        xsuite_coordinates      = _bend_xsuite_coordinates(xs_particles),
        parameters              = {
            "e1": e1,
            "e2": e2,
            "ae1": ae1,
            "ae2": ae2,
        },
        notes                   = [
            "BEND edge coverage checks the E1/E2 fractional bend-edge terms "
            "and AE1/AE2 absolute edge-angle terms.",
        ])

########################################
# Rotation Tracking
########################################
@pytest.mark.parametrize(
    "rotation",
    [np.pi / 2, -np.pi / 2])
def test_bend_conversion_matches_sad_tracking_for_rotated_bends(
        write_lattice,
        tmp_path,
        rotation):
    """
    Converted rotated SAD BEND elements should match SAD tracking.
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

        BEND        TEST_BEND   = (
            L       = 0.5
            ANGLE   = 0.1
            ROTATE  = {rotation}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_tracking_rotate_{rotation:+.6f}.sad")

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

    _assert_bend_tracking_matches_sad(
        test_name               = (
            "test_bend_conversion_matches_sad_tracking_for_rotated_bends"),
        lattice_text            = lattice_text,
        initial_coordinates     = _bend_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _bend_sad_coordinates(sad_particles),
        xsuite_coordinates      = _bend_xsuite_coordinates(xs_particles),
        parameters              = {"rotation": rotation})

########################################
# Offset Tracking
########################################
def test_bend_conversion_matches_sad_tracking_for_element_offsets(
        write_lattice,
        tmp_path):
    """
    An offset SAD BEND element should match SAD tracking when the offset is
    purely out of the bending plane (DY only).

    A DX offset (or combined DX+DY) is not tested here: see
    test_bend_offset_orbit_residual_diverges_in_tracking for the
    tracking-mode divergence lock-in, and
    test_bend_offset_orbit_residual_is_angle_squared_order for the
    quantified twiss-side residual (docs/sad-behaviour.md).
    """
    dx, dy = 0.0, -1.0E-3
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

        BEND        TEST_BEND   = (
            L       = 0.5
            ANGLE   = 0.1
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_tracking_dx_{dx:+.3e}_dy_{dy:+.3e}.sad")

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

    _assert_bend_tracking_matches_sad(
        test_name               = (
            "test_bend_conversion_matches_sad_tracking_for_element_offsets"),
        lattice_text            = lattice_text,
        initial_coordinates     = _bend_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _bend_sad_coordinates(sad_particles),
        xsuite_coordinates      = _bend_xsuite_coordinates(xs_particles),
        parameters              = {"dx": dx, "dy": dy},
        notes                   = [
            "Offset out of the bending plane (DY only) should match SAD "
            "exactly, same as the thin-bend case.",
        ])

@pytest.mark.parametrize(
    "dx, dy",
    [(1.0E-3, 0.0), (1.0E-3, -1.0E-3)])
def test_bend_offset_orbit_residual_diverges_in_tracking(
        write_lattice,
        tmp_path,
        dx,
        dy):
    """
    The tracking-mode counterpart of
    test_bend_offset_orbit_residual_is_angle_squared_order: a DX-offset
    (or combined DX+DY) curved bend diverges from SAD in tracking too, on
    x, px, and zeta -- the same reference-orbit residual, now confirmed
    with actual particle dynamics rather than only the closed-orbit twiss
    value. y, py, and delta still match (confirmed empirically for both
    parametrisations, so DY again contributes nothing of its own). This
    is a coarse divergence lock-in (no quantified formula), the same
    style as test_sol_disfrin_off_diverges_from_xsuite_in_tracking.
    """
    diverging_coordinates = {"x", "px", "zeta"}

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

        BEND        TEST_BEND   = (
            L       = 0.5
            ANGLE   = 0.1
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = f"bend_offset_residual_tracking_{dx:+.3e}_{dy:+.3e}.sad")

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

    _assert_bend_tracking_matches_or_diverges(
        test_name               = "test_bend_offset_orbit_residual_diverges_in_tracking",
        lattice_text            = lattice_text,
        initial_coordinates     = _bend_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _bend_sad_coordinates(sad_particles),
        xsuite_coordinates      = _bend_xsuite_coordinates(xs_particles),
        parameters              = {"dx": dx, "dy": dy},
        diverging_coordinates   = diverging_coordinates,
        notes                   = [
            "The DX-offset reference-orbit residual (docs/sad-behaviour.md) "
            "surfaces in tracking as a divergence on x/px/zeta; y/py/delta "
            "still match.",
        ])

########################################
# Rotated Offset Twiss
########################################
@pytest.mark.parametrize(
    "rotation, dx, dy",
    [
        (np.pi / 2, 1.0E-3, 0.0),
        (np.pi / 2, 0.0, -1.0E-3),
        (np.pi / 2, 1.0E-3, -1.0E-3),
        (-np.pi / 2, 1.0E-3, 0.0),
        (-np.pi / 2, 0.0, -1.0E-3),
        (-np.pi / 2, 1.0E-3, -1.0E-3),
    ])
def test_bend_conversion_matches_sad_twiss_for_rotated_element_offsets(
        write_lattice,
        tmp_path,
        rotation,
        dx,
        dy):
    """
    The twiss-side counterpart of
    test_bend_conversion_matches_sad_tracking_for_rotated_element_offsets:
    a rotated, offset bend's x/px/y/py/zeta/dx/dy pattern diverges the
    same way in twiss as in tracking (DX out-of-plane matches, DY
    in-plane diverges on y/py/zeta/dy). betx/bety/alfx/alfy additionally
    diverge in every parametrisation here, regardless of which axis
    carries the offset -- confirmed empirically: ROTATE != 0 combined
    with any nonzero offset on a curved bend triggers the same SAD-side
    coupling artifact locked in by
    test_bend_offset_rotated_coupling_is_a_sad_side_artifact, even for the
    DX-only case that the tracking test above shows as a full match
    (tracking never computes twiss parameters, so it cannot see this). A
    combined DX+DY offset additionally shows a small (~1e-9) but genuine
    dx cross-term absent from either pure-axis case.
    """
    diverging_columns = {"betx", "bety", "alfx", "alfy"}
    if dy != 0.0:
        diverging_columns |= {"y", "py", "zeta", "dy"}
    if dx != 0.0 and dy != 0.0:
        diverging_columns |= {"dx"}

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_BEND   = (
            L       = 0.5
            ANGLE   = 0.1
            ROTATE  = {rotation}
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = (
                f"bend_twiss_rotate_{rotation:+.6f}"
                f"_dx_{dx:+.3e}_dy_{dy:+.3e}.sad"))

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

        sad_values      = _bend_twiss_values(tw_sad, "END")
        xsuite_values   = _bend_twiss_values(tw_xs, "end")
    finally:
        os.chdir(cwd)

    _assert_bend_twiss_matches_or_diverges(
        test_name           = (
            "test_bend_conversion_matches_sad_twiss_for_rotated_element_offsets"),
        lattice_text        = lattice_text,
        sad_values          = sad_values,
        xsuite_values       = xsuite_values,
        parameters          = {"rotation": rotation, "dx": dx, "dy": dy},
        diverging_columns   = diverging_columns,
        notes               = [
            "betx/bety/alfx/alfy always diverge for a rotated, offset, "
            "curved bend (docs/sad-behaviour.md); y/py/zeta/dy diverge "
            "only when DY is nonzero (the in-plane component); dx "
            "diverges only when DX and DY are both nonzero together.",
        ])

########################################
# Rotated Offset Tracking
########################################
@pytest.mark.parametrize(
    "rotation, dx, dy",
    [
        (np.pi / 2, 1.0E-3, 0.0),
        (np.pi / 2, 0.0, -1.0E-3),
        (np.pi / 2, 1.0E-3, -1.0E-3),
        (-np.pi / 2, 1.0E-3, 0.0),
        (-np.pi / 2, 0.0, -1.0E-3),
        (-np.pi / 2, 1.0E-3, -1.0E-3),
    ])
def test_bend_conversion_matches_sad_tracking_for_rotated_element_offsets(
        write_lattice,
        tmp_path,
        rotation,
        dx,
        dy):
    """
    A rotated, offset SAD BEND element matches SAD tracking exactly when
    the offset lies purely along DX -- once ROTATE = +-pi/2, DX is
    physically out of the (now vertical) bending plane, the same way DY
    is out of plane for an unrotated bend.

    A DY (or combined DX+DY) offset diverges instead: once rotated, DY
    becomes the in-bending-plane component and reproduces the same
    reference-orbit residual as the unrotated DX case, on y/py/zeta
    instead of x/px/zeta -- confirmed empirically to diverge beyond
    tolerance on exactly those three coordinates, regardless of rotation
    sign, with or without a simultaneous DX component. See
    test_bend_offset_rotated_coupling_is_a_sad_side_artifact for the
    further, separate twiss-side coupling artifact this combination also
    triggers (docs/sad-behaviour.md); tracking alone does not compute
    twiss parameters, so that artifact has no coordinate to surface on
    here.
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

        BEND        TEST_BEND   = (
            L       = 0.5
            ANGLE   = 0.1
            ROTATE  = {rotation}
            DX      = {dx}
            DY      = {dy}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = (
                f"bend_tracking_rotate_{rotation:+.6f}"
                f"_dx_{dx:+.3e}_dy_{dy:+.3e}.sad"))

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

    diverging_coordinates = {"y", "py", "zeta"} if dy != 0.0 else set()

    _assert_bend_tracking_matches_or_diverges(
        test_name               = (
            "test_bend_conversion_matches_sad_tracking_for_rotated_element_offsets"),
        lattice_text            = lattice_text,
        initial_coordinates     = _bend_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates         = _bend_sad_coordinates(sad_particles),
        xsuite_coordinates      = _bend_xsuite_coordinates(xs_particles),
        parameters              = {"rotation": rotation, "dx": dx, "dy": dy},
        diverging_coordinates   = diverging_coordinates,
        notes                   = [
            "A DX offset is physically out of the bending plane once "
            "ROTATE = +-pi/2, so it should match SAD exactly; a DY "
            "component is in-plane and reproduces the unrotated DX "
            "residual on y/py/zeta instead of x/px/zeta.",
        ])

########################################
# Rotated Offset Coupling (Accepted SAD-Side Limitation)
########################################
def test_bend_offset_rotated_coupling_is_a_sad_side_artifact(write_lattice, tmp_path):
    """
    Combining ROTATE with an offset on a curved (ANGLE != 0) bend makes
    SAD's own reported linear coupling (R1/R4) diverge from Xsuite's in a
    way that is not real dynamical coupling: SAD's R1 sits on sin(ROTATE)
    (cos(ROTATE) past a fixed ~52 degree branch point) the instant the
    offset is nonzero, essentially independent of the offset's actual
    magnitude -- confirmed here at two offset sizes three orders of
    magnitude apart. Xsuite's own, independently-computed coupling stays
    small and physically continuous throughout.

    betx/bety/alfx/alfy diverge alongside R1/R4 -- SAD's own reported
    twiss parameters are reconstructed from its discontinuous R-matrix, so
    they inherit the same artifact. Confirmed empirically: the divergence
    is ~1e-3, three orders of magnitude past the normal (1e-9, 1e-5) twiss
    tolerance, and (like R1) barely changes between the two offset
    magnitudes tested, the same magnitude-independent signature.

    This is accepted as a SAD-side characteristic, not a converter bug and
    not something sad2xs should try to reproduce -- see
    docs/sad-behaviour.md for the summary. It was investigated in much
    more depth than is committed here (an Edwards-Teng/Mais-Ripken
    convention mismatch and a converter bug were both ruled out, and the
    trigger was isolated to curvature specifically), but the responsible
    SAD-internal mechanism could not be confirmed without SAD source
    access, so only the directly-observable, distilled evidence is locked
    in below.
    """
    rotation            = np.pi / 4
    angle               = 0.05
    dx_values           = [1.0E-6, 1.0E-3]
    sad_r1_values       = []
    sad_values_by_dx    = []
    xsuite_values_by_dx = []

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        for dx in dx_values:
            lattice_path = write_lattice(
                f"""\
                MOMENTUM    = 1.0 GEV;

                BEND        TEST_BEND   = (
                    L       = 0.5
                    ANGLE   = {angle}
                    ROTATE  = {rotation}
                    DX      = {dx}
                );

                MARK        START       = ()
                            END         = ();

                LINE        TEST_LINE   = (START TEST_BEND END);
                """,
                filename = f"bend_offset_rotated_coupling_{dx:.0e}.sad")

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

            sad_values      = _bend_twiss_values(tw_sad, "END")
            xsuite_values   = _bend_twiss_values(tw_xs, "end")
            et_values       = edwards_teng_optics_at(tw_xs, "end")
            sad_r1          = tw_sad["R1", "END"]

            sad_r1_values.append(sad_r1)
            sad_values_by_dx.append(sad_values)
            xsuite_values_by_dx.append(xsuite_values)

            assert abs(sad_r1 - np.sin(rotation)) < 1.0E-3, (
                "SAD's R1 should sit on sin(ROTATE) once the bend is "
                "offset (docs/sad-behaviour.md) -- if this no longer "
                "holds, the SAD-side artifact's characterisation has "
                f"changed and needs re-investigating. Got R1="
                f"{sad_r1:.6f} at dx={dx:.0e}.")
            assert abs(et_values["r11"]) < 1.0E-2, (
                "Xsuite's own coupling should stay small and physically "
                f"continuous, unlike SAD's. Got r11={et_values['r11']:.3e} "
                f"at dx={dx:.0e}.")

            for name in ("betx", "bety", "alfx", "alfy"):
                diff = abs(sad_values[name] - xsuite_values[name])
                assert diff > 5.0E-4, (
                    f"SAD's {name} should diverge from Xsuite's by a "
                    "large, tolerance-clearing amount alongside R1/R4 for "
                    f"a rotated, offset, curved bend. Got diff={diff:.3e} "
                    f"at dx={dx:.0e}.")
    finally:
        os.chdir(cwd)

    assert abs(sad_r1_values[0] - sad_r1_values[1]) < 1.0E-3, (
        "SAD's R1 should barely change between two offset magnitudes "
        "three orders of magnitude apart -- a real dynamical coupling "
        "effect would scale with the offset; this is the core evidence "
        "that it does not.")

    for name in ("betx", "bety", "alfx", "alfy"):
        assert abs(
                sad_values_by_dx[0][name] - sad_values_by_dx[1][name]
                ) < 1.0E-3, (
            f"SAD's {name} should likewise barely change between the two "
            "offset magnitudes three orders of magnitude apart -- the "
            "same magnitude-independent signature as R1/R4.")

################################################################################
# F1/FRINGE soft-edge fringe import (_import_sad_bend_fringes) -- see
# docs/sad-behaviour.md and docs/design-decisions.md
################################################################################
def test_bend_fringe_import_defaults_off(write_lattice, tmp_path):
    """
    Without _import_sad_bend_fringes, F1/FRINGE on a BEND should have no
    effect on the converted xt.Bend -- edge_entry_fint/hgap stay at
    Xsuite's own defaults, same as if F1/FRINGE were never set.
    """
    lattice_text = """\
    MOMENTUM    = 1.0 GEV;

    BEND        TEST_BEND   = (
        L       = 1.2
        ANGLE   = 0.08
        F1      = 0.04
        FRINGE  = 1
    );

    MARK        START       = ()
                END         = ();

    LINE        TEST_LINE   = (START TEST_BEND END);
    """
    lattice_path = write_lattice(lattice_text, filename = "bend_fringe_import_default_off.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    bend = line["test_bend"]
    assert bend.edge_entry_fint == 0.0 and bend.edge_entry_hgap == 0.0, (
        "F1/FRINGE should be ignored by default (_import_sad_bend_fringes "
        "defaults to False) -- edge_entry_fint/hgap should stay at "
        "Xsuite's own defaults, not be populated from F1.")

@pytest.mark.parametrize("fringe, entry_active, exit_active", [(-1, True, False), (-2, False, True)])
def test_bend_fringe_import_fringe_gates_single_edge(
        write_lattice, tmp_path, fringe, entry_active, exit_active):
    """
    FRINGE=-1/-2 should gate the fringe import to a single edge (entry-only/
    exit-only respectively) -- the other edge should stay at Xsuite's own
    defaults, not be populated from F1.
    """
    lattice_text = f"""\
    MOMENTUM    = 1.0 GEV;

    BEND        TEST_BEND   = (
        L       = 1.2
        ANGLE   = 0.08
        F1      = 0.04
        FRINGE  = {fringe}
    );

    MARK        START       = ()
                END         = ();

    LINE        TEST_LINE   = (START TEST_BEND END);
    """
    lattice_path = write_lattice(
        lattice_text, filename = f"bend_fringe_import_fringe_{fringe}.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path            = str(lattice_path),
        output_directory            = "N/A",
        _verbose                    = False,
        _test_mode                  = True,
        _import_sad_bend_fringes    = True)

    bend = line["test_bend"]
    if entry_active:
        assert bend.edge_entry_fint != 0.0, (
            f"FRINGE={fringe} should activate the entry edge fringe.")
    else:
        assert bend.edge_entry_fint == 0.0 and bend.edge_entry_hgap == 0.0, (
            f"FRINGE={fringe} should leave the entry edge at Xsuite's own "
            "defaults.")
    if exit_active:
        assert bend.edge_exit_fint != 0.0, (
            f"FRINGE={fringe} should activate the exit edge fringe.")
    else:
        assert bend.edge_exit_fint == 0.0 and bend.edge_exit_hgap == 0.0, (
            f"FRINGE={fringe} should leave the exit edge at Xsuite's own "
            "defaults.")

@pytest.mark.parametrize("delta", [0.0])
def test_bend_fringe_import_matches_sad_on_momentum(write_lattice, tmp_path, delta):
    """
    With _import_sad_bend_fringes=True, on-momentum (delta=0) tracking
    through a converted ANGLE!=0 BEND should match SAD closely -- the
    fh=F1/12 mapping is a derived closed form here, not an approximation
    (docs/sad-behaviour.md).
    """
    L, ANGLE, F1 = 1.2, 0.08, 0.04
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

        BEND        TEST_BEND   = (
            L       = {L}
            ANGLE   = {ANGLE}
            F1      = {F1}
            FRINGE  = 1
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text, filename = f"bend_fringe_import_on_momentum_{delta:+.3f}.sad")

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

    np.testing.assert_allclose(
        xs_particles.py, sad_particles["py"], rtol = 1E-3, atol = 1E-12,
        err_msg = (
            "On-momentum, the fh=F1/12 closed form should reproduce SAD's "
            "BEND fringe kick to a fraction of a percent."))

@pytest.mark.parametrize("delta", [0.03, -0.03])
def test_bend_fringe_import_off_momentum_residual_is_bounded(write_lattice, tmp_path, delta):
    """
    Off-momentum, Xsuite's native fint/hgap fringe formula scales the
    wrong way with delta relative to SAD (docs/sad-behaviour.md,
    docs/design-decisions.md) -- a known, characterised limitation, not a
    converter bug. This asserts the CURRENT bounded residual explicitly:
    if Xsuite/MAD-NG's upstream formula ever changes, this test should
    start failing (residual outside the asserted band) and surface for
    review, rather than silently continuing to pass or silently staying
    wrong.
    """
    L, ANGLE, F1 = 1.2, 0.08, 0.04
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

        BEND        TEST_BEND   = (
            L       = {L}
            ANGLE   = {ANGLE}
            F1      = {F1}
            FRINGE  = 1
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """
        lattice_path = write_lattice(
            lattice_text, filename = f"bend_fringe_import_off_momentum_{delta:+.3f}.sad")

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

    rel_err_pct = 100 * (xs_particles.py[0] - sad_particles["py"][0]) / sad_particles["py"][0]
    # Measured residual at this geometry/delta: +1.65% (delta=+0.03),
    # +3.46% (delta=-0.03). Bounded tightly around the measured value so
    # an upstream fix (residual shrinking) surfaces for review, not a
    # silent pass.
    expected_pct = {0.03: 1.65, -0.03: 3.46}[delta]
    assert abs(rel_err_pct - expected_pct) < 0.5, (
        f"Off-momentum residual for delta={delta} should stay near the "
        f"currently-characterised {expected_pct}% (got {rel_err_pct:.3f}%). "
        "A residual well outside this band means Xsuite's native fringe "
        "momentum-scaling has changed -- worth reviewing whether the "
        "off-momentum limitation this flag carries can now be relaxed.")
