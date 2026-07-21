"""
================================================================================
Tests for bend element writer serialisation
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import pytest
import xtrack as xt

from tests.support.writer_helpers import write_and_load as _shared_write_and_load

################################################################################
# Helpers
################################################################################
def _write_and_load(line, tmp_path):
    """
    Write a line using the public SAD2XS writer entry points, reload it in a
    clean Xsuite environment, and return the environment and reloaded line.

    The bend writer outputs:
      - A base element: env.new(name=`hbend...`, prototype=xt.Bend, length=L)
      - A clone:        env.new(name=`b1`, prototype=`hbend...`, angle=<literal>, k0=`k0_b1`)
      - Optics file:    k0_b1 = angle/length   (24 decimal places)

    The angle itself is a fixed literal; only k0 is a live deferred
    expression, so modifying env[`k0_b1`] changes k0 without moving the
    geometric angle. Edge angles (entry/exit/fdown) are written as bare
    literal numbers. shift_x and shift_y are written as literal Python
    string expressions that Xsuite evaluates on load.

    Vertical bends (rot_s_rad ≈ π/2) carry the rotation on the base element;
    the clone inherits it. Skew bends (arbitrary rot_s_rad) carry the rotation
    on the clone as a literal string.

    For a combined function magnet (k1 != 0), k1 is also written as a live
    deferred expression `k1_{name}`, alongside k0.
    """
    return _shared_write_and_load(line, tmp_path, output_header = "Bend writer test")


def _writer_roundtrip(line, tmp_path):
    """
    Write and reload a line. Returns the reloaded line only.
    """
    _, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)
    return reloaded_line


def _build_hbend_line(
        angle                   = 0.1,
        length                  = 0.5,
        edge_entry_angle        = 0.0,
        edge_exit_angle         = 0.0,
        edge_entry_angle_fdown  = 0.0,
        edge_exit_angle_fdown   = 0.0,
        edge_entry_fint         = 0.0,
        edge_entry_hgap         = 0.0,
        edge_exit_fint          = 0.0,
        edge_exit_hgap          = 0.0,
        shift_x                 = 0.0,
        shift_y                 = 0.0,
        knl                     = None,
        ksl                     = None):
    """
    Build a minimal single horizontal-bend Xsuite line with a reference
    particle. Horizontal bends have rot_s_rad = 0 (the default).
    angle must be non-zero so the bend writer classifies the element as a bend
    (h = angle/length != 0) rather than a corrector.
    """
    bend_kwargs = dict(
        angle                   = angle,
        length                  = length,
        edge_entry_angle        = edge_entry_angle,
        edge_exit_angle         = edge_exit_angle,
        edge_entry_angle_fdown  = edge_entry_angle_fdown,
        edge_exit_angle_fdown   = edge_exit_angle_fdown,
        edge_entry_fint         = edge_entry_fint,
        edge_entry_hgap         = edge_entry_hgap,
        edge_exit_fint          = edge_exit_fint,
        edge_exit_hgap          = edge_exit_hgap,
        shift_x                 = shift_x,
        shift_y                 = shift_y)
    if edge_entry_fint or edge_entry_hgap or edge_exit_fint or edge_exit_hgap:
        bend_kwargs["edge_entry_model"] = "full"
        bend_kwargs["edge_exit_model"]  = "full"
    if knl is not None:
        bend_kwargs["knl"] = knl
    if ksl is not None:
        bend_kwargs["ksl"] = ksl

    line = xt.Line(
        elements      = [xt.Marker(), xt.Bend(**bend_kwargs), xt.Marker()],
        element_names = ["start", "b1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_vbend_line(
        angle  = 0.05,
        length = 0.4):
    """
    Build a minimal single vertical-bend Xsuite line.
    Vertical bends have rot_s_rad = π/2; the writer puts this on the base
    element rather than the clone.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Bend(
            angle      = angle,
            length     = length,
            rot_s_rad  = np.pi / 2), xt.Marker()],
        element_names = ["start", "vb1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_sbend_line(
        angle     = 0.08,
        length    = 0.6,
        rot_s_rad = np.pi / 4):
    """
    Build a minimal single skew-bend Xsuite line.
    Skew bends have a rot_s_rad that is not 0 or +π/2; the writer places the
    rotation on the clone as a literal string expression.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Bend(
            angle     = angle,
            length    = length,
            rot_s_rad = rot_s_rad), xt.Marker()],
        element_names = ["start", "sb1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


################################################################################
# Horizontal Bend — Basic Serialisation
################################################################################
def test_bend_writer_reloads_as_xsuite_bend(tmp_path):
    """
    A written Bend element should reload as an xt.Bend in a clean Xsuite
    environment.
    """
    original_line = _build_hbend_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["b1"], xt.Bend), (
        "Written Bend element `b1` should reload as xt.Bend. "
        f"""Got: {type(reloaded_line["b1"]).__name__}.""")


def test_bend_writer_preserves_element_name(tmp_path):
    """
    A written Bend element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_hbend_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "b1" in list(reloaded_line.element_names), (
        "Reloaded line should contain Bend element `b1`. "
        f"Got: {list(reloaded_line.element_names)}.")


def test_bend_writer_preserves_length(tmp_path):
    """
    The length of a Bend should be preserved through a write and reload cycle.
    Length is written on the shared base element, not the clone.
    """
    original_line = _build_hbend_line(length = 0.75)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].length == pytest.approx(0.75), (
        "Writer roundtrip should preserve Bend length. "
        f"""Original: 0.75, reloaded: {reloaded_line["b1"].length}.""")


################################################################################
# Horizontal Bend — Angle (Optics Expression)
################################################################################
def test_bend_writer_preserves_positive_angle(tmp_path):
    """
    A positive bending angle should be preserved through a write and reload
    cycle. The angle is written as a fixed literal on the clone; k0 =
    angle/length is written separately as a deferred expression.
    """
    original_line = _build_hbend_line(angle = 0.12, length = 0.6)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].angle == pytest.approx(0.12), (
        "Writer roundtrip should preserve positive Bend angle. "
        f"""Original: 0.12, reloaded: {reloaded_line["b1"].angle}.""")


def test_bend_writer_preserves_negative_angle(tmp_path):
    """
    A negative bending angle (negative k0) should be preserved through a write
    and reload cycle.
    """
    original_line = _build_hbend_line(angle = -0.08, length = 0.5)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].angle == pytest.approx(-0.08), (
        "Writer roundtrip should preserve negative Bend angle. "
        f"""Original: -0.08, reloaded: {reloaded_line["b1"].angle}.""")


def test_bend_writer_angle_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the bend strength k0_b1 should exist in the
    Xsuite environment and equal angle/length.
    """
    angle  = 0.12
    length = 0.6
    original_line = _build_hbend_line(angle = angle, length = length)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    expected_k0 = angle / length
    assert env["k0_b1"] == pytest.approx(expected_k0), (
        "Optics variable `k0_b1` should equal angle/length after reload. "
        f"""Expected: {expected_k0}, got: {env["k0_b1"]}.""")


def test_bend_writer_k0_is_tunable_via_optics_variable(tmp_path):
    """
    The k0_b1 optics variable should remain live after reload: modifying it
    should immediately update the Bend k0. The geometric angle is a fixed literal
    and must remain unchanged when k0 is varied.
    """
    original_line = _build_hbend_line(angle = 0.12, length = 0.6)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    new_k0 = 0.30
    env["k0_b1"] = new_k0

    assert reloaded_line["b1"].k0 == pytest.approx(new_k0), (
        "Modifying optics variable `k0_b1` should update the Bend k0. "
        f"""Expected: {new_k0}, got: {reloaded_line["b1"].k0}.""")
    assert reloaded_line["b1"].angle == pytest.approx(0.12), (
        "The geometric angle should remain fixed when k0 is varied. "
        f"""Expected: 0.12, got: {reloaded_line["b1"].angle}.""")


################################################################################
# Horizontal Bend — Edge Angles (Bare Literals)
################################################################################
def test_bend_writer_preserves_edge_entry_angle(tmp_path):
    """
    The edge_entry_angle of a Bend should be preserved through a write and
    reload cycle. Edge angles are written as bare literal numbers in the lattice
    file (not as optics expression variables).
    """
    original_line = _build_hbend_line(edge_entry_angle = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].edge_entry_angle == pytest.approx(0.05), (
        "Writer roundtrip should preserve Bend edge_entry_angle. "
        f"""Original: 0.05, reloaded: {reloaded_line["b1"].edge_entry_angle}.""")


def test_bend_writer_preserves_edge_exit_angle(tmp_path):
    """
    The edge_exit_angle of a Bend should be preserved through a write and
    reload cycle.
    """
    original_line = _build_hbend_line(edge_exit_angle = 0.04)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].edge_exit_angle == pytest.approx(0.04), (
        "Writer roundtrip should preserve Bend edge_exit_angle. "
        f"""Original: 0.04, reloaded: {reloaded_line["b1"].edge_exit_angle}.""")


def test_bend_writer_preserves_edge_entry_angle_fdown(tmp_path):
    """
    The edge_entry_angle_fdown (field-clamp fringe entry) of a Bend should be
    preserved through a write and reload cycle.
    """
    original_line = _build_hbend_line(edge_entry_angle_fdown = 0.03)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].edge_entry_angle_fdown == pytest.approx(0.03), (
        "Writer roundtrip should preserve Bend edge_entry_angle_fdown. "
        f"""Original: 0.03, reloaded: {reloaded_line["b1"].edge_entry_angle_fdown}.""")


def test_bend_writer_preserves_edge_exit_angle_fdown(tmp_path):
    """
    The edge_exit_angle_fdown (field-clamp fringe exit) of a Bend should be
    preserved through a write and reload cycle.
    """
    original_line = _build_hbend_line(edge_exit_angle_fdown = 0.02)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].edge_exit_angle_fdown == pytest.approx(0.02), (
        "Writer roundtrip should preserve Bend edge_exit_angle_fdown. "
        f"""Original: 0.02, reloaded: {reloaded_line["b1"].edge_exit_angle_fdown}.""")


################################################################################
# Horizontal Bend — Edge Fringe (fint/hgap)
################################################################################
def test_bend_writer_preserves_edge_entry_fint(tmp_path):
    """
    The edge_entry_fint of a Bend (F1/FRINGE soft-edge fringe import) should
    be preserved through a write and reload cycle.
    """
    original_line = _build_hbend_line(edge_entry_fint = 0.06)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].edge_entry_fint == pytest.approx(0.06), (
        "Writer roundtrip should preserve Bend edge_entry_fint. "
        f"""Original: 0.06, reloaded: {reloaded_line["b1"].edge_entry_fint}.""")


def test_bend_writer_preserves_edge_entry_hgap(tmp_path):
    """
    The edge_entry_hgap of a Bend should be preserved through a write and
    reload cycle.
    """
    original_line = _build_hbend_line(edge_entry_hgap = 0.06)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].edge_entry_hgap == pytest.approx(0.06), (
        "Writer roundtrip should preserve Bend edge_entry_hgap. "
        f"""Original: 0.06, reloaded: {reloaded_line["b1"].edge_entry_hgap}.""")


def test_bend_writer_preserves_edge_exit_fint(tmp_path):
    """
    The edge_exit_fint of a Bend should be preserved through a write and
    reload cycle.
    """
    original_line = _build_hbend_line(edge_exit_fint = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].edge_exit_fint == pytest.approx(0.05), (
        "Writer roundtrip should preserve Bend edge_exit_fint. "
        f"""Original: 0.05, reloaded: {reloaded_line["b1"].edge_exit_fint}.""")


def test_bend_writer_preserves_edge_exit_hgap(tmp_path):
    """
    The edge_exit_hgap of a Bend should be preserved through a write and
    reload cycle.
    """
    original_line = _build_hbend_line(edge_exit_hgap = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].edge_exit_hgap == pytest.approx(0.05), (
        "Writer roundtrip should preserve Bend edge_exit_hgap. "
        f"""Original: 0.05, reloaded: {reloaded_line["b1"].edge_exit_hgap}.""")


def test_bend_writer_treats_fringed_bend_as_non_simple(tmp_path):
    """
    A Bend whose ONLY non-default attribute is edge fint/hgap (no edge
    angles, offsets, k1, or multipole content) must still route through the
    writer's full serialisation form, not the compact one-liner -- the
    compact form omits every extra attribute, including fint/hgap.
    """
    original_line = _build_hbend_line(edge_entry_fint = 0.06, edge_entry_hgap = 0.06)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].edge_entry_fint == pytest.approx(0.06), (
        "A Bend with only fint/hgap set (otherwise default) should not be "
        "misclassified as `simple` by the writer -- got edge_entry_fint="
        f"""{reloaded_line["b1"].edge_entry_fint} after roundtrip, expected 0.06.""")


################################################################################
# Horizontal Bend — Offsets (Literal Strings)
################################################################################
def test_bend_writer_preserves_positive_shift_x(tmp_path):
    """
    A positive horizontal offset shift_x of a Bend should be preserved through
    a write and reload cycle. shift_x is written as a literal Python string
    expression, which Xsuite evaluates on load.
    """
    original_line = _build_hbend_line(shift_x = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve positive Bend shift_x. "
        f"""Original: 1.0E-3, reloaded: {reloaded_line["b1"].shift_x}.""")


def test_bend_writer_preserves_negative_shift_y(tmp_path):
    """
    A negative vertical offset shift_y of a Bend should be preserved through a
    write and reload cycle.
    """
    original_line = _build_hbend_line(shift_y = -2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve negative Bend shift_y. "
        f"""Original: -2.0E-3, reloaded: {reloaded_line["b1"].shift_y}.""")


################################################################################
# Horizontal Bend — All Fields Simultaneously (Complex Path)
################################################################################
def test_bend_writer_preserves_all_fields_simultaneously(tmp_path):
    """
    A Bend with angle, edge angles, and offsets all non-zero should preserve
    all fields through a write and reload cycle. This exercises the complex
    (multi-field) output path rather than the compact single-line form.
    """
    original_line = _build_hbend_line(
        angle                   = 0.12,
        length                  = 0.6,
        edge_entry_angle        = 0.05,
        edge_exit_angle         = 0.04,
        edge_entry_angle_fdown  = 0.03,
        edge_exit_angle_fdown   = 0.02,
        shift_x                 = 1.0E-3,
        shift_y                 = -2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].angle                  == pytest.approx(0.12),   (
        f"""Should preserve angle. Reloaded: {reloaded_line["b1"].angle}.""")
    assert reloaded_line["b1"].length                 == pytest.approx(0.6),    (
        f"""Should preserve length. Reloaded: {reloaded_line["b1"].length}.""")
    assert reloaded_line["b1"].edge_entry_angle       == pytest.approx(0.05),   (
        f"""Should preserve edge_entry_angle. Reloaded: {reloaded_line["b1"].edge_entry_angle}.""")
    assert reloaded_line["b1"].edge_exit_angle        == pytest.approx(0.04),   (
        f"""Should preserve edge_exit_angle. Reloaded: {reloaded_line["b1"].edge_exit_angle}.""")
    assert reloaded_line["b1"].edge_entry_angle_fdown == pytest.approx(0.03),   (
        f"""Should preserve edge_entry_angle_fdown. Reloaded: {reloaded_line["b1"].edge_entry_angle_fdown}.""")
    assert reloaded_line["b1"].edge_exit_angle_fdown  == pytest.approx(0.02),   (
        f"""Should preserve edge_exit_angle_fdown. Reloaded: {reloaded_line["b1"].edge_exit_angle_fdown}.""")
    assert reloaded_line["b1"].shift_x                == pytest.approx(1.0E-3), (
        f"""Should preserve shift_x. Reloaded: {reloaded_line["b1"].shift_x}.""")
    assert reloaded_line["b1"].shift_y                == pytest.approx(-2.0E-3),(
        f"""Should preserve shift_y. Reloaded: {reloaded_line["b1"].shift_y}.""")


################################################################################
# Vertical Bend
################################################################################
def test_bend_writer_vertical_bend_reloads_as_xsuite_bend(tmp_path):
    """
    A vertical Bend (rot_s_rad = π/2) should reload as an xt.Bend. The writer
    places the rotation on the shared base element (`vbend...`) rather than the
    clone, so the clone inherits it.
    """
    original_line = _build_vbend_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["vb1"], xt.Bend), (
        "Written vertical Bend `vb1` should reload as xt.Bend. "
        f"""Got: {type(reloaded_line["vb1"]).__name__}.""")


def test_bend_writer_vertical_bend_preserves_angle(tmp_path):
    """
    The bending angle of a vertical Bend should be preserved through a write
    and reload cycle.
    """
    original_line = _build_vbend_line(angle = 0.05, length = 0.4)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["vb1"].angle == pytest.approx(0.05), (
        "Writer roundtrip should preserve vertical Bend angle. "
        f"""Original: 0.05, reloaded: {reloaded_line["vb1"].angle}.""")


def test_bend_writer_vertical_bend_preserves_rotation(tmp_path):
    """
    The rot_s_rad = π/2 of a vertical Bend should be preserved through a write
    and reload cycle. It is encoded on the shared base element and inherited by
    the clone.
    """
    original_line = _build_vbend_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["vb1"].rot_s_rad == pytest.approx(np.pi / 2), (
        "Writer roundtrip should preserve vertical Bend rot_s_rad = π/2. "
        f"""Reloaded: {reloaded_line["vb1"].rot_s_rad}.""")


################################################################################
# Skew Bend
################################################################################
def test_bend_writer_skew_bend_reloads_as_xsuite_bend(tmp_path):
    """
    A skew Bend (rot_s_rad not in {0, +π/2}) should reload as an xt.Bend. The
    writer places the rotation on the clone as a literal string expression.
    """
    original_line = _build_sbend_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["sb1"], xt.Bend), (
        "Written skew Bend `sb1` should reload as xt.Bend. "
        f"""Got: {type(reloaded_line["sb1"]).__name__}.""")


def test_bend_writer_skew_bend_preserves_rotation(tmp_path):
    """
    The arbitrary rot_s_rad of a skew Bend should be preserved through a write
    and reload cycle.
    """
    rot = np.pi / 4
    original_line = _build_sbend_line(rot_s_rad = rot)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sb1"].rot_s_rad == pytest.approx(rot), (
        "Writer roundtrip should preserve skew Bend rot_s_rad. "
        f"""Original: {rot}, reloaded: {reloaded_line["sb1"].rot_s_rad}.""")


def test_bend_writer_skew_bend_preserves_angle(tmp_path):
    """
    The bending angle of a skew Bend should be preserved through a write and
    reload cycle. This exercises the sbend code path, where the clone carries
    both the angle expression and the rot_s_rad literal string, distinct from
    the hbend (rotation on base) and vbend (rotation on base) paths.
    """
    original_line = _build_sbend_line(angle = 0.08, length = 0.6)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sb1"].angle == pytest.approx(0.08), (
        "Writer roundtrip should preserve skew Bend angle. "
        f"""Original: 0.08, reloaded: {reloaded_line["sb1"].angle}.""")


@pytest.mark.parametrize("rot_s_rad", [np.pi, -np.pi / 2])
def test_bend_writer_preserves_explicit_special_rotations(tmp_path, rot_s_rad):
    """
    External Xsuite bends with pi or -pi/2 rotations should be written as that
    representation, not rewritten into SAD2XS conversion canonical form.
    """
    original_line = _build_sbend_line(
        angle     = 0.08,
        length    = 0.6,
        rot_s_rad = rot_s_rad)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sb1"].angle == pytest.approx(0.08), (
        "Writer roundtrip should preserve explicit-rotation Bend angle. "
        f"""Original: 0.08, reloaded: {reloaded_line["sb1"].angle}.""")
    assert reloaded_line["sb1"].rot_s_rad == pytest.approx(rot_s_rad), (
        "Writer roundtrip should preserve explicit Bend rot_s_rad. "
        f"""Original: {rot_s_rad}, reloaded: {reloaded_line["sb1"].rot_s_rad}.""")


################################################################################
# Multiple Bends
################################################################################
def test_bend_writer_preserves_multiple_bends_independently(tmp_path):
    """
    Multiple Bend elements with different angles and lengths should each
    preserve their individual values through a single write and reload cycle.
    Each gets its own optics variable (k0_ba, k0_bb).
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Bend(angle = 0.10, length = 0.5),
            xt.Bend(angle = 0.06, length = 0.4),
            xt.Marker(),
        ],
        element_names = ["start", "ba", "bb", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    assert reloaded_line["ba"].angle  == pytest.approx(0.10), (
        "Writer roundtrip should preserve angle for `ba`. "
        f"""Original: 0.10, reloaded: {reloaded_line["ba"].angle}.""")
    assert reloaded_line["ba"].length == pytest.approx(0.5),  (
        "Writer roundtrip should preserve length for `ba`. "
        f"""Original: 0.5, reloaded: {reloaded_line["ba"].length}.""")
    assert reloaded_line["bb"].angle  == pytest.approx(0.06), (
        "Writer roundtrip should preserve angle for `bb`. "
        f"""Original: 0.06, reloaded: {reloaded_line["bb"].angle}.""")
    assert reloaded_line["bb"].length == pytest.approx(0.4),  (
        "Writer roundtrip should preserve length for `bb`. "
        f"""Original: 0.4, reloaded: {reloaded_line["bb"].length}.""")


def test_bend_writer_bends_with_same_length_share_base_element(tmp_path):
    """
    Two Bend elements with the same length should share a single base element
    in the output lattice file and each have their own k0 optics variable.
    Both angles should be independently preserved.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Bend(angle = 0.10, length = 0.5),
            xt.Bend(angle = 0.08, length = 0.5),
            xt.Marker(),
        ],
        element_names = ["start", "ba", "bb", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    assert reloaded_line["ba"].angle == pytest.approx(0.10), (
        "Bends sharing a base element: angle for `ba` should be preserved. "
        f"""Original: 0.10, reloaded: {reloaded_line["ba"].angle}.""")
    assert reloaded_line["bb"].angle == pytest.approx(0.08), (
        "Bends sharing a base element: angle for `bb` should be preserved. "
        f"""Original: 0.08, reloaded: {reloaded_line["bb"].angle}.""")
    assert env["k0_ba"] == pytest.approx(0.10 / 0.5), (
        f"""`k0_ba` should equal angle/length. Reloaded: {env["k0_ba"]}.""")
    assert env["k0_bb"] == pytest.approx(0.08 / 0.5), (
        f"""`k0_bb` should equal angle/length. Reloaded: {env["k0_bb"]}.""")


################################################################################
# Precision
################################################################################
def test_bend_writer_preserves_angle_at_full_double_precision(tmp_path):
    """
    The bend angle should survive the write and reload cycle at full IEEE 754
    double precision. The optics file writes k0 at 24 decimal places. An angle
    derived from π (an irrational number) exercises the precision path beyond
    what a simple round decimal value would expose.
    """
    angle  = np.pi / 37
    length = 0.5
    original_line = _build_hbend_line(angle = angle, length = length)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].angle == pytest.approx(angle, rel = 1E-12), (
        "Writer roundtrip should preserve Bend angle to full double precision. "
        f"""Original: {angle}, reloaded: {reloaded_line["b1"].angle}, """
        f"""diff: {abs(reloaded_line["b1"].angle - angle)}.""")


################################################################################
# k1 Combined Function
################################################################################
def test_bend_writer_k1_is_preserved_for_combined_function_magnet(tmp_path):
    """
    A combined function bend (angle != 0 AND k1 != 0) should preserve k1
    through a write and reload cycle.

    This is a regression test for preserving the combined-function quadrupole
    gradient independently from the dipole angle.
    """
    original_line = _build_hbend_line(angle = 0.1, length = 0.5)
    original_line["b1"].k1 = 0.5

    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["b1"].k1 == pytest.approx(0.5), (
        "Writer roundtrip should preserve combined function Bend k1. "
        f"""Original: 0.5, reloaded: {reloaded_line["b1"].k1}.""")


################################################################################
# Combined Multipole Components
################################################################################
########################################
# Higher-Order knl Components
########################################
def test_bend_writer_preserves_knl_combined_multipole_component(tmp_path):
    """
    A bend with a combined sextupole component (knl[2] != 0) should preserve
    that component through a write and reload cycle.
    """
    original_line = _build_hbend_line(angle = 0.1, knl = [0.0, 0.0, 5.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_knl = np.asarray(original_line["b1"].knl)
    reloaded_knl = np.asarray(reloaded_line["b1"].knl)

    assert reloaded_knl.tolist() == pytest.approx(original_knl.tolist()), (
        "Writer roundtrip should preserve bend knl combined multipole components. "
        f"Original knl: {original_knl.tolist()}, "
        f"reloaded knl: {reloaded_knl.tolist()}.")


########################################
# Higher-Order ksl Components
########################################
def test_bend_writer_preserves_ksl_combined_multipole_component(tmp_path):
    """
    A bend with a combined skew sextupole component (ksl[2] != 0) should
    preserve that component through a write and reload cycle.
    """
    original_line = _build_hbend_line(angle = 0.1, ksl = [0.0, 0.0, -3.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_ksl = np.asarray(original_line["b1"].ksl)
    reloaded_ksl = np.asarray(reloaded_line["b1"].ksl)

    assert reloaded_ksl.tolist() == pytest.approx(original_ksl.tolist()), (
        "Writer roundtrip should preserve bend ksl combined multipole components. "
        f"Original ksl: {original_ksl.tolist()}, "
        f"reloaded ksl: {reloaded_ksl.tolist()}.")


def test_bend_writer_preserves_knl_and_ksl_components_simultaneously(tmp_path):
    """
    A bend carrying both knl and ksl combined multipole components should
    preserve both through a write and reload cycle.
    """
    original_line = _build_hbend_line(
        angle   = 0.1,
        knl     = [0.0, 0.0, 5.0E-4],
        ksl     = [0.0, 0.0, -3.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_knl = np.asarray(original_line["b1"].knl)
    reloaded_knl = np.asarray(reloaded_line["b1"].knl)
    original_ksl = np.asarray(original_line["b1"].ksl)
    reloaded_ksl = np.asarray(reloaded_line["b1"].ksl)

    assert reloaded_knl.tolist() == pytest.approx(original_knl.tolist()), (
        "Writer roundtrip should preserve bend knl. "
        f"Original: {original_knl.tolist()}, reloaded: {reloaded_knl.tolist()}.")
    assert reloaded_ksl.tolist() == pytest.approx(original_ksl.tolist()), (
        "Writer roundtrip should preserve bend ksl. "
        f"Original: {original_ksl.tolist()}, reloaded: {reloaded_ksl.tolist()}.")
