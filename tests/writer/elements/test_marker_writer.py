"""
================================================================================
Tests for marker element writer serialisation
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
import pytest
import xtrack as xt

import sad2xs as s2x
from sad2xs.config import Config

################################################################################
# Helpers
################################################################################
def _write_and_load(line, tmp_path, offset_marker_locations=None):
    """
    Write a line using the public SAD2XS writer entry points, reload it in a
    clean Xsuite environment, and return the environment and reloaded line.

    Pass offset_marker_locations to test the offset-marker insertion mechanism.
    The offset marker writer generates a MARKER_POSITIONS dict in the lattice
    file; with the default Config (_install_offset_markers=True), it also emits
    the loop that calls line.insert() to place the markers at their s-positions.
    """
    output_dir = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = "Marker writer test",
        offset_marker_locations = offset_marker_locations,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = "test_lattice_import_optics",
        output_directory  = str(output_dir),
        output_header     = "Marker writer test",
        config            = Config(_verbose = False))

    env = xt.Environment()
    env.call(str(output_dir / "test_lattice.py"))
    env.call(str(output_dir / "test_lattice_import_optics.py"))

    return env, env.lines["line"]


def _writer_roundtrip(line, tmp_path):
    """
    Write and reload a line. Returns the reloaded line only.
    """
    _, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)
    return reloaded_line


def _build_marker_line(*names):
    """
    Build a minimal Xsuite line containing one xt.Marker per name provided,
    surrounded by start and end markers. The start and end markers are always
    named 'start' and 'end'. Additional marker names are passed as positional
    arguments.

    Example: _build_marker_line('m1', 'm2') → ['start', 'm1', 'm2', 'end']
    """
    all_names = ["start"] + list(names) + ["end"]
    elements  = [xt.Marker() for _ in all_names]

    line = xt.Line(elements = elements, element_names = all_names)

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    return line


################################################################################
# Basic Serialisation
################################################################################
def test_marker_writer_reloads_as_xsuite_marker(tmp_path):
    """
    A written Marker element should reload as an xt.Marker in a clean Xsuite
    environment.
    """
    original_line = _build_marker_line("m1")
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["m1"], xt.Marker), (
        "Written Marker element 'm1' should reload as xt.Marker. "
        f"Got: {type(reloaded_line['m1']).__name__}.")


def test_marker_writer_preserves_element_name(tmp_path):
    """
    A written Marker element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_marker_line("m1")
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "m1" in list(reloaded_line.element_names), (
        "Reloaded line should contain Marker element 'm1'. "
        f"Got: {list(reloaded_line.element_names)}.")


def test_marker_writer_preserves_start_and_end_markers(tmp_path):
    """
    The conventional 'start' and 'end' markers that bracket every line should
    both survive the write and reload cycle.
    """
    original_line = _build_marker_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    names = list(reloaded_line.element_names)
    assert "start" in names, (
        "Reloaded line should contain 'start' marker. "
        f"Got: {names}.")
    assert "end" in names, (
        "Reloaded line should contain 'end' marker. "
        f"Got: {names}.")


def test_marker_writer_preserves_multiple_markers(tmp_path):
    """
    Multiple Marker elements with distinct names should all be present in the
    reloaded line.
    """
    original_line = _build_marker_line("ma", "mb", "mc")
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    names = list(reloaded_line.element_names)
    for name in ("ma", "mb", "mc"):
        assert name in names, (
            f"Reloaded line should contain marker '{name}'. Got: {names}.")


def test_marker_writer_preserves_element_order(tmp_path):
    """
    The order of Marker elements in the line should be preserved through a write
    and reload cycle. The reloaded element_names sequence must match the
    original.
    """
    original_line = _build_marker_line("m1", "m2", "m3")
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_names = list(original_line.element_names)
    reloaded_names = list(reloaded_line.element_names)

    assert reloaded_names == original_names, (
        "Writer roundtrip should preserve element order. "
        f"Original: {original_names}, reloaded: {reloaded_names}.")


def test_marker_writer_reloads_all_markers_as_xsuite_marker(tmp_path):
    """
    Every element in a marker-only line should reload as an xt.Marker. The
    writer uses a shared loop so all markers are created the same way.
    """
    original_line = _build_marker_line("ma", "mb")
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    for name in ("start", "ma", "mb", "end"):
        assert isinstance(reloaded_line[name], xt.Marker), (
            f"Element '{name}' should reload as xt.Marker. "
            f"Got: {type(reloaded_line[name]).__name__}.")


def test_marker_writer_preserves_single_marker_line(tmp_path):
    """
    A minimal line containing only two markers (start and end) should survive
    the write and reload cycle with both markers present.
    """
    original_line = _build_marker_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert len(list(reloaded_line.element_names)) == 2, (
        "Reloaded marker-only line should contain exactly 2 elements (start, end). "
        f"Got: {list(reloaded_line.element_names)}.")


################################################################################
# Offset Markers
################################################################################
def _build_drift_and_marker_line():
    """
    Build a line containing a 1 m drift between start and end markers. Used for
    offset marker tests where the writer inserts a marker at a specific s
    position inside the drift.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Drift(length = 1.0), xt.Marker()],
        element_names = ["start", "d1", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    return line


def test_marker_writer_offset_marker_is_present_in_reloaded_line(tmp_path):
    """
    An offset marker passed via offset_marker_locations should appear in the
    reloaded line as a named element. The marker writer adds it to the shared
    ALL_MARKERS list so it is created in the environment the same way as a
    regular marker.
    """
    original_line = _build_drift_and_marker_line()
    _, reloaded_line = _write_and_load(
        line                    = original_line,
        tmp_path                = tmp_path,
        offset_marker_locations = {"om1": [0.5]})

    assert "om1" in list(reloaded_line.element_names), (
        "Offset marker 'om1' should appear in the reloaded line element_names. "
        f"Got: {list(reloaded_line.element_names)}.")


def test_marker_writer_offset_marker_reloads_as_xsuite_marker(tmp_path):
    """
    An offset marker inserted via offset_marker_locations should reload as an
    xt.Marker in the Xsuite environment.
    """
    original_line = _build_drift_and_marker_line()
    _, reloaded_line = _write_and_load(
        line                    = original_line,
        tmp_path                = tmp_path,
        offset_marker_locations = {"om1": [0.5]})

    assert isinstance(reloaded_line["om1"], xt.Marker), (
        "Offset marker 'om1' should reload as xt.Marker. "
        f"Got: {type(reloaded_line['om1']).__name__}.")


def test_marker_writer_offset_marker_is_inserted_at_correct_s_position(tmp_path):
    """
    An offset marker should be inserted at the s-position specified in
    offset_marker_locations. With the default Config (_install_offset_markers=True),
    the lattice file emits the insertion loop, so the marker ends up at the
    correct s coordinate after reload.
    """
    original_line = _build_drift_and_marker_line()
    _, reloaded_line = _write_and_load(
        line                    = original_line,
        tmp_path                = tmp_path,
        offset_marker_locations = {"om1": [0.5]})

    s_om1 = reloaded_line.get_table()['s', 'om1']
    assert s_om1 == pytest.approx(0.5), (
        "Offset marker 'om1' should be inserted at s = 0.5 m. "
        f"Got: s = {s_om1}.")


def test_marker_writer_multiple_offset_markers_at_distinct_positions(tmp_path):
    """
    Two offset markers at different s-positions should each be present and
    correctly placed in the reloaded line.
    """
    original_line = _build_drift_and_marker_line()
    _, reloaded_line = _write_and_load(
        line                    = original_line,
        tmp_path                = tmp_path,
        offset_marker_locations = {"oma": [0.3], "omb": [0.7]})

    names = list(reloaded_line.element_names)
    assert "oma" in names, (
        f"Offset marker 'oma' should be in the reloaded line. Got: {names}.")
    assert "omb" in names, (
        f"Offset marker 'omb' should be in the reloaded line. Got: {names}.")

    s_oma = reloaded_line.get_table()['s', 'oma']
    s_omb = reloaded_line.get_table()['s', 'omb']
    assert s_oma == pytest.approx(0.3), (
        f"Offset marker 'oma' should be at s = 0.3. Got: {s_oma}.")
    assert s_omb == pytest.approx(0.7), (
        f"Offset marker 'omb' should be at s = 0.7. Got: {s_omb}.")
