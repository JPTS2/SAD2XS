"""
================================================================================
Tests for sextupole element writer serialisation
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
    variables, which verifies that k2 / k2s are written as live deferred
    expressions rather than baked-in constants.
    """
    output_dir = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = "Sextupole writer test",
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = "test_lattice_import_optics",
        output_directory  = str(output_dir),
        output_header     = "Sextupole writer test",
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


def _build_sext_line(
        length    = 0.3,
        k2        = 0.0,
        k2s       = 0.0,
        shift_x   = 0.0,
        shift_y   = 0.0,
        rot_s_rad = 0.0,
        knl       = None,
        ksl       = None):
    """
    Build a minimal single-sextupole Xsuite line with a reference particle.
    Keyword arguments map directly to xt.Sextupole fields.
    """
    sext_kwargs = dict(
        length    = length,
        k2        = k2,
        k2s       = k2s,
        shift_x   = shift_x,
        shift_y   = shift_y,
        rot_s_rad = rot_s_rad)

    if knl is not None:
        sext_kwargs["knl"] = knl
    if ksl is not None:
        sext_kwargs["ksl"] = ksl

    line = xt.Line(
        elements      = [xt.Marker(), xt.Sextupole(**sext_kwargs), xt.Marker()],
        element_names = ["start", "s1", "end"])

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
def test_sext_writer_reloads_as_xsuite_sextupole(tmp_path):
    """
    A written sextupole element should reload as an xt.Sextupole in a clean
    Xsuite environment.
    """
    original_line = _build_sext_line(k2 = 0.5)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["s1"], xt.Sextupole), (
        "Written sextupole element 's1' should reload as xt.Sextupole. "
        f"Got: {type(reloaded_line['s1']).__name__}.")


def test_sext_writer_preserves_element_name(tmp_path):
    """
    A written sextupole element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_sext_line(k2 = 0.5)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "s1" in list(reloaded_line.element_names), (
        "Reloaded line should contain sextupole element 's1'. "
        f"Got: {list(reloaded_line.element_names)}.")


########################################
# Element Order
########################################
def test_sext_writer_preserves_element_order(tmp_path):
    """
    Multiple sextupole and marker elements should appear in the same order
    after a write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Sextupole(length = 0.3, k2 = 0.5),
            xt.Marker(),
            xt.Sextupole(length = 0.3, k2 = -0.5),
            xt.Marker(),
        ],
        element_names = ["start", "sf", "mid", "sd", "end"])

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
def test_sext_writer_preserves_length(tmp_path):
    """
    A sextupole element's length should be preserved through a write and
    reload cycle.
    """
    original_line = _build_sext_line(length = 0.45, k2 = 0.5)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].length == pytest.approx(0.45), (
        "Writer roundtrip should preserve sextupole length. "
        f"Original: 0.45, reloaded: {reloaded_line['s1'].length}.")


########################################
# Normal Sextupole Strength via Optics Expression
########################################
def test_sext_writer_preserves_positive_k2(tmp_path):
    """
    A focusing sextupole's k2 should be preserved through a write and reload
    cycle. k2 is written to the optics file as a named variable k2_s1 and
    referenced from the lattice file as a deferred expression.
    """
    original_line = _build_sext_line(k2 = 0.5)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].k2 == pytest.approx(0.5), (
        "Writer roundtrip should preserve positive sextupole k2. "
        f"Original: 0.5, reloaded: {reloaded_line['s1'].k2}.")


def test_sext_writer_preserves_negative_k2(tmp_path):
    """
    A defocusing sextupole's k2 should be preserved through a write and
    reload cycle.
    """
    original_line = _build_sext_line(k2 = -0.5)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].k2 == pytest.approx(-0.5), (
        "Writer roundtrip should preserve negative sextupole k2. "
        f"Original: -0.5, reloaded: {reloaded_line['s1'].k2}.")


def test_sext_writer_preserves_zero_k2(tmp_path):
    """
    A zero-strength sextupole should survive a write and reload cycle with
    k2 remaining zero. Zero-strength sextupoles appear as lattice placeholders.
    """
    original_line = _build_sext_line(k2 = 0.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].k2 == pytest.approx(0.0), (
        "Writer roundtrip should preserve zero sextupole k2. "
        f"Reloaded: {reloaded_line['s1'].k2}.")


def test_sext_writer_k2_preserves_full_double_precision(tmp_path):
    """
    A sextupole k2 with many significant digits should survive a write and
    reload cycle at full double precision. The optics file writes k2_s1 to
    24 decimal places, which exceeds the ~17 significant digits of IEEE 754
    double precision.
    """
    k2_precise = 0.23456789012345678
    original_line = _build_sext_line(k2 = k2_precise)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].k2 == pytest.approx(k2_precise, rel = 1E-15), (
        "Writer roundtrip should preserve sextupole k2 at full double "
        f"precision. Original: {k2_precise!r}, reloaded: {reloaded_line['s1'].k2!r}.")


########################################
# k2 Written as Tunable Optics Expression
########################################
def test_sext_writer_k2_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the sextupole's k2 should be accessible as
    a named optics variable k2_s1 in the Xsuite environment. This confirms
    that k2 is written as a deferred expression reference rather than a
    baked-in constant.
    """
    original_line = _build_sext_line(k2 = 0.5)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["k2_s1"] == pytest.approx(0.5), (
        "Optics variable 'k2_s1' should exist in the environment after reload "
        "and equal the original k2 value. "
        f"Got: {env['k2_s1']}.")


def test_sext_writer_k2_optics_variable_is_tunable(tmp_path):
    """
    The k2_s1 optics variable written to the optics file should remain live:
    modifying it in the reloaded environment should immediately update the
    sextupole's k2 in the line. This is the core contract of the expression-
    based optics variable mechanism.
    """
    original_line = _build_sext_line(k2 = 0.5)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["k2_s1"] = 1.0

    assert reloaded_line["s1"].k2 == pytest.approx(1.0), (
        "Modifying optics variable 'k2_s1' should update the sextupole's k2 "
        "in the reloaded line. The k2 should be a live deferred expression, "
        f"not a constant. Got: {reloaded_line['s1'].k2}.")


########################################
# Skew Sextupole Strength via Optics Expression
########################################
def test_sext_writer_preserves_positive_k2s(tmp_path):
    """
    A positive skew sextupole's k2s should be preserved through a write and
    reload cycle. This exercises the simple skew path in the writer where only
    k2s is non-zero.
    """
    original_line = _build_sext_line(k2s = 0.15)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].k2s == pytest.approx(0.15), (
        "Writer roundtrip should preserve positive skew sextupole k2s. "
        f"Original: 0.15, reloaded: {reloaded_line['s1'].k2s}.")
    assert reloaded_line["s1"].k2 == pytest.approx(0.0), (
        "Pure skew sextupole should have zero k2 after roundtrip. "
        f"Reloaded k2: {reloaded_line['s1'].k2}.")


def test_sext_writer_preserves_negative_k2s(tmp_path):
    """
    A negative skew sextupole's k2s should be preserved through a write and
    reload cycle.
    """
    original_line = _build_sext_line(k2s = -0.15)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].k2s == pytest.approx(-0.15), (
        "Writer roundtrip should preserve negative skew sextupole k2s. "
        f"Original: -0.15, reloaded: {reloaded_line['s1'].k2s}.")


def test_sext_writer_k2s_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, a skew sextupole's k2s should be accessible
    as optics variable k2s_s1 in the Xsuite environment. This confirms the
    skew strength is written as a deferred expression, not a hardcoded constant.
    """
    original_line = _build_sext_line(k2s = 0.15)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["k2s_s1"] == pytest.approx(0.15), (
        "Optics variable 'k2s_s1' should exist in the environment after reload "
        "and equal the original k2s value. "
        f"Got: {env['k2s_s1']}.")


def test_sext_writer_k2s_optics_variable_is_tunable(tmp_path):
    """
    The k2s_s1 optics variable should remain live after reload: modifying it
    should immediately update the skew sextupole's k2s in the line.
    """
    original_line = _build_sext_line(k2s = 0.15)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["k2s_s1"] = 0.3

    assert reloaded_line["s1"].k2s == pytest.approx(0.3), (
        "Modifying optics variable 'k2s_s1' should update the sextupole's "
        "k2s in the reloaded line. "
        f"Got: {reloaded_line['s1'].k2s}.")


########################################
# Normal and Skew Strengths Combined
########################################
def test_sext_writer_preserves_k2_and_k2s_simultaneously(tmp_path):
    """
    A sextupole with both k2 and k2s non-zero should preserve both through a
    write and reload cycle. Both strengths non-zero triggers the writer's
    complex path. Both values should be written to the optics file and both
    should be accessible as live optics variables.
    """
    original_line = _build_sext_line(k2 = 0.5, k2s = 0.05)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].k2 == pytest.approx(0.5), (
        "Writer roundtrip should preserve k2 when both k2 and k2s are set. "
        f"Original: 0.5, reloaded: {reloaded_line['s1'].k2}.")
    assert reloaded_line["s1"].k2s == pytest.approx(0.05), (
        "Writer roundtrip should preserve k2s when both k2 and k2s are set. "
        f"Original: 0.05, reloaded: {reloaded_line['s1'].k2s}.")
    assert env["k2_s1"] == pytest.approx(0.5), (
        "Optics variable 'k2_s1' should be written and accessible when both "
        "k2 and k2s are non-zero.")
    assert env["k2s_s1"] == pytest.approx(0.05), (
        "Optics variable 'k2s_s1' should be written and accessible when both "
        "k2 and k2s are non-zero.")


################################################################################
# Misalignments via Hardcoded Values
################################################################################
# shift_x, shift_y, and rot_s_rad are NOT written as optics variables.
# They are written as literal numeric strings in the lattice file, e.g.:
#   env.new(name = 's1', parent = 'sext_0.3', shift_x = '0.001')
# The string is evaluated by Xsuite's expression engine when the file is
# loaded. The tests below verify that positive, negative, and scientific-
# notation values all survive this literal-string encoding correctly.
########################################
# Horizontal Offset
########################################
def test_sext_writer_preserves_positive_shift_x(tmp_path):
    """
    A positive horizontal offset shift_x should be preserved through a write
    and reload cycle. Non-zero shift_x triggers the writer's complex path.
    """
    original_line = _build_sext_line(k2 = 0.5, shift_x = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve positive sextupole shift_x. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['s1'].shift_x}.")


def test_sext_writer_preserves_negative_shift_x(tmp_path):
    """
    A negative horizontal offset shift_x should be preserved through a write
    and reload cycle. The literal string encoding must correctly handle the
    unary minus in the evaluated expression.
    """
    original_line = _build_sext_line(k2 = 0.5, shift_x = -1.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].shift_x == pytest.approx(-1.5E-3), (
        "Writer roundtrip should preserve negative sextupole shift_x. "
        f"Original: -1.5E-3, reloaded: {reloaded_line['s1'].shift_x}.")


def test_sext_writer_preserves_shift_x_in_scientific_notation(tmp_path):
    """
    A very small shift_x value that Python formats in scientific notation
    should survive a write and reload cycle.
    """
    original_line = _build_sext_line(k2 = 0.5, shift_x = 2.34567891E-6)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].shift_x == pytest.approx(2.34567891E-6), (
        "Writer roundtrip should preserve a shift_x value written in scientific "
        f"notation. Original: 2.34567891E-6, reloaded: {reloaded_line['s1'].shift_x}.")


########################################
# Vertical Offset
########################################
def test_sext_writer_preserves_positive_shift_y(tmp_path):
    """
    A positive vertical offset shift_y should be preserved through a write and
    reload cycle. Non-zero shift_y triggers the writer's complex path.
    """
    original_line = _build_sext_line(k2 = 0.5, shift_y = 2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].shift_y == pytest.approx(2.0E-3), (
        "Writer roundtrip should preserve positive sextupole shift_y. "
        f"Original: 2.0E-3, reloaded: {reloaded_line['s1'].shift_y}.")


def test_sext_writer_preserves_negative_shift_y(tmp_path):
    """
    A negative vertical offset shift_y should be preserved through a write and
    reload cycle, including correct handling of the unary minus.
    """
    original_line = _build_sext_line(k2 = 0.5, shift_y = -2.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].shift_y == pytest.approx(-2.5E-3), (
        "Writer roundtrip should preserve negative sextupole shift_y. "
        f"Original: -2.5E-3, reloaded: {reloaded_line['s1'].shift_y}.")


def test_sext_writer_preserves_shift_y_in_scientific_notation(tmp_path):
    """
    A very small shift_y value requiring scientific notation should survive a
    write and reload cycle.
    """
    original_line = _build_sext_line(k2 = 0.5, shift_y = -9.87654321E-7)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].shift_y == pytest.approx(-9.87654321E-7), (
        "Writer roundtrip should preserve a shift_y value written in scientific "
        f"notation. Original: -9.87654321E-7, reloaded: {reloaded_line['s1'].shift_y}.")


########################################
# In-Plane Rotation
########################################
def test_sext_writer_preserves_positive_rot_s_rad(tmp_path):
    """
    A positive in-plane rotation rot_s_rad should be preserved through a write
    and reload cycle.
    """
    original_line = _build_sext_line(k2 = 0.5, rot_s_rad = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve positive sextupole rot_s_rad. "
        f"Original: 0.05, reloaded: {reloaded_line['s1'].rot_s_rad}.")


def test_sext_writer_preserves_negative_rot_s_rad(tmp_path):
    """
    A negative in-plane rotation rot_s_rad should be preserved through a write
    and reload cycle, including correct handling of the unary minus.
    """
    original_line = _build_sext_line(k2 = 0.5, rot_s_rad = -0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].rot_s_rad == pytest.approx(-0.05), (
        "Writer roundtrip should preserve negative sextupole rot_s_rad. "
        f"Original: -0.05, reloaded: {reloaded_line['s1'].rot_s_rad}.")


########################################
# All Misalignments Simultaneously
########################################
def test_sext_writer_preserves_all_misalignments_simultaneously(tmp_path):
    """
    A sextupole with shift_x, shift_y, and rot_s_rad all non-zero should
    preserve all three through a write and reload cycle.
    """
    original_line = _build_sext_line(
        shift_x   = 1.0E-3,
        shift_y   = -2.0E-3,
        rot_s_rad = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve shift_x alongside other misalignments. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['s1'].shift_x}.")
    assert reloaded_line["s1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve shift_y alongside other misalignments. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['s1'].shift_y}.")
    assert reloaded_line["s1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve rot_s_rad alongside other misalignments. "
        f"Original: 0.05, reloaded: {reloaded_line['s1'].rot_s_rad}.")


def test_sext_writer_preserves_k2_with_all_misalignments(tmp_path):
    """
    A sextupole with k2, shift_x, shift_y, and rot_s_rad all non-zero should
    preserve all four through a write and reload cycle. This exercises the full
    complex path in the writer alongside the optics expression for k2.
    """
    original_line = _build_sext_line(
        k2        = 0.5,
        shift_x   = 1.0E-3,
        shift_y   = -2.0E-3,
        rot_s_rad = 0.05)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["s1"].k2 == pytest.approx(0.5), (
        "Writer roundtrip should preserve k2 alongside misalignments. "
        f"Original: 0.5, reloaded: {reloaded_line['s1'].k2}.")
    assert reloaded_line["s1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve shift_x alongside k2. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['s1'].shift_x}.")
    assert reloaded_line["s1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve shift_y alongside k2. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['s1'].shift_y}.")
    assert reloaded_line["s1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve rot_s_rad alongside k2. "
        f"Original: 0.05, reloaded: {reloaded_line['s1'].rot_s_rad}.")
    assert env["k2_s1"] == pytest.approx(0.5), (
        "Optics variable 'k2_s1' should remain accessible alongside hardcoded "
        "misalignment values. "
        f"Got: {env['k2_s1']}.")


################################################################################
# Combined Multipole Components
################################################################################
########################################
# Higher-Order knl Components
########################################
def test_sext_writer_preserves_knl_combined_multipole_component(tmp_path):
    """
    A sextupole with a combined octupole component (knl[3] != 0) should
    preserve that component through a write and reload cycle.

    This test is expected to FAIL. The sextupole writer reads and writes only
    k2, k2s, shift_x, shift_y, and rot_s_rad. It does not read or write knl
    or ksl, so combined multipole components are silently dropped on reload.
    See issue #17.
    """
    original_line = _build_sext_line(k2 = 0.5, knl = [0.0, 0.0, 0.0, 8.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_knl = np.asarray(original_line["s1"].knl)
    reloaded_knl = np.asarray(reloaded_line["s1"].knl)

    assert reloaded_knl.tolist() == pytest.approx(original_knl.tolist()), (
        "Writer roundtrip should preserve sextupole knl combined multipole "
        "components. The sextupole writer does not write knl, so this "
        "component is silently lost on reload. See issue #17. "
        f"Original knl: {original_knl.tolist()}, "
        f"reloaded knl: {reloaded_knl.tolist()}.")


########################################
# Higher-Order ksl Components
########################################
def test_sext_writer_preserves_ksl_combined_multipole_component(tmp_path):
    """
    A sextupole with a combined skew octupole component (ksl[3] != 0) should
    preserve that component through a write and reload cycle.

    This test is expected to FAIL. The sextupole writer does not write ksl.
    Combined skew multipole components are silently dropped on reload.
    See issue #17.
    """
    original_line = _build_sext_line(k2 = 0.5, ksl = [0.0, 0.0, 0.0, -4.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_ksl = np.asarray(original_line["s1"].ksl)
    reloaded_ksl = np.asarray(reloaded_line["s1"].ksl)

    assert reloaded_ksl.tolist() == pytest.approx(original_ksl.tolist()), (
        "Writer roundtrip should preserve sextupole ksl combined multipole "
        "components. The sextupole writer does not write ksl, so this "
        "component is silently lost on reload. See issue #17. "
        f"Original ksl: {original_ksl.tolist()}, "
        f"reloaded ksl: {reloaded_ksl.tolist()}.")


def test_sext_writer_preserves_knl_and_ksl_components_simultaneously(tmp_path):
    """
    A sextupole carrying both knl and ksl combined multipole components should
    preserve both through a write and reload cycle.

    This test is expected to FAIL. Neither knl nor ksl is written by the
    sextupole writer. Both are silently lost on reload. See issue #17.
    """
    original_line = _build_sext_line(
        k2  = 0.5,
        knl = [0.0, 0.0, 0.0, 8.0E-4],
        ksl = [0.0, 0.0, 0.0, -4.0E-4])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    original_knl = np.asarray(original_line["s1"].knl)
    reloaded_knl = np.asarray(reloaded_line["s1"].knl)
    original_ksl = np.asarray(original_line["s1"].ksl)
    reloaded_ksl = np.asarray(reloaded_line["s1"].ksl)

    assert reloaded_knl.tolist() == pytest.approx(original_knl.tolist()), (
        "Writer roundtrip should preserve sextupole knl. See issue #17. "
        f"Original: {original_knl.tolist()}, reloaded: {reloaded_knl.tolist()}.")
    assert reloaded_ksl.tolist() == pytest.approx(original_ksl.tolist()), (
        "Writer roundtrip should preserve sextupole ksl. See issue #17. "
        f"Original: {original_ksl.tolist()}, reloaded: {reloaded_ksl.tolist()}.")


################################################################################
# Multi-Element Behaviour
################################################################################
########################################
# Multiple Sextupoles
########################################
def test_sext_writer_preserves_multiple_sexts_independently(tmp_path):
    """
    Multiple sextupole elements with different strengths should each preserve
    their individual k2 values independently through a single write and reload
    cycle. Each sextupole writes its own optics variable (k2_sf, k2_sd, k2_sz).
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Sextupole(length = 0.3, k2 = +0.5),
            xt.Sextupole(length = 0.3, k2 = -0.5),
            xt.Sextupole(length = 0.3, k2 =  0.0),
            xt.Marker(),
        ],
        element_names = ["start", "sf", "sd", "sz", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    expected = {"sf": +0.5, "sd": -0.5, "sz": 0.0}

    for name, expected_k2 in expected.items():
        assert reloaded_line[name].k2 == pytest.approx(expected_k2), (
            f"Writer roundtrip should preserve k2 for sextupole '{name}'. "
            f"Expected: {expected_k2}, reloaded: {reloaded_line[name].k2}.")

    assert env["k2_sf"] == pytest.approx(0.5), (
        "Optics variable 'k2_sf' should be accessible and correct after reload.")
    assert env["k2_sd"] == pytest.approx(-0.5), (
        "Optics variable 'k2_sd' should be accessible and correct after reload.")


########################################
# Mixed Normal and Skew Sextupoles
########################################
def test_sext_writer_preserves_mixed_normal_and_skew_sexts(tmp_path):
    """
    A line containing normal, skew, and combined-strength sextupoles should
    preserve all strengths independently through a single write and reload
    cycle. Each sextupole should have its own correctly named optics variables.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Sextupole(length = 0.3, k2  = +0.5),
            xt.Sextupole(length = 0.3, k2s = +0.15),
            xt.Sextupole(length = 0.3, k2  = -0.3, k2s = 0.05),
            xt.Marker(),
        ],
        element_names = ["start", "snorm", "sskew", "scombined", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    assert reloaded_line["snorm"].k2 == pytest.approx(0.5), (
        "Writer roundtrip should preserve normal sextupole k2. "
        f"Original: 0.5, reloaded: {reloaded_line['snorm'].k2}.")
    assert reloaded_line["snorm"].k2s == pytest.approx(0.0), (
        "Normal sextupole should have zero k2s after roundtrip. "
        f"Reloaded k2s: {reloaded_line['snorm'].k2s}.")

    assert reloaded_line["sskew"].k2s == pytest.approx(0.15), (
        "Writer roundtrip should preserve skew sextupole k2s. "
        f"Original: 0.15, reloaded: {reloaded_line['sskew'].k2s}.")
    assert reloaded_line["sskew"].k2 == pytest.approx(0.0), (
        "Pure skew sextupole should have zero k2 after roundtrip. "
        f"Reloaded k2: {reloaded_line['sskew'].k2}.")

    assert reloaded_line["scombined"].k2 == pytest.approx(-0.3), (
        "Writer roundtrip should preserve k2 for a combined-strength sext. "
        f"Original: -0.3, reloaded: {reloaded_line['scombined'].k2}.")
    assert reloaded_line["scombined"].k2s == pytest.approx(0.05), (
        "Writer roundtrip should preserve k2s for a combined-strength sext. "
        f"Original: 0.05, reloaded: {reloaded_line['scombined'].k2s}.")

    assert env["k2_snorm"] == pytest.approx(0.5), (
        "Optics variable 'k2_snorm' should be accessible and correct.")
    assert env["k2s_sskew"] == pytest.approx(0.15), (
        "Optics variable 'k2s_sskew' should be accessible and correct.")
