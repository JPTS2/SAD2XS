"""
================================================================================
Tests for SAD BEND conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE.txt for details.

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

from sad2xs.converter._004_element_converter import convert_bends
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
        "x":  (DELTA_X_ATOL, DELTA_X_RTOL),
        "px": (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "y":  (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "py": (DELTA_PY_ATOL, DELTA_PY_RTOL),
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
        "x":  sad_particles["x"],
        "px": sad_particles["px"],
        "y":  sad_particles["y"],
        "py": sad_particles["py"],
    }

def _bend_xsuite_coordinates(xs_particles):
    """
    Pack Xsuite tracking coordinates for diagnostic reports.
    """
    return {
        "x":  xs_particles.x,
        "px": xs_particles.px,
        "y":  xs_particles.y,
        "py": xs_particles.py,
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
def test_bend_converter_preserves_offsets_and_rotation(
        parsed_elements,
        xsuite_environment,
        sad2xs_config,
        assert_environment_element):
    """
    SAD BEND DX, DY, and ROTATE should map to Xsuite element fields.
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
                "rotate":   np.pi / 2,
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
    assert bend.rot_s_rad == pytest.approx(-np.pi / 2), (
        "Converted bend should apply the SAD-to-Xsuite rotation sign.")

def test_bend_converter_requires_length_for_nonzero_angle(
        parsed_elements,
        xsuite_environment,
        sad2xs_config):
    """
    A non-zero-angle SAD BEND without length should fail clearly.
    """
    with pytest.raises(ValueError, match = "missing length"):
        convert_bends(
            parsed_elements = parsed_elements(
                element_type        = "bend",
                element_name        = "test_bend",
                element_variables   = {"angle": 0.1}),
            environment     = xsuite_environment,
            config          = sad2xs_config)

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

def test_bend_pipeline_preserves_edges_offsets_and_rotation(write_lattice):
    """
    Full conversion should preserve BEND edge terms, offsets, and rotation.
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
        filename = "bend_pipeline_preserves_edges_offsets_rotation.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "boff", "end"], (
        "Converted line should preserve offset bend order.")
    assert isinstance(line["boff"], xt.Bend), (
        "Converted offset bend should be an Xsuite Bend.")
    assert line["boff"].edge_entry_angle == pytest.approx(0.06), (
        "Converted bend should preserve E1*ANGLE + AE1.")
    assert line["boff"].edge_exit_angle == pytest.approx(0.005), (
        "Converted bend should preserve E2*ANGLE + AE2.")
    assert line["boff"].shift_x == pytest.approx(1.0E-3), (
        "Converted bend should preserve SAD DX as Xsuite shift_x.")
    assert line["boff"].shift_y == pytest.approx(-2.0E-3), (
        "Converted bend should preserve SAD DY as Xsuite shift_y.")
    assert line["boff"].rot_s_rad == pytest.approx(-np.pi / 2), (
        "Converted bend should apply the SAD-to-Xsuite rotation sign.")

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
@pytest.mark.parametrize(
    "dx, dy",
    [
        (1.0E-3, 0.0),
        (0.0, -1.0E-3),
        (1.0E-3, -1.0E-3),
    ])
def test_bend_conversion_matches_sad_twiss_for_element_offsets(
        write_lattice,
        tmp_path,
        dx,
        dy):
    """
    Converted offset SAD BEND elements should match SAD optics and dispersion.
    """
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
@pytest.mark.parametrize(
    "dx, dy",
    [
        (1.0E-3, 0.0),
        (0.0, -1.0E-3),
        (1.0E-3, -1.0E-3),
    ])
def test_bend_conversion_matches_sad_tracking_for_element_offsets(
        write_lattice,
        tmp_path,
        dx,
        dy):
    """
    Converted offset SAD BEND elements should match SAD tracking.
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
            "Offset BEND tracking coverage checks SAD DX/DY convention.",
        ])
