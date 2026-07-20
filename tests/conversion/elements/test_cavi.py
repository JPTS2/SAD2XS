"""
================================================================================
Tests for SAD CAVI conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-20
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
from sad2xs.converter._004_element_converter import convert_cavities
from sad2xs.sad_helpers import track_sad
from tests.support.config import (
    DELTA_DELTA_ATOL,
    DELTA_DELTA_RTOL,
    DELTA_S_ATOL,
    DELTA_S_RTOL,
    DELTA_ZETA_ATOL,
    DELTA_ZETA_RTOL)
from tests.support.diagnostics import (
    diagnostic_report_path,
    write_tracking_failure_report,
    write_twiss_failure_report)
from tests.support.tracking_helpers import track_xsuite_particles
from sad2xs.sad_helpers import twiss_sad

################################################################################
# Diagnostic Helpers
################################################################################
CAVI_ARTIFACT_CATEGORY = "conversion/elements/cavi"

def _cavi_config():
    """
    Return a quiet config for deterministic CAVI conversion tests.
    """
    return Config(_verbose = False)

def _cavi_tracking_tolerances():
    """
    Return coordinate tolerances used by cavity tracking comparisons.
    """
    return {
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
    }

def _cavi_twiss_tolerances():
    """
    Return tolerances used by cavity optics comparisons.
    """
    return {
        "s":     (DELTA_S_ATOL, DELTA_S_RTOL),
        "zeta":  (DELTA_ZETA_ATOL, DELTA_ZETA_RTOL),
        "delta": (DELTA_DELTA_ATOL, DELTA_DELTA_RTOL),
    }

def _cavi_twiss_values(twiss, element_name, s_name = "s"):
    """
    Pack cavity Twiss values for diagnostic reports.
    """
    return {
        "s":     twiss[s_name, element_name],
        "zeta":  twiss["zeta", element_name],
        "delta": twiss["delta", element_name],
    }

def _cavi_xsuite_sad_s(twiss, line):
    """
    Build the SAD-equivalent s-coordinate used by legacy cavity comparisons.
    """
    table = line.get_table(attr = True)
    ds = np.concatenate([[0], twiss.s[1:] - twiss.s[:-1]])
    dzeta = np.concatenate([[0], twiss.zeta[1:] - twiss.zeta[:-1]])
    time_delays = table.element_type == "TimeDelay"
    time_delays = np.concatenate([[0], time_delays[:-1]])
    dzeta = np.where(time_delays, 0, dzeta)

    sad_s = np.zeros_like(twiss.s)
    for idx in range(1, len(sad_s)):
        sad_s[idx] = sad_s[idx - 1] + ds[idx] - dzeta[idx]
    return sad_s

def _cavi_initial_coordinates(
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

def _cavi_sad_coordinates(sad_particles):
    """
    Pack SAD tracking coordinates for diagnostic reports.
    """
    return {
        "zeta":  sad_particles["zeta"],
        "delta": sad_particles["delta"],
    }

def _cavi_xsuite_coordinates(xs_particles):
    """
    Pack Xsuite tracking coordinates for diagnostic reports.
    """
    return {
        "zeta":  xs_particles.zeta,
        "delta": xs_particles.delta,
    }

def _assert_cavi_twiss_matches_sad(
        test_name,
        lattice_text,
        sad_values,
        xsuite_values,
        parameters,
        notes = None):
    """
    Assert cavity optics equivalence and write a Markdown report on failure.
    """
    tolerances = _cavi_twiss_tolerances()
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
            category   = CAVI_ARTIFACT_CATEGORY,
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
            f"Converted cavity optics should match SAD. "
            f"Failed values: {failed_values}. "
            f"Diagnostic report: {report_path}")

def _assert_cavi_tracking_matches_sad(
        test_name,
        lattice_text,
        initial_coordinates,
        sad_coordinates,
        xsuite_coordinates,
        parameters,
        notes = None):
    """
    Assert cavity tracking equivalence and write a Markdown report on failure.
    """
    tolerances = _cavi_tracking_tolerances()
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
            category   = CAVI_ARTIFACT_CATEGORY,
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
            f"Converted cavity tracking should match SAD. "
            f"Failed coordinates: {failed_coordinates}. "
            f"Diagnostic report: {report_path}")

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
def test_cavi_converter_creates_xsuite_cavity(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Parsed SAD CAVI elements should become active Xsuite Cavity elements.
    """
    xsuite_environment["fshift"] = 0.0

    convert_cavities(
        parsed_elements = parsed_elements(
            element_type      = "cavi",
            element_name      = "test_cavi",
            element_variables = {
                "l":    0.5,
                "volt": 1.0E7,
                "freq": 1.0E8,
                "phi":  0.125,
            }),
        environment     = xsuite_environment,
        config          = _cavi_config())

    cavity = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_cavi",
        element_type = xt.Cavity)

    assert cavity.length == pytest.approx(0.5), (
        "Converted CAVI should preserve the parsed SAD length.")
    assert cavity.voltage == pytest.approx(1.0E7), (
        "Converted CAVI should preserve the parsed SAD voltage.")
    assert cavity.frequency == pytest.approx(1.0E8), (
        "Converted CAVI should preserve the parsed SAD frequency when "
        "fshift is zero.")

def test_cavi_converter_sets_phase_in_radians(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    SAD PHI should be expressed as Xsuite phase in radians (offset by π).
    """
    xsuite_environment["fshift"] = 0.0

    convert_cavities(
        parsed_elements = parsed_elements(
            element_type      = "cavi",
            element_name      = "test_cavi",
            element_variables = {
                "l":    0.0,
                "volt": 1.0E7,
                "freq": 1.0E8,
                "phi":  0.125,
            }),
        environment     = xsuite_environment,
        config          = _cavi_config())

    cavity = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_cavi",
        element_type = xt.Cavity)

    assert cavity.phase == pytest.approx(np.pi + 0.125), (
        "Converted CAVI should express SAD PHI using Xsuite phase in radians.")

def test_cavi_converter_preserves_symbolic_phase_with_environment_variable(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Symbolic SAD CAVI PHI should remain controlled by Xsuite variables.
    """
    xsuite_environment["fshift"] = 0.0
    xsuite_environment["phi_cavi"] = 0.125

    convert_cavities(
        parsed_elements = parsed_elements(
            element_type      = "cavi",
            element_name      = "test_cavi",
            element_variables = {
                "l":    0.0,
                "volt": 1.0E7,
                "freq": 1.0E8,
                "phi":  "phi_cavi",
            }),
        environment     = xsuite_environment,
        config          = _cavi_config())

    cavity = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_cavi",
        element_type = xt.Cavity)

    assert cavity.phase == pytest.approx(np.pi + 0.125), (
        "Symbolic CAVI PHI should evaluate through Xsuite phase in radians.")

########################################
# Frequency and Harmonic Handling
########################################
def test_cavi_converter_uses_frequency_when_frequency_is_supplied(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    SAD CAVI FREQ should map to Xsuite frequency with zero harmonic.
    """
    xsuite_environment["fshift"] = 0.0

    convert_cavities(
        parsed_elements = parsed_elements(
            element_type      = "cavi",
            element_name      = "test_cavi",
            element_variables = {
                "l":    0.0,
                "volt": 1.0E7,
                "freq": 1.0E8,
                "phi":  0.0,
            }),
        environment     = xsuite_environment,
        config          = _cavi_config())

    cavity = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_cavi",
        element_type = xt.Cavity)

    assert cavity.frequency == pytest.approx(1.0E8), (
        "Frequency-driven CAVI should preserve Xsuite frequency.")
    assert cavity.harmonic == pytest.approx(0.0), (
        "Frequency-driven CAVI should not also set Xsuite harmonic.")

def test_cavi_converter_uses_harmonic_when_harmonic_is_supplied(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    SAD CAVI HARM should map to current Xsuite harmonic support.
    """
    convert_cavities(
        parsed_elements = parsed_elements(
            element_type      = "cavi",
            element_name      = "test_cavi",
            element_variables = {
                "l":    0.0,
                "volt": 1.0E7,
                "harm": 400.0,
                "phi":  0.0,
            }),
        environment     = xsuite_environment,
        config          = _cavi_config())

    cavity = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_cavi",
        element_type = xt.Cavity)

    assert cavity.frequency == pytest.approx(0.0), (
        "Harmonic-driven CAVI should not also set Xsuite frequency.")
    assert cavity.harmonic == pytest.approx(400.0), (
        "Harmonic-driven CAVI should set Xsuite harmonic directly.")

########################################
# Thin and Thick Cavity Behaviour
########################################
@pytest.mark.parametrize("length", [0.0, 0.5])
def test_cavi_converter_preserves_thin_and_thick_cavities(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        length):
    """
    Thin and thick SAD CAVI elements should remain active Xsuite cavities.
    """
    xsuite_environment["fshift"] = 0.0

    convert_cavities(
        parsed_elements = parsed_elements(
            element_type      = "cavi",
            element_name      = "test_cavi",
            element_variables = {
                "l":    length,
                "volt": 1.0E7,
                "freq": 1.0E8,
                "phi":  0.0,
            }),
        environment     = xsuite_environment,
        config          = _cavi_config())

    cavity = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_cavi",
        element_type = xt.Cavity)

    assert cavity.length == pytest.approx(length), (
        "Converted CAVI should preserve zero and nonzero SAD lengths.")
    assert cavity.voltage == pytest.approx(1.0E7), (
        "Converted CAVI should remain active for zero and nonzero lengths.")

################################################################################
# Pipeline Behaviour
################################################################################
########################################
# Full Conversion
########################################
@pytest.mark.parametrize("length", [0.0, 0.5])
def test_cavi_pipeline_preserves_names_order_and_rf_settings(
        write_lattice,
        length):
    """
    Full conversion should preserve CAVI names, order, and RF settings.
    """
    lattice_path = write_lattice(
        f"""\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_DRIFT  = (L = 1.0);
        CAVI        TEST_CAVI   = (
            L       = {length}
            VOLT    = 10000000
            FREQ    = 100000000
            PHI     = 0.125
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT TEST_CAVI TEST_DRIFT END);
        """,
        filename = "cavi_pipeline_preserves_names_order_and_rf_settings.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.element_names == [
        "start",
        "test_drift",
        "test_cavi",
        "test_drift",
        "end",
    ], (
        "Converted CAVI line should preserve SAD element order and names.")
    assert isinstance(line["test_cavi"], xt.Cavity), (
        "Converted CAVI should remain an active Xsuite Cavity.")
    assert line["test_cavi"].length == pytest.approx(length), (
        "Pipeline CAVI conversion should preserve the SAD cavity length.")
    assert line["test_cavi"].voltage == pytest.approx(1.0E7), (
        "Pipeline CAVI conversion should preserve the SAD cavity voltage.")
    assert line["test_cavi"].frequency == pytest.approx(1.0E8), (
        "Pipeline CAVI conversion should preserve the SAD cavity frequency.")
    assert line["test_cavi"].phase == pytest.approx(np.pi + 0.125), (
        "Pipeline CAVI conversion should use Xsuite phase in radians.")

def test_cavi_pipeline_preserves_harmonic_rf_setting(write_lattice):
    """
    Full conversion should preserve HARM as native Xsuite harmonic RF.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_DRIFT  = (L = 1.0);
        CAVI        TEST_CAVI   = (
            L       = 0.0
            VOLT    = 10000000
            HARM    = 400
            PHI     = 0.0
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT TEST_CAVI TEST_DRIFT END);
        """,
        filename = "cavi_pipeline_preserves_harmonic_rf_setting.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert isinstance(line["test_cavi"], xt.Cavity), (
        "Harmonic CAVI should remain an active Xsuite Cavity.")
    assert line["test_cavi"].frequency == pytest.approx(0.0), (
        "Harmonic CAVI should not also set Xsuite frequency.")
    assert line["test_cavi"].harmonic == pytest.approx(400.0), (
        "Pipeline CAVI conversion should preserve HARM as Xsuite harmonic.")
    assert line["test_cavi"].phase == pytest.approx(np.pi), (
        "Pipeline harmonic CAVI conversion should use Xsuite phase in radians.")

################################################################################
# Physics Equivalence
################################################################################
########################################
# RF Optics
########################################
@pytest.mark.parametrize(
    "length, phi",
    [
        (0.0, -0.125),
        (0.0, 0.0),
        (0.0, 0.125),
        (0.5, -0.125),
        (0.5, 0.0),
        (0.5, 0.125),
    ])
def test_cavi_conversion_matches_sad_twiss_for_phase(
        write_lattice,
        tmp_path,
        length,
        phi):
    """
    Converted CAVI elements should match SAD 6D optics for RF phase changes.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = f"""\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_DRIFT  = (L = 1.0);
        CAVI        TEST_CAVI   = (
            L       = {length}
            VOLT    = 10000000
            FREQ    = 100000000
            PHI     = {phi}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT TEST_CAVI TEST_DRIFT END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = "cavi_twiss_phase.sad")

        tw_sad = twiss_sad(
            lattice_filepath        = lattice_path.name,
            line_name               = "TEST_LINE",
            calc6d                  = True,
            closed                  = False,
            reverse_element_order   = False,
            reverse_survey_horizontal  = False,
            rfsw              = True,
            additional_commands     = "")

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path = str(lattice_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)

        tw_xs = line.twiss(
            method            = "6d",
            _continue_if_lost = True,
            start             = xt.START,
            end               = xt.END,
            betx              = 1,
            bety              = 1)
        tw_xs["s_sad"] = _cavi_xsuite_sad_s(tw_xs, line)

        sad_values = _cavi_twiss_values(tw_sad, "END")
        xsuite_values = _cavi_twiss_values(tw_xs, "end", s_name = "s_sad")
    finally:
        os.chdir(cwd)

    _assert_cavi_twiss_matches_sad(
        test_name     = "test_cavi_conversion_matches_sad_twiss_for_phase",
        lattice_text  = lattice_text,
        sad_values    = sad_values,
        xsuite_values = xsuite_values,
        parameters    = {"length": length, "phi": phi},
        notes         = [])

@pytest.mark.parametrize(
    "zeta, delta",
    [
        (1.0E-3, 0.0),
        (0.0, 1.0E-3),
        (1.0E-3, -1.0E-3),
    ])
def test_cavi_conversion_matches_sad_tracking_for_longitudinal_offsets(
        write_lattice,
        tmp_path,
        zeta,
        delta):
    """
    Converted CAVI elements should match SAD tracking for longitudinal offsets.
    """
    x_init     = np.array([0.0])
    px_init    = np.array([0.0])
    y_init     = np.array([0.0])
    py_init    = np.array([0.0])
    zeta_init  = np.array([zeta])
    delta_init = np.array([delta])

    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        lattice_text = """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_DRIFT  = (L = 1.0);
        CAVI        TEST_CAVI   = (
            L       = 0.0
            VOLT    = 10000000
            FREQ    = 100000000
            PHI     = 0.0
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT TEST_CAVI TEST_DRIFT END);
        """
        lattice_path = write_lattice(
            lattice_text,
            filename = "cavi_tracking_longitudinal_offsets.sad")

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

        xs_particles = track_xsuite_particles(
            line, x_init, px_init, y_init, py_init, zeta_init, delta_init)
    finally:
        os.chdir(cwd)

    _assert_cavi_tracking_matches_sad(
        test_name           = (
            "test_cavi_conversion_matches_sad_tracking_for_longitudinal_offsets"),
        lattice_text        = lattice_text,
        initial_coordinates = _cavi_initial_coordinates(
            x_init,
            px_init,
            y_init,
            py_init,
            zeta_init,
            delta_init),
        sad_coordinates     = _cavi_sad_coordinates(sad_particles),
        xsuite_coordinates  = _cavi_xsuite_coordinates(xs_particles),
        parameters          = {"zeta": zeta, "delta": delta},
        notes               = [])
