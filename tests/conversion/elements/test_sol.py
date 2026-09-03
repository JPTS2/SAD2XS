"""
================================================================================
Tests for SAD SOL conversion
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

from scipy.constants import c as clight

from sad2xs.config import Config
from sad2xs.converter._004_element_converter import convert_solenoids
from sad2xs.sad_helpers import track_sad, transfer_matrix_sad
from tests.support.config import (
    DELTA_DELTA_ATOL,
    DELTA_DELTA_RTOL,
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
# Diagnostic Helpers
################################################################################
SOL_ARTIFACT_CATEGORY = "conversion/elements/sol"

def _sol_expected_ks(bz, p0c = 1.0E9):
    """
    Return the expected Xsuite solenoid ks from SAD BZ at the test momentum.
    """
    return bz * clight / p0c


def _set_reference_environment(environment, p0c = 1.0E9, q0 = 1.0):
    """
    Populate the minimum environment variables needed by direct SOL conversion.
    """
    environment["p0c"] = p0c
    environment["q0"] = q0
    environment["mass0"] = xt.ELECTRON_MASS_EV
    environment.particle_ref = xt.Particles(
        p0c   = p0c,
        q0    = q0,
        mass0 = xt.ELECTRON_MASS_EV)
    return environment

def _sol_tracking_tolerances():
    """
    Return coordinate tolerances used by solenoid tracking comparisons.
    """
    return {
        "x":     (DELTA_X_ATOL, DELTA_X_RTOL),
        "px":    (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":     (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py":    (DELTA_PY_ATOL, DELTA_PY_RTOL),
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
    }

def _sol_twiss_tolerances():
    """
    Return coordinate tolerances used by solenoid Twiss comparisons.
    """
    return {
        "s":     (1E-9, 1E-5),
        "betx":  (1E-9, 1E-5),
        "bety":  (1E-9, 1E-5),
        "alfx":  (1E-9, 1E-5),
        "alfy":  (1E-9, 1E-5),
        "x":     (DELTA_X_ATOL, DELTA_X_RTOL),
        "px":    (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":     (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py":    (DELTA_PY_ATOL, DELTA_PY_RTOL),
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
    }

def _sol_orbit_values(twiss_table, marker):
    """
    Return orbit coordinates at a marker from a SAD or Xsuite Twiss table.
    """
    return {
        "s":     twiss_table["s", marker],
        "x":     twiss_table["x", marker],
        "px":    twiss_table["px", marker],
        "y":     twiss_table["y", marker],
        "py":    twiss_table["py", marker],
        "zeta":  twiss_table["zeta", marker],
        "delta": twiss_table["delta", marker],
    }

def _sol_optics_values(twiss_table, marker):
    """
    Return optics coordinates at a marker from a SAD Twiss table.
    """
    return {
        "s":     twiss_table["s", marker],
        "betx":  twiss_table["betx", marker],
        "bety":  twiss_table["bety", marker],
        "alfx":  twiss_table["alfx", marker],
        "alfy":  twiss_table["alfy", marker],
        "zeta":  twiss_table["zeta", marker],
        "delta": twiss_table["delta", marker],
    }

def _sol_xsuite_optics_values(twiss_table, marker):
    """
    Return Xsuite optics in SAD's coupled beta/alpha convention.
    """
    edwards_teng = edwards_teng_optics_at(twiss_table, marker)
    return {
        "s":     twiss_table["s", marker],
        "betx":  edwards_teng["betx"],
        "bety":  edwards_teng["bety"],
        "alfx":  edwards_teng["alfx"],
        "alfy":  edwards_teng["alfy"],
        "zeta":  twiss_table["zeta", marker],
        "delta": twiss_table["delta", marker],
    }

def _sol_initial_coordinates(
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

def _sol_sad_coordinates(sad_particles):
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

def _sol_xsuite_coordinates(xs_particles):
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

def _assert_sol_tracking_matches_sad(
        test_name,
        lattice_text,
        initial_coordinates,
        sad_coordinates,
        xsuite_coordinates,
        parameters,
        notes = None):
    """
    Assert solenoid tracking equivalence and write a Markdown report on failure.
    """
    tolerances = _sol_tracking_tolerances()
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
            category   = SOL_ARTIFACT_CATEGORY,
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
            f"Converted solenoid tracking should match SAD. "
            f"Failed coordinates: {failed_coordinates}. "
            f"Diagnostic report: {report_path}")

def _assert_sol_twiss_matches_sad(
        test_name,
        lattice_text,
        sad_values,
        xsuite_values,
        parameters,
        notes = None):
    """
    Assert solenoid Twiss equivalence and write a Markdown report on failure.
    """
    tolerances = _sol_twiss_tolerances()
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
            category   = SOL_ARTIFACT_CATEGORY,
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
            f"Converted solenoid Twiss should match SAD. "
            f"Failed values: {failed_values}. "
            f"Diagnostic report: {report_path}")

################################################################################
# SAD Lattice Helpers
################################################################################
def _bound_solenoid_lattice(
        bz,
        sol_out_bz = None,
        disfrin = True,
        sol_in_parameters = "",
        sol_out_parameters = "",
        middle_element = "DRIFT       SOL_DRIFT   = (L = 1.0);",
        middle_name = "SOL_DRIFT",
        line_expression = None):
    """
    Build a standard bound-solenoid SAD lattice around one middle element.

    `disfrin` defaults to `True` (`DISFRIN = 1` on both boundaries) since
    SAD2XS does not model the SAD solenoid fringe kick — that is the fair
    comparison baseline. Pass `disfrin = False` deliberately to exercise the
    known, accepted divergence this causes (see `test_sol_disfrin_off_...`).
    """
    if line_expression is None:
        line_expression = f"START SOL_IN {middle_name} SOL_OUT END"
    if sol_out_bz is None:
        sol_out_bz = bz
    disfrin_parameter = "DISFRIN = 1" if disfrin else ""

    return f"""\
    MOMENTUM    = 1.0 GEV;

    {middle_element}
    SOL         SOL_IN      = (BZ = {bz} BOUND = 1 GEO = 1 {disfrin_parameter} {sol_in_parameters})
                SOL_OUT     = (BZ = {sol_out_bz} BOUND = 1 {disfrin_parameter} {sol_out_parameters});

    MARK        START       = ()
                END         = ();

    LINE        TEST_LINE   = ({line_expression});
    """

def _reference_transform_lattice(
        sol_in_parameters = "",
        sol_out_parameters = "",
        line_expression = None):
    """
    Build a zero-field SOL lattice for reference-transform physics checks.
    """
    if line_expression is None:
        line_expression = "START SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END"

    return f"""\
    MOMENTUM    = 1.0 GEV;

    DRIFT       SOL_DRIFT   = (L = 1.0);
    SOL         SOL_IN      = (BZ = 0.0 BOUND = 1 {sol_in_parameters})
                SOL_OUT     = (BZ = 0.0 BOUND = 1 {sol_out_parameters});

    MARK        START       = ()
                SOL_START   = ()
                SOL_END     = ()
                END         = ();

    LINE        TEST_LINE   = ({line_expression});
    """

def _compare_sol_orbit_twiss(
        write_lattice,
        rebuild_lattice,
        tmp_path,
        lattice_text,
        filename,
        test_name,
        sad_marker,
        xsuite_marker,
        parameters,
        notes = None):
    """
    Compare SAD and Xsuite orbit Twiss values for one generated SOL lattice.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_path = write_lattice(lattice_text, filename = filename)
        rebuilt_path = rebuild_lattice(lattice_path)

        tw_sad = twiss_sad(
            lattice_filepath        = lattice_path.name,
            line_name               = "TEST_LINE",
            calc6d                  = False,
            closed                  = False,
            reverse_element_order   = False,
            reverse_survey_horizontal  = False,
            rfsw              = True,
            rad               = False,
            radcod        = False,
            radtaper               = False,
            additional_commands     = "")

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path = str(rebuilt_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)

        tw_xs = line.twiss4d(
            _continue_if_lost = True,
            start             = xt.START,
            end               = xt.END,
            betx              = 1.0,
            bety              = 1.0)
    finally:
        os.chdir(cwd)

    _assert_sol_twiss_matches_sad(
        test_name      = test_name,
        lattice_text   = lattice_text,
        sad_values     = _sol_orbit_values(tw_sad, sad_marker),
        xsuite_values  = _sol_orbit_values(tw_xs, xsuite_marker),
        parameters     = parameters,
        notes          = notes)

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
@pytest.mark.parametrize(
    "bz",
    [-0.1, 0.0, 0.1])
def test_sol_converter_creates_xsuite_uniform_solenoid(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        sad2xs_config,
        bz):
    """
    Parsed SAD SOL elements should become Xsuite UniformSolenoid elements.
    """
    _set_reference_environment(xsuite_environment)

    convert_solenoids(
        parsed_elements = parsed_elements(
            element_type      = "sol",
            element_name      = "test_sol",
            element_variables = {"bz": bz}),
        environment = xsuite_environment,
        config      = sad2xs_config)

    solenoid = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_sol",
        element_type = xt.UniformSolenoid)

    assert solenoid.ks == pytest.approx(_sol_expected_ks(bz)), (
        "Converted SOL should preserve SAD BZ as Xsuite solenoid ks.")

def test_sol_converter_creates_all_solenoids(
        xsuite_environment,
        assert_environment_element,
        sad2xs_config):
    """
    Multiple parsed SAD SOL elements should all be converted.
    """
    _set_reference_environment(xsuite_environment)

    convert_solenoids(
        parsed_elements = {
            "sol": {
                "sol_a": {"bz": 0.1},
                "sol_b": {"bz": -0.1},
            },
        },
        environment = xsuite_environment,
        config      = sad2xs_config)

    assert set(xsuite_environment.element_dict) == {"sol_a", "sol_b"}, (
        "All parsed SAD SOL elements should be present in the environment.")
    assert_environment_element(
        environment  = xsuite_environment,
        element_name = "sol_a",
        element_type = xt.UniformSolenoid)
    assert_environment_element(
        environment  = xsuite_environment,
        element_name = "sol_b",
        element_type = xt.UniformSolenoid)

########################################
# DISFRIN Warning
########################################
def test_sol_converter_warns_once_for_lattice_missing_disfrin(
        xsuite_environment,
        caplog):
    """
    Converting a lattice with solenoids missing DISFRIN=1 should warn exactly
    once for the whole lattice, not once per non-compliant element.
    """
    caplog.set_level(
        logging.DEBUG,
        logger = "sad2xs.converter._004_element_converter")
    _set_reference_environment(xsuite_environment)

    convert_solenoids(
        parsed_elements = {
            "sol": {
                "sol_a": {"bz": 0.1},
                "sol_b": {"bz": -0.1},
                "sol_c": {"bz": 0.2, "disfrin": 1.0},
            },
        },
        environment = xsuite_environment,
        config      = Config())

    disfrin_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "DISFRIN" in r.getMessage()]
    assert len(disfrin_warnings) == 1, (
        "Converting a lattice with solenoids missing DISFRIN=1 should warn "
        f"exactly once. Got: {[r.getMessage() for r in caplog.records]!r}")
    debug_details = [
        record.getMessage() for record in caplog.records
        if record.levelno == logging.DEBUG
        and "Solenoids without DISFRIN=1" in record.getMessage()]
    assert debug_details == [
        "Solenoids without DISFRIN=1: sol_a, sol_b"
    ], "Debug logging should name the solenoids behind the summary warning."

def test_sol_converter_does_not_warn_when_every_solenoid_has_disfrin(
        xsuite_environment,
        caplog):
    """
    Converting a lattice where every solenoid has DISFRIN=1 should not warn.
    The parser stores DISFRIN = 1 as the float 1.0, so that is what the
    converter must recognise.
    """
    _set_reference_environment(xsuite_environment)

    convert_solenoids(
        parsed_elements = {
            "sol": {
                "sol_a": {"bz": 0.1, "disfrin": 1.0},
                "sol_b": {"bz": -0.1, "disfrin": 1.0},
            },
        },
        environment = xsuite_environment,
        config      = Config())

    disfrin_warnings = [
        r for r in caplog.records if "DISFRIN" in r.getMessage()]
    assert disfrin_warnings == [], (
        "Converting a lattice where every solenoid has DISFRIN=1 should not "
        f"warn. Got: {[r.getMessage() for r in disfrin_warnings]!r}")

def test_sol_converter_disfrin_warning_visible_in_quiet_mode(
        xsuite_environment,
        sad2xs_config,
        caplog):
    """
    The DISFRIN warning must remain visible in quiet mode: quiet mode
    suppresses progress and debug output, never warnings.
    """
    _set_reference_environment(xsuite_environment)

    convert_solenoids(
        parsed_elements = {
            "sol": {
                "sol_a": {"bz": 0.1},
            },
        },
        environment = xsuite_environment,
        config      = sad2xs_config)

    disfrin_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "DISFRIN" in r.getMessage()]
    assert len(disfrin_warnings) == 1, (
        "The DISFRIN warning should be emitted even in quiet mode. "
        f"Got records: {[r.getMessage() for r in caplog.records]!r}")

################################################################################
# Bound Solenoid Reference Elements
################################################################################
########################################
# Direct Converter Behaviour
########################################
def test_sol_bound_converter_creates_compound_reference_transform_line(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        sad2xs_config):
    """
    Bound SAD SOL elements should create the current compound transform line.
    """
    _set_reference_environment(xsuite_environment)

    convert_solenoids(
        parsed_elements = parsed_elements(
            element_type      = "sol",
            element_name      = "test_sol",
            element_variables = {
                "bz":     0.1,
                "bound":  1.0,
                "dx":     0.001,
                "dy":     -0.002,
                "dz":     0.003,
                "chi1":   0.004,
                "chi2":   -0.005,
                "chi3":   0.006,
            }),
        environment = xsuite_environment,
        config      = sad2xs_config)

    assert "test_sol" in xsuite_environment.lines, (
        "Bound SOL conversion should create a compound Xsuite line.")
    assert xsuite_environment.lines["test_sol"].element_names == [
        "test_sol_bound",
        "test_sol_dxy",
        "test_sol_dz",
        "test_sol_rot",
    ], (
        "Bound SOL compound line should preserve the documented transform "
        "component order.")

    assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_sol_bound",
        element_type = xt.UniformSolenoid)
    assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_sol_dxy",
        element_type = xt.Translation)
    assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_sol_dz",
        element_type = xt.TimeDelay)
    assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_sol_rot",
        element_type = xt.Rotation)

def test_sol_bound_converter_applies_reference_transform_signs(
        parsed_elements,
        xsuite_environment,
        sad2xs_config):
    """
    Bound SOL reference transforms should apply SAD-to-Xsuite sign conventions.
    """
    _set_reference_environment(xsuite_environment)

    convert_solenoids(
        parsed_elements = parsed_elements(
            element_type      = "sol",
            element_name      = "test_sol",
            element_variables = {
                "bz":     0.1,
                "bound":  1.0,
                "dx":     0.001,
                "dy":     -0.002,
                "dz":     0.003,
                "chi1":   0.004,
                "chi2":   -0.005,
                "chi3":   0.006,
            }),
        environment = xsuite_environment,
        config      = sad2xs_config)

    assert xsuite_environment["test_sol_dxy"].shift_x == pytest.approx(-0.001), (
        "Bound SOL DX should use the current SAD2XS sign convention.")
    assert xsuite_environment["test_sol_dxy"].shift_y == pytest.approx(0.002), (
        "Bound SOL DY should use the current SAD2XS sign convention.")
    assert xsuite_environment["test_sol_dz"].shift_zeta == pytest.approx(-0.003), (
        "Bound SOL DZ should map to the current SAD2XS longitudinal shift.")
    assert xsuite_environment["test_sol_rot"].rot_y_rad == pytest.approx(0.004), (
        "Bound SOL CHI1 should store radians with the current SAD2XS sign convention.")
    assert xsuite_environment["test_sol_rot"].rot_x_rad == pytest.approx(0.005), (
        "Bound SOL CHI2 should store radians with the current SAD2XS sign convention.")
    assert xsuite_environment["test_sol_rot"].rot_s_rad == pytest.approx(0.006), (
        "Bound SOL CHI3 should store radians with the current SAD2XS sign convention.")

def test_sol_bound_reference_transforms_use_current_xsuite_api(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        sad2xs_config):
    """
    Bound SOL transforms should use the current Xsuite transform elements.
    """
    _set_reference_environment(xsuite_environment)

    convert_solenoids(
        parsed_elements = parsed_elements(
            element_type      = "sol",
            element_name      = "test_sol",
            element_variables = {
                "bz":     0.1,
                "bound":  1.0,
                "dx":     0.001,
                "dy":     -0.002,
                "dz":     0.003,
                "chi1":   0.004,
                "chi2":   -0.005,
                "chi3":   0.006,
            }),
        environment = xsuite_environment,
        config      = sad2xs_config)

    assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_sol_dxy",
        element_type = xt.Translation)
    assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_sol_dz",
        element_type = xt.TimeDelay)
    assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_sol_rot",
        element_type = xt.Rotation)

################################################################################
# Pipeline Behaviour
################################################################################
########################################
# Bound Solenoid Regions
########################################
def test_sol_pipeline_converts_elements_between_bound_solenoids(write_lattice):
    """
    Elements between bound SOL markers should be converted into solenoid regions.
    """
    bz = 0.1
    lattice_text = _bound_solenoid_lattice(bz = bz)
    lattice_path = write_lattice(
        lattice_text,
        filename = "sol_pipeline_converts_bound_region.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        line_name        = "TEST_LINE",
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert "sol_drife_sol_in" not in line.element_names, (
        "Typo guard: converted SOL region should use the expected element name.")
    assert "sol_drift_sol_in" in line.element_names, (
        "The drift between bound solenoids should be replaced by a solenoid "
        "region element tagged with the incoming SOL name.")
    assert isinstance(line["sol_drift_sol_in"], xt.UniformSolenoid), (
        "The converted region between bound solenoids should be active.")
    assert line["sol_drift_sol_in"].length == pytest.approx(1.0), (
        "The converted solenoid region should preserve the middle element length.")
    assert line["sol_drift_sol_in"].ks == pytest.approx(_sol_expected_ks(bz)), (
        "The converted solenoid region should use the incoming bound SOL field.")

def test_sol_pipeline_thin_cavity_between_bound_solenoids_needs_no_conversion(
        write_lattice,
        caplog):
    """
    A thin (zero-length) Cavity between bound SOL markers -- e.g. one of
    RF-MULT's interleaved slices -- has no propagation distance for the
    continuous solenoid field to act over, so it should not be flagged as
    unconverted the way a thick, unhandled element would be.
    """
    caplog.set_level(
        logging.WARNING,
        logger = "sad2xs.converter._006_solenoid_converter")

    lattice_text = _bound_solenoid_lattice(
        bz              = 0.1,
        middle_element  = "MULT        M1          = (VOLT = 1.0E5 FREQ = 5.0E8);",
        middle_name     = "M1")
    lattice_path = write_lattice(
        lattice_text,
        filename = "sol_pipeline_thin_cavity_needs_no_conversion.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        line_name        = "TEST_LINE",
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert "m1_cavi_0" in line.element_names, (
        "The thin RF-MULT Cavity slice should still be present in the "
        "converted line.")
    assert isinstance(line["m1_cavi_0"], xt.Cavity), (
        "The thin RF-MULT Cavity slice should remain an Xsuite Cavity, "
        "not be swept into a solenoid-embedding replacement.")

    warnings = [
        record for record in caplog.records
        if "has not been converted" in record.getMessage()]
    assert warnings == [], (
        "A thin Cavity between bound solenoids needs no solenoid embedding "
        "and should not trigger the `has not been converted` warning.")

def test_sol_pipeline_thick_cavity_between_bound_solenoids_still_warns(
        write_lattice,
        caplog):
    """
    A thick (nonzero-length) Cavity between bound SOL markers genuinely
    does need solenoid embedding (a real propagation distance through the
    continuous field), which is not yet implemented -- it should still
    trigger the existing warning rather than being silently accepted.
    """
    caplog.set_level(
        logging.WARNING,
        logger = "sad2xs.converter._006_solenoid_converter")

    lattice_text = _bound_solenoid_lattice(
        bz              = 0.1,
        middle_element  = "CAVI        C1          = (L = 0.5 VOLT = 1.0E5 FREQ = 5.0E8);",
        middle_name     = "C1")
    lattice_path = write_lattice(
        lattice_text,
        filename = "sol_pipeline_thick_cavity_still_warns.sad")

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    warnings = [
        record for record in caplog.records
        if "has not been converted" in record.getMessage()]
    assert len(warnings) == 1, (
        "A thick Cavity between bound solenoids is not yet handled and "
        "should still trigger the `has not been converted` warning.")

def test_sol_pipeline_thick_rf_mult_multipole_slices_embed_solenoid_field(
        write_lattice,
        caplog):
    """
    A thick RF-MULT (K1 and VOLT both set) between bound SOL markers slices
    into interleaved Multipole/Cavity pairs (see test_mult.py). Each
    Multipole slice is a real xt.Multipole once the compound line is
    flattened, so it should be picked up by the existing generic
    Multipole-in-solenoid embedding path exactly as a plain K1 MULT would
    be -- no RF-specific handling needed there. The interleaved Cavity
    slices should remain exempt, as already covered above.
    """
    caplog.set_level(
        logging.WARNING,
        logger = "sad2xs.converter._006_solenoid_converter")

    bz = 0.1
    k1 = 0.3
    lattice_text = _bound_solenoid_lattice(
        bz              = bz,
        middle_element  = f"MULT        M1          = "
                           f"(L = 2.0 K1 = {k1} VOLT = 1.0E5 FREQ = 5.0E8);",
        middle_name     = "M1")
    lattice_path = write_lattice(
        lattice_text,
        filename = "sol_pipeline_thick_rf_mult_embeds_solenoid_field.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        line_name        = "TEST_LINE",
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    n_slices = Config().N_SLICES_MULT_RF

    for i in range(n_slices):
        mult_slice = line[f"m1_mult_{i}_sol_in"]
        assert isinstance(mult_slice, xt.UniformSolenoid), (
            f"RF-MULT Multipole slice m1_mult_{i} between bound solenoids "
            "should be embedded into a UniformSolenoid, same as a plain "
            f"K1 MULT would be. Got {type(mult_slice)}.")
        assert mult_slice.ks == pytest.approx(_sol_expected_ks(bz)), (
            f"m1_mult_{i} should carry the incoming bound SOL field."
        )
        assert mult_slice.knl[1] == pytest.approx(k1 / n_slices), (
            f"m1_mult_{i} should preserve its share of K1 through the "
            "solenoid embedding.")

        cavi_slice = line[f"m1_cavi_{i}"]
        assert isinstance(cavi_slice, xt.Cavity), (
            f"RF-MULT Cavity slice m1_cavi_{i} should remain an Xsuite "
            f"Cavity, not be swept into solenoid embedding. Got "
            f"{type(cavi_slice)}.")

    warnings = [
        record for record in caplog.records
        if "has not been converted" in record.getMessage()]
    assert warnings == [], (
        "A thick RF-MULT between bound solenoids should convert fully via "
        "the existing Multipole/Cavity embedding paths, with no "
        "`has not been converted` warning.")

def test_sol_pipeline_requires_geometric_solenoid_in_bound_pair(write_lattice):
    """
    Bound SOL pairs without a geometric boundary should fail clearly.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       SOL_DRIFT   = (L = 1.0);
        SOL         SOL_IN      = (BZ = 0.1 BOUND = 1)
                    SOL_OUT     = (BZ = 0.0 BOUND = 1);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START SOL_IN SOL_DRIFT SOL_OUT END);
        """,
        filename = "sol_pipeline_requires_geo_bound_pair.sad")

    with pytest.raises(ValueError, match = "Neither solenoid in pair"):
        s2x.convert_sad_to_xsuite(
            sad_lattice_path = str(lattice_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)


########################################
# Powered K1 Soft-Edge Fringes
########################################
def test_centered_mult_k1_fringe_inside_powered_solenoid_keeps_source_map(
        write_lattice, caplog):
    """Solenoid segment edges should conjugate a centred K1 fringe map."""
    lattice_path = write_lattice(
        _bound_solenoid_lattice(
            bz = 0.1,
            middle_element = (
                "MULT M1=(L=0.5 K1=0.1 F1=0.02 F2=0.01 "
                "FRINGE=3 DISFRIN=1);"),
            middle_name = "M1"),
        filename = "mult_fringe_inside_powered_solenoid.sad")

    caplog.set_level(
        logging.WARNING,
        logger = "sad2xs.converter._006_solenoid_converter")
    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        line_name        = "TEST_LINE",
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert isinstance(line["m1_sol_in"], xt.UniformSolenoid)
    assert line["m1_sol_in"].ks == pytest.approx(_sol_expected_ks(0.1))
    fringe_names = [
        name for name in line.element_names if "m1_fringe_" in name]
    assert fringe_names == ["m1_fringe_in", "m1_fringe_out"]
    assert "combined paraxial body map" not in caplog.text
    assert "offset element(s) with SAD K1 soft-edge fringes" not in caplog.text


def test_offset_mult_k1_fringes_in_powered_solenoid_warn_once(
        write_lattice, caplog):
    """Offset K1 fringe maps in powered BZ should raise one clear warning."""
    lattice_path = write_lattice(
        _bound_solenoid_lattice(
            bz = 0.1,
            middle_element = """
                MULT M1=(L=0.5 K1=0.1 F1=0.02 FRINGE=3 DX=0.001 DISFRIN=1)
                     M2=(L=0.5 K1=0.1 F1=0.02 FRINGE=3 DY=-0.002 DISFRIN=1);""",
            line_expression = "START SOL_IN M1 M2 SOL_OUT END"),
        filename = "offset_mult_fringes_inside_powered_solenoid.sad")

    caplog.set_level(
        logging.DEBUG,
        logger = "sad2xs.converter._006_solenoid_converter")
    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        line_name        = "TEST_LINE",
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    warnings = [
        record for record in caplog.records
        if record.levelno == logging.WARNING
        and "offset element(s) with SAD K1 soft-edge fringes"
        in record.getMessage()]
    assert len(warnings) == 1, (
        "Offset K1 fringes in powered BZ should emit one summary warning. "
        f"Got: {[record.getMessage() for record in caplog.records]!r}")
    assert warnings[0].getMessage().startswith(
        "2 offset element(s) with SAD K1 soft-edge fringes")
    debug_details = [
        record.getMessage() for record in caplog.records
        if record.levelno == logging.DEBUG
        and "Offset elements with K1 fringes" in record.getMessage()]
    assert debug_details == [
        "Offset elements with K1 fringes affected by the powered-solenoid "
        "limitation: m1, m2"
    ], "Debug logging should name the elements behind the summary warning."


########################################
# K0/SK0 Body Limitation
########################################
def test_mult_dipole_body_in_powered_solenoid_warns_once(
        write_lattice, caplog):
    """K0/SK0 in powered BZ should expose the known body-map difference."""
    lattice_path = write_lattice(
        _bound_solenoid_lattice(
            bz = 0.1,
            middle_element = """
                MULT M1=(L=0.5 K0=0.001 K1=0.1 DISFRIN=1)
                     M2=(L=0.5 SK0=-0.002 K1=0.1 DISFRIN=1);""",
            line_expression = "START SOL_IN M1 M2 SOL_OUT END"),
        filename = "mult_dipole_body_inside_powered_solenoid.sad")

    caplog.set_level(
        logging.DEBUG,
        logger = "sad2xs.converter._006_solenoid_converter")
    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        line_name        = "TEST_LINE",
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    warnings = [
        record for record in caplog.records
        if record.levelno == logging.WARNING
        and "combined paraxial body map" in record.getMessage()]
    assert len(warnings) == 1, (
        "K0/SK0 bodies in powered BZ should emit one summary warning. "
        f"Got: {[record.getMessage() for record in caplog.records]!r}")
    assert warnings[0].getMessage().startswith("2 element(s)")
    debug_details = [
        record.getMessage() for record in caplog.records
        if record.levelno == logging.DEBUG
        and "K0/SK0 body limitation" in record.getMessage()]
    assert debug_details == [
        "Elements affected by the powered-solenoid K0/SK0 body limitation: "
        "m1, m2"
    ], "Debug logging should name the elements behind the summary warning."


@pytest.mark.parametrize("dipole_parameter", ["K0", "SK0"])
def test_mult_dipole_body_in_powered_solenoid_has_measured_matrix_residual(
        write_lattice, tmp_path, dipole_parameter):
    """The K0/SK0 response should expose the accepted combined-body difference."""
    matrices = {"sad": {}, "xsuite": {}}
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        for state, strength in (("off", 0.0), ("on", 0.001)):
            lattice_text = _bound_solenoid_lattice(
                bz = 1.0,
                middle_element = (
                    f"MULT M1=(L=0.5 K1=0.1 "
                    f"{dipole_parameter}={strength} DISFRIN=1);"),
                middle_name = "M1")
            lattice_path = write_lattice(
                lattice_text,
                filename = (
                    f"mult_{dipole_parameter.lower()}_powered_bz_{state}.sad"))
            matrices["sad"][state] = transfer_matrix_sad(
                lattice_filepath = lattice_path.name,
                line_name        = "TEST_LINE")[:4, :4]
            line = s2x.convert_sad_to_xsuite(
                sad_lattice_path      = str(lattice_path),
                line_name             = "TEST_LINE",
                output_directory      = "N/A",
                SIMPLIFY_MULTIPOLES   = False,
                _verbose              = False,
                _test_mode            = True)
            matrices["xsuite"][state] = linear_transfer_matrix_4d(line)
    finally:
        os.chdir(cwd)

    sad_response = matrices["sad"]["on"] - matrices["sad"]["off"]
    xsuite_response = matrices["xsuite"]["on"] - matrices["xsuite"]["off"]
    response_scale = np.max(np.abs(sad_response))
    residual = np.max(np.abs(xsuite_response - sad_response))
    assert response_scale > 1e-10
    assert residual / response_scale == pytest.approx(0.997, abs = 0.002), (
        f"{dipole_parameter} in powered BZ should retain the measured "
        "SAD/Xsuite combined-body response residual. The isolated response "
        "is almost entirely missing in the split Xtrack representation. "
        f"Measured relative maximum: {residual / response_scale:.6e}.")


def test_shared_mult_keeps_one_fringe_map_and_context_specific_bodies(
        write_lattice):
    """Solenoid context belongs on each body, not on the shared face maps."""
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        MULT M1 = (L=0.5 K1=0.1 F1=0.02 FRINGE=3 DISFRIN=1);
        SOL S1 = (BZ=0.1 BOUND=1 GEO=1 DISFRIN=1)
            S2 = (BZ=0.1 BOUND=1 DISFRIN=1)
            S3 = (BZ=-0.2 BOUND=1 GEO=1 DISFRIN=1)
            S4 = (BZ=-0.2 BOUND=1 DISFRIN=1)
            S5 = (BZ=0.0 BOUND=1 GEO=1 DISFRIN=1)
            S6 = (BZ=0.0 BOUND=1 DISFRIN=1);
        MARK START=() END=();
        LINE TEST_LINE = (START S1 M1 S2 S3 M1 S4 S5 M1 S6 END);
        """,
        filename = "shared_mult_fringe_in_inconsistent_solenoids.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        line_name        = "TEST_LINE",
        output_directory = "N/A",
        SIMPLIFY_MULTIPOLES = False,
        _verbose         = False,
        _test_mode       = True)

    fringe_names = [
        name for name in line.element_names if "m1_fringe_" in name]
    assert fringe_names == [
        "m1_fringe_in", "m1_fringe_out",
        "m1_fringe_in", "m1_fringe_out",
        "m1_fringe_in", "m1_fringe_out"]
    assert isinstance(line["m1_s1"], xt.UniformSolenoid)
    assert isinstance(line["m1_s3"], xt.UniformSolenoid)
    assert isinstance(line["m1"], xt.Multipole)


########################################
# Powered K1 Soft-Edge SAD Tracking
########################################
@pytest.mark.parametrize(
    "case_name, fringe_name, fringe_value, bz, rotation",
    [
        ("f1_positive_bz", "F1", 0.4,  1.0,  0.0),
        ("f1_negative_bz", "F1", 0.4, -1.0,  0.3),
        ("f2_positive_bz", "F2", 0.03, 1.0,  0.0),
        ("f2_negative_bz", "F2", 0.03, -1.0, -0.2),
    ])
def test_centered_powered_mult_fringe_response_matches_sad_tracking(
        write_lattice, tmp_path, case_name, fringe_name, fringe_value, bz,
        rotation):
    """Adjacent solenoid segment edges should reproduce SAD's local-BZ face."""
    initial = {
        "x": np.array([0.0, 1.0e-6, -0.8e-6]),
        "px": np.array([0.0, -0.6e-6, 0.9e-6]),
        "y": np.array([0.0, 0.7e-6, 1.1e-6]),
        "py": np.array([0.0, 0.8e-6, -0.5e-6]),
        "zeta": np.zeros(3),
        "delta": np.array([0.0, 1.0e-6, -1.0e-6]),
    }

    def lattice(fringe):
        return _bound_solenoid_lattice(
            bz = bz,
            middle_element = (
                "MULT M1=(L=0.5 K1=0.1 "
                f"{fringe_name}={fringe_value if fringe else 0.0} "
                f"ROTATE={rotation} "
                f"FRINGE={3 if fringe else 0} DISFRIN=1);"),
            middle_name = "M1")

    sad_results = {}
    xsuite_results = {}
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        for state in ("off", "on"):
            lattice_text = lattice(state == "on")
            lattice_path = write_lattice(
                lattice_text,
                filename = f"mult_powered_{case_name}_{state}.sad")
            sad_results[state] = track_sad(
                lattice_filepath     = lattice_path.name,
                line_name            = "TEST_LINE",
                x_init               = initial["x"],
                px_init              = initial["px"],
                y_init               = initial["y"],
                py_init              = initial["py"],
                zeta_init            = initial["zeta"],
                delta_init           = initial["delta"],
                n_turns              = 1,
                rfsw                 = False,
                rad                  = False,
                fluc                 = False,
                radcod               = False,
                radtaper             = False,
                turn_by_turn_monitor = False,
                with_progress        = False,
                wall_time            = 30)
            line = s2x.convert_sad_to_xsuite(
                sad_lattice_path = str(lattice_path),
                line_name        = "TEST_LINE",
                output_directory = "N/A",
                SIMPLIFY_MULTIPOLES = False,
                _verbose         = False,
                _test_mode       = True)
            xsuite_results[state] = track_xsuite_particles(
                line,
                initial["x"], initial["px"],
                initial["y"], initial["py"],
                initial["zeta"], initial["delta"])
    finally:
        os.chdir(cwd)

    sad_coordinates = {
        key: _sol_sad_coordinates(sad_results["on"])[key]
        - _sol_sad_coordinates(sad_results["off"])[key]
        for key in ("x", "px", "y", "py", "zeta")}
    xsuite_coordinates = {
        key: _sol_xsuite_coordinates(xsuite_results["on"])[key]
        - _sol_xsuite_coordinates(xsuite_results["off"])[key]
        for key in ("x", "px", "y", "py", "zeta")}
    for coordinate in ("x", "px", "y", "py"):
        response_scale = np.max(np.abs(sad_coordinates[coordinate]))
        residual = np.max(np.abs(
            xsuite_coordinates[coordinate] - sad_coordinates[coordinate]))
        assert response_scale > 1e-10
        assert residual / response_scale < 1e-5, (
            f"Powered {fringe_name} response in {coordinate} has relative "
            f"SAD/Xsuite residual {residual / response_scale:.6e}.")
    np.testing.assert_allclose(
        xsuite_coordinates["zeta"], sad_coordinates["zeta"],
        rtol = 0.0, atol = 2e-14)

def test_sol_pipeline_preserves_reversed_bound_solenoid_order(write_lattice):
    """
    Reversed bound SOL components should still build a deterministic line.
    """
    lattice_path = write_lattice(
        _bound_solenoid_lattice(
            bz              = 0.1,
            sol_out_bz      = 0.0,
            line_expression = "START -SOL_IN SOL_DRIFT SOL_OUT END"),
        filename = "sol_pipeline_preserves_reversed_bound_order.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert "sol_drift_sol_out" in line.element_names, (
        "A reversed incoming SOL should use the ahead solenoid field for the "
        "converted middle region.")
    assert isinstance(line["sol_drift_sol_out"], xt.UniformSolenoid), (
        "The converted reversed region should remain an active solenoid.")
    assert line["sol_drift_sol_out"].ks == pytest.approx(0.0), (
        "The reversed incoming SOL case should use the ahead bound SOL field.")

################################################################################
# Physics Equivalence
################################################################################
########################################
# Orbit Twiss
########################################
@pytest.mark.parametrize(
    "bz",
    [0.0, -0.1, 0.1])
def test_sol_orbit_matches_sad_twiss_at_end(write_lattice, tmp_path, bz):
    """
    Converted bound SOL regions should match SAD closed-orbit Twiss values.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = _bound_solenoid_lattice(bz = bz)
        lattice_path = write_lattice(
            lattice_text,
            filename = f"sol_twiss_bz_{bz:+.3f}.sad")

        tw_sad = twiss_sad(
            lattice_filepath        = lattice_path.name,
            line_name               = "TEST_LINE",
            calc6d                  = False,
            closed                  = False,
            reverse_element_order   = False,
            reverse_survey_horizontal  = False,
            rfsw              = True,
            rad               = False,
            radcod        = False,
            radtaper               = False,
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
            betx              = 1.0,
            bety              = 1.0)
    finally:
        os.chdir(cwd)

    sad_values = _sol_orbit_values(tw_sad, "END")
    xsuite_values = _sol_orbit_values(tw_xs, "end")

    _assert_sol_twiss_matches_sad(
        test_name      = "test_sol_orbit_matches_sad_twiss_at_end",
        lattice_text   = lattice_text,
        sad_values     = sad_values,
        xsuite_values  = xsuite_values,
        parameters     = {"bz": bz})

########################################
# Optics Twiss
########################################
@pytest.mark.parametrize(
    "bz",
    [0.0, -0.1, 0.1])
def test_sol_optics_matches_sad_twiss_at_end(
        write_lattice,
        rebuild_lattice,
        tmp_path,
        bz):
    """
    Converted bound SOL regions should match SAD beta/alpha Twiss values.

    This is deliberately separate from the orbit comparison so any active
    solenoid optics discrepancy is isolated from reference-frame conversion.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = _bound_solenoid_lattice(bz = bz)
        lattice_path = write_lattice(
            lattice_text,
            filename = f"sol_optics_twiss_bz_{bz:+.3f}.sad")
        rebuilt_path = rebuild_lattice(lattice_path)

        tw_sad = twiss_sad(
            lattice_filepath        = lattice_path.name,
            line_name               = "TEST_LINE",
            calc6d                  = False,
            closed                  = False,
            reverse_element_order   = False,
            reverse_survey_horizontal  = False,
            rfsw              = True,
            rad               = False,
            radcod        = False,
            radtaper               = False,
            additional_commands     = "")

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path = str(rebuilt_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)

        tw_xs = line.twiss4d(
            _continue_if_lost = True,
            start             = xt.START,
            end               = xt.END,
            betx              = 1.0,
            bety              = 1.0)
    finally:
        os.chdir(cwd)

    sad_values = _sol_optics_values(tw_sad, "END")
    xsuite_values = _sol_xsuite_optics_values(tw_xs, "end")

    _assert_sol_twiss_matches_sad(
        test_name      = "test_sol_optics_matches_sad_twiss_at_end",
        lattice_text   = lattice_text,
        sad_values     = sad_values,
        xsuite_values  = xsuite_values,
        parameters     = {"bz": bz},
        notes          = [
            "This is an active-solenoid optics comparison, separate from "
            "orbit/reference-frame checks.",
            "Xsuite beta/alpha values use SAD's Edwards-Teng convention; "
            "see docs/helpers/sad-helpers.md.",
        ])

########################################
# End-to-End Tracking
########################################
def _run_sol_tracking_comparison(
        write_lattice,
        tmp_path,
        bz,
        test_name):
    """
    Run one end-to-end bound-SOL tracking comparison.
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
        lattice_text = _bound_solenoid_lattice(bz = bz)
        lattice_path = write_lattice(
            lattice_text,
            filename = f"sol_tracking_bz_{bz:+.3f}.sad")

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
            sad_lattice_path = str(lattice_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)

        xs_particles = track_xsuite_particles(
            line, x_init, px_init, y_init, py_init, zeta_init, delta_init)
    finally:
        os.chdir(cwd)

    _assert_sol_tracking_matches_sad(
        test_name           = test_name,
        lattice_text        = lattice_text,
        initial_coordinates = _sol_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates     = _sol_sad_coordinates(sad_particles),
        xsuite_coordinates  = _sol_xsuite_coordinates(xs_particles),
        parameters          = {"bz": bz})

def test_sol_unpowered_end_to_end_tracking_matches_sad_for_transverse_offsets(
        write_lattice,
        tmp_path):
    """
    Unpowered bound SOL regions should match SAD tracking before powered cases.
    """
    _run_sol_tracking_comparison(
        write_lattice = write_lattice,
        tmp_path      = tmp_path,
        bz            = 0.0,
        test_name     = (
            "test_sol_unpowered_end_to_end_tracking_matches_sad_for_"
            "transverse_offsets"))

@pytest.mark.parametrize(
    "bz",
    [-0.1, 0.1])
def test_sol_powered_end_to_end_tracking_matches_sad_for_transverse_offsets(
        write_lattice,
        tmp_path,
        bz):
    """
    Powered bound SOL regions should match SAD tracking for offset particles.
    """
    _run_sol_tracking_comparison(
        write_lattice = write_lattice,
        tmp_path      = tmp_path,
        bz            = bz,
        test_name     = (
            "test_sol_powered_end_to_end_tracking_matches_sad_for_"
            "transverse_offsets"))

########################################
# Accepted DISFRIN Limitation
########################################
def test_sol_disfrin_off_diverges_from_xsuite_in_tracking(write_lattice, tmp_path):
    """
    Without DISFRIN=1, SAD's solenoid fringe kick diverges from Xsuite
    tracking beyond normal tolerance.

    Tracks at an offset large enough for the cubic-order kick to clear
    tolerance. SAD2XS does not model this kick, so every converted lattice
    behaves as if DISFRIN=1 were set. This is a documented limitation, not an
    open bug. See docs/converter/solenoids.md.
    """
    bz = 2.0
    x_init     = np.array([0.1])
    px_init    = np.array([0.0])
    y_init     = np.array([0.1])
    py_init    = np.array([0.0])
    zeta_init  = np.array([0.0])
    delta_init = np.array([0.0])

    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = _bound_solenoid_lattice(bz = bz, disfrin = False)
        lattice_path = write_lattice(
            lattice_text,
            filename = "sol_disfrin_off_diverges.sad")

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
            sad_lattice_path = str(lattice_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)

        xs_particles = track_xsuite_particles(
            line, x_init, px_init, y_init, py_init, zeta_init, delta_init)
    finally:
        os.chdir(cwd)

    tolerances          = _sol_tracking_tolerances()
    xsuite_coordinates  = _sol_xsuite_coordinates(xs_particles)
    sad_coordinates     = _sol_sad_coordinates(sad_particles)

    diverging_coordinates = []
    for coord, xs_values in xsuite_coordinates.items():
        atol, rtol = tolerances[coord]
        if not np.all(np.isclose(
                sad_coordinates[coord],
                xs_values,
                rtol = rtol,
                atol = atol)):
            diverging_coordinates.append(coord)

    assert diverging_coordinates, (
        "Without DISFRIN=1, SAD is expected to diverge from Xsuite beyond "
        "normal tracking tolerance on at least one coordinate (SAD2XS does "
        "not model the fringe kick). It is not required to diverge on every "
        "coordinate: zeta/delta, for example, are conserved by this purely "
        "transverse kick and are expected to keep matching. If this now "
        "passes, the accepted limitation may have changed and "
        "docs/reference/sad-behaviour.md needs review.")

################################################################################
# Reference Transform Physics
################################################################################
SOL_REFERENCE_TRANSFORMS = [
    pytest.param(
        "DX = 0.001 DY = -0.002",
        {"transform": "dxdy", "dx": 0.001, "dy": -0.002},
        id = "dxdy"),
    pytest.param(
        "DZ = 0.003",
        {"transform": "dz", "dz": 0.003},
        id = "dz"),
    pytest.param(
        "DPX = 0.001",
        {"transform": "dpx", "dpx": 0.001},
        id = "dpx"),
    pytest.param(
        "DPY = -0.001",
        {"transform": "dpy", "dpy": -0.001},
        id = "dpy"),
    pytest.param(
        "CHI1 = 0.001",
        {"transform": "chi1", "chi1": 0.001},
        id = "chi1"),
    pytest.param(
        "CHI2 = -0.001",
        {"transform": "chi2", "chi2": -0.001},
        id = "chi2"),
    pytest.param(
        "DX = 0.001 DY = -0.002 DPX = 0.001 DPY = -0.001",
        {
            "transform": "dxdy_dpx_dpy",
            "dx":  0.001,
            "dy":  -0.002,
            "dpx": 0.001,
            "dpy": -0.001,
        },
        id = "dxdy_dpx_dpy"),
    pytest.param(
        "DX = 0.001 DY = -0.002 CHI1 = 0.001 CHI2 = -0.001",
        {
            "transform": "dxdy_chi1_chi2",
            "dx":   0.001,
            "dy":   -0.002,
            "chi1": 0.001,
            "chi2": -0.001,
        },
        id = "dxdy_chi1_chi2"),
]

SOL_REFERENCE_GEO_PLACEMENTS = [
    pytest.param("in", "SOL_START", "sol_start", id = "geo_in"),
    pytest.param("out", "SOL_START", "sol_start", id = "geo_out"),
]

SOL_REFERENCE_LINE_ORIENTATIONS = [
    pytest.param(
        "forward",
        "START SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END",
        id = "forward"),
    pytest.param(
        "rev_in",
        "START -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END",
        id = "rev_in"),
    pytest.param(
        "rev_out",
        "START SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END",
        id = "rev_out"),
    pytest.param(
        "rev_both",
        "START -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END",
        id = "rev_both"),
]

########################################
# Zero-Field Legacy Matrix
########################################
@pytest.mark.parametrize(
    "transform_parameters, parameters",
    SOL_REFERENCE_TRANSFORMS)
@pytest.mark.parametrize(
    "geo_placement, sad_marker, xsuite_marker",
    SOL_REFERENCE_GEO_PLACEMENTS)
@pytest.mark.parametrize(
    "orientation, line_expression",
    SOL_REFERENCE_LINE_ORIENTATIONS)
def test_sol_reference_transform_orbit_matches_sad_twiss(
        write_lattice,
        rebuild_lattice,
        tmp_path,
        transform_parameters,
        parameters,
        geo_placement,
        sad_marker,
        xsuite_marker,
        orientation,
        line_expression):
    """
    Bound GEO SOL reference transforms should preserve SAD marker orbits.

    This test deliberately uses BZ = 0 at both SOL boundaries. It isolates the
    reference-frame transforms from active solenoid fields, field steps, and
    fringe-model differences.
    """
    if geo_placement == "in":
        sol_in_parameters = f"GEO = 1 {transform_parameters}"
        sol_out_parameters = ""
    else:
        sol_in_parameters = ""
        sol_out_parameters = f"GEO = 1 {transform_parameters}"

    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = _reference_transform_lattice(
            sol_in_parameters  = sol_in_parameters,
            sol_out_parameters = sol_out_parameters,
            line_expression    = line_expression)
        lattice_path = write_lattice(
            lattice_text,
            filename = "sol_reference_transform_legacy_matrix.sad")
        rebuilt_path = rebuild_lattice(lattice_path)

        tw_sad = twiss_sad(
            lattice_filepath        = lattice_path.name,
            line_name               = "TEST_LINE",
            calc6d                  = False,
            closed                  = False,
            reverse_element_order   = False,
            reverse_survey_horizontal  = False,
            rfsw              = True,
            rad               = False,
            radcod        = False,
            radtaper               = False,
            additional_commands     = "")

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path = str(rebuilt_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)

        tw_xs = line.twiss4d(
            _continue_if_lost = True,
            start             = xt.START,
            end               = xt.END,
            betx              = 1.0,
            bety              = 1.0)
    finally:
        os.chdir(cwd)

    sad_values = _sol_orbit_values(tw_sad, sad_marker)
    xsuite_values = _sol_orbit_values(tw_xs, xsuite_marker)

    _assert_sol_twiss_matches_sad(
        test_name      = "test_sol_reference_transform_orbit_matches_sad_twiss",
        lattice_text   = lattice_text,
        sad_values     = sad_values,
        xsuite_values  = xsuite_values,
        parameters     = {
            **parameters,
            "geo":    geo_placement,
            "marker": sad_marker.lower(),
            "line":   orientation,
        },
        notes          = [
            "This zero-field marker-orbit comparison isolates the line-aware "
            "bound/geometric SOL reference transform path.",
        ])

########################################
# Zero-Field Exit Restoration
########################################
@pytest.mark.parametrize(
    "transform_parameters, parameters",
    SOL_REFERENCE_TRANSFORMS)
@pytest.mark.parametrize(
    "geo_placement",
    ["in", "out"])
@pytest.mark.parametrize(
    "orientation, line_expression",
    SOL_REFERENCE_LINE_ORIENTATIONS)
def test_sol_reference_transform_restores_design_orbit_at_end(
        write_lattice,
        rebuild_lattice,
        tmp_path,
        transform_parameters,
        parameters,
        geo_placement,
        orientation,
        line_expression):
    """
    Bound GEO SOL transforms return to the SAD design orbit at END.

    Checks the END marker after the full solenoid region, so a failure points
    at exit restoration or element-order semantics rather than the internal
    zero-field transform. Parametrised identically to
    test_sol_reference_transform_orbit_matches_sad_twiss, so the two together
    cover all 16 converter categories.
    """
    if geo_placement == "in":
        sol_in_parameters = f"GEO = 1 {transform_parameters}"
        sol_out_parameters = ""
    else:
        sol_in_parameters = ""
        sol_out_parameters = f"GEO = 1 {transform_parameters}"

    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = _reference_transform_lattice(
            sol_in_parameters  = sol_in_parameters,
            sol_out_parameters = sol_out_parameters,
            line_expression    = line_expression)
        lattice_path = write_lattice(
            lattice_text,
            filename = "sol_reference_transform_end_restoration.sad")
        rebuilt_path = rebuild_lattice(lattice_path)

        tw_sad = twiss_sad(
            lattice_filepath        = lattice_path.name,
            line_name               = "TEST_LINE",
            calc6d                  = False,
            closed                  = False,
            reverse_element_order   = False,
            reverse_survey_horizontal  = False,
            rfsw              = True,
            rad               = False,
            radcod        = False,
            radtaper               = False,
            additional_commands     = "")

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path = str(rebuilt_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)

        tw_xs = line.twiss4d(
            _continue_if_lost = True,
            start             = xt.START,
            end               = xt.END,
            betx              = 1.0,
            bety              = 1.0)
    finally:
        os.chdir(cwd)

    sad_values = _sol_orbit_values(tw_sad, "END")
    xsuite_values = _sol_orbit_values(tw_xs, "end")

    _assert_sol_twiss_matches_sad(
        test_name      = (
            "test_sol_reference_transform_restores_design_orbit_at_end"),
        lattice_text   = lattice_text,
        sad_values     = sad_values,
        xsuite_values  = xsuite_values,
        parameters     = {
            **parameters,
            "geo":         "geo_" + geo_placement,
            "orientation": orientation,
            "marker":      "end",
        },
        notes          = [
            "This checks the END marker after the full solenoid region. "
            "A failure here points to exit restoration / element-order "
            "semantics rather than the internal reference transform.",
        ])

########################################
# Zero-Field Interior Orbit Restoration
########################################
SOL_INTERIOR_KICK_CASES = [
    pytest.param(
        "MULT        TEST_MULT1  = (K0 = +0.001 SK0 = +0.001)\n"
        "            TEST_MULT2  = (K0 = -0.001 SK0 = -0.001);",
        "SOL_IN SOL_START TEST_MULT1 SOL_DRIFT TEST_MULT2 SOL_END SOL_OUT END",
        {"kick_case": "balanced_xy"},
        id = "balanced_xy"),
    pytest.param(
        "MULT        TEST_MULT   = (K0 = 0.001);",
        "SOL_IN SOL_START SOL_DRIFT TEST_MULT SOL_END SOL_OUT END",
        {"kick_case": "horizontal"},
        id = "horizontal"),
    pytest.param(
        "MULT        TEST_MULT   = (SK0 = -0.001);",
        "SOL_IN SOL_START SOL_DRIFT TEST_MULT SOL_END SOL_OUT END",
        {"kick_case": "vertical"},
        id = "vertical"),
    pytest.param(
        "MULT        TEST_MULT1  = (K0 = +0.001 SK0 = +0.001)\n"
        "            TEST_MULT2  = (K0 = -0.001 SK0 = -0.001)\n"
        "            TEST_MULT3  = (K0 = +0.001);",
        "SOL_IN SOL_START TEST_MULT1 SOL_DRIFT TEST_MULT2 TEST_MULT3 "
        "SOL_END SOL_OUT END",
        {"kick_case": "combined"},
        id = "combined"),
]

@pytest.mark.parametrize(
    "geo_placement",
    ["in", "out"])
@pytest.mark.parametrize(
    "middle_element, line_expression, parameters",
    SOL_INTERIOR_KICK_CASES)
def test_sol_reference_transform_restores_orbit_with_interior_kicks(
        write_lattice,
        rebuild_lattice,
        tmp_path,
        geo_placement,
        middle_element,
        line_expression,
        parameters):
    """
    Bound SOL reference transforms should preserve SAD orbit restoration.

    This ports the legacy SOL output-orbit tests that used internal MULT kicks
    to create a displaced trajectory before the outgoing SOL boundary.
    """
    if geo_placement == "in":
        sol_in_parameters = "GEO = 1"
        sol_out_parameters = ""
    else:
        sol_in_parameters = ""
        sol_out_parameters = "GEO = 1"

    lattice_text = f"""\
    MOMENTUM    = 1.0 GEV;

    DRIFT       SOL_DRIFT   = (L = 1.0);
    {middle_element}

    SOL         SOL_IN      = (BZ = 0.0 BOUND = 1 {sol_in_parameters})
                SOL_OUT     = (BZ = 0.0 BOUND = 1 {sol_out_parameters});

    MARK        START       = ()
                SOL_START   = ()
                SOL_END     = ()
                END         = ();

    LINE        TEST_LINE   = (START {line_expression});
    """

    _compare_sol_orbit_twiss(
        write_lattice   = write_lattice,
        rebuild_lattice = rebuild_lattice,
        tmp_path        = tmp_path,
        lattice_text    = lattice_text,
        filename        = "sol_reference_transform_interior_kicks.sad",
        test_name       = (
            "test_sol_reference_transform_restores_orbit_with_interior_kicks"),
        sad_marker     = "END",
        xsuite_marker  = "end",
        parameters     = {
            **parameters,
            "geo": "geo_" + geo_placement,
        },
        notes          = [
            "This ports the legacy SOL output-orbit checks with internal MULT "
            "kicks and zero solenoidal field.",
        ])

########################################
# Powered Reference-Shift Cases
########################################
@pytest.mark.parametrize(
    "bz, transform_parameters, parameters",
    [
        pytest.param(
            1E-6,
            "DX = 0.001 DY = -0.001 CHI1 = 0.001 CHI2 = -0.001",
            {"bz": 1E-6, "case": "very_weak_dxdy_chi1_chi2"},
            id = "very_weak_dxdy_chi1_chi2"),
        pytest.param(
            1E-3,
            "DX = 0.001 DY = -0.001 CHI1 = 0.001 CHI2 = -0.001",
            {"bz": 1E-3, "case": "weak_dxdy_chi1_chi2"},
            id = "weak_dxdy_chi1_chi2"),
        pytest.param(
            1.0,
            "DX = 0.001 DY = -0.001 DPX = 0.001 DPY = -0.001",
            {"bz": 1.0, "case": "strong_dxdy_dpx_dpy"},
            id = "strong_dxdy_dpx_dpy"),
    ])
def test_sol_powered_reference_shift_orbit_matches_sad_at_end(
        write_lattice,
        rebuild_lattice,
        tmp_path,
        bz,
        transform_parameters,
        parameters):
    """
    Powered SOL regions with GEO reference shifts should match SAD orbit Twiss.

    This ports the legacy powered SOL cases, including very weak and weak
    fields used to exercise the small-field expansion.
    """
    lattice_text = f"""\
    MOMENTUM    = 1.0 GEV;

    DRIFT       SHORT_DRIFT = (L = 0.1);
    SOL         SOL_IN      = (
                    BZ = {bz} BOUND = 1 GEO = 1 DISFRIN = 1 {transform_parameters})
                SOL_OUT     = (BZ = {bz} BOUND = 1 DISFRIN = 1);

    MARK        START       = ()
                SOL_START   = ()
                SOL_END     = ()
                END         = ();

    LINE        SOL_DRIFT   = (
                    SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT
                    SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT
                    SHORT_DRIFT SHORT_DRIFT)
                TEST_LINE   = (
                    START SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
    """

    _compare_sol_orbit_twiss(
        write_lattice   = write_lattice,
        rebuild_lattice = rebuild_lattice,
        tmp_path        = tmp_path,
        lattice_text    = lattice_text,
        filename        = "sol_powered_reference_shift_orbit.sad",
        test_name       = (
            "test_sol_powered_reference_shift_orbit_matches_sad_at_end"),
        sad_marker     = "END",
        xsuite_marker  = "end",
        parameters     = parameters,
        notes          = [
            "This ports the legacy powered SOL reference-shift checks.",
        ])

################################################################################
# Element Conversion Inside Solenoid Regions
################################################################################
########################################
# SAD-Supported Inserted Elements
########################################
@pytest.mark.parametrize(
    "middle_element, middle_name, converted_name, expected_length, expected_knl",
    [
        (
            "QUAD        TEST_QUAD   = (L = 0.5 K1 = 0.2);",
            "TEST_QUAD",
            "test_quad_sol_in",
            0.5,
            [0.0, 0.2],
        ),
        (
            "BEND        TEST_BEND   = (L = 0.5 ANGLE = 0.0);",
            "TEST_BEND",
            "test_bend_sol_in",
            0.5,
            [0.0, 0.0],
        ),
        (
            "MULT        TEST_MULT   = (K1 = 0.2);",
            "TEST_MULT",
            "test_mult_sol_in",
            0.0,
            [0.0, 0.2],
        ),
    ])
def test_sol_pipeline_preserves_supported_elements_inside_solenoid_region(
        write_lattice,
        middle_element,
        middle_name,
        converted_name,
        expected_length,
        expected_knl):
    """
    SAD-supported elements inside SOL regions should convert consistently.

    SAD supports DRIFT, straight BEND, QUAD, and MULT between SOL boundaries.
    Direct SEXT and OCT are not part of that supported inserted-element set;
    higher-order content should be represented through MULT.
    """
    lattice_text = _bound_solenoid_lattice(
        bz             = 0.1,
        middle_element = middle_element,
        middle_name    = middle_name)
    lattice_path = write_lattice(
        lattice_text,
        filename = f"sol_region_preserves_{middle_name.lower()}.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        line_name        = "TEST_LINE",
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert converted_name in line.element_names, (
        "Element inside bound SOL region should be replaced by a "
        "solenoid-region element with a deterministic name.")
    converted = line[converted_name]
    assert isinstance(converted, xt.UniformSolenoid), (
        "Converted element inside bound SOL region should be an active "
        "UniformSolenoid.")
    assert converted.length == pytest.approx(expected_length), (
        "Converted element inside bound SOL region should preserve length.")
    assert np.asarray(converted.knl[:len(expected_knl)], dtype = float) == \
        pytest.approx(expected_knl), (
        "Converted element inside bound SOL region should preserve normal "
        "multipole content.")

@pytest.mark.parametrize(
    "middle_element, expected_type",
    [
        (
            "APERT       TEST_APERT  = (AX = 0.02 AY = 0.03 "
            "DX1 = -0.01 DX2 = 0.01 DY1 = -0.015 DY2 = 0.015);",
            xt.LimitRectEllipse,
        ),
        (
            "APERT       TEST_APERT  = (DX1 = -0.01 DX2 = 0.02);",
            xt.LimitRect,
        ),
    ],
    ids = ["limitrectellipse", "limitrect"])
def test_sol_pipeline_preserves_apertures_inside_solenoid_region(
        write_lattice,
        middle_element,
        expected_type):
    """
    Zero-length APERT elements between bound SOL boundaries should pass
    through unconverted, like other known zero-length elements (Marker,
    Translation, TimeDelay, Rotation).
    """
    lattice_text = _bound_solenoid_lattice(
        bz             = 0.1,
        middle_element = middle_element,
        middle_name    = "TEST_APERT")
    lattice_path = write_lattice(
        lattice_text,
        filename = f"sol_region_preserves_apert_{expected_type.__name__.lower()}.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert "test_apert" in line.element_names, (
        "APERT inside a bound SOL region should remain in the line by its "
        "own name, not be replaced by a solenoid-region element.")
    assert isinstance(line["test_apert"], expected_type), (
        "APERT inside a bound SOL region should pass through unconverted.")

def test_sol_pipeline_rejects_bending_angle_inside_solenoid_region(write_lattice):
    """
    BEND elements with non-zero angle inside a bound SOL region should fail.
    """
    lattice_text = _bound_solenoid_lattice(
        bz             = 0.1,
        middle_element = "BEND        TEST_BEND   = (L = 0.5 ANGLE = 0.01);",
        middle_name    = "TEST_BEND")
    lattice_path = write_lattice(
        lattice_text,
        filename = "sol_region_rejects_bend_angle.sad")

    with pytest.raises(AssertionError, match = "Bend .* with non-zero angle"):
        s2x.convert_sad_to_xsuite(
            sad_lattice_path = str(lattice_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)
