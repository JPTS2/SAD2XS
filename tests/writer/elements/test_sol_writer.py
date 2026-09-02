"""
================================================================================
Tests for solenoid element writer serialisation
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

from sad2xs.config import Config
from tests.support.writer_helpers import write_and_load as _shared_write_and_load

################################################################################
# Helpers
################################################################################
def _write_and_load(line, tmp_path):
    """
    Write a line using the public SAD2XS writer entry points, reload it in a
    clean Xsuite environment, and return the environment and reloaded line.

    The environment is returned so tests can verify that solenoid ks is NOT
    written as an optics variable — unlike quadrupole k1, solenoid ks is baked
    into the lattice file as a literal number. There is also no solenoid optics
    file function; the solenoid writer is lattice-file only.
    """
    return _shared_write_and_load(line, tmp_path, output_header = "Solenoid writer test")


def _writer_roundtrip(line, tmp_path):
    """
    Write and reload a line. Returns the reloaded line only.
    """
    _, reloaded_line = _write_and_load(line, tmp_path)
    return reloaded_line


def _build_sol_line(
        length    = 0.5,
        ks        = 0.0,
        knl       = None,
        ksl       = None,
        shift_x   = 0.0,
        shift_y   = 0.0,
        rot_s_rad = 0.0,
        x0        = 0.0,
        y0        = 0.0):
    """
    Build a minimal single-solenoid Xsuite line with a reference particle.
    Keyword arguments map directly to xt.UniformSolenoid fields.
    """
    sol_kwargs = dict(
        length    = length,
        ks        = ks,
        shift_x   = shift_x,
        shift_y   = shift_y,
        rot_s_rad = rot_s_rad,
        x0        = x0,
        y0        = y0)

    if knl is not None:
        sol_kwargs["knl"] = knl
    if ksl is not None:
        sol_kwargs["ksl"] = ksl

    line = xt.Line(
        elements      = [xt.Marker(), xt.UniformSolenoid(**sol_kwargs), xt.Marker()],
        element_names = ["start", "sol1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


################################################################################
# Basic Serialisation
################################################################################
########################################
# Element Type and Name
########################################
def test_sol_writer_reloads_as_xsuite_uniform_solenoid(tmp_path):
    """
    A written solenoid element should reload as an xt.UniformSolenoid in a
    clean Xsuite environment.
    """
    original_line = _build_sol_line(ks = 0.1)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["sol1"], xt.UniformSolenoid), (
        "Written solenoid element `sol1` should reload as xt.UniformSolenoid. "
        f"""Got: {type(reloaded_line["sol1"]).__name__}.""")


def test_sol_writer_applies_configured_integrator(tmp_path):
    """Generated lattices must retain the production solenoid integration."""
    reloaded = _writer_roundtrip(_build_sol_line(knl = [0.0, 0.01]), tmp_path)
    config   = Config(_verbose = False)

    assert reloaded["sol1"].integrator == config.INTEGRATOR_SOL
    assert reloaded["sol1"].num_multipole_kicks == (
        config.N_INTEGRATOR_KICKS_SOL)


def test_sol_writer_preserves_element_name(tmp_path):
    """
    A written solenoid element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_sol_line(ks = 0.1)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "sol1" in list(reloaded_line.element_names), (
        "Reloaded line should contain solenoid element `sol1`. "
        f"Got: {list(reloaded_line.element_names)}.")


########################################
# Element Order
########################################
def test_sol_writer_preserves_element_order(tmp_path):
    """
    Multiple solenoid and marker elements should appear in the same order after
    a write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.UniformSolenoid(length = 0.5, ks = 0.1),
            xt.Marker(),
            xt.UniformSolenoid(length = 0.5, ks = -0.1),
            xt.Marker(),
        ],
        element_names = ["start", "sola", "mid", "solb", "end"])

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
def test_sol_writer_preserves_length(tmp_path):
    """
    A solenoid element's length should be preserved through a write and reload
    cycle.
    """
    original_line = _build_sol_line(length = 0.75, ks = 0.1)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].length == pytest.approx(0.75), (
        "Writer roundtrip should preserve solenoid length. "
        f"""Original: 0.75, reloaded: {reloaded_line["sol1"].length}.""")


########################################
# Solenoid Strength (ks) as Literal Number
########################################
def test_sol_writer_preserves_positive_ks(tmp_path):
    """
    A positive solenoid strength ks should be preserved through a write and
    reload cycle. Unlike quadrupole k1, ks is written as a bare literal number
    in the lattice file (not a string expression, not an optics variable).
    """
    original_line = _build_sol_line(ks = 0.1)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].ks == pytest.approx(0.1), (
        "Writer roundtrip should preserve positive solenoid ks. "
        f"""Original: 0.1, reloaded: {reloaded_line["sol1"].ks}.""")


def test_sol_writer_preserves_negative_ks(tmp_path):
    """
    A negative solenoid strength ks should be preserved through a write and
    reload cycle.
    """
    original_line = _build_sol_line(ks = -0.1)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].ks == pytest.approx(-0.1), (
        "Writer roundtrip should preserve negative solenoid ks. "
        f"""Original: -0.1, reloaded: {reloaded_line["sol1"].ks}.""")


def test_sol_writer_preserves_zero_ks(tmp_path):
    """
    A zero-strength solenoid should survive a write and reload cycle.
    """
    original_line = _build_sol_line(ks = 0.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].ks == pytest.approx(0.0), (
        "Writer roundtrip should preserve zero solenoid ks. "
        f"""Reloaded: {reloaded_line["sol1"].ks}.""")


def test_sol_writer_preserves_ks_at_full_double_precision(tmp_path):
    """
    A solenoid ks with many significant digits should survive a write and
    reload cycle at full double precision.
    """
    ks_precise = 0.12345678901234567
    original_line = _build_sol_line(ks = ks_precise)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].ks == pytest.approx(ks_precise, rel = 1E-15), (
        "Writer roundtrip should preserve solenoid ks at full double precision. "
        f"""Original: {ks_precise!r}, reloaded: {reloaded_line["sol1"].ks!r}.""")


########################################
# ks Not Written as an Optics Variable
########################################
def test_sol_writer_ks_is_not_written_as_optics_variable(tmp_path):
    """
    Unlike quadrupole k1, solenoid ks is written as a bare literal number in
    the lattice file, not as a deferred optics expression. There is no solenoid
    optics file function; the Xsuite environment should have no `ks_sol1`
    variable after reload.

    This is a key distinction from the quad/sext/oct writers where strengths
    are tunable via named optics variables.
    """
    original_line = _build_sol_line(ks = 0.1)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    with pytest.raises(KeyError):
        _ = env["ks_sol1"]


########################################
# knl and ksl Written for Solenoids
########################################
def test_sol_writer_preserves_knl_component(tmp_path):
    """
    A solenoid with a combined multipole knl component should preserve it
    through a write and reload cycle. Unlike quad/sext/oct writers which drop
    knl, the solenoid writer writes knl as a literal array.
    """
    original_line = _build_sol_line(ks = 0.1, knl = [0.0, 5.0E-3])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["sol1"].knl)[1] == pytest.approx(5.0E-3), (
        "Writer roundtrip should preserve solenoid knl[1]. "
        f"""Original: 5.0E-3, reloaded: {np.asarray(reloaded_line["sol1"].knl)[1]}.""")


def test_sol_writer_preserves_ksl_component(tmp_path):
    """
    A solenoid with a combined multipole ksl component should preserve it
    through a write and reload cycle. The solenoid writer writes ksl as a
    literal array.
    """
    original_line = _build_sol_line(ks = 0.1, ksl = [0.0, -3.0E-3])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["sol1"].ksl)[1] == pytest.approx(-3.0E-3), (
        "Writer roundtrip should preserve solenoid ksl[1]. "
        f"""Original: -3.0E-3, reloaded: {np.asarray(reloaded_line["sol1"].ksl)[1]}.""")


def test_sol_writer_preserves_knl_and_ksl_simultaneously(tmp_path):
    """
    A solenoid with both knl and ksl components should preserve both through a
    write and reload cycle.
    """
    original_line = _build_sol_line(
        ks  = 0.1,
        knl = [0.0, 5.0E-3],
        ksl = [0.0, -3.0E-3])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["sol1"].knl)[1] == pytest.approx(5.0E-3), (
        "Writer roundtrip should preserve solenoid knl[1] when ksl is also set. "
        f"""Original: 5.0E-3, reloaded: {np.asarray(reloaded_line["sol1"].knl)[1]}.""")
    assert np.asarray(reloaded_line["sol1"].ksl)[1] == pytest.approx(-3.0E-3), (
        "Writer roundtrip should preserve solenoid ksl[1] when knl is also set. "
        f"""Original: -3.0E-3, reloaded: {np.asarray(reloaded_line["sol1"].ksl)[1]}.""")


################################################################################
# Misalignments via Hardcoded Values
################################################################################
########################################
# Horizontal Offset
########################################
def test_sol_writer_preserves_positive_shift_x(tmp_path):
    """
    A positive horizontal offset shift_x should be preserved through a write
    and reload cycle.
    """
    original_line = _build_sol_line(ks = 0.1, shift_x = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve positive solenoid shift_x. "
        f"""Original: 1.0E-3, reloaded: {reloaded_line["sol1"].shift_x}.""")


def test_sol_writer_preserves_negative_shift_x(tmp_path):
    """
    A negative horizontal offset shift_x should be preserved through a write
    and reload cycle.
    """
    original_line = _build_sol_line(ks = 0.1, shift_x = -1.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].shift_x == pytest.approx(-1.5E-3), (
        "Writer roundtrip should preserve negative solenoid shift_x. "
        f"""Original: -1.5E-3, reloaded: {reloaded_line["sol1"].shift_x}.""")


def test_sol_writer_preserves_shift_x_in_scientific_notation(tmp_path):
    """
    A very small shift_x value requiring scientific notation should survive a
    write and reload cycle.
    """
    original_line = _build_sol_line(ks = 0.1, shift_x = 5.67890123E-6)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].shift_x == pytest.approx(5.67890123E-6), (
        "Writer roundtrip should preserve a shift_x value in scientific notation. "
        f"""Original: 5.67890123E-6, reloaded: {reloaded_line["sol1"].shift_x}.""")


########################################
# Vertical Offset
########################################
def test_sol_writer_preserves_positive_shift_y(tmp_path):
    """
    A positive vertical offset shift_y should be preserved through a write and
    reload cycle.
    """
    original_line = _build_sol_line(ks = 0.1, shift_y = 2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].shift_y == pytest.approx(2.0E-3), (
        "Writer roundtrip should preserve positive solenoid shift_y. "
        f"""Original: 2.0E-3, reloaded: {reloaded_line["sol1"].shift_y}.""")


def test_sol_writer_preserves_negative_shift_y(tmp_path):
    """
    A negative vertical offset shift_y should be preserved through a write and
    reload cycle.
    """
    original_line = _build_sol_line(ks = 0.1, shift_y = -2.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].shift_y == pytest.approx(-2.5E-3), (
        "Writer roundtrip should preserve negative solenoid shift_y. "
        f"""Original: -2.5E-3, reloaded: {reloaded_line["sol1"].shift_y}.""")


def test_sol_writer_preserves_shift_y_in_scientific_notation(tmp_path):
    """
    A very small shift_y value requiring scientific notation should survive a
    write and reload cycle.
    """
    original_line = _build_sol_line(ks = 0.1, shift_y = -6.54321098E-7)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].shift_y == pytest.approx(-6.54321098E-7), (
        "Writer roundtrip should preserve a shift_y value in scientific notation. "
        f"""Original: -6.54321098E-7, reloaded: {reloaded_line["sol1"].shift_y}.""")


########################################
# In-Plane Rotation
########################################
def test_sol_writer_preserves_positive_rot_s_rad(tmp_path):
    """
    A positive in-plane rotation rot_s_rad should be preserved through a write
    and reload cycle.
    """
    original_line = _build_sol_line(ks = 0.1, rot_s_rad = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve positive solenoid rot_s_rad. "
        f"""Original: 0.05, reloaded: {reloaded_line["sol1"].rot_s_rad}.""")


def test_sol_writer_preserves_negative_rot_s_rad(tmp_path):
    """
    A negative in-plane rotation rot_s_rad should be preserved through a write
    and reload cycle.
    """
    original_line = _build_sol_line(ks = 0.1, rot_s_rad = -0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].rot_s_rad == pytest.approx(-0.05), (
        "Writer roundtrip should preserve negative solenoid rot_s_rad. "
        f"""Original: -0.05, reloaded: {reloaded_line["sol1"].rot_s_rad}.""")


########################################
# Position Offsets (x0, y0)
########################################
def test_sol_writer_preserves_positive_x0(tmp_path):
    """
    A positive solenoid axis offset x0 should be preserved through a write and
    reload cycle. x0 is written as a literal string expression, identical to
    the shift_x mechanism.
    """
    original_line = _build_sol_line(ks = 0.1, x0 = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].x0 == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve positive solenoid x0. "
        f"""Original: 1.0E-3, reloaded: {reloaded_line["sol1"].x0}.""")


def test_sol_writer_preserves_negative_x0(tmp_path):
    """
    A negative solenoid axis offset x0 should be preserved through a write and
    reload cycle.
    """
    original_line = _build_sol_line(ks = 0.1, x0 = -1.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].x0 == pytest.approx(-1.5E-3), (
        "Writer roundtrip should preserve negative solenoid x0. "
        f"""Original: -1.5E-3, reloaded: {reloaded_line["sol1"].x0}.""")


def test_sol_writer_preserves_positive_y0(tmp_path):
    """
    A positive solenoid axis offset y0 should be preserved through a write and
    reload cycle.
    """
    original_line = _build_sol_line(ks = 0.1, y0 = 2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].y0 == pytest.approx(2.0E-3), (
        "Writer roundtrip should preserve positive solenoid y0. "
        f"""Original: 2.0E-3, reloaded: {reloaded_line["sol1"].y0}.""")


def test_sol_writer_preserves_negative_y0(tmp_path):
    """
    A negative solenoid axis offset y0 should be preserved through a write and
    reload cycle.
    """
    original_line = _build_sol_line(ks = 0.1, y0 = -2.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].y0 == pytest.approx(-2.5E-3), (
        "Writer roundtrip should preserve negative solenoid y0. "
        f"""Original: -2.5E-3, reloaded: {reloaded_line["sol1"].y0}.""")


########################################
# Strength with All Fields
########################################
def test_sol_writer_preserves_ks_with_all_misalignments(tmp_path):
    """
    A solenoid with ks, shift_x, shift_y, rot_s_rad, x0, and y0 all non-zero
    should preserve all fields through a write and reload cycle.
    """
    original_line = _build_sol_line(
        ks        = 0.1,
        shift_x   = 1.0E-3,
        shift_y   = -2.0E-3,
        rot_s_rad = 0.05,
        x0        = 0.5E-3,
        y0        = -0.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["sol1"].ks        == pytest.approx(0.1),    (
        f"""Writer roundtrip should preserve ks. Reloaded: {reloaded_line["sol1"].ks}.""")
    assert reloaded_line["sol1"].shift_x   == pytest.approx(1.0E-3), (
        f"""Writer roundtrip should preserve shift_x. Reloaded: {reloaded_line["sol1"].shift_x}.""")
    assert reloaded_line["sol1"].shift_y   == pytest.approx(-2.0E-3),(
        f"""Writer roundtrip should preserve shift_y. Reloaded: {reloaded_line["sol1"].shift_y}.""")
    assert reloaded_line["sol1"].rot_s_rad == pytest.approx(0.05),   (
        f"""Writer roundtrip should preserve rot_s_rad. Reloaded: {reloaded_line["sol1"].rot_s_rad}.""")
    assert reloaded_line["sol1"].x0        == pytest.approx(0.5E-3), (
        f"""Writer roundtrip should preserve x0. Reloaded: {reloaded_line["sol1"].x0}.""")
    assert reloaded_line["sol1"].y0        == pytest.approx(-0.5E-3),(
        f"""Writer roundtrip should preserve y0. Reloaded: {reloaded_line["sol1"].y0}.""")


################################################################################
# Multi-Element Behaviour
################################################################################
########################################
# Multiple Solenoids
########################################
def test_sol_writer_preserves_multiple_solenoids_independently(tmp_path):
    """
    Multiple solenoid elements with different ks values should each preserve
    their individual strength through a single write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.UniformSolenoid(length = 0.5, ks = +0.1),
            xt.UniformSolenoid(length = 0.5, ks = -0.1),
            xt.UniformSolenoid(length = 0.5, ks =  0.0),
            xt.Marker(),
        ],
        element_names = ["start", "sola", "solb", "solz", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    expected = {"sola": +0.1, "solb": -0.1, "solz": 0.0}

    for name, expected_ks in expected.items():
        assert reloaded_line[name].ks == pytest.approx(expected_ks), (
            f"Writer roundtrip should preserve ks for solenoid `{name}`. "
            f"Expected: {expected_ks}, reloaded: {reloaded_line[name].ks}.")
