"""
================================================================================
Tests for octupole element writer serialisation
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

    Returning the environment allows tests to inspect and modify optics
    variables, which verifies that k3 / k3s are written as live deferred
    expressions rather than baked-in constants.
    """
    return _shared_write_and_load(line, tmp_path, output_header = "Octupole writer test")


def _writer_roundtrip(line, tmp_path):
    """
    Write and reload a line. Returns the reloaded line only.
    """
    _, reloaded_line = _write_and_load(line, tmp_path)
    return reloaded_line


def _build_oct_line(
        length    = 0.2,
        k3        = 0.0,
        k3s       = 0.0,
        shift_x   = 0.0,
        shift_y   = 0.0,
        rot_s_rad = 0.0,
        knl       = None,
        ksl       = None):
    """
    Build a minimal single-octupole Xsuite line with a reference particle.
    Keyword arguments map directly to xt.Octupole fields.
    """
    oct_kwargs = dict(
        length    = length,
        k3        = k3,
        k3s       = k3s,
        shift_x   = shift_x,
        shift_y   = shift_y,
        rot_s_rad = rot_s_rad)

    if knl is not None:
        oct_kwargs["knl"] = knl
    if ksl is not None:
        oct_kwargs["ksl"] = ksl

    line = xt.Line(
        elements      = [xt.Marker(), xt.Octupole(**oct_kwargs), xt.Marker()],
        element_names = ["start", "o1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


################################################################################
# Basic Serialisation
################################################################################
########################################
# Element Type and Name
########################################
def test_oct_writer_reloads_as_xsuite_octupole(tmp_path):
    """
    A written octupole element should reload as an xt.Octupole in a clean
    Xsuite environment.
    """
    original_line = _build_oct_line(k3 = 50.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["o1"], xt.Octupole), (
        "Written octupole element `o1` should reload as xt.Octupole. "
        f"""Got: {type(reloaded_line["o1"]).__name__}.""")


def test_oct_writer_preserves_element_name(tmp_path):
    """
    A written octupole element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_oct_line(k3 = 50.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "o1" in list(reloaded_line.element_names), (
        "Reloaded line should contain octupole element `o1`. "
        f"Got: {list(reloaded_line.element_names)}.")


########################################
# Element Order
########################################
def test_oct_writer_preserves_element_order(tmp_path):
    """
    Multiple octupole and marker elements should appear in the same order after
    a write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Octupole(length = 0.2, k3 = 50.0),
            xt.Marker(),
            xt.Octupole(length = 0.2, k3 = -50.0),
            xt.Marker(),
        ],
        element_names = ["start", "of", "mid", "od", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

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
def test_oct_writer_preserves_length(tmp_path):
    """
    An octupole element's length should be preserved through a write and
    reload cycle.
    """
    original_line = _build_oct_line(length = 0.35, k3 = 50.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].length == pytest.approx(0.35), (
        "Writer roundtrip should preserve octupole length. "
        f"""Original: 0.35, reloaded: {reloaded_line["o1"].length}.""")


########################################
# Normal Octupole Strength via Optics Expression
########################################
def test_oct_writer_preserves_positive_k3(tmp_path):
    """
    A focusing octupole's k3 should be preserved through a write and reload
    cycle. k3 is written to the optics file as a named variable k3_o1 and
    referenced from the lattice file as a deferred expression.
    """
    original_line = _build_oct_line(k3 = 50.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].k3 == pytest.approx(50.0), (
        "Writer roundtrip should preserve positive octupole k3. "
        f"""Original: 50.0, reloaded: {reloaded_line["o1"].k3}.""")


def test_oct_writer_preserves_negative_k3(tmp_path):
    """
    A defocusing octupole's k3 should be preserved through a write and reload
    cycle.
    """
    original_line = _build_oct_line(k3 = -50.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].k3 == pytest.approx(-50.0), (
        "Writer roundtrip should preserve negative octupole k3. "
        f"""Original: -50.0, reloaded: {reloaded_line["o1"].k3}.""")


def test_oct_writer_preserves_zero_k3(tmp_path):
    """
    A zero-strength octupole should survive a write and reload cycle with k3
    remaining zero. Zero-strength octupoles appear as lattice placeholders.
    """
    original_line = _build_oct_line(k3 = 0.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].k3 == pytest.approx(0.0), (
        "Writer roundtrip should preserve zero octupole k3. "
        f"""Reloaded: {reloaded_line["o1"].k3}.""")


def test_oct_writer_k3_preserves_full_double_precision(tmp_path):
    """
    An octupole k3 with many significant digits should survive a write and
    reload cycle at full double precision. The optics file writes k3_o1 to
    24 decimal places, which exceeds the ~17 significant digits of IEEE 754
    double precision.
    """
    k3_precise = 34.567890123456789
    original_line = _build_oct_line(k3 = k3_precise)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].k3 == pytest.approx(k3_precise, rel = 1E-15), (
        "Writer roundtrip should preserve octupole k3 at full double "
        f"""precision. Original: {k3_precise!r}, reloaded: {reloaded_line["o1"].k3!r}.""")


########################################
# k3 Written as Tunable Optics Expression
########################################
def test_oct_writer_k3_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the octupole's k3 should be accessible as a
    named optics variable k3_o1 in the Xsuite environment. This confirms that
    k3 is written as a deferred expression reference rather than a baked-in
    constant.
    """
    original_line = _build_oct_line(k3 = 50.0)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["k3_o1"] == pytest.approx(50.0), (
        "Optics variable `k3_o1` should exist in the environment after reload "
        "and equal the original k3 value. "
        f"""Got: {env["k3_o1"]}.""")


def test_oct_writer_k3_optics_variable_is_tunable(tmp_path):
    """
    The k3_o1 optics variable written to the optics file should remain live:
    modifying it in the reloaded environment should immediately update the
    octupole's k3 in the line. This is the core contract of the expression-
    based optics variable mechanism.
    """
    original_line = _build_oct_line(k3 = 50.0)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["k3_o1"] = 100.0

    assert reloaded_line["o1"].k3 == pytest.approx(100.0), (
        "Modifying optics variable `k3_o1` should update the octupole's k3 "
        "in the reloaded line. The k3 should be a live deferred expression, "
        f"""not a constant. Got: {reloaded_line["o1"].k3}.""")


########################################
# Skew Octupole Strength via Optics Expression
########################################
def test_oct_writer_preserves_positive_k3s(tmp_path):
    """
    A positive skew octupole's k3s should be preserved through a write and
    reload cycle. This exercises the simple skew path in the writer where only
    k3s is non-zero.
    """
    original_line = _build_oct_line(k3s = 15.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].k3s == pytest.approx(15.0), (
        "Writer roundtrip should preserve positive skew octupole k3s. "
        f"""Original: 15.0, reloaded: {reloaded_line["o1"].k3s}.""")
    assert reloaded_line["o1"].k3 == pytest.approx(0.0), (
        "Pure skew octupole should have zero k3 after roundtrip. "
        f"""Reloaded k3: {reloaded_line["o1"].k3}.""")


def test_oct_writer_preserves_negative_k3s(tmp_path):
    """
    A negative skew octupole's k3s should be preserved through a write and
    reload cycle.
    """
    original_line = _build_oct_line(k3s = -15.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].k3s == pytest.approx(-15.0), (
        "Writer roundtrip should preserve negative skew octupole k3s. "
        f"""Original: -15.0, reloaded: {reloaded_line["o1"].k3s}.""")


def test_oct_writer_k3s_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, a skew octupole's k3s should be accessible
    as optics variable k3s_o1 in the Xsuite environment. This confirms the
    skew strength is written as a deferred expression, not a hardcoded constant.
    """
    original_line = _build_oct_line(k3s = 15.0)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["k3s_o1"] == pytest.approx(15.0), (
        "Optics variable `k3s_o1` should exist in the environment after reload "
        "and equal the original k3s value. "
        f"""Got: {env["k3s_o1"]}.""")


def test_oct_writer_k3s_optics_variable_is_tunable(tmp_path):
    """
    The k3s_o1 optics variable should remain live after reload: modifying it
    should immediately update the skew octupole's k3s in the line.
    """
    original_line = _build_oct_line(k3s = 15.0)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["k3s_o1"] = 30.0

    assert reloaded_line["o1"].k3s == pytest.approx(30.0), (
        "Modifying optics variable `k3s_o1` should update the octupole's "
        "k3s in the reloaded line. "
        f"""Got: {reloaded_line["o1"].k3s}.""")


########################################
# Normal and Skew Strengths Combined
########################################
def test_oct_writer_preserves_k3_and_k3s_simultaneously(tmp_path):
    """
    An octupole with both k3 and k3s non-zero should preserve both through a
    write and reload cycle. Both strengths non-zero triggers the writer's
    complex path. Both values should be written to the optics file and both
    should be accessible as live optics variables.
    """
    original_line = _build_oct_line(k3 = 50.0, k3s = 5.0)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].k3 == pytest.approx(50.0), (
        "Writer roundtrip should preserve k3 when both k3 and k3s are set. "
        f"""Original: 50.0, reloaded: {reloaded_line["o1"].k3}.""")
    assert reloaded_line["o1"].k3s == pytest.approx(5.0), (
        "Writer roundtrip should preserve k3s when both k3 and k3s are set. "
        f"""Original: 5.0, reloaded: {reloaded_line["o1"].k3s}.""")
    assert env["k3_o1"] == pytest.approx(50.0), (
        "Optics variable `k3_o1` should be written and accessible when both "
        "k3 and k3s are non-zero.")
    assert env["k3s_o1"] == pytest.approx(5.0), (
        "Optics variable `k3s_o1` should be written and accessible when both "
        "k3 and k3s are non-zero.")


################################################################################
# Misalignments via Hardcoded Values
################################################################################
# shift_x, shift_y, and rot_s_rad are NOT written as optics variables.
# They are written as literal numeric strings in the lattice file, e.g.:
#   env.new(name = "o1", prototype = "oct_0.2", shift_x = "0.001")
# The string is evaluated by Xsuite's expression engine when the file is
# loaded. The tests below verify that positive, negative, and scientific-
# notation values all survive this literal-string encoding correctly.
########################################
# Horizontal Offset
########################################
def test_oct_writer_preserves_positive_shift_x(tmp_path):
    """
    A positive horizontal offset shift_x should be preserved through a write
    and reload cycle. Non-zero shift_x triggers the writer's complex path.
    """
    original_line = _build_oct_line(k3 = 50.0, shift_x = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve positive octupole shift_x. "
        f"""Original: 1.0E-3, reloaded: {reloaded_line["o1"].shift_x}.""")


def test_oct_writer_preserves_negative_shift_x(tmp_path):
    """
    A negative horizontal offset shift_x should be preserved through a write
    and reload cycle. The literal string encoding must correctly handle the
    unary minus in the evaluated expression.
    """
    original_line = _build_oct_line(k3 = 50.0, shift_x = -1.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].shift_x == pytest.approx(-1.5E-3), (
        "Writer roundtrip should preserve negative octupole shift_x. "
        f"""Original: -1.5E-3, reloaded: {reloaded_line["o1"].shift_x}.""")


def test_oct_writer_preserves_shift_x_in_scientific_notation(tmp_path):
    """
    A very small shift_x value that Python formats in scientific notation
    should survive a write and reload cycle.
    """
    original_line = _build_oct_line(k3 = 50.0, shift_x = 3.45678912E-6)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].shift_x == pytest.approx(3.45678912E-6), (
        "Writer roundtrip should preserve a shift_x value written in scientific "
        f"""notation. Original: 3.45678912E-6, reloaded: {reloaded_line["o1"].shift_x}.""")


########################################
# Vertical Offset
########################################
def test_oct_writer_preserves_positive_shift_y(tmp_path):
    """
    A positive vertical offset shift_y should be preserved through a write and
    reload cycle. Non-zero shift_y triggers the writer's complex path.
    """
    original_line = _build_oct_line(k3 = 50.0, shift_y = 2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].shift_y == pytest.approx(2.0E-3), (
        "Writer roundtrip should preserve positive octupole shift_y. "
        f"""Original: 2.0E-3, reloaded: {reloaded_line["o1"].shift_y}.""")


def test_oct_writer_preserves_negative_shift_y(tmp_path):
    """
    A negative vertical offset shift_y should be preserved through a write and
    reload cycle, including correct handling of the unary minus.
    """
    original_line = _build_oct_line(k3 = 50.0, shift_y = -2.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].shift_y == pytest.approx(-2.5E-3), (
        "Writer roundtrip should preserve negative octupole shift_y. "
        f"""Original: -2.5E-3, reloaded: {reloaded_line["o1"].shift_y}.""")


def test_oct_writer_preserves_shift_y_in_scientific_notation(tmp_path):
    """
    A very small shift_y value requiring scientific notation should survive a
    write and reload cycle.
    """
    original_line = _build_oct_line(k3 = 50.0, shift_y = -8.76543219E-7)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].shift_y == pytest.approx(-8.76543219E-7), (
        "Writer roundtrip should preserve a shift_y value written in scientific "
        f"""notation. Original: -8.76543219E-7, reloaded: {reloaded_line["o1"].shift_y}.""")


########################################
# In-Plane Rotation
########################################
def test_oct_writer_preserves_positive_rot_s_rad(tmp_path):
    """
    A positive in-plane rotation rot_s_rad should be preserved through a write
    and reload cycle.
    """
    original_line = _build_oct_line(k3 = 50.0, rot_s_rad = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve positive octupole rot_s_rad. "
        f"""Original: 0.05, reloaded: {reloaded_line["o1"].rot_s_rad}.""")


def test_oct_writer_preserves_negative_rot_s_rad(tmp_path):
    """
    A negative in-plane rotation rot_s_rad should be preserved through a write
    and reload cycle, including correct handling of the unary minus.
    """
    original_line = _build_oct_line(k3 = 50.0, rot_s_rad = -0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].rot_s_rad == pytest.approx(-0.05), (
        "Writer roundtrip should preserve negative octupole rot_s_rad. "
        f"""Original: -0.05, reloaded: {reloaded_line["o1"].rot_s_rad}.""")


########################################
# All Misalignments Simultaneously
########################################
def test_oct_writer_preserves_all_misalignments_simultaneously(tmp_path):
    """
    An octupole with shift_x, shift_y, and rot_s_rad all non-zero should
    preserve all three through a write and reload cycle.
    """
    original_line = _build_oct_line(
        shift_x   = 1.0E-3,
        shift_y   = -2.0E-3,
        rot_s_rad = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve shift_x alongside other misalignments. "
        f"""Original: 1.0E-3, reloaded: {reloaded_line["o1"].shift_x}.""")
    assert reloaded_line["o1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve shift_y alongside other misalignments. "
        f"""Original: -2.0E-3, reloaded: {reloaded_line["o1"].shift_y}.""")
    assert reloaded_line["o1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve rot_s_rad alongside other misalignments. "
        f"""Original: 0.05, reloaded: {reloaded_line["o1"].rot_s_rad}.""")


def test_oct_writer_preserves_k3_with_all_misalignments(tmp_path):
    """
    An octupole with k3, shift_x, shift_y, and rot_s_rad all non-zero should
    preserve all four through a write and reload cycle. This exercises the full
    complex path in the writer alongside the optics expression for k3.
    """
    original_line = _build_oct_line(
        k3        = 50.0,
        shift_x   = 1.0E-3,
        shift_y   = -2.0E-3,
        rot_s_rad = 0.05)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["o1"].k3 == pytest.approx(50.0), (
        "Writer roundtrip should preserve k3 alongside misalignments. "
        f"""Original: 50.0, reloaded: {reloaded_line["o1"].k3}.""")
    assert reloaded_line["o1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve shift_x alongside k3. "
        f"""Original: 1.0E-3, reloaded: {reloaded_line["o1"].shift_x}.""")
    assert reloaded_line["o1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve shift_y alongside k3. "
        f"""Original: -2.0E-3, reloaded: {reloaded_line["o1"].shift_y}.""")
    assert reloaded_line["o1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve rot_s_rad alongside k3. "
        f"""Original: 0.05, reloaded: {reloaded_line["o1"].rot_s_rad}.""")
    assert env["k3_o1"] == pytest.approx(50.0), (
        "Optics variable `k3_o1` should remain accessible alongside hardcoded "
        "misalignment values. "
        f"""Got: {env["k3_o1"]}.""")


################################################################################
# Combined Multipole Components
################################################################################
########################################
# Higher-Order knl Components
########################################
def test_oct_writer_preserves_knl_combined_multipole_component(tmp_path):
    """
    An octupole with a combined decapole component (knl[4] != 0) should
    preserve that component through a write and reload cycle.

    This is a regression test for preserving combined multipole components
    carried by octupole elements.
    """
    original_line = _build_oct_line(k3 = 50.0, knl = [0.0, 0.0, 0.0, 0.0, 6.0E-5])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_knl = np.asarray(original_line["o1"].knl)
    reloaded_knl = np.asarray(reloaded_line["o1"].knl)

    assert reloaded_knl.tolist() == pytest.approx(original_knl.tolist()), (
        "Writer roundtrip should preserve octupole knl combined multipole "
        "components. The octupole writer does not write knl, so this "
        "component is silently lost on reload. "
        f"Original knl: {original_knl.tolist()}, "
        f"reloaded knl: {reloaded_knl.tolist()}.")


########################################
# Higher-Order ksl Components
########################################
def test_oct_writer_preserves_ksl_combined_multipole_component(tmp_path):
    """
    An octupole with a combined skew decapole component (ksl[4] != 0) should
    preserve that component through a write and reload cycle.

    This is the skew-component counterpart to the combined multipole knl
    preservation test.
    """
    original_line = _build_oct_line(k3 = 50.0, ksl = [0.0, 0.0, 0.0, 0.0, -3.0E-5])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_ksl = np.asarray(original_line["o1"].ksl)
    reloaded_ksl = np.asarray(reloaded_line["o1"].ksl)

    assert reloaded_ksl.tolist() == pytest.approx(original_ksl.tolist()), (
        "Writer roundtrip should preserve octupole ksl combined multipole "
        "components. The octupole writer does not write ksl, so this "
        "component is silently lost on reload. "
        f"Original ksl: {original_ksl.tolist()}, "
        f"reloaded ksl: {reloaded_ksl.tolist()}.")


def test_oct_writer_preserves_knl_and_ksl_components_simultaneously(tmp_path):
    """
    An octupole carrying both knl and ksl combined multipole components should
    preserve both through a write and reload cycle.

    knl and ksl components should be preserved independently when both are
    present on the same element.
    """
    original_line = _build_oct_line(
        k3  = 50.0,
        knl = [0.0, 0.0, 0.0, 0.0, 6.0E-5],
        ksl = [0.0, 0.0, 0.0, 0.0, -3.0E-5])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_knl = np.asarray(original_line["o1"].knl)
    reloaded_knl = np.asarray(reloaded_line["o1"].knl)
    original_ksl = np.asarray(original_line["o1"].ksl)
    reloaded_ksl = np.asarray(reloaded_line["o1"].ksl)

    assert reloaded_knl.tolist() == pytest.approx(original_knl.tolist()), (
        "Writer roundtrip should preserve octupole knl. "
        f"Original: {original_knl.tolist()}, reloaded: {reloaded_knl.tolist()}.")
    assert reloaded_ksl.tolist() == pytest.approx(original_ksl.tolist()), (
        "Writer roundtrip should preserve octupole ksl. "
        f"Original: {original_ksl.tolist()}, reloaded: {reloaded_ksl.tolist()}.")


################################################################################
# Multi-Element Behaviour
################################################################################
########################################
# Multiple Octupoles
########################################
def test_oct_writer_preserves_multiple_octs_independently(tmp_path):
    """
    Multiple octupole elements with different strengths should each preserve
    their individual k3 values independently through a single write and reload
    cycle. Each octupole writes its own optics variable (k3_of, k3_od, k3_oz).
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Octupole(length = 0.2, k3 = +50.0),
            xt.Octupole(length = 0.2, k3 = -50.0),
            xt.Octupole(length = 0.2, k3 =   0.0),
            xt.Marker(),
        ],
        element_names = ["start", "of", "od", "oz", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    expected = {"of": +50.0, "od": -50.0, "oz": 0.0}

    for name, expected_k3 in expected.items():
        assert reloaded_line[name].k3 == pytest.approx(expected_k3), (
            f"Writer roundtrip should preserve k3 for octupole `{name}`. "
            f"Expected: {expected_k3}, reloaded: {reloaded_line[name].k3}.")

    assert env["k3_of"] == pytest.approx(50.0), (
        "Optics variable `k3_of` should be accessible and correct after reload.")
    assert env["k3_od"] == pytest.approx(-50.0), (
        "Optics variable `k3_od` should be accessible and correct after reload.")


########################################
# Mixed Normal and Skew Octupoles
########################################
def test_oct_writer_preserves_mixed_normal_and_skew_octs(tmp_path):
    """
    A line containing normal, skew, and combined-strength octupoles should
    preserve all strengths independently through a single write and reload
    cycle. Each octupole should have its own correctly named optics variables.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Octupole(length = 0.2, k3  = +50.0),
            xt.Octupole(length = 0.2, k3s = +15.0),
            xt.Octupole(length = 0.2, k3  = -30.0, k3s = 5.0),
            xt.Marker(),
        ],
        element_names = ["start", "onorm", "oskew", "ocombined", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    assert reloaded_line["onorm"].k3 == pytest.approx(50.0), (
        "Writer roundtrip should preserve normal octupole k3. "
        f"""Original: 50.0, reloaded: {reloaded_line["onorm"].k3}.""")
    assert reloaded_line["onorm"].k3s == pytest.approx(0.0), (
        "Normal octupole should have zero k3s after roundtrip. "
        f"""Reloaded k3s: {reloaded_line["onorm"].k3s}.""")

    assert reloaded_line["oskew"].k3s == pytest.approx(15.0), (
        "Writer roundtrip should preserve skew octupole k3s. "
        f"""Original: 15.0, reloaded: {reloaded_line["oskew"].k3s}.""")
    assert reloaded_line["oskew"].k3 == pytest.approx(0.0), (
        "Pure skew octupole should have zero k3 after roundtrip. "
        f"""Reloaded k3: {reloaded_line["oskew"].k3}.""")

    assert reloaded_line["ocombined"].k3 == pytest.approx(-30.0), (
        "Writer roundtrip should preserve k3 for a combined-strength oct. "
        f"""Original: -30.0, reloaded: {reloaded_line["ocombined"].k3}.""")
    assert reloaded_line["ocombined"].k3s == pytest.approx(5.0), (
        "Writer roundtrip should preserve k3s for a combined-strength oct. "
        f"""Original: 5.0, reloaded: {reloaded_line["ocombined"].k3s}.""")

    assert env["k3_onorm"] == pytest.approx(50.0), (
        "Optics variable `k3_onorm` should be accessible and correct.")
    assert env["k3s_oskew"] == pytest.approx(15.0), (
        "Optics variable `k3s_oskew` should be accessible and correct.")
