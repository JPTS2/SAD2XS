"""
================================================================================
Tests for corrector element writer serialisation
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

    Correctors are xt.Bend elements with h = 0 (k0_from_h=False, angle=0,
    k0 set explicitly). The corrector writer outputs:
      - A base element: env.new(name='hcorr...', prototype=xt.Bend, length=L)
      - A clone:        env.new(name='c1', prototype='hcorr...', k0='k0_c1')
      - Optics file:    k0_c1 = <value>   (24 decimal places)

    This differs from the bend writer, which writes a fixed literal angle
    alongside k0 as the deferred expression. For correctors, k0 IS the
    optics variable directly; modifying env['k0_c1'] immediately updates
    line['c1'].k0.

    Vertical correctors (rot_s_rad ≈ π/2) carry the rotation on the shared
    base element. Skew correctors (arbitrary rot_s_rad) carry the rotation on
    the clone as a literal string expression.

    Edge angles and shifts follow the same convention as bends: bare literals
    and literal Python strings respectively.
    """
    return _shared_write_and_load(line, tmp_path, output_header = "Corrector writer test")


def _writer_roundtrip(line, tmp_path):
    """
    Write and reload a line. Returns the reloaded line only.
    """
    _, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)
    return reloaded_line


def _build_hcorr_line(
        k0                      = 1.0E-4,
        length                  = 0.3,
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
    Build a minimal single horizontal-corrector Xsuite line with a reference
    particle. Horizontal correctors are xt.Bend elements with k0_from_h=False
    (so h = angle/length = 0) and k0 set explicitly. The writer classifies them
    as correctors because line['c1'].h == 0.
    """
    corr_kwargs = dict(
        k0                      = k0,
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
        corr_kwargs["edge_entry_model"] = "full"
        corr_kwargs["edge_exit_model"]  = "full"
    if knl is not None:
        corr_kwargs["knl"] = knl
    if ksl is not None:
        corr_kwargs["ksl"] = ksl

    line = xt.Line(
        elements      = [xt.Marker(), xt.Bend(**corr_kwargs), xt.Marker()],
        element_names = ["start", "c1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_vcorr_line(
        k0     = 1.0E-4,
        length = 0.3):
    """
    Build a minimal single vertical-corrector Xsuite line.
    Vertical correctors have rot_s_rad = π/2; the writer puts this on the base
    element rather than the clone.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Bend(
            k0        = k0,
            length    = length,
            rot_s_rad = np.pi / 2), xt.Marker()],
        element_names = ["start", "vc1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_scorr_line(
        k0        = 1.0E-4,
        length    = 0.3,
        rot_s_rad = np.pi / 4):
    """
    Build a minimal single skew-corrector Xsuite line.
    Skew correctors have a rot_s_rad not in {0, +π/2}; the writer places the
    rotation on the clone as a literal string expression.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Bend(
            k0        = k0,
            length    = length,
            rot_s_rad = rot_s_rad), xt.Marker()],
        element_names = ["start", "sc1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


################################################################################
# Horizontal Corrector — Basic Serialisation
################################################################################
def test_corr_writer_reloads_as_xsuite_bend(tmp_path):
    """
    A written corrector element should reload as an xt.Bend in a clean Xsuite
    environment. Correctors are xt.Bend elements with h = 0 and no reference
    orbit curvature; they reload as the same Bend type.
    """
    original_line = _build_hcorr_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["c1"], xt.Bend), (
        "Written corrector element 'c1' should reload as xt.Bend. "
        f"Got: {type(reloaded_line['c1']).__name__}.")


def test_corr_writer_preserves_element_name(tmp_path):
    """
    A written corrector element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_hcorr_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "c1" in list(reloaded_line.element_names), (
        "Reloaded line should contain corrector element 'c1'. "
        f"Got: {list(reloaded_line.element_names)}.")


def test_corr_writer_preserves_length(tmp_path):
    """
    The length of a corrector should be preserved through a write and reload
    cycle. Length is written on the shared base element, not the clone.
    """
    original_line = _build_hcorr_line(length = 0.45)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].length == pytest.approx(0.45), (
        "Writer roundtrip should preserve corrector length. "
        f"Original: 0.45, reloaded: {reloaded_line['c1'].length}.")


################################################################################
# Horizontal Corrector — k0 (Optics Expression)
################################################################################
def test_corr_writer_preserves_positive_k0(tmp_path):
    """
    A positive dipole field strength k0 should be preserved through a write and
    reload cycle. Unlike bends, correctors carry no separate literal angle on
    the clone -- k0 is the only field strength written.
    """
    original_line = _build_hcorr_line(k0 = 1.5E-4)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].k0 == pytest.approx(1.5E-4), (
        "Writer roundtrip should preserve positive corrector k0. "
        f"Original: 1.5E-4, reloaded: {reloaded_line['c1'].k0}.")


def test_corr_writer_preserves_negative_k0(tmp_path):
    """
    A negative dipole field strength k0 should be preserved through a write and
    reload cycle.
    """
    original_line = _build_hcorr_line(k0 = -2.0E-4)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].k0 == pytest.approx(-2.0E-4), (
        "Writer roundtrip should preserve negative corrector k0. "
        f"Original: -2.0E-4, reloaded: {reloaded_line['c1'].k0}.")


def test_corr_writer_k0_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the corrector strength k0_c1 should exist in
    the Xsuite environment and equal the original k0 value. Unlike bends (which
    store k0 = angle/length), for correctors k0 is the value written directly.
    """
    original_line = _build_hcorr_line(k0 = 1.5E-4)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["k0_c1"] == pytest.approx(1.5E-4), (
        "Optics variable 'k0_c1' should equal the original k0 after reload. "
        f"Expected: 1.5E-4, got: {env['k0_c1']}.")


def test_corr_writer_k0_is_tunable_via_optics_variable(tmp_path):
    """
    The k0_c1 optics variable should remain live after reload: modifying it
    should immediately update the corrector k0 in the line.
    """
    original_line = _build_hcorr_line(k0 = 1.5E-4)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["k0_c1"] = 3.0E-4

    assert reloaded_line["c1"].k0 == pytest.approx(3.0E-4), (
        "Modifying optics variable 'k0_c1' should update the corrector k0. "
        f"Expected: 3.0E-4, got: {reloaded_line['c1'].k0}.")


################################################################################
# Horizontal Corrector — Edge Angles (Bare Literals)
################################################################################
def test_corr_writer_preserves_edge_entry_angle(tmp_path):
    """
    The edge_entry_angle of a corrector should be preserved through a write and
    reload cycle. Edge angles are written as bare literal numbers, not as optics
    expression variables, identical to the bend writer convention.
    """
    original_line = _build_hcorr_line(edge_entry_angle = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].edge_entry_angle == pytest.approx(0.05), (
        "Writer roundtrip should preserve corrector edge_entry_angle. "
        f"Original: 0.05, reloaded: {reloaded_line['c1'].edge_entry_angle}.")


def test_corr_writer_preserves_edge_exit_angle(tmp_path):
    """
    The edge_exit_angle of a corrector should be preserved through a write and
    reload cycle.
    """
    original_line = _build_hcorr_line(edge_exit_angle = 0.04)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].edge_exit_angle == pytest.approx(0.04), (
        "Writer roundtrip should preserve corrector edge_exit_angle. "
        f"Original: 0.04, reloaded: {reloaded_line['c1'].edge_exit_angle}.")


def test_corr_writer_preserves_edge_entry_angle_fdown(tmp_path):
    """
    The edge_entry_angle_fdown of a corrector should be preserved through a
    write and reload cycle.
    """
    original_line = _build_hcorr_line(edge_entry_angle_fdown = 0.03)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].edge_entry_angle_fdown == pytest.approx(0.03), (
        "Writer roundtrip should preserve corrector edge_entry_angle_fdown. "
        f"Original: 0.03, reloaded: {reloaded_line['c1'].edge_entry_angle_fdown}.")


def test_corr_writer_preserves_edge_exit_angle_fdown(tmp_path):
    """
    The edge_exit_angle_fdown of a corrector should be preserved through a
    write and reload cycle.
    """
    original_line = _build_hcorr_line(edge_exit_angle_fdown = 0.02)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].edge_exit_angle_fdown == pytest.approx(0.02), (
        "Writer roundtrip should preserve corrector edge_exit_angle_fdown. "
        f"Original: 0.02, reloaded: {reloaded_line['c1'].edge_exit_angle_fdown}.")


################################################################################
# Horizontal Corrector — Edge Fringe (fint/hgap)
################################################################################
def test_corr_writer_preserves_edge_entry_fint(tmp_path):
    """
    The edge_entry_fint of a corrector (FB1/FB2/FRINGE soft-edge fringe
    import) should be preserved through a write and reload cycle.
    """
    original_line = _build_hcorr_line(edge_entry_fint = 0.06)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].edge_entry_fint == pytest.approx(0.06), (
        "Writer roundtrip should preserve corrector edge_entry_fint. "
        f"Original: 0.06, reloaded: {reloaded_line['c1'].edge_entry_fint}.")


def test_corr_writer_preserves_edge_entry_hgap(tmp_path):
    """
    The edge_entry_hgap of a corrector should be preserved through a write
    and reload cycle.
    """
    original_line = _build_hcorr_line(edge_entry_hgap = 0.06)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].edge_entry_hgap == pytest.approx(0.06), (
        "Writer roundtrip should preserve corrector edge_entry_hgap. "
        f"Original: 0.06, reloaded: {reloaded_line['c1'].edge_entry_hgap}.")


def test_corr_writer_preserves_edge_exit_fint(tmp_path):
    """
    The edge_exit_fint of a corrector should be preserved through a write
    and reload cycle.
    """
    original_line = _build_hcorr_line(edge_exit_fint = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].edge_exit_fint == pytest.approx(0.05), (
        "Writer roundtrip should preserve corrector edge_exit_fint. "
        f"Original: 0.05, reloaded: {reloaded_line['c1'].edge_exit_fint}.")


def test_corr_writer_preserves_edge_exit_hgap(tmp_path):
    """
    The edge_exit_hgap of a corrector should be preserved through a write
    and reload cycle.
    """
    original_line = _build_hcorr_line(edge_exit_hgap = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].edge_exit_hgap == pytest.approx(0.05), (
        "Writer roundtrip should preserve corrector edge_exit_hgap. "
        f"Original: 0.05, reloaded: {reloaded_line['c1'].edge_exit_hgap}.")


def test_corr_writer_treats_fringed_corrector_as_non_simple(tmp_path):
    """
    A corrector whose ONLY non-default attribute is edge fint/hgap must
    still route through the writer's full serialisation form, not the
    compact one-liner -- the compact form omits every extra attribute,
    including fint/hgap.
    """
    original_line = _build_hcorr_line(edge_entry_fint = 0.06, edge_entry_hgap = 0.06)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].edge_entry_fint == pytest.approx(0.06), (
        "A corrector with only fint/hgap set (otherwise default) should not "
        "be misclassified as 'simple' by the writer -- got edge_entry_fint="
        f"{reloaded_line['c1'].edge_entry_fint} after roundtrip, expected 0.06.")


################################################################################
# Horizontal Corrector — Offsets (Literal Strings)
################################################################################
def test_corr_writer_preserves_positive_shift_x(tmp_path):
    """
    A positive horizontal offset shift_x of a corrector should be preserved
    through a write and reload cycle. shift_x is written as a literal Python
    string expression, identical to the bend writer convention.
    """
    original_line = _build_hcorr_line(shift_x = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve positive corrector shift_x. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['c1'].shift_x}.")


def test_corr_writer_preserves_negative_shift_y(tmp_path):
    """
    A negative vertical offset shift_y of a corrector should be preserved
    through a write and reload cycle.
    """
    original_line = _build_hcorr_line(shift_y = -2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve negative corrector shift_y. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['c1'].shift_y}.")


################################################################################
# Horizontal Corrector — All Fields Simultaneously (Complex Path)
################################################################################
def test_corr_writer_preserves_all_fields_simultaneously(tmp_path):
    """
    A corrector with k0, edge angles, and offsets all non-zero should preserve
    all fields through a write and reload cycle. This exercises the complex
    (multi-field) output path rather than the compact single-line form.
    """
    original_line = _build_hcorr_line(
        k0                      = 1.5E-4,
        length                  = 0.45,
        edge_entry_angle        = 0.05,
        edge_exit_angle         = 0.04,
        edge_entry_angle_fdown  = 0.03,
        edge_exit_angle_fdown   = 0.02,
        shift_x                 = 1.0E-3,
        shift_y                 = -2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].k0                    == pytest.approx(1.5E-4),  (
        f"Should preserve k0. Reloaded: {reloaded_line['c1'].k0}.")
    assert reloaded_line["c1"].length                == pytest.approx(0.45),    (
        f"Should preserve length. Reloaded: {reloaded_line['c1'].length}.")
    assert reloaded_line["c1"].edge_entry_angle      == pytest.approx(0.05),    (
        f"Should preserve edge_entry_angle. Reloaded: {reloaded_line['c1'].edge_entry_angle}.")
    assert reloaded_line["c1"].edge_exit_angle       == pytest.approx(0.04),    (
        f"Should preserve edge_exit_angle. Reloaded: {reloaded_line['c1'].edge_exit_angle}.")
    assert reloaded_line["c1"].edge_entry_angle_fdown == pytest.approx(0.03),   (
        f"Should preserve edge_entry_angle_fdown. Reloaded: {reloaded_line['c1'].edge_entry_angle_fdown}.")
    assert reloaded_line["c1"].edge_exit_angle_fdown  == pytest.approx(0.02),   (
        f"Should preserve edge_exit_angle_fdown. Reloaded: {reloaded_line['c1'].edge_exit_angle_fdown}.")
    assert reloaded_line["c1"].shift_x               == pytest.approx(1.0E-3),  (
        f"Should preserve shift_x. Reloaded: {reloaded_line['c1'].shift_x}.")
    assert reloaded_line["c1"].shift_y               == pytest.approx(-2.0E-3), (
        f"Should preserve shift_y. Reloaded: {reloaded_line['c1'].shift_y}.")


################################################################################
# Vertical Corrector
################################################################################
def test_corr_writer_vertical_corr_reloads_as_xsuite_bend(tmp_path):
    """
    A vertical corrector (rot_s_rad = π/2) should reload as an xt.Bend. The
    writer places the rotation on the shared base element ('vcorr...') rather
    than the clone.
    """
    original_line = _build_vcorr_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["vc1"], xt.Bend), (
        "Written vertical corrector 'vc1' should reload as xt.Bend. "
        f"Got: {type(reloaded_line['vc1']).__name__}.")


def test_corr_writer_vertical_corr_preserves_k0(tmp_path):
    """
    The dipole field strength k0 of a vertical corrector should be preserved
    through a write and reload cycle.
    """
    original_line = _build_vcorr_line(k0 = 1.5E-4)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["vc1"].k0 == pytest.approx(1.5E-4), (
        "Writer roundtrip should preserve vertical corrector k0. "
        f"Original: 1.5E-4, reloaded: {reloaded_line['vc1'].k0}.")


def test_corr_writer_vertical_corr_preserves_rotation(tmp_path):
    """
    The rot_s_rad = π/2 of a vertical corrector should be preserved through a
    write and reload cycle. It is encoded on the shared base element and
    inherited by the clone.
    """
    original_line = _build_vcorr_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["vc1"].rot_s_rad == pytest.approx(np.pi / 2), (
        "Writer roundtrip should preserve vertical corrector rot_s_rad = π/2. "
        f"Reloaded: {reloaded_line['vc1'].rot_s_rad}.")


################################################################################
# Skew Corrector
################################################################################
def test_corr_writer_skew_corr_reloads_as_xsuite_bend(tmp_path):
    """
    A skew corrector (rot_s_rad not in {0, +π/2}) should reload as an xt.Bend.
    The writer places the rotation on the clone as a literal string expression.
    """
    original_line = _build_scorr_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["sc1"], xt.Bend), (
        "Written skew corrector 'sc1' should reload as xt.Bend. "
        f"Got: {type(reloaded_line['sc1']).__name__}.")


def test_corr_writer_skew_corr_preserves_k0(tmp_path):
    """
    The dipole field strength k0 of a skew corrector should be preserved
    through a write and reload cycle. This exercises the scorr code path, where
    the clone carries both the k0 optics expression and the rot_s_rad literal
    string.
    """
    original_line = _build_scorr_line(k0 = 1.5E-4)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sc1"].k0 == pytest.approx(1.5E-4), (
        "Writer roundtrip should preserve skew corrector k0. "
        f"Original: 1.5E-4, reloaded: {reloaded_line['sc1'].k0}.")


def test_corr_writer_skew_corr_preserves_rotation(tmp_path):
    """
    The arbitrary rot_s_rad of a skew corrector should be preserved through a
    write and reload cycle.
    """
    rot = np.pi / 4
    original_line = _build_scorr_line(rot_s_rad = rot)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sc1"].rot_s_rad == pytest.approx(rot), (
        "Writer roundtrip should preserve skew corrector rot_s_rad. "
        f"Original: {rot}, reloaded: {reloaded_line['sc1'].rot_s_rad}.")


@pytest.mark.parametrize("rot_s_rad", [np.pi, -np.pi / 2])
def test_corr_writer_preserves_explicit_special_rotations(tmp_path, rot_s_rad):
    """
    External Xsuite correctors with pi or -pi/2 rotations should be written as
    that representation, not rewritten into SAD2XS conversion canonical form.
    """
    original_line = _build_scorr_line(
        k0        = 1.5E-4,
        length    = 0.3,
        rot_s_rad = rot_s_rad)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sc1"].k0 == pytest.approx(1.5E-4), (
        "Writer roundtrip should preserve explicit-rotation corrector k0. "
        f"Original: 1.5E-4, reloaded: {reloaded_line['sc1'].k0}.")
    assert reloaded_line["sc1"].rot_s_rad == pytest.approx(rot_s_rad), (
        "Writer roundtrip should preserve explicit corrector rot_s_rad. "
        f"Original: {rot_s_rad}, reloaded: {reloaded_line['sc1'].rot_s_rad}.")


################################################################################
# Multiple Correctors
################################################################################
def test_corr_writer_preserves_multiple_corrs_independently(tmp_path):
    """
    Multiple corrector elements with different k0 values and lengths should each
    preserve their individual values through a single write and reload cycle.
    Each gets its own k0 optics variable (k0_ca, k0_cb).
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Bend(k0 = 1.5E-4, length = 0.3),
            xt.Bend(k0 = 2.0E-4, length = 0.4),
            xt.Marker(),
        ],
        element_names = ["start", "ca", "cb", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    assert reloaded_line["ca"].k0     == pytest.approx(1.5E-4), (
        "Writer roundtrip should preserve k0 for 'ca'. "
        f"Original: 1.5E-4, reloaded: {reloaded_line['ca'].k0}.")
    assert reloaded_line["ca"].length == pytest.approx(0.3),    (
        "Writer roundtrip should preserve length for 'ca'. "
        f"Original: 0.3, reloaded: {reloaded_line['ca'].length}.")
    assert reloaded_line["cb"].k0     == pytest.approx(2.0E-4), (
        "Writer roundtrip should preserve k0 for 'cb'. "
        f"Original: 2.0E-4, reloaded: {reloaded_line['cb'].k0}.")
    assert reloaded_line["cb"].length == pytest.approx(0.4),    (
        "Writer roundtrip should preserve length for 'cb'. "
        f"Original: 0.4, reloaded: {reloaded_line['cb'].length}.")


def test_corr_writer_corrs_with_same_length_share_base_element(tmp_path):
    """
    Two corrector elements with the same length should share a single base
    element in the output lattice file and each have their own k0 optics
    variable. Both k0 values should be independently preserved.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Bend(k0 = 1.5E-4, length = 0.3),
            xt.Bend(k0 = 2.0E-4, length = 0.3),
            xt.Marker(),
        ],
        element_names = ["start", "ca", "cb", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    assert reloaded_line["ca"].k0 == pytest.approx(1.5E-4), (
        "Correctors sharing a base element: k0 for 'ca' should be preserved. "
        f"Original: 1.5E-4, reloaded: {reloaded_line['ca'].k0}.")
    assert reloaded_line["cb"].k0 == pytest.approx(2.0E-4), (
        "Correctors sharing a base element: k0 for 'cb' should be preserved. "
        f"Original: 2.0E-4, reloaded: {reloaded_line['cb'].k0}.")
    assert env["k0_ca"] == pytest.approx(1.5E-4), (
        f"'k0_ca' should equal the original k0. Got: {env['k0_ca']}.")
    assert env["k0_cb"] == pytest.approx(2.0E-4), (
        f"'k0_cb' should equal the original k0. Got: {env['k0_cb']}.")


################################################################################
# Precision
################################################################################
def test_corr_writer_preserves_k0_at_full_double_precision(tmp_path):
    """
    The corrector k0 should survive the write and reload cycle at full IEEE 754
    double precision. The optics file writes k0 at 24 decimal places. An
    irrational value exercises the precision path beyond what a simple round
    decimal would expose.
    """
    k0 = np.pi * 1.0E-4
    original_line = _build_hcorr_line(k0 = k0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].k0 == pytest.approx(k0, rel = 1E-12), (
        "Writer roundtrip should preserve corrector k0 to full double precision. "
        f"Original: {k0}, reloaded: {reloaded_line['c1'].k0}, "
        f"diff: {abs(reloaded_line['c1'].k0 - k0)}.")


################################################################################
# Combined Multipole Components
################################################################################
########################################
# Higher-Order knl Components
########################################
def test_corr_writer_preserves_knl_combined_multipole_component(tmp_path):
    """
    A corrector with a combined sextupole component (knl[2] != 0) should
    preserve that component through a write and reload cycle.
    """
    original_line = _build_hcorr_line(k0 = 1.0E-4, knl = [0.0, 0.0, 5.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_knl = np.asarray(original_line["c1"].knl)
    reloaded_knl = np.asarray(reloaded_line["c1"].knl)

    assert reloaded_knl.tolist() == pytest.approx(original_knl.tolist()), (
        "Writer roundtrip should preserve corrector knl combined multipole components. "
        f"Original knl: {original_knl.tolist()}, "
        f"reloaded knl: {reloaded_knl.tolist()}.")


########################################
# Higher-Order ksl Components
########################################
def test_corr_writer_preserves_ksl_combined_multipole_component(tmp_path):
    """
    A corrector with a combined skew sextupole component (ksl[2] != 0) should
    preserve that component through a write and reload cycle.
    """
    original_line = _build_hcorr_line(k0 = 1.0E-4, ksl = [0.0, 0.0, -3.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_ksl = np.asarray(original_line["c1"].ksl)
    reloaded_ksl = np.asarray(reloaded_line["c1"].ksl)

    assert reloaded_ksl.tolist() == pytest.approx(original_ksl.tolist()), (
        "Writer roundtrip should preserve corrector ksl combined multipole components. "
        f"Original ksl: {original_ksl.tolist()}, "
        f"reloaded ksl: {reloaded_ksl.tolist()}.")


def test_corr_writer_preserves_knl_and_ksl_components_simultaneously(tmp_path):
    """
    A corrector carrying both knl and ksl combined multipole components should
    preserve both through a write and reload cycle.
    """
    original_line = _build_hcorr_line(
        k0      = 1.0E-4,
        knl     = [0.0, 0.0, 5.0E-4],
        ksl     = [0.0, 0.0, -3.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_knl = np.asarray(original_line["c1"].knl)
    reloaded_knl = np.asarray(reloaded_line["c1"].knl)
    original_ksl = np.asarray(original_line["c1"].ksl)
    reloaded_ksl = np.asarray(reloaded_line["c1"].ksl)

    assert reloaded_knl.tolist() == pytest.approx(original_knl.tolist()), (
        "Writer roundtrip should preserve corrector knl. "
        f"Original: {original_knl.tolist()}, reloaded: {reloaded_knl.tolist()}.")
    assert reloaded_ksl.tolist() == pytest.approx(original_ksl.tolist()), (
        "Writer roundtrip should preserve corrector ksl. "
        f"Original: {original_ksl.tolist()}, reloaded: {reloaded_ksl.tolist()}.")
