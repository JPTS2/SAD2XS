"""
================================================================================
Tests for magnet base-element length precision in the writer
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-17
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
# Constants
################################################################################
PRECISION               = Config().MAGNET_LENGTH_PRECISION
SUB_PRECISION_OFFSET    = PRECISION / 4
SUPER_PRECISION_OFFSET  = 50 * PRECISION

################################################################################
# Helpers
################################################################################
def _write_and_load(line, tmp_path):
    """
    Write a line using the public SAD2XS writer entry points and reload it in
    a clean Xsuite environment. Base elements are named/grouped by length; a
    name collision between two distinct base elements raises on reload
    (`env.new` refuses to redefine an existing name), so this is the
    operation that exercises the length-precision handling.
    """
    output_dir = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = "Magnet length precision test",
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = "test_lattice_import_optics",
        output_directory  = str(output_dir),
        output_header     = "Magnet length precision test",
        config            = Config(_verbose = False))

    env = xt.Environment()
    env.call(str(output_dir / "test_lattice.py"))
    env.call(str(output_dir / "test_lattice_import_optics.py"))

    return env.lines["line"]


def _build_quad_pair_line(offset):
    line = xt.Line(
        elements      = [
            xt.Marker(),
            xt.Quadrupole(length = 0.4 + offset, k1 = 0.1),
            xt.Quadrupole(length = 0.4 - offset, k1 = 0.2),
            xt.Marker()],
        element_names = ["start", "q1", "q2", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_bend_pair_line(offset):
    line = xt.Line(
        elements      = [
            xt.Marker(),
            xt.Bend(length = 0.6 + offset, k0 = 0.01, angle = 0.006),
            xt.Bend(length = 0.6 - offset, k0 = 0.02, angle = 0.012),
            xt.Marker()],
        element_names = ["start", "b1", "b2", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_corrector_pair_line(offset):
    # Correctors are Bend elements with angle = 0 (see extract_corrector_information)
    line = xt.Line(
        elements      = [
            xt.Marker(),
            xt.Bend(length = 0.3 + offset, k0 = 0.001, angle = 0),
            xt.Bend(length = 0.3 - offset, k0 = 0.002, angle = 0),
            xt.Marker()],
        element_names = ["start", "c1", "c2", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line

################################################################################
# Sub-precision lengths must not collide on reload
################################################################################
def test_quads_within_precision_reload_without_name_collision(tmp_path):
    """
    Two quadrupoles whose lengths differ by less than MAGNET_LENGTH_PRECISION
    round to the same base-element name. Both must still reload as distinct
    elements, each keeping its own k1.
    """
    original_line = _build_quad_pair_line(offset = SUB_PRECISION_OFFSET)
    reloaded_line = _write_and_load(original_line, tmp_path)

    assert reloaded_line["q1"].k1 == pytest.approx(0.1), (
        "Quadrupole 'q1' should keep its own k1 after reload despite sharing "
        "a truncated base-element length with 'q2'")
    assert reloaded_line["q2"].k1 == pytest.approx(0.2), (
        "Quadrupole 'q2' should keep its own k1 after reload despite sharing "
        "a truncated base-element length with 'q1'")
    assert reloaded_line["q1"].length == pytest.approx(0.4, abs = PRECISION), (
        "Quadrupole 'q1' length should round-trip to within MAGNET_LENGTH_PRECISION")
    assert reloaded_line["q2"].length == pytest.approx(0.4, abs = PRECISION), (
        "Quadrupole 'q2' length should round-trip to within MAGNET_LENGTH_PRECISION")


def test_bends_within_precision_reload_without_name_collision(tmp_path):
    """
    Two bends whose lengths differ by less than MAGNET_LENGTH_PRECISION round
    to the same base-element name (this is the case originally reported: a
    duplicate `hbend<length>` base element raising on reload).
    """
    original_line = _build_bend_pair_line(offset = SUB_PRECISION_OFFSET)
    reloaded_line = _write_and_load(original_line, tmp_path)

    assert reloaded_line["b1"].k0 == pytest.approx(0.01), (
        "Bend 'b1' should keep its own k0 after reload despite sharing a "
        "truncated base-element length with 'b2'")
    assert reloaded_line["b2"].k0 == pytest.approx(0.02), (
        "Bend 'b2' should keep its own k0 after reload despite sharing a "
        "truncated base-element length with 'b1'")
    assert reloaded_line["b1"].angle == pytest.approx(0.006), (
        "Bend 'b1' should keep its own angle after reload")
    assert reloaded_line["b2"].angle == pytest.approx(0.012), (
        "Bend 'b2' should keep its own angle after reload")


def test_correctors_within_precision_reload_without_name_collision(tmp_path):
    """
    Two correctors (Bend elements with angle = 0) whose lengths differ by
    less than MAGNET_LENGTH_PRECISION round to the same base-element name.
    """
    original_line = _build_corrector_pair_line(offset = SUB_PRECISION_OFFSET)
    reloaded_line = _write_and_load(original_line, tmp_path)

    assert reloaded_line["c1"].k0 == pytest.approx(0.001), (
        "Corrector 'c1' should keep its own k0 after reload despite sharing "
        "a truncated base-element length with 'c2'")
    assert reloaded_line["c2"].k0 == pytest.approx(0.002), (
        "Corrector 'c2' should keep its own k0 after reload despite sharing "
        "a truncated base-element length with 'c1'")

################################################################################
# Lengths beyond precision must remain distinct (no over-merging)
################################################################################
def test_quads_beyond_precision_keep_distinct_lengths(tmp_path):
    """
    Two quadrupoles whose lengths differ by much more than
    MAGNET_LENGTH_PRECISION must round-trip with their own distinct lengths,
    not collapse onto a shared base-element length.
    """
    original_line = _build_quad_pair_line(offset = SUPER_PRECISION_OFFSET)
    reloaded_line = _write_and_load(original_line, tmp_path)

    assert reloaded_line["q1"].length != reloaded_line["q2"].length, (
        "Quadrupoles with lengths differing by more than MAGNET_LENGTH_PRECISION "
        "should not be merged onto a shared base-element length")
    assert reloaded_line["q1"].length == pytest.approx(0.4 + SUPER_PRECISION_OFFSET, abs = PRECISION)
    assert reloaded_line["q2"].length == pytest.approx(0.4 - SUPER_PRECISION_OFFSET, abs = PRECISION)


def test_bends_beyond_precision_keep_distinct_lengths(tmp_path):
    """
    Two bends whose lengths differ by much more than MAGNET_LENGTH_PRECISION
    must round-trip with their own distinct lengths.
    """
    original_line = _build_bend_pair_line(offset = SUPER_PRECISION_OFFSET)
    reloaded_line = _write_and_load(original_line, tmp_path)

    assert reloaded_line["b1"].length != reloaded_line["b2"].length, (
        "Bends with lengths differing by more than MAGNET_LENGTH_PRECISION "
        "should not be merged onto a shared base-element length")
