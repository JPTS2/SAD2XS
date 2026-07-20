"""
================================================================================
Tests for reference shift element writer serialisation
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

    All five reference shift element types write their parameters as live optics
    expression variables. The variable name is derived from the element name:

        Translation 'rs1' -> dx_rs1, dy_rs1
        TimeDelay 'rs1' -> dz_rs1
        Rotation 'rs1' (rot_y_rad) -> chi1_rs1  (SAD CHI1)
        Rotation 'rs1' (rot_x_rad) -> chi2_rs1  (SAD CHI2)
        Rotation 'rs1' (rot_s_rad) -> chi3_rs1  (SAD CHI3)

    Zero-valued fields are not written to the optics file; the lattice file
    always references the variable, and env.vars.default_to_zero = True returns
    0 for any undefined variable on reload.
    """
    return _shared_write_and_load(line, tmp_path, output_header = "Reference shift writer test")


def _writer_roundtrip(line, tmp_path):
    """
    Write and reload a line. Returns the reloaded line only.
    """
    _, reloaded_line = _write_and_load(line, tmp_path)
    return reloaded_line


def _build_translation_line(shift_x = 0.0, shift_y = 0.0):
    """
    Build a minimal single-Translation Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Translation(shift_x = shift_x, shift_y = shift_y), xt.Marker()],
        element_names = ["start", "rs1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_timedelay_line(shift_zeta = 0.0):
    """
    Build a minimal single-TimeDelay Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.TimeDelay(shift_zeta = shift_zeta), xt.Marker()],
        element_names = ["start", "rs1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_rotation_chi1_line(rot_y_rad = 0.0):
    """
    Build a minimal single-Rotation (chi1/rot_y_rad) Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Rotation(rot_y_rad = rot_y_rad), xt.Marker()],
        element_names = ["start", "rs1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_rotation_chi2_line(rot_x_rad = 0.0):
    """
    Build a minimal single-Rotation (chi2/rot_x_rad) Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Rotation(rot_x_rad = rot_x_rad), xt.Marker()],
        element_names = ["start", "rs1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_rotation_chi3_line(rot_s_rad = 0.0):
    """
    Build a minimal single-Rotation (chi3/rot_s_rad) Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Rotation(rot_s_rad = rot_s_rad), xt.Marker()],
        element_names = ["start", "rs1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


################################################################################
# Translation
################################################################################
########################################
# Basic Serialisation
########################################
def test_refshift_writer_translation_reloads_as_xsuite_translation(tmp_path):
    """
    A written Translation element should reload as an xt.Translation in a clean
    Xsuite environment.
    """
    original_line = _build_translation_line(shift_x = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["rs1"], xt.Translation), (
        "Written Translation element 'rs1' should reload as xt.Translation. "
        f"Got: {type(reloaded_line['rs1']).__name__}.")


def test_refshift_writer_translation_preserves_element_name(tmp_path):
    """
    A written Translation element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_translation_line(shift_x = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "rs1" in list(reloaded_line.element_names), (
        "Reloaded line should contain Translation element 'rs1'. "
        f"Got: {list(reloaded_line.element_names)}.")


########################################
# shift_x Field
########################################
def test_refshift_writer_translation_preserves_positive_shift_x(tmp_path):
    """
    A positive transverse shift_x should be preserved through a write and
    reload cycle. shift_x is written as optics variable dx_rs1.
    """
    original_line = _build_translation_line(shift_x = 1.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].shift_x == pytest.approx(1.5E-3), (
        "Writer roundtrip should preserve positive Translation shift_x. "
        f"Original: 1.5E-3, reloaded: {reloaded_line['rs1'].shift_x}.")


def test_refshift_writer_translation_preserves_negative_shift_x(tmp_path):
    """
    A negative transverse shift_x should be preserved through a write and
    reload cycle.
    """
    original_line = _build_translation_line(shift_x = -1.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].shift_x == pytest.approx(-1.5E-3), (
        "Writer roundtrip should preserve negative Translation shift_x. "
        f"Original: -1.5E-3, reloaded: {reloaded_line['rs1'].shift_x}.")


def test_refshift_writer_translation_shift_x_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the Translation shift_x field should be
    accessible as named optics variable dx_rs1 in the Xsuite environment.
    """
    original_line = _build_translation_line(shift_x = 1.5E-3)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["dx_rs1"] == pytest.approx(1.5E-3), (
        "Optics variable 'dx_rs1' should exist in the environment after reload "
        "and equal the original shift_x. "
        f"Got: {env['dx_rs1']}.")


def test_refshift_writer_translation_shift_x_is_tunable_via_optics_variable(tmp_path):
    """
    The dx_rs1 optics variable should remain live after reload: modifying it
    should immediately update the Translation shift_x in the line.
    """
    original_line = _build_translation_line(shift_x = 1.5E-3)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["dx_rs1"] = 3.0E-3

    assert reloaded_line["rs1"].shift_x == pytest.approx(3.0E-3), (
        "Modifying optics variable 'dx_rs1' should update the Translation shift_x. "
        f"Got: {reloaded_line['rs1'].shift_x}.")


########################################
# shift_y Field
########################################
def test_refshift_writer_translation_preserves_positive_shift_y(tmp_path):
    """
    A positive transverse shift_y should be preserved through a write and
    reload cycle. shift_y is written as optics variable dy_rs1.
    """
    original_line = _build_translation_line(shift_y = 2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].shift_y == pytest.approx(2.0E-3), (
        "Writer roundtrip should preserve positive Translation shift_y. "
        f"Original: 2.0E-3, reloaded: {reloaded_line['rs1'].shift_y}.")


def test_refshift_writer_translation_preserves_negative_shift_y(tmp_path):
    """
    A negative transverse shift_y should be preserved through a write and
    reload cycle.
    """
    original_line = _build_translation_line(shift_y = -2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve negative Translation shift_y. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['rs1'].shift_y}.")


def test_refshift_writer_translation_shift_y_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the Translation shift_y field should be
    accessible as named optics variable dy_rs1 in the Xsuite environment.
    """
    original_line = _build_translation_line(shift_y = 2.0E-3)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["dy_rs1"] == pytest.approx(2.0E-3), (
        "Optics variable 'dy_rs1' should exist in the environment after reload "
        "and equal the original shift_y. "
        f"Got: {env['dy_rs1']}.")


def test_refshift_writer_translation_shift_y_is_tunable_via_optics_variable(tmp_path):
    """
    The dy_rs1 optics variable should remain live after reload: modifying it
    should immediately update the Translation shift_y in the line.
    """
    original_line = _build_translation_line(shift_y = 2.0E-3)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["dy_rs1"] = 4.0E-3

    assert reloaded_line["rs1"].shift_y == pytest.approx(4.0E-3), (
        "Modifying optics variable 'dy_rs1' should update the Translation shift_y. "
        f"Got: {reloaded_line['rs1'].shift_y}.")


########################################
# shift_x and shift_y Simultaneously
########################################
def test_refshift_writer_translation_preserves_shift_x_and_shift_y_simultaneously(tmp_path):
    """
    A Translation with both shift_x and shift_y non-zero should preserve both
    through a write and reload cycle. Each field has its own independent optics
    variable.
    """
    original_line = _build_translation_line(shift_x = 1.5E-3, shift_y = -2.0E-3)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].shift_x == pytest.approx(1.5E-3), (
        "Writer roundtrip should preserve shift_x when shift_y is also non-zero. "
        f"Original: 1.5E-3, reloaded: {reloaded_line['rs1'].shift_x}.")
    assert reloaded_line["rs1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve shift_y when shift_x is also non-zero. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['rs1'].shift_y}.")
    assert env["dx_rs1"] == pytest.approx(1.5E-3), (
        "Optics variable 'dx_rs1' should be accessible when shift_y is also set. "
        f"Got: {env['dx_rs1']}.")
    assert env["dy_rs1"] == pytest.approx(-2.0E-3), (
        "Optics variable 'dy_rs1' should be accessible when shift_x is also set. "
        f"Got: {env['dy_rs1']}.")


########################################
# Zero Value (not written to optics file)
########################################
def test_refshift_writer_translation_preserves_zero_shift_x(tmp_path):
    """
    A Translation with shift_x=0 should survive a write and reload cycle with
    shift_x remaining zero. Zero shift_x is not written to the optics file; the
    lattice file references 'dx_rs1' and env.vars.default_to_zero = True returns
    0 for the undefined variable.
    """
    original_line = _build_translation_line(shift_x = 0.0, shift_y = 2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].shift_x == pytest.approx(0.0), (
        "Writer roundtrip should preserve zero Translation shift_x (handled by "
        "default_to_zero). "
        f"Reloaded: {reloaded_line['rs1'].shift_x}.")


########################################
# Precision
########################################
def test_refshift_writer_translation_shift_x_preserved_at_full_double_precision(tmp_path):
    """
    A Translation shift_x with many significant digits should survive a write
    and reload cycle at full double precision. The optics file writes dx_rs1 to
    24 decimal places.
    """
    dx_precise = 1.23456789012345678E-4
    original_line = _build_translation_line(shift_x = dx_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["dx_rs1"] == pytest.approx(dx_precise, rel = 1E-15), (
        "Writer roundtrip should preserve Translation shift_x at full double "
        "precision. "
        f"Original: {dx_precise!r}, reloaded env var: {env['dx_rs1']!r}.")


########################################
# Multiple Translations
########################################
def test_refshift_writer_preserves_multiple_translations_independently(tmp_path):
    """
    Multiple Translation elements with different shift_x/shift_y values should
    each preserve their individual values through a single write and reload
    cycle. Each element writes its own independent optics variables.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Translation(shift_x = +1.0E-3, shift_y =  0.0),
            xt.Translation(shift_x =  0.0,    shift_y = -2.0E-3),
            xt.Translation(shift_x = +0.5E-3, shift_y = +1.5E-3),
            xt.Marker(),
        ],
        element_names = ["start", "rsa", "rsb", "rsc", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    assert reloaded_line["rsa"].shift_x == pytest.approx(+1.0E-3), (
        "Writer roundtrip should preserve shift_x for 'rsa'. "
        f"Original: +1.0E-3, reloaded: {reloaded_line['rsa'].shift_x}.")
    assert reloaded_line["rsb"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve shift_y for 'rsb'. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['rsb'].shift_y}.")
    assert reloaded_line["rsc"].shift_x == pytest.approx(+0.5E-3), (
        "Writer roundtrip should preserve shift_x for 'rsc'. "
        f"Original: +0.5E-3, reloaded: {reloaded_line['rsc'].shift_x}.")
    assert reloaded_line["rsc"].shift_y == pytest.approx(+1.5E-3), (
        "Writer roundtrip should preserve shift_y for 'rsc'. "
        f"Original: +1.5E-3, reloaded: {reloaded_line['rsc'].shift_y}.")

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
# Rotation CHI1 (rot_y_rad)
################################################################################
########################################
# Basic Serialisation
########################################
def test_refshift_writer_rotation_chi1_reloads_as_xsuite_rotation(tmp_path):
    """
    A written Rotation element with rot_y_rad should reload as an xt.Rotation
    in a clean Xsuite environment. rot_y_rad maps to SAD CHI1; the optics
    variable is chi1_{name}.
    """
    original_line = _build_rotation_chi1_line(rot_y_rad = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["rs1"], xt.Rotation), (
        "Written Rotation (chi1) element 'rs1' should reload as xt.Rotation. "
        f"Got: {type(reloaded_line['rs1']).__name__}.")


########################################
# rot_y_rad Field
########################################
def test_refshift_writer_rotation_chi1_preserves_positive_rot_y_rad(tmp_path):
    """
    A positive rot_y_rad should be preserved through a write and reload cycle.
    rot_y_rad is written as optics variable chi1_rs1.
    """
    original_line = _build_rotation_chi1_line(rot_y_rad = 5.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].rot_y_rad == pytest.approx(5.0E-3), (
        "Writer roundtrip should preserve positive Rotation rot_y_rad. "
        f"Original: 5.0E-3, reloaded: {reloaded_line['rs1'].rot_y_rad}.")


def test_refshift_writer_rotation_chi1_preserves_negative_rot_y_rad(tmp_path):
    """
    A negative rot_y_rad should be preserved through a write and reload cycle.
    """
    original_line = _build_rotation_chi1_line(rot_y_rad = -5.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].rot_y_rad == pytest.approx(-5.0E-3), (
        "Writer roundtrip should preserve negative Rotation rot_y_rad. "
        f"Original: -5.0E-3, reloaded: {reloaded_line['rs1'].rot_y_rad}.")


def test_refshift_writer_rotation_chi1_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, rot_y_rad should be accessible as named optics
    variable chi1_rs1 in the Xsuite environment.
    """
    original_line = _build_rotation_chi1_line(rot_y_rad = 5.0E-3)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi1_rs1"] == pytest.approx(5.0E-3), (
        "Optics variable 'chi1_rs1' should exist in the environment after reload "
        "and equal the original rot_y_rad. "
        f"Got: {env['chi1_rs1']}.")


def test_refshift_writer_rotation_chi1_is_tunable_via_optics_variable(tmp_path):
    """
    The chi1_rs1 optics variable should remain live after reload: modifying it
    should immediately update the Rotation rot_y_rad in the line.
    """
    original_line = _build_rotation_chi1_line(rot_y_rad = 5.0E-3)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["chi1_rs1"] = 10.0E-3

    assert reloaded_line["rs1"].rot_y_rad == pytest.approx(10.0E-3), (
        "Modifying optics variable 'chi1_rs1' should update the Rotation rot_y_rad. "
        f"Got: {reloaded_line['rs1'].rot_y_rad}.")


def test_refshift_writer_rotation_chi1_preserved_at_full_double_precision(tmp_path):
    """
    A Rotation rot_y_rad with many significant digits should survive a write and
    reload cycle at full double precision.
    """
    value_precise = 4.56789012345678901E-3
    original_line = _build_rotation_chi1_line(rot_y_rad = value_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi1_rs1"] == pytest.approx(value_precise, rel = 1E-15), (
        "Writer roundtrip should preserve Rotation rot_y_rad at full double precision. "
        f"Original: {value_precise!r}, reloaded env var: {env['chi1_rs1']!r}.")


################################################################################
# Rotation CHI2 (rot_x_rad)
################################################################################
########################################
# Basic Serialisation
########################################
def test_refshift_writer_rotation_chi2_reloads_as_xsuite_rotation(tmp_path):
    """
    A written Rotation element with rot_x_rad should reload as an xt.Rotation
    in a clean Xsuite environment. rot_x_rad maps to SAD CHI2; the optics
    variable is chi2_{name}.
    """
    original_line = _build_rotation_chi2_line(rot_x_rad = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["rs1"], xt.Rotation), (
        "Written Rotation (chi2) element 'rs1' should reload as xt.Rotation. "
        f"Got: {type(reloaded_line['rs1']).__name__}.")


########################################
# rot_x_rad Field
########################################
def test_refshift_writer_rotation_chi2_preserves_positive_rot_x_rad(tmp_path):
    """
    A positive rot_x_rad should be preserved through a write and reload cycle.
    rot_x_rad is written as optics variable chi2_rs1.
    """
    original_line = _build_rotation_chi2_line(rot_x_rad = 5.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].rot_x_rad == pytest.approx(5.0E-3), (
        "Writer roundtrip should preserve positive Rotation rot_x_rad. "
        f"Original: 5.0E-3, reloaded: {reloaded_line['rs1'].rot_x_rad}.")


def test_refshift_writer_rotation_chi2_preserves_negative_rot_x_rad(tmp_path):
    """
    A negative rot_x_rad should be preserved through a write and reload cycle.
    """
    original_line = _build_rotation_chi2_line(rot_x_rad = -5.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].rot_x_rad == pytest.approx(-5.0E-3), (
        "Writer roundtrip should preserve negative Rotation rot_x_rad. "
        f"Original: -5.0E-3, reloaded: {reloaded_line['rs1'].rot_x_rad}.")


def test_refshift_writer_rotation_chi2_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, rot_x_rad should be accessible as named optics
    variable chi2_rs1 in the Xsuite environment.
    """
    original_line = _build_rotation_chi2_line(rot_x_rad = 5.0E-3)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi2_rs1"] == pytest.approx(5.0E-3), (
        "Optics variable 'chi2_rs1' should exist in the environment after reload "
        "and equal the original rot_x_rad. "
        f"Got: {env['chi2_rs1']}.")


def test_refshift_writer_rotation_chi2_is_tunable_via_optics_variable(tmp_path):
    """
    The chi2_rs1 optics variable should remain live after reload: modifying it
    should immediately update the Rotation rot_x_rad in the line.
    """
    original_line = _build_rotation_chi2_line(rot_x_rad = 5.0E-3)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["chi2_rs1"] = 10.0E-3

    assert reloaded_line["rs1"].rot_x_rad == pytest.approx(10.0E-3), (
        "Modifying optics variable 'chi2_rs1' should update the Rotation rot_x_rad. "
        f"Got: {reloaded_line['rs1'].rot_x_rad}.")


def test_refshift_writer_rotation_chi2_preserved_at_full_double_precision(tmp_path):
    """
    A Rotation rot_x_rad with many significant digits should survive a write and
    reload cycle at full double precision.
    """
    value_precise = 4.56789012345678901E-3
    original_line = _build_rotation_chi2_line(rot_x_rad = value_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi2_rs1"] == pytest.approx(value_precise, rel = 1E-15), (
        "Writer roundtrip should preserve Rotation rot_x_rad at full double precision. "
        f"Original: {value_precise!r}, reloaded env var: {env['chi2_rs1']!r}.")


################################################################################
# Rotation CHI3 (rot_s_rad)
################################################################################
########################################
# Basic Serialisation
########################################
def test_refshift_writer_rotation_chi3_reloads_as_xsuite_rotation(tmp_path):
    """
    A written Rotation element with rot_s_rad should reload as an xt.Rotation
    in a clean Xsuite environment. rot_s_rad maps to SAD CHI3; the optics
    variable is chi3_{name}.
    """
    original_line = _build_rotation_chi3_line(rot_s_rad = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["rs1"], xt.Rotation), (
        "Written Rotation (chi3) element 'rs1' should reload as xt.Rotation. "
        f"Got: {type(reloaded_line['rs1']).__name__}.")


########################################
# rot_s_rad Field
########################################
def test_refshift_writer_rotation_chi3_preserves_positive_rot_s_rad(tmp_path):
    """
    A positive rot_s_rad should be preserved through a write and reload cycle.
    rot_s_rad is written as optics variable chi3_rs1.
    """
    original_line = _build_rotation_chi3_line(rot_s_rad = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve positive Rotation rot_s_rad. "
        f"Original: 0.05, reloaded: {reloaded_line['rs1'].rot_s_rad}.")


def test_refshift_writer_rotation_chi3_preserves_negative_rot_s_rad(tmp_path):
    """
    A negative rot_s_rad should be preserved through a write and reload cycle.
    """
    original_line = _build_rotation_chi3_line(rot_s_rad = -0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["rs1"].rot_s_rad == pytest.approx(-0.05), (
        "Writer roundtrip should preserve negative Rotation rot_s_rad. "
        f"Original: -0.05, reloaded: {reloaded_line['rs1'].rot_s_rad}.")


def test_refshift_writer_rotation_chi3_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, rot_s_rad should be accessible as named optics
    variable chi3_rs1 in the Xsuite environment.
    """
    original_line = _build_rotation_chi3_line(rot_s_rad = 0.05)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi3_rs1"] == pytest.approx(0.05), (
        "Optics variable 'chi3_rs1' should exist in the environment after reload "
        "and equal the original rot_s_rad. "
        f"Got: {env['chi3_rs1']}.")


def test_refshift_writer_rotation_chi3_is_tunable_via_optics_variable(tmp_path):
    """
    The chi3_rs1 optics variable should remain live after reload: modifying it
    should immediately update the Rotation rot_s_rad in the line.
    """
    original_line = _build_rotation_chi3_line(rot_s_rad = 0.05)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["chi3_rs1"] = 0.10

    assert reloaded_line["rs1"].rot_s_rad == pytest.approx(0.10), (
        "Modifying optics variable 'chi3_rs1' should update the Rotation rot_s_rad. "
        f"Got: {reloaded_line['rs1'].rot_s_rad}.")


def test_refshift_writer_rotation_chi3_preserved_at_full_double_precision(tmp_path):
    """
    A Rotation rot_s_rad with many significant digits should survive a write and
    reload cycle at full double precision.
    """
    value_precise = 4.56789012345678901E-2
    original_line = _build_rotation_chi3_line(rot_s_rad = value_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["chi3_rs1"] == pytest.approx(value_precise, rel = 1E-15), (
        "Writer roundtrip should preserve Rotation rot_s_rad at full double precision. "
        f"Original: {value_precise!r}, reloaded env var: {env['chi3_rs1']!r}.")


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
            xt.Translation(shift_x = 1.0E-3, shift_y = -2.0E-3),
            xt.TimeDelay(shift_zeta = 0.5E-3),
            xt.Rotation(rot_y_rad = 3.0E-3),
            xt.Rotation(rot_x_rad = -4.0E-3),
            xt.Rotation(rot_s_rad = 0.05),
            xt.Marker(),
        ],
        element_names = ["start", "rsxy", "rsdz", "rsyr", "rsxr", "rssr", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    assert reloaded_line["rsxy"].shift_x == pytest.approx( 1.0E-3), (
        f"Writer roundtrip should preserve Translation shift_x. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['rsxy'].shift_x}.")
    assert reloaded_line["rsxy"].shift_y == pytest.approx(-2.0E-3), (
        f"Writer roundtrip should preserve Translation shift_y. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['rsxy'].shift_y}.")
    assert reloaded_line["rsdz"].shift_zeta == pytest.approx( 0.5E-3), (
        f"Writer roundtrip should preserve TimeDelay shift_zeta. "
        f"Original: 0.5E-3, reloaded: {reloaded_line['rsdz'].shift_zeta}.")
    assert reloaded_line["rsyr"].rot_y_rad == pytest.approx( 3.0E-3), (
        f"Writer roundtrip should preserve Rotation rot_y_rad (chi1). "
        f"Original: 3.0E-3, reloaded: {reloaded_line['rsyr'].rot_y_rad}.")
    assert reloaded_line["rsxr"].rot_x_rad == pytest.approx(-4.0E-3), (
        f"Writer roundtrip should preserve Rotation rot_x_rad (chi2). "
        f"Original: -4.0E-3, reloaded: {reloaded_line['rsxr'].rot_x_rad}.")
    assert reloaded_line["rssr"].rot_s_rad == pytest.approx( 0.05),   (
        f"Writer roundtrip should preserve Rotation rot_s_rad (chi3). "
        f"Original: 0.05, reloaded: {reloaded_line['rssr'].rot_s_rad}.")

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
