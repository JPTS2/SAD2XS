"""
================================================================================
Tests for SAD DRIFT conversion
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

from sad2xs.converter._004_element_converter import convert_drifts
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
    DELTA_Y_RTOL,
    POSITIVE_TEST_VALUES)
from tests.support.diagnostics import (
    diagnostic_report_path,
    write_twiss_failure_report)
from sad2xs.sad_helpers import twiss_sad

################################################################################
# Diagnostic Helpers
################################################################################
DRIFT_ARTIFACT_CATEGORY = "conversion/elements/drift"

def _assert_drift_twiss_scan_matches_sad(
        test_values,
        sad_values,
        xsuite_values,
        lattice_template):
    """
    Assert drift Twiss scan equivalence and write a Markdown report on failure.
    """
    tolerances = {
        "s":  (DELTA_S_ATOL, DELTA_S_RTOL),
        "x":  (DELTA_X_ATOL, DELTA_X_RTOL),
        "y":  (DELTA_Y_ATOL, DELTA_Y_RTOL),
        "px": (DELTA_PX_ATOL, DELTA_PX_RTOL),
        "py": (DELTA_PY_ATOL, DELTA_PY_RTOL),
    }
    failed_values = []

    for name, xs_values in xsuite_values.items():
        atol, rtol = tolerances[name]
        if not np.all(np.isclose(
                sad_values[name],
                xs_values,
                rtol = rtol,
                atol = atol)):
            failed_values.append(name)

    if failed_values:
        flattened_sad_values = {}
        flattened_xsuite_values = {}
        flattened_tolerances = {}

        for idx, test_value in enumerate(test_values):
            for name in sad_values:
                key = f"{name}@L={test_value:.12e}"
                flattened_sad_values[key] = sad_values[name][idx]
                flattened_xsuite_values[key] = xsuite_values[name][idx]
                flattened_tolerances[key] = tolerances[name]

        report_path = diagnostic_report_path(
            test_name   = "test_drift_conversion_matches_sad_twiss_scan",
            category    = DRIFT_ARTIFACT_CATEGORY)
        write_twiss_failure_report(
            report_path     = report_path,
            title           = "test_drift_conversion_matches_sad_twiss_scan failure",
            lattice_text    = lattice_template,
            sad_values      = flattened_sad_values,
            xsuite_values   = flattened_xsuite_values,
            tolerances      = flattened_tolerances,
            parameters      = {"n_scan_values": len(test_values)},
            notes           = [
                "Each Twiss value is keyed as quantity@L=<drift length>.",
                "The SAD lattice template uses TEST_VAL for the scanned drift "
                "length.",
            ])
        pytest.fail(
            f"Converted drift Twiss scan should match SAD. "
            f"Failed values: {failed_values}. "
            f"Diagnostic report: {report_path}")

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
@pytest.mark.parametrize(
    "length",
    [0.0, 1.0, "l_drift"])
def test_drift_converter_creates_xsuite_drift(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        length):
    """
    Parsed SAD DRIFT elements should become Xsuite Drift elements.
    """
    convert_drifts(
        parsed_elements = parsed_elements(
            element_type        = "drift",
            element_name        = "test_drift",
            element_variables   = {"l": length}),
        environment     = xsuite_environment)

    drift = assert_environment_element(
        environment     = xsuite_environment,
        element_name    = "test_drift",
        element_type    = xt.Drift)

    assert drift.length == length, (
        "Converted drift length should preserve the parsed SAD length value.")

def test_drift_converter_creates_all_drifts(
        xsuite_environment,
        assert_environment_element):
    """
    Multiple parsed SAD DRIFT elements should all be converted.
    """
    parsed_elements = {
        "drift": {
            "d1": {"l": 1.0},
            "d2": {"l": 2.0},
            "d3": {"l": "l_drift"},
        },
    }

    convert_drifts(
        parsed_elements = parsed_elements,
        environment     = xsuite_environment)

    assert set(xsuite_environment.element_dict) == {"d1", "d2", "d3"}, (
        "All parsed SAD DRIFT elements should be present in the environment.")
    for drift_name, expected_length in [
            ("d1", 1.0),
            ("d2", 2.0),
            ("d3", "l_drift")]:
        drift = assert_environment_element(
            environment     = xsuite_environment,
            element_name    = drift_name,
            element_type    = xt.Drift)
        assert drift.length == expected_length, (
            f"Converted drift '{drift_name}' should preserve its parsed "
            "length.")

def test_drift_converter_requires_length(parsed_elements, xsuite_environment):
    """
    A SAD DRIFT without length should fail clearly during element conversion.
    """
    with pytest.raises(ValueError, match = "missing length"):
        convert_drifts(
            parsed_elements = parsed_elements(
                element_type        = "drift",
                element_name        = "test_drift",
                element_variables   = {}),
            environment     = xsuite_environment)

########################################
# Pipeline Behaviour
########################################
def test_drift_pipeline_preserves_names_order_and_lengths(write_lattice):
    """
    Full conversion should preserve SAD DRIFT names, order, and lengths.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1          = (L = 1.0)
                    D2          = (L = 2.0);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START D1 D2 END);
        """,
        filename = "drift_pipeline_preserves_names_order_lengths.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert line.element_names == ["start", "d1", "d2", "end"], (
        "Converted line should preserve SAD element names and order.")
    assert isinstance(line["d1"], xt.Drift), (
        "Converted element 'd1' should be an Xsuite Drift.")
    assert isinstance(line["d2"], xt.Drift), (
        "Converted element 'd2' should be an Xsuite Drift.")
    assert line["d1"].length == pytest.approx(1.0), (
        "Converted drift 'd1' should preserve its SAD length.")
    assert line["d2"].length == pytest.approx(2.0), (
        "Converted drift 'd2' should preserve its SAD length.")

def test_drift_pipeline_preserves_symbolic_length(write_lattice):
    """
    Full conversion should preserve SAD DRIFT symbolic length expressions.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        LDRIFT      = 1.25;

        DRIFT       D1          = (L = LDRIFT);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START D1 END);
        """,
        filename = "drift_pipeline_preserves_symbolic_length.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

    assert isinstance(line["d1"], xt.Drift), (
        "Converted symbolic-length drift should be an Xsuite Drift.")
    assert line["d1"].length == pytest.approx(1.25), (
        "Converted drift should resolve and preserve the SAD symbolic length.")

################################################################################
# Physics Equivalence
################################################################################
########################################
# Default Drift Optics
########################################
def test_drift_conversion_matches_sad_twiss_scan(write_lattice, tmp_path):
    """
    Converted SAD DRIFT elements should match SAD 4D Twiss propagation.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        s_sad       = np.zeros_like(POSITIVE_TEST_VALUES)
        s_xs        = np.zeros_like(POSITIVE_TEST_VALUES)
        x_sad       = np.zeros_like(POSITIVE_TEST_VALUES)
        x_xs        = np.zeros_like(POSITIVE_TEST_VALUES)
        y_sad       = np.zeros_like(POSITIVE_TEST_VALUES)
        y_xs        = np.zeros_like(POSITIVE_TEST_VALUES)
        px_sad      = np.zeros_like(POSITIVE_TEST_VALUES)
        px_xs       = np.zeros_like(POSITIVE_TEST_VALUES)
        py_sad      = np.zeros_like(POSITIVE_TEST_VALUES)
        py_xs       = np.zeros_like(POSITIVE_TEST_VALUES)
        lattice_template = """\
        MOMENTUM    = 1.0 GEV;
        TEST_VAL    = <scan value>;

        DRIFT       TEST_DRIFT  = (L = TEST_VAL);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT END);
        """

        for iteration, test_val in enumerate(POSITIVE_TEST_VALUES):
            lattice_path = write_lattice(
                f"""\
                MOMENTUM    = 1.0 GEV;
                TEST_VAL    = {test_val};

                DRIFT       TEST_DRIFT  = (L = TEST_VAL);

                MARK        START       = ()
                            END         = ();

                LINE        TEST_LINE   = (START TEST_DRIFT END);
                """,
                filename = "test_lattice.sad")

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

            s_sad[iteration]    = tw_sad["s", "END"]
            s_xs[iteration]     = tw_xs["s", "end"]
            x_sad[iteration]    = tw_sad["x", "END"]
            x_xs[iteration]     = tw_xs["x", "end"]
            y_sad[iteration]    = tw_sad["y", "END"]
            y_xs[iteration]     = tw_xs["y", "end"]
            px_sad[iteration]   = tw_sad["px", "END"]
            px_xs[iteration]    = tw_xs["px", "end"]
            py_sad[iteration]   = tw_sad["py", "END"]
            py_xs[iteration]    = tw_xs["py", "end"]
    finally:
        os.chdir(cwd)

    _assert_drift_twiss_scan_matches_sad(
        test_values         = POSITIVE_TEST_VALUES,
        sad_values          = {
            "s":  s_sad,
            "x":  x_sad,
            "y":  y_sad,
            "px": px_sad,
            "py": py_sad,
        },
        xsuite_values       = {
            "s":  s_xs,
            "x":  x_xs,
            "y":  y_xs,
            "px": px_xs,
            "py": py_xs,
        },
        lattice_template    = lattice_template)
