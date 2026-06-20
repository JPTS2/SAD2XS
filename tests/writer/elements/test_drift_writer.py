"""
================================================================================
Tests for drift element writer serialisation
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-20
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import xtrack as xt

import sad2xs as s2x
from sad2xs.config import Config

################################################################################
# Helpers
################################################################################
def _writer_roundtrip(line, tmp_path):
    """
    Write a line using the public SAD2XS writer entry points and reload it in a
    clean Xsuite environment. Returns the reloaded line.
    """
    output_dir = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = "Drift writer test",
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = "test_lattice_import_optics",
        output_directory  = str(output_dir),
        output_header     = "Drift writer test",
        config            = Config(_verbose = False))

    env = xt.Environment()
    env.call(str(output_dir / "test_lattice.py"))
    env.call(str(output_dir / "test_lattice_import_optics.py"))

    return env.lines["line"]


def _build_drift_line(length):
    """
    Build a minimal single-drift Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Drift(length = length), xt.Marker()],
        element_names = ["start", "d1", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    return line


################################################################################
# Basic Serialisation
################################################################################
########################################
# Element Type and Name
########################################
def test_drift_writer_reloads_as_xsuite_drift(tmp_path):
    """
    A written drift element should reload as an xt.Drift in a clean Xsuite
    environment.
    """
    original_line = _build_drift_line(length = 1.5)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["d1"], xt.Drift), (
        "Written drift element 'd1' should reload as xt.Drift. "
        f"Got: {type(reloaded_line['d1']).__name__}.")


def test_drift_writer_preserves_element_name(tmp_path):
    """
    A written drift element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_drift_line(length = 1.5)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "d1" in list(reloaded_line.element_names), (
        "Reloaded line should contain drift element 'd1'. "
        f"Got: {list(reloaded_line.element_names)}.")


########################################
# Element Order
########################################
def test_drift_writer_preserves_element_order(tmp_path):
    """
    Multiple drift and marker elements should appear in the same order after
    a write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Drift(length = 1.0),
            xt.Marker(),
            xt.Drift(length = 2.0),
            xt.Marker(),
        ],
        element_names = ["start", "d1", "mid", "d2", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    assert list(reloaded_line.element_names) == list(line.element_names), (
        "Writer roundtrip should preserve element names and order. "
        f"Original: {list(line.element_names)}; "
        f"Reloaded: {list(reloaded_line.element_names)}.")


################################################################################
# Field Preservation
################################################################################
########################################
# Length
########################################
def test_drift_writer_preserves_length(tmp_path):
    """
    A drift element's length should be preserved exactly through a write and
    reload cycle.
    """
    original_line = _build_drift_line(length = 1.5)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["d1"].length == pytest.approx(1.5), (
        "Writer roundtrip should preserve drift length. "
        f"Original: 1.5, reloaded: {reloaded_line['d1'].length}.")


def test_drift_writer_preserves_zero_length(tmp_path):
    """
    A zero-length drift should survive a write and reload cycle unchanged.
    Zero-length drifts appear in converted lines as spacers between elements
    placed at the same s-position.
    """
    original_line = _build_drift_line(length = 0.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["d1"].length == pytest.approx(0.0), (
        "Writer roundtrip should preserve zero drift length. "
        f"Reloaded: {reloaded_line['d1'].length}.")


def test_drift_writer_preserves_short_length(tmp_path):
    """
    A very short drift should preserve its length through a write and reload
    cycle. Short drifts appear as residual gaps after element slicing.
    """
    original_line = _build_drift_line(length = 1.0E-6)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["d1"].length == pytest.approx(1.0E-6), (
        "Writer roundtrip should preserve very short drift length. "
        f"Original: 1.0E-6, reloaded: {reloaded_line['d1'].length}.")


def test_drift_writer_preserves_large_length(tmp_path):
    """
    A large drift length should be preserved through a write and reload cycle.
    """
    original_line = _build_drift_line(length = 100.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["d1"].length == pytest.approx(100.0), (
        "Writer roundtrip should preserve large drift length. "
        f"Original: 100.0, reloaded: {reloaded_line['d1'].length}.")


################################################################################
# Multi-Element Behaviour
################################################################################
########################################
# Multiple Drifts
########################################
def test_drift_writer_preserves_multiple_drifts_independently(tmp_path):
    """
    Multiple drift elements of different lengths should each preserve their
    individual lengths independently through a single write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Drift(length = 1.0),
            xt.Drift(length = 2.5),
            xt.Drift(length = 0.5),
            xt.Marker(),
        ],
        element_names = ["start", "d1", "d2", "d3", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    expected = {"d1": 1.0, "d2": 2.5, "d3": 0.5}

    for name, expected_length in expected.items():
        assert reloaded_line[name].length == pytest.approx(expected_length), (
            f"Writer roundtrip should preserve length for drift '{name}'. "
            f"Expected: {expected_length}, reloaded: {reloaded_line[name].length}.")
