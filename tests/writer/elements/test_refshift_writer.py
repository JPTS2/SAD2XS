"""
================================================================================
Tests for reference shift element writer serialisation
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
def _write_and_load(line, tmp_path):
    """
    Write a line using the public SAD2XS writer entry points, reload it in a
    clean Xsuite environment, and return the environment and reloaded line.

    All five reference shift element types write their parameters as live optics
    expression variables. The variable name is derived from the element name:

        XYShift   'rs1' -> dx_rs1, dy_rs1
        TimeDelay 'rs1' -> dz_rs1
        YRotation 'rs1' -> chi1_rs1  (SAD CHI1)
        XRotation 'rs1' -> chi2_rs1  (SAD CHI2)
        SRotation 'rs1' -> chi3_rs1  (SAD CHI3)

    Zero-valued fields are not written to the optics file; the lattice file
    always references the variable, and env.vars.default_to_zero = True returns
    0 for any undefined variable on reload.
    """
    output_dir = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = "Reference shift writer test",
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = "test_lattice_import_optics",
        output_directory  = str(output_dir),
        output_header     = "Reference shift writer test",
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


def _build_xyshift_line(dx = 0.0, dy = 0.0):
    """
    Build a minimal single-XYShift Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.XYShift(dx = dx, dy = dy), xt.Marker()],
        element_names = ["start", "rs1", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    return line


def _build_timedelay_line(shift_zeta = 0.0):
    """
    Build a minimal single-TimeDelay Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.TimeDelay(shift_zeta = shift_zeta), xt.Marker()],
        element_names = ["start", "rs1", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    return line


def _build_yrotation_line(angle = 0.0):
    """
    Build a minimal single-YRotation Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.YRotation(angle = angle), xt.Marker()],
        element_names = ["start", "rs1", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    return line


def _build_xrotation_line(angle = 0.0):
    """
    Build a minimal single-XRotation Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.XRotation(angle = angle), xt.Marker()],
        element_names = ["start", "rs1", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    return line


def _build_srotation_line(angle = 0.0):
    """
    Build a minimal single-SRotation Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.SRotation(angle = angle), xt.Marker()],
        element_names = ["start", "rs1", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    return line


################################################################################
# XYShift
################################################################################
########################################
# Basic Serialisation
########################################
def test_refshift_writer_xyshift_reloads_as_xsuite_xyshift(tmp_path):
    """
    A written XYShift element should reload as an xt.XYShift in a clean
    Xsuite environment.
    """
    original_line = _build_xyshift_line(dx = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["rs1"], xt.XYShift), (
        "Written XYShift element 'rs1' should reload as xt.XYShift. "
        f"Got: {type(reloaded_line['rs1']).__name__}.")


def test_refshift_writer_xyshift_preserves_element_name(tmp_path):
    """
    A written XYShift element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_xyshift_line(dx = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "rs1" in list(reloaded_line.element_names), (
        "Reloaded line should contain XYShift element 'rs1'. "
        f"Got: {list(reloaded_line.element_names)}.")


########################################
# dx Field
########################################
def test_refshift_writer_xyshift_preserves_positive_dx(tmp_path):
    """
    A positive transverse shift dx should be preserved through a write and
    reload cycle. dx is written as optics variable dx_rs1.
    """
    original_line = _build_xyshift_line(dx = 1.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].dx == pytest.approx(1.5E-3), (
        "Writer roundtrip should preserve positive XYShift dx. "
        f"Original: 1.5E-3, reloaded: {reloaded_line['rs1'].dx}.")


def test_refshift_writer_xyshift_preserves_negative_dx(tmp_path):
    """
    A negative transverse shift dx should be preserved through a write and
    reload cycle.
    """
    original_line = _build_xyshift_line(dx = -1.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].dx == pytest.approx(-1.5E-3), (
        "Writer roundtrip should preserve negative XYShift dx. "
        f"Original: -1.5E-3, reloaded: {reloaded_line['rs1'].dx}.")


def test_refshift_writer_xyshift_dx_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the XYShift dx field should be accessible as
    named optics variable dx_rs1 in the Xsuite environment.
    """
    original_line = _build_xyshift_line(dx = 1.5E-3)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["dx_rs1"] == pytest.approx(1.5E-3), (
        "Optics variable 'dx_rs1' should exist in the environment after reload "
        "and equal the original dx. "
        f"Got: {env['dx_rs1']}.")


def test_refshift_writer_xyshift_dx_is_tunable_via_optics_variable(tmp_path):
    """
    The dx_rs1 optics variable should remain live after reload: modifying it
    should immediately update the XYShift dx in the line.
    """
    original_line = _build_xyshift_line(dx = 1.5E-3)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["dx_rs1"] = 3.0E-3

    assert reloaded_line["rs1"].dx == pytest.approx(3.0E-3), (
        "Modifying optics variable 'dx_rs1' should update the XYShift dx. "
        f"Got: {reloaded_line['rs1'].dx}.")


########################################
# dy Field
########################################
def test_refshift_writer_xyshift_preserves_positive_dy(tmp_path):
    """
    A positive transverse shift dy should be preserved through a write and
    reload cycle. dy is written as optics variable dy_rs1.
    """
    original_line = _build_xyshift_line(dy = 2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].dy == pytest.approx(2.0E-3), (
        "Writer roundtrip should preserve positive XYShift dy. "
        f"Original: 2.0E-3, reloaded: {reloaded_line['rs1'].dy}.")


def test_refshift_writer_xyshift_preserves_negative_dy(tmp_path):
    """
    A negative transverse shift dy should be preserved through a write and
    reload cycle.
    """
    original_line = _build_xyshift_line(dy = -2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].dy == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve negative XYShift dy. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['rs1'].dy}.")


def test_refshift_writer_xyshift_dy_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the XYShift dy field should be accessible as
    named optics variable dy_rs1 in the Xsuite environment.
    """
    original_line = _build_xyshift_line(dy = 2.0E-3)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["dy_rs1"] == pytest.approx(2.0E-3), (
        "Optics variable 'dy_rs1' should exist in the environment after reload "
        "and equal the original dy. "
        f"Got: {env['dy_rs1']}.")


def test_refshift_writer_xyshift_dy_is_tunable_via_optics_variable(tmp_path):
    """
    The dy_rs1 optics variable should remain live after reload: modifying it
    should immediately update the XYShift dy in the line.
    """
    original_line = _build_xyshift_line(dy = 2.0E-3)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["dy_rs1"] = 4.0E-3

    assert reloaded_line["rs1"].dy == pytest.approx(4.0E-3), (
        "Modifying optics variable 'dy_rs1' should update the XYShift dy. "
        f"Got: {reloaded_line['rs1'].dy}.")


########################################
# dx and dy Simultaneously
########################################
def test_refshift_writer_xyshift_preserves_dx_and_dy_simultaneously(tmp_path):
    """
    An XYShift with both dx and dy non-zero should preserve both through a
    write and reload cycle. Each field has its own independent optics variable.
    """
    original_line = _build_xyshift_line(dx = 1.5E-3, dy = -2.0E-3)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].dx == pytest.approx(1.5E-3), (
        "Writer roundtrip should preserve dx when dy is also non-zero. "
        f"Original: 1.5E-3, reloaded: {reloaded_line['rs1'].dx}.")
    assert reloaded_line["rs1"].dy == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve dy when dx is also non-zero. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['rs1'].dy}.")
    assert env["dx_rs1"] == pytest.approx(1.5E-3), (
        "Optics variable 'dx_rs1' should be accessible when dy is also set. "
        f"Got: {env['dx_rs1']}.")
    assert env["dy_rs1"] == pytest.approx(-2.0E-3), (
        "Optics variable 'dy_rs1' should be accessible when dx is also set. "
        f"Got: {env['dy_rs1']}.")


########################################
# Zero Value (not written to optics file)
########################################
def test_refshift_writer_xyshift_preserves_zero_dx(tmp_path):
    """
    An XYShift with dx=0 should survive a write and reload cycle with dx
    remaining zero. Zero dx is not written to the optics file; the lattice file
    references 'dx_rs1' and env.vars.default_to_zero = True returns 0 for the
    undefined variable.
    """
    original_line = _build_xyshift_line(dx = 0.0, dy = 2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].dx == pytest.approx(0.0), (
        "Writer roundtrip should preserve zero XYShift dx (handled by "
        "default_to_zero). "
        f"Reloaded: {reloaded_line['rs1'].dx}.")


########################################
# Precision
########################################
def test_refshift_writer_xyshift_dx_preserved_at_full_double_precision(tmp_path):
    """
    An XYShift dx with many significant digits should survive a write and
    reload cycle at full double precision. The optics file writes dx_rs1 to
    24 decimal places.
    """
    dx_precise = 1.23456789012345678E-4
    original_line = _build_xyshift_line(dx = dx_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["dx_rs1"] == pytest.approx(dx_precise, rel = 1E-15), (
        "Writer roundtrip should preserve XYShift dx at full double precision. "
        f"Original: {dx_precise!r}, reloaded env var: {env['dx_rs1']!r}.")


########################################
# Multiple XYShifts
########################################
def test_refshift_writer_preserves_multiple_xyshifts_independently(tmp_path):
    """
    Multiple XYShift elements with different dx/dy values should each preserve
    their individual values through a single write and reload cycle. Each
    element writes its own independent optics variables.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.XYShift(dx = +1.0E-3, dy =  0.0),
            xt.XYShift(dx =  0.0,    dy = -2.0E-3),
            xt.XYShift(dx = +0.5E-3, dy = +1.5E-3),
            xt.Marker(),
        ],
        element_names = ["start", "rsa", "rsb", "rsc", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    assert reloaded_line["rsa"].dx == pytest.approx(+1.0E-3), (
        "Writer roundtrip should preserve dx for 'rsa'. "
        f"Original: +1.0E-3, reloaded: {reloaded_line['rsa'].dx}.")
    assert reloaded_line["rsb"].dy == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve dy for 'rsb'. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['rsb'].dy}.")
    assert reloaded_line["rsc"].dx == pytest.approx(+0.5E-3), (
        "Writer roundtrip should preserve dx for 'rsc'. "
        f"Original: +0.5E-3, reloaded: {reloaded_line['rsc'].dx}.")
    assert reloaded_line["rsc"].dy == pytest.approx(+1.5E-3), (
        "Writer roundtrip should preserve dy for 'rsc'. "
        f"Original: +1.5E-3, reloaded: {reloaded_line['rsc'].dy}.")

    assert env["dx_rsa"] == pytest.approx(+1.0E-3), (
        "Optics variable 'dx_rsa' should be accessible and correct.")
    assert env["dy_rsb"] == pytest.approx(-2.0E-3), (
        "Optics variable 'dy_rsb' should be accessible and correct.")


################################################################################
# TimeDelay
################################################################################
########################################
# Basic Serialisation
########################################
def test_refshift_writer_timedelay_reloads_as_xsuite_timedelay(tmp_path):
    """
    A written TimeDelay element should reload as an xt.TimeDelay in a clean
    Xsuite environment.
    """
    original_line = _build_timedelay_line(shift_zeta = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["rs1"], xt.TimeDelay), (
        "Written TimeDelay element 'rs1' should reload as xt.TimeDelay. "
        f"Got: {type(reloaded_line['rs1']).__name__}.")


########################################
# shift_zeta Field
########################################
def test_refshift_writer_timedelay_preserves_positive_shift_zeta(tmp_path):
    """
    A positive longitudinal shift_zeta should be preserved through a write and
    reload cycle. shift_zeta is written as optics variable dz_rs1.
    """
    original_line = _build_timedelay_line(shift_zeta = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].shift_zeta == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve positive TimeDelay shift_zeta. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['rs1'].shift_zeta}.")


def test_refshift_writer_timedelay_preserves_negative_shift_zeta(tmp_path):
    """
    A negative longitudinal shift_zeta should be preserved through a write
    and reload cycle.
    """
    original_line = _build_timedelay_line(shift_zeta = -1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].shift_zeta == pytest.approx(-1.0E-3), (
        "Writer roundtrip should preserve negative TimeDelay shift_zeta. "
        f"Original: -1.0E-3, reloaded: {reloaded_line['rs1'].shift_zeta}.")


def test_refshift_writer_timedelay_shift_zeta_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the TimeDelay shift_zeta field should be
    accessible as named optics variable dz_rs1 in the Xsuite environment.
    """
    original_line = _build_timedelay_line(shift_zeta = 1.0E-3)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["dz_rs1"] == pytest.approx(1.0E-3), (
        "Optics variable 'dz_rs1' should exist in the environment after reload "
        "and equal the original shift_zeta. "
        f"Got: {env['dz_rs1']}.")


def test_refshift_writer_timedelay_shift_zeta_is_tunable_via_optics_variable(tmp_path):
    """
    The dz_rs1 optics variable should remain live after reload: modifying it
    should immediately update the TimeDelay shift_zeta in the line.
    """
    original_line = _build_timedelay_line(shift_zeta = 1.0E-3)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["dz_rs1"] = 2.0E-3

    assert reloaded_line["rs1"].shift_zeta == pytest.approx(2.0E-3), (
        "Modifying optics variable 'dz_rs1' should update the TimeDelay shift_zeta. "
        f"Got: {reloaded_line['rs1'].shift_zeta}.")


def test_refshift_writer_timedelay_shift_zeta_preserved_at_full_double_precision(tmp_path):
    """
    A TimeDelay shift_zeta with many significant digits should survive a write
    and reload cycle at full double precision.
    """
    dz_precise = 1.23456789012345678E-4
    original_line = _build_timedelay_line(shift_zeta = dz_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["dz_rs1"] == pytest.approx(dz_precise, rel = 1E-15), (
        "Writer roundtrip should preserve TimeDelay shift_zeta at full double precision. "
        f"Original: {dz_precise!r}, reloaded env var: {env['dz_rs1']!r}.")


################################################################################
# YRotation (CHI1)
################################################################################
########################################
# Basic Serialisation
########################################
def test_refshift_writer_yrotation_reloads_as_xsuite_yrotation(tmp_path):
    """
    A written YRotation element should reload as an xt.YRotation in a clean
    Xsuite environment. YRotation maps to SAD CHI1; the optics variable is
    chi1_{name}.
    """
    original_line = _build_yrotation_line(angle = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["rs1"], xt.YRotation), (
        "Written YRotation element 'rs1' should reload as xt.YRotation. "
        f"Got: {type(reloaded_line['rs1']).__name__}.")


########################################
# angle Field
########################################
def test_refshift_writer_yrotation_preserves_positive_angle(tmp_path):
    """
    A positive YRotation angle should be preserved through a write and reload
    cycle. Angle is written as optics variable chi1_rs1.
    """
    original_line = _build_yrotation_line(angle = 5.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].angle == pytest.approx(5.0E-3), (
        "Writer roundtrip should preserve positive YRotation angle. "
        f"Original: 5.0E-3, reloaded: {reloaded_line['rs1'].angle}.")


def test_refshift_writer_yrotation_preserves_negative_angle(tmp_path):
    """
    A negative YRotation angle should be preserved through a write and reload
    cycle.
    """
    original_line = _build_yrotation_line(angle = -5.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].angle == pytest.approx(-5.0E-3), (
        "Writer roundtrip should preserve negative YRotation angle. "
        f"Original: -5.0E-3, reloaded: {reloaded_line['rs1'].angle}.")


def test_refshift_writer_yrotation_angle_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the YRotation angle should be accessible as
    named optics variable chi1_rs1 in the Xsuite environment.
    """
    original_line = _build_yrotation_line(angle = 5.0E-3)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi1_rs1"] == pytest.approx(5.0E-3), (
        "Optics variable 'chi1_rs1' should exist in the environment after reload "
        "and equal the original YRotation angle. "
        f"Got: {env['chi1_rs1']}.")


def test_refshift_writer_yrotation_angle_is_tunable_via_optics_variable(tmp_path):
    """
    The chi1_rs1 optics variable should remain live after reload: modifying it
    should immediately update the YRotation angle in the line.
    """
    original_line = _build_yrotation_line(angle = 5.0E-3)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["chi1_rs1"] = 10.0E-3

    assert reloaded_line["rs1"].angle == pytest.approx(10.0E-3), (
        "Modifying optics variable 'chi1_rs1' should update the YRotation angle. "
        f"Got: {reloaded_line['rs1'].angle}.")


def test_refshift_writer_yrotation_angle_preserved_at_full_double_precision(tmp_path):
    """
    A YRotation angle with many significant digits should survive a write and
    reload cycle at full double precision.
    """
    angle_precise = 4.56789012345678901E-3
    original_line = _build_yrotation_line(angle = angle_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi1_rs1"] == pytest.approx(angle_precise, rel = 1E-15), (
        "Writer roundtrip should preserve YRotation angle at full double precision. "
        f"Original: {angle_precise!r}, reloaded env var: {env['chi1_rs1']!r}.")


################################################################################
# XRotation (CHI2)
################################################################################
########################################
# Basic Serialisation
########################################
def test_refshift_writer_xrotation_reloads_as_xsuite_xrotation(tmp_path):
    """
    A written XRotation element should reload as an xt.XRotation in a clean
    Xsuite environment. XRotation maps to SAD CHI2; the optics variable is
    chi2_{name}.
    """
    original_line = _build_xrotation_line(angle = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["rs1"], xt.XRotation), (
        "Written XRotation element 'rs1' should reload as xt.XRotation. "
        f"Got: {type(reloaded_line['rs1']).__name__}.")


########################################
# angle Field
########################################
def test_refshift_writer_xrotation_preserves_positive_angle(tmp_path):
    """
    A positive XRotation angle should be preserved through a write and reload
    cycle. Angle is written as optics variable chi2_rs1.
    """
    original_line = _build_xrotation_line(angle = 5.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].angle == pytest.approx(5.0E-3), (
        "Writer roundtrip should preserve positive XRotation angle. "
        f"Original: 5.0E-3, reloaded: {reloaded_line['rs1'].angle}.")


def test_refshift_writer_xrotation_preserves_negative_angle(tmp_path):
    """
    A negative XRotation angle should be preserved through a write and reload
    cycle.
    """
    original_line = _build_xrotation_line(angle = -5.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].angle == pytest.approx(-5.0E-3), (
        "Writer roundtrip should preserve negative XRotation angle. "
        f"Original: -5.0E-3, reloaded: {reloaded_line['rs1'].angle}.")


def test_refshift_writer_xrotation_angle_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the XRotation angle should be accessible as
    named optics variable chi2_rs1 in the Xsuite environment.
    """
    original_line = _build_xrotation_line(angle = 5.0E-3)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi2_rs1"] == pytest.approx(5.0E-3), (
        "Optics variable 'chi2_rs1' should exist in the environment after reload "
        "and equal the original XRotation angle. "
        f"Got: {env['chi2_rs1']}.")


def test_refshift_writer_xrotation_angle_is_tunable_via_optics_variable(tmp_path):
    """
    The chi2_rs1 optics variable should remain live after reload: modifying it
    should immediately update the XRotation angle in the line.
    """
    original_line = _build_xrotation_line(angle = 5.0E-3)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["chi2_rs1"] = 10.0E-3

    assert reloaded_line["rs1"].angle == pytest.approx(10.0E-3), (
        "Modifying optics variable 'chi2_rs1' should update the XRotation angle. "
        f"Got: {reloaded_line['rs1'].angle}.")


def test_refshift_writer_xrotation_angle_preserved_at_full_double_precision(tmp_path):
    """
    An XRotation angle with many significant digits should survive a write and
    reload cycle at full double precision.
    """
    angle_precise = 4.56789012345678901E-3
    original_line = _build_xrotation_line(angle = angle_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi2_rs1"] == pytest.approx(angle_precise, rel = 1E-15), (
        "Writer roundtrip should preserve XRotation angle at full double precision. "
        f"Original: {angle_precise!r}, reloaded env var: {env['chi2_rs1']!r}.")


################################################################################
# SRotation (CHI3)
################################################################################
########################################
# Basic Serialisation
########################################
def test_refshift_writer_srotation_reloads_as_xsuite_srotation(tmp_path):
    """
    A written SRotation element should reload as an xt.SRotation in a clean
    Xsuite environment. SRotation maps to SAD CHI3; the optics variable is
    chi3_{name}.
    """
    original_line = _build_srotation_line(angle = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["rs1"], xt.SRotation), (
        "Written SRotation element 'rs1' should reload as xt.SRotation. "
        f"Got: {type(reloaded_line['rs1']).__name__}.")


########################################
# angle Field
########################################
def test_refshift_writer_srotation_preserves_positive_angle(tmp_path):
    """
    A positive SRotation angle should be preserved through a write and reload
    cycle. Angle is written as optics variable chi3_rs1.
    """
    original_line = _build_srotation_line(angle = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].angle == pytest.approx(0.05), (
        "Writer roundtrip should preserve positive SRotation angle. "
        f"Original: 0.05, reloaded: {reloaded_line['rs1'].angle}.")


def test_refshift_writer_srotation_preserves_negative_angle(tmp_path):
    """
    A negative SRotation angle should be preserved through a write and reload
    cycle.
    """
    original_line = _build_srotation_line(angle = -0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].angle == pytest.approx(-0.05), (
        "Writer roundtrip should preserve negative SRotation angle. "
        f"Original: -0.05, reloaded: {reloaded_line['rs1'].angle}.")


def test_refshift_writer_srotation_angle_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the SRotation angle should be accessible as
    named optics variable chi3_rs1 in the Xsuite environment.
    """
    original_line = _build_srotation_line(angle = 0.05)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi3_rs1"] == pytest.approx(0.05), (
        "Optics variable 'chi3_rs1' should exist in the environment after reload "
        "and equal the original SRotation angle. "
        f"Got: {env['chi3_rs1']}.")


def test_refshift_writer_srotation_angle_is_tunable_via_optics_variable(tmp_path):
    """
    The chi3_rs1 optics variable should remain live after reload: modifying it
    should immediately update the SRotation angle in the line.
    """
    original_line = _build_srotation_line(angle = 0.05)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["chi3_rs1"] = 0.10

    assert reloaded_line["rs1"].angle == pytest.approx(0.10), (
        "Modifying optics variable 'chi3_rs1' should update the SRotation angle. "
        f"Got: {reloaded_line['rs1'].angle}.")


def test_refshift_writer_srotation_angle_preserved_at_full_double_precision(tmp_path):
    """
    An SRotation angle with many significant digits should survive a write and
    reload cycle at full double precision.
    """
    angle_precise = 4.56789012345678901E-2
    original_line = _build_srotation_line(angle = angle_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi3_rs1"] == pytest.approx(angle_precise, rel = 1E-15), (
        "Writer roundtrip should preserve SRotation angle at full double precision. "
        f"Original: {angle_precise!r}, reloaded env var: {env['chi3_rs1']!r}.")


################################################################################
# Mixed Reference Shift Types
################################################################################
########################################
# Multiple Types in One Line
########################################
def test_refshift_writer_preserves_all_five_types_in_one_line(tmp_path):
    """
    A line containing all five reference shift element types simultaneously
    should preserve each element's parameter independently through a write and
    reload cycle. Each type writes to its own distinct optics variable namespace.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.XYShift(dx = 1.0E-3, dy = -2.0E-3),
            xt.TimeDelay(shift_zeta = 0.5E-3),
            xt.YRotation(angle = 3.0E-3),
            xt.XRotation(angle = -4.0E-3),
            xt.SRotation(angle = 0.05),
            xt.Marker(),
        ],
        element_names = ["start", "rsxy", "rsdz", "rsyr", "rsxr", "rssr", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    assert reloaded_line["rsxy"].dx    == pytest.approx( 1.0E-3), (
        f"Writer roundtrip should preserve XYShift dx. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['rsxy'].dx}.")
    assert reloaded_line["rsxy"].dy    == pytest.approx(-2.0E-3), (
        f"Writer roundtrip should preserve XYShift dy. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['rsxy'].dy}.")
    assert reloaded_line["rsdz"].shift_zeta == pytest.approx( 0.5E-3), (
        f"Writer roundtrip should preserve TimeDelay shift_zeta. "
        f"Original: 0.5E-3, reloaded: {reloaded_line['rsdz'].shift_zeta}.")
    assert reloaded_line["rsyr"].angle == pytest.approx( 3.0E-3), (
        f"Writer roundtrip should preserve YRotation angle. "
        f"Original: 3.0E-3, reloaded: {reloaded_line['rsyr'].angle}.")
    assert reloaded_line["rsxr"].angle == pytest.approx(-4.0E-3), (
        f"Writer roundtrip should preserve XRotation angle. "
        f"Original: -4.0E-3, reloaded: {reloaded_line['rsxr'].angle}.")
    assert reloaded_line["rssr"].angle == pytest.approx( 0.05),   (
        f"Writer roundtrip should preserve SRotation angle. "
        f"Original: 0.05, reloaded: {reloaded_line['rssr'].angle}.")

    assert env["dx_rsxy"]    == pytest.approx( 1.0E-3), (
        "Optics variable 'dx_rsxy' should be accessible and correct.")
    assert env["dy_rsxy"]    == pytest.approx(-2.0E-3), (
        "Optics variable 'dy_rsxy' should be accessible and correct.")
    assert env["dz_rsdz"]    == pytest.approx( 0.5E-3), (
        "Optics variable 'dz_rsdz' should be accessible and correct.")
    assert env["chi1_rsyr"]  == pytest.approx( 3.0E-3), (
        "Optics variable 'chi1_rsyr' should be accessible and correct.")
    assert env["chi2_rsxr"]  == pytest.approx(-4.0E-3), (
        "Optics variable 'chi2_rsxr' should be accessible and correct.")
    assert env["chi3_rssr"]  == pytest.approx( 0.05),   (
        "Optics variable 'chi3_rssr' should be accessible and correct.")
