"""
================================================================================
Tests for quadrupole element writer serialisation
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
import numpy as np
import pytest
import xtrack as xt

import sad2xs as s2x
from sad2xs.config import Config

################################################################################
# Helpers
################################################################################
def _write_and_load(line, tmp_path):
    """
    Write a line using the public SAD2XS writer entry points, reload it in a
    clean Xsuite environment, and return the environment and reloaded line.

    Returning the environment allows tests to inspect and modify optics
    variables, which verifies that k1 / k1s are written as live deferred
    expressions rather than baked-in constants.
    """
    output_dir = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = "Quadrupole writer test",
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = "test_lattice_import_optics",
        output_directory  = str(output_dir),
        output_header     = "Quadrupole writer test",
        config            = Config(_verbose = False))

    env = xt.Environment()
    env.call(str(output_dir / "test_lattice.py"))
    env.call(str(output_dir / "test_lattice_import_optics.py"))

    return env, env.lines["line"]


def _writer_roundtrip(line, tmp_path):
    """
    Write and reload a line. Returns the reloaded line only.
    """
    _, reloaded_line = _write_and_load(line, tmp_path)
    return reloaded_line


def _build_quad_line(
        length    = 0.5,
        k1        = 0.0,
        k1s       = 0.0,
        shift_x   = 0.0,
        shift_y   = 0.0,
        rot_s_rad = 0.0,
        knl       = None,
        ksl       = None):
    """
    Build a minimal single-quadrupole Xsuite line with a reference particle.
    Keyword arguments map directly to xt.Quadrupole fields.
    """
    quad_kwargs = dict(
        length    = length,
        k1        = k1,
        k1s       = k1s,
        shift_x   = shift_x,
        shift_y   = shift_y,
        rot_s_rad = rot_s_rad)

    if knl is not None:
        quad_kwargs["knl"] = knl
    if ksl is not None:
        quad_kwargs["ksl"] = ksl

    line = xt.Line(
        elements      = [xt.Marker(), xt.Quadrupole(**quad_kwargs), xt.Marker()],
        element_names = ["start", "q1", "end"])

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
def test_quad_writer_reloads_as_xsuite_quadrupole(tmp_path):
    """
    A written quadrupole element should reload as an xt.Quadrupole in a clean
    Xsuite environment.
    """
    original_line = _build_quad_line(k1 = 0.2)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["q1"], xt.Quadrupole), (
        "Written quadrupole element 'q1' should reload as xt.Quadrupole. "
        f"Got: {type(reloaded_line['q1']).__name__}.")


def test_quad_writer_preserves_element_name(tmp_path):
    """
    A written quadrupole element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_quad_line(k1 = 0.2)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "q1" in list(reloaded_line.element_names), (
        "Reloaded line should contain quadrupole element 'q1'. "
        f"Got: {list(reloaded_line.element_names)}.")


########################################
# Element Order
########################################
def test_quad_writer_preserves_element_order(tmp_path):
    """
    Multiple quadrupole and marker elements should appear in the same order
    after a write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Quadrupole(length = 0.5, k1 = 0.2),
            xt.Marker(),
            xt.Quadrupole(length = 0.5, k1 = -0.2),
            xt.Marker(),
        ],
        element_names = ["start", "qf", "mid", "qd", "end"])

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
def test_quad_writer_preserves_length(tmp_path):
    """
    A quadrupole element's length should be preserved through a write and
    reload cycle.
    """
    original_line = _build_quad_line(length = 0.75, k1 = 0.2)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].length == pytest.approx(0.75), (
        "Writer roundtrip should preserve quadrupole length. "
        f"Original: 0.75, reloaded: {reloaded_line['q1'].length}.")


########################################
# Normal Quadrupole Strength via Optics Expression
########################################
def test_quad_writer_preserves_positive_k1(tmp_path):
    """
    A focusing quadrupole's k1 should be preserved through a write and reload
    cycle. k1 is written to the optics file as a named variable k1_q1 and
    referenced from the lattice file as a deferred expression.
    """
    original_line = _build_quad_line(k1 = 0.2)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].k1 == pytest.approx(0.2), (
        "Writer roundtrip should preserve positive quadrupole k1. "
        f"Original: 0.2, reloaded: {reloaded_line['q1'].k1}.")


def test_quad_writer_preserves_negative_k1(tmp_path):
    """
    A defocusing quadrupole's k1 should be preserved through a write and
    reload cycle.
    """
    original_line = _build_quad_line(k1 = -0.2)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].k1 == pytest.approx(-0.2), (
        "Writer roundtrip should preserve negative quadrupole k1. "
        f"Original: -0.2, reloaded: {reloaded_line['q1'].k1}.")


def test_quad_writer_preserves_zero_k1(tmp_path):
    """
    A zero-strength quadrupole should survive a write and reload cycle with
    k1 remaining zero. Zero-strength quadrupoles appear as lattice placeholders.
    """
    original_line = _build_quad_line(k1 = 0.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].k1 == pytest.approx(0.0), (
        "Writer roundtrip should preserve zero quadrupole k1. "
        f"Reloaded: {reloaded_line['q1'].k1}.")


def test_quad_writer_k1_preserves_full_double_precision(tmp_path):
    """
    A quadrupole k1 with many significant digits should survive a write and
    reload cycle at full double precision. The optics file writes k1_q1 to
    24 decimal places, which exceeds the ~17 significant digits of IEEE 754
    double precision.
    """
    k1_precise = 0.12345678901234567
    original_line = _build_quad_line(k1 = k1_precise)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].k1 == pytest.approx(k1_precise, rel = 1E-15), (
        "Writer roundtrip should preserve quadrupole k1 at full double "
        f"precision. Original: {k1_precise!r}, reloaded: {reloaded_line['q1'].k1!r}.")


########################################
# k1 Written as Tunable Optics Expression
########################################
def test_quad_writer_k1_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the quadrupole's k1 should be accessible as
    a named optics variable k1_q1 in the Xsuite environment. This confirms
    that k1 is written as a deferred expression reference rather than a
    baked-in constant. The variable name is derived from the element name.
    """
    original_line = _build_quad_line(k1 = 0.2)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["k1_q1"] == pytest.approx(0.2), (
        "Optics variable 'k1_q1' should exist in the environment after reload "
        "and equal the original k1 value. "
        f"Got: {env['k1_q1']}.")


def test_quad_writer_k1_optics_variable_is_tunable(tmp_path):
    """
    The k1_q1 optics variable written to the optics file should remain live:
    modifying it in the reloaded environment should immediately update the
    quadrupole's k1 in the line. This is the core contract of the expression-
    based optics variable mechanism.
    """
    original_line = _build_quad_line(k1 = 0.2)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["k1_q1"] = 0.4

    assert reloaded_line["q1"].k1 == pytest.approx(0.4), (
        "Modifying optics variable 'k1_q1' should update the quadrupole's k1 "
        "in the reloaded line. The k1 should be a live deferred expression, "
        f"not a constant. Got: {reloaded_line['q1'].k1}.")


########################################
# Skew Quadrupole Strength via Optics Expression
########################################
def test_quad_writer_preserves_positive_k1s(tmp_path):
    """
    A positive skew quadrupole's k1s should be preserved through a write and
    reload cycle. This exercises the simple skew path in the writer where only
    k1s is non-zero.
    """
    original_line = _build_quad_line(k1s = 0.15)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].k1s == pytest.approx(0.15), (
        "Writer roundtrip should preserve positive skew quadrupole k1s. "
        f"Original: 0.15, reloaded: {reloaded_line['q1'].k1s}.")
    assert reloaded_line["q1"].k1 == pytest.approx(0.0), (
        "Pure skew quadrupole should have zero k1 after roundtrip. "
        f"Reloaded k1: {reloaded_line['q1'].k1}.")


def test_quad_writer_preserves_negative_k1s(tmp_path):
    """
    A negative skew quadrupole's k1s should be preserved through a write and
    reload cycle.
    """
    original_line = _build_quad_line(k1s = -0.15)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].k1s == pytest.approx(-0.15), (
        "Writer roundtrip should preserve negative skew quadrupole k1s. "
        f"Original: -0.15, reloaded: {reloaded_line['q1'].k1s}.")


def test_quad_writer_k1s_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, a skew quadrupole's k1s should be accessible
    as optics variable k1s_q1 in the Xsuite environment. This confirms the
    skew strength is written as a deferred expression, not a hardcoded constant.
    """
    original_line = _build_quad_line(k1s = 0.15)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["k1s_q1"] == pytest.approx(0.15), (
        "Optics variable 'k1s_q1' should exist in the environment after reload "
        "and equal the original k1s value. "
        f"Got: {env['k1s_q1']}.")


def test_quad_writer_k1s_optics_variable_is_tunable(tmp_path):
    """
    The k1s_q1 optics variable should remain live after reload: modifying it
    should immediately update the skew quadrupole's k1s in the line.
    """
    original_line = _build_quad_line(k1s = 0.15)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["k1s_q1"] = 0.3

    assert reloaded_line["q1"].k1s == pytest.approx(0.3), (
        "Modifying optics variable 'k1s_q1' should update the quadrupole's "
        "k1s in the reloaded line. "
        f"Got: {reloaded_line['q1'].k1s}.")


########################################
# Normal and Skew Strengths Combined
########################################
def test_quad_writer_preserves_k1_and_k1s_simultaneously(tmp_path):
    """
    A quadrupole with both k1 and k1s non-zero should preserve both through a
    write and reload cycle. Both strengths non-zero triggers the writer's
    complex path. Both values should be written to the optics file and both
    should be accessible as live optics variables.
    """
    original_line = _build_quad_line(k1 = 0.2, k1s = 0.05)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].k1 == pytest.approx(0.2), (
        "Writer roundtrip should preserve k1 when both k1 and k1s are set. "
        f"Original: 0.2, reloaded: {reloaded_line['q1'].k1}.")
    assert reloaded_line["q1"].k1s == pytest.approx(0.05), (
        "Writer roundtrip should preserve k1s when both k1 and k1s are set. "
        f"Original: 0.05, reloaded: {reloaded_line['q1'].k1s}.")
    assert env["k1_q1"] == pytest.approx(0.2), (
        "Optics variable 'k1_q1' should be written and accessible when both "
        "k1 and k1s are non-zero.")
    assert env["k1s_q1"] == pytest.approx(0.05), (
        "Optics variable 'k1s_q1' should be written and accessible when both "
        "k1 and k1s are non-zero.")


################################################################################
# Misalignments via Hardcoded Values
################################################################################
# shift_x, shift_y, and rot_s_rad are NOT written as optics variables.
# They are written as literal numeric strings in the lattice file, e.g.:
#   env.new(name = 'q1', prototype = 'quad_0.5', shift_x = '0.001')
# The string is evaluated by Xsuite's expression engine when the file is
# loaded. The tests below verify that positive, negative, and scientific-
# notation values all survive this literal-string encoding correctly.
########################################
# Horizontal Offset
########################################
def test_quad_writer_preserves_positive_shift_x(tmp_path):
    """
    A positive horizontal offset shift_x should be preserved through a write
    and reload cycle. Non-zero shift_x triggers the writer's complex path.
    """
    original_line = _build_quad_line(k1 = 0.2, shift_x = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve positive quadrupole shift_x. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['q1'].shift_x}.")


def test_quad_writer_preserves_negative_shift_x(tmp_path):
    """
    A negative horizontal offset shift_x should be preserved through a write
    and reload cycle. The literal string encoding must correctly handle the
    unary minus in the evaluated expression.
    """
    original_line = _build_quad_line(k1 = 0.2, shift_x = -1.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].shift_x == pytest.approx(-1.5E-3), (
        "Writer roundtrip should preserve negative quadrupole shift_x. "
        f"Original: -1.5E-3, reloaded: {reloaded_line['q1'].shift_x}.")


def test_quad_writer_preserves_shift_x_in_scientific_notation(tmp_path):
    """
    A very small shift_x value that Python formats in scientific notation
    should survive a write and reload cycle. The literal string encoding must
    correctly evaluate scientific notation such as '1.23456789e-06'.
    """
    original_line = _build_quad_line(k1 = 0.2, shift_x = 1.23456789E-6)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].shift_x == pytest.approx(1.23456789E-6), (
        "Writer roundtrip should preserve a shift_x value written in scientific "
        f"notation. Original: 1.23456789E-6, reloaded: {reloaded_line['q1'].shift_x}.")


########################################
# Vertical Offset
########################################
def test_quad_writer_preserves_positive_shift_y(tmp_path):
    """
    A positive vertical offset shift_y should be preserved through a write and
    reload cycle. Non-zero shift_y triggers the writer's complex path.
    """
    original_line = _build_quad_line(k1 = 0.2, shift_y = 2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].shift_y == pytest.approx(2.0E-3), (
        "Writer roundtrip should preserve positive quadrupole shift_y. "
        f"Original: 2.0E-3, reloaded: {reloaded_line['q1'].shift_y}.")


def test_quad_writer_preserves_negative_shift_y(tmp_path):
    """
    A negative vertical offset shift_y should be preserved through a write and
    reload cycle, including correct handling of the unary minus.
    """
    original_line = _build_quad_line(k1 = 0.2, shift_y = -2.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].shift_y == pytest.approx(-2.5E-3), (
        "Writer roundtrip should preserve negative quadrupole shift_y. "
        f"Original: -2.5E-3, reloaded: {reloaded_line['q1'].shift_y}.")


def test_quad_writer_preserves_shift_y_in_scientific_notation(tmp_path):
    """
    A very small shift_y value requiring scientific notation should survive a
    write and reload cycle.
    """
    original_line = _build_quad_line(k1 = 0.2, shift_y = -9.87654321E-7)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].shift_y == pytest.approx(-9.87654321E-7), (
        "Writer roundtrip should preserve a shift_y value written in scientific "
        f"notation. Original: -9.87654321E-7, reloaded: {reloaded_line['q1'].shift_y}.")


########################################
# In-Plane Rotation
########################################
def test_quad_writer_preserves_positive_rot_s_rad(tmp_path):
    """
    A positive in-plane rotation rot_s_rad should be preserved through a write
    and reload cycle. The value 0.05 rad avoids the ±pi/4 skew-conversion
    shortcut applied during SAD conversion.
    """
    original_line = _build_quad_line(k1 = 0.2, rot_s_rad = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve positive quadrupole rot_s_rad. "
        f"Original: 0.05, reloaded: {reloaded_line['q1'].rot_s_rad}.")


def test_quad_writer_preserves_negative_rot_s_rad(tmp_path):
    """
    A negative in-plane rotation rot_s_rad should be preserved through a write
    and reload cycle, including correct handling of the unary minus.
    """
    original_line = _build_quad_line(k1 = 0.2, rot_s_rad = -0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].rot_s_rad == pytest.approx(-0.05), (
        "Writer roundtrip should preserve negative quadrupole rot_s_rad. "
        f"Original: -0.05, reloaded: {reloaded_line['q1'].rot_s_rad}.")


########################################
# All Misalignments Simultaneously
########################################
def test_quad_writer_preserves_all_misalignments_simultaneously(tmp_path):
    """
    A quadrupole with shift_x, shift_y, and rot_s_rad all non-zero should
    preserve all three through a write and reload cycle.
    """
    original_line = _build_quad_line(
        shift_x   = 1.0E-3,
        shift_y   = -2.0E-3,
        rot_s_rad = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve shift_x alongside other misalignments. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['q1'].shift_x}.")
    assert reloaded_line["q1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve shift_y alongside other misalignments. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['q1'].shift_y}.")
    assert reloaded_line["q1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve rot_s_rad alongside other misalignments. "
        f"Original: 0.05, reloaded: {reloaded_line['q1'].rot_s_rad}.")


def test_quad_writer_preserves_k1_with_all_misalignments(tmp_path):
    """
    A quadrupole with k1, shift_x, shift_y, and rot_s_rad all non-zero should
    preserve all four through a write and reload cycle. This exercises the full
    complex path in the writer alongside the optics expression for k1.
    """
    original_line = _build_quad_line(
        k1        = 0.2,
        shift_x   = 1.0E-3,
        shift_y   = -2.0E-3,
        rot_s_rad = 0.05)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["q1"].k1 == pytest.approx(0.2), (
        "Writer roundtrip should preserve k1 alongside misalignments. "
        f"Original: 0.2, reloaded: {reloaded_line['q1'].k1}.")
    assert reloaded_line["q1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve shift_x alongside k1. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['q1'].shift_x}.")
    assert reloaded_line["q1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve shift_y alongside k1. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['q1'].shift_y}.")
    assert reloaded_line["q1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve rot_s_rad alongside k1. "
        f"Original: 0.05, reloaded: {reloaded_line['q1'].rot_s_rad}.")

    assert env["k1_q1"] == pytest.approx(0.2), (
        "Optics variable 'k1_q1' should remain accessible alongside hardcoded "
        "misalignment values. "
        f"Got: {env['k1_q1']}.")


################################################################################
# Combined Multipole Components
################################################################################
########################################
# Higher-Order knl Components
########################################
def test_quad_writer_preserves_knl_combined_multipole_component(tmp_path):
    """
    A quadrupole with a combined sextupole component (knl[2] != 0) should
    preserve that component through a write and reload cycle.

    This is a regression test for preserving combined multipole components
    carried by quadrupole elements.
    """
    original_line = _build_quad_line(k1 = 0.2, knl = [0.0, 0.0, 5.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_knl = np.asarray(original_line["q1"].knl)
    reloaded_knl = np.asarray(reloaded_line["q1"].knl)

    assert reloaded_knl.tolist() == pytest.approx(original_knl.tolist()), (
        "Writer roundtrip should preserve quadrupole knl combined multipole "
        "components. The quadrupole writer does not write knl, so this "
        "component is silently lost on reload. "
        f"Original knl: {original_knl.tolist()}, "
        f"reloaded knl: {reloaded_knl.tolist()}.")


########################################
# Higher-Order ksl Components
########################################
def test_quad_writer_preserves_ksl_combined_multipole_component(tmp_path):
    """
    A quadrupole with a combined skew sextupole component (ksl[2] != 0) should
    preserve that component through a write and reload cycle.

    This is the skew-component counterpart to the combined multipole knl
    preservation test.
    """
    original_line = _build_quad_line(k1 = 0.2, ksl = [0.0, 0.0, -3.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_ksl = np.asarray(original_line["q1"].ksl)
    reloaded_ksl = np.asarray(reloaded_line["q1"].ksl)

    assert reloaded_ksl.tolist() == pytest.approx(original_ksl.tolist()), (
        "Writer roundtrip should preserve quadrupole ksl combined multipole "
        "components. The quadrupole writer does not write ksl, so this "
        "component is silently lost on reload. "
        f"Original ksl: {original_ksl.tolist()}, "
        f"reloaded ksl: {reloaded_ksl.tolist()}.")


def test_quad_writer_preserves_knl_and_ksl_components_simultaneously(tmp_path):
    """
    A quadrupole carrying both knl and ksl combined multipole components should
    preserve both through a write and reload cycle.

    knl and ksl components should be preserved independently when both are
    present on the same element.
    """
    original_line = _build_quad_line(
        k1  = 0.2,
        knl = [0.0, 0.0, 5.0E-4],
        ksl = [0.0, 0.0, -3.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_knl = np.asarray(original_line["q1"].knl)
    reloaded_knl = np.asarray(reloaded_line["q1"].knl)
    original_ksl = np.asarray(original_line["q1"].ksl)
    reloaded_ksl = np.asarray(reloaded_line["q1"].ksl)

    assert reloaded_knl.tolist() == pytest.approx(original_knl.tolist()), (
        "Writer roundtrip should preserve quadrupole knl. "
        f"Original: {original_knl.tolist()}, reloaded: {reloaded_knl.tolist()}.")
    assert reloaded_ksl.tolist() == pytest.approx(original_ksl.tolist()), (
        "Writer roundtrip should preserve quadrupole ksl. "
        f"Original: {original_ksl.tolist()}, reloaded: {reloaded_ksl.tolist()}.")


################################################################################
# Multi-Element Behaviour
################################################################################
########################################
# Multiple Quadrupoles
########################################
def test_quad_writer_preserves_multiple_quads_independently(tmp_path):
    """
    Multiple quadrupole elements with different strengths should each preserve
    their individual k1 values independently through a single write and reload
    cycle. Each quad writes its own optics variable (k1_qf, k1_qd, k1_qz).
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Quadrupole(length = 0.5, k1 = +0.2),
            xt.Quadrupole(length = 0.5, k1 = -0.2),
            xt.Quadrupole(length = 0.5, k1 =  0.0),
            xt.Marker(),
        ],
        element_names = ["start", "qf", "qd", "qz", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    expected = {"qf": +0.2, "qd": -0.2, "qz": 0.0}

    for name, expected_k1 in expected.items():
        assert reloaded_line[name].k1 == pytest.approx(expected_k1), (
            f"Writer roundtrip should preserve k1 for quadrupole '{name}'. "
            f"Expected: {expected_k1}, reloaded: {reloaded_line[name].k1}.")

    assert env["k1_qf"] == pytest.approx(0.2), (
        "Optics variable 'k1_qf' should be accessible and correct after reload.")
    assert env["k1_qd"] == pytest.approx(-0.2), (
        "Optics variable 'k1_qd' should be accessible and correct after reload.")


########################################
# Mixed Normal and Skew Quadrupoles
########################################
def test_quad_writer_preserves_mixed_normal_and_skew_quads(tmp_path):
    """
    A line containing normal, skew, and combined-strength quadrupoles should
    preserve all strengths independently through a single write and reload
    cycle. Each quad should have its own correctly named optics variables.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Quadrupole(length = 0.5, k1  = +0.2),
            xt.Quadrupole(length = 0.5, k1s = +0.15),
            xt.Quadrupole(length = 0.5, k1  = -0.1, k1s = 0.05),
            xt.Marker(),
        ],
        element_names = ["start", "qnorm", "qskew", "qcombined", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    assert reloaded_line["qnorm"].k1 == pytest.approx(0.2), (
        "Writer roundtrip should preserve normal quadrupole k1. "
        f"Original: 0.2, reloaded: {reloaded_line['qnorm'].k1}.")
    assert reloaded_line["qnorm"].k1s == pytest.approx(0.0), (
        "Normal quadrupole should have zero k1s after roundtrip. "
        f"Reloaded k1s: {reloaded_line['qnorm'].k1s}.")

    assert reloaded_line["qskew"].k1s == pytest.approx(0.15), (
        "Writer roundtrip should preserve skew quadrupole k1s. "
        f"Original: 0.15, reloaded: {reloaded_line['qskew'].k1s}.")
    assert reloaded_line["qskew"].k1 == pytest.approx(0.0), (
        "Pure skew quadrupole should have zero k1 after roundtrip. "
        f"Reloaded k1: {reloaded_line['qskew'].k1}.")

    assert reloaded_line["qcombined"].k1 == pytest.approx(-0.1), (
        "Writer roundtrip should preserve k1 for a combined-strength quad. "
        f"Original: -0.1, reloaded: {reloaded_line['qcombined'].k1}.")
    assert reloaded_line["qcombined"].k1s == pytest.approx(0.05), (
        "Writer roundtrip should preserve k1s for a combined-strength quad. "
        f"Original: 0.05, reloaded: {reloaded_line['qcombined'].k1s}.")

    assert env["k1_qnorm"] == pytest.approx(0.2), (
        "Optics variable 'k1_qnorm' should be accessible and correct.")
    assert env["k1s_qskew"] == pytest.approx(0.15), (
        "Optics variable 'k1s_qskew' should be accessible and correct.")
