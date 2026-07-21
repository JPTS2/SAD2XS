"""
================================================================================
Tests for cavity element writer serialisation
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

    The environment is returned so tests can inspect and modify the optics
    variables volt_c1, freq_c1, phase_c1 written for the cavity. All three cavity
    parameters are written as live deferred expressions.

    The frequency expression uses the pattern `freq_c1 * (1 + fshift)` where
    fshift is the global frequency shift variable (default 0.0). This means
    modifying env[`fshift`] updates all cavity frequencies simultaneously.
    """
    return _shared_write_and_load(line, tmp_path, output_header = "Cavity writer test")


def _writer_roundtrip(line, tmp_path):
    """
    Write and reload a line. Returns the reloaded line only.
    """
    _, reloaded_line = _write_and_load(line, tmp_path)
    return reloaded_line


def _build_cavi_line(
        frequency = 352.2E6,
        voltage   = 6.0E6,
        phase     = np.pi,
        length    = 0.0):
    """
    Build a minimal single-cavity Xsuite line with a reference particle.
    Default values approximate a typical proton synchrotron RF system.
    frequency is in Hz, voltage is in V, phase is in radians.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Cavity(
            frequency = frequency,
            voltage   = voltage,
            phase     = phase,
            length    = length), xt.Marker()],
        element_names = ["start", "c1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


################################################################################
# Basic Serialisation
################################################################################
########################################
# Element Type and Name
########################################
def test_cavi_writer_reloads_as_xsuite_cavity(tmp_path):
    """
    A written cavity element should reload as an xt.Cavity in a clean Xsuite
    environment.
    """
    original_line = _build_cavi_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["c1"], xt.Cavity), (
        "Written cavity element `c1` should reload as xt.Cavity. "
        f"""Got: {type(reloaded_line["c1"]).__name__}.""")


def test_cavi_writer_preserves_element_name(tmp_path):
    """
    A written cavity element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_cavi_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "c1" in list(reloaded_line.element_names), (
        "Reloaded line should contain cavity element `c1`. "
        f"Got: {list(reloaded_line.element_names)}.")


########################################
# Element Order
########################################
def test_cavi_writer_preserves_element_order(tmp_path):
    """
    Multiple cavity and marker elements should appear in the same order after
    a write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Cavity(frequency = 352.2E6, voltage = 6.0E6, phase = np.pi),
            xt.Marker(),
            xt.Cavity(frequency = 704.4E6, voltage = 3.0E6, phase = np.pi),
            xt.Marker(),
        ],
        element_names = ["start", "c1", "mid", "c2", "end"])

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
def test_cavi_writer_preserves_zero_length_cavity(tmp_path):
    """
    A thin (zero-length) cavity should survive a write and reload cycle. Most
    RF cavities in accelerator models are represented as thin elements.
    """
    original_line = _build_cavi_line(length = 0.0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].length == pytest.approx(0.0), (
        "Writer roundtrip should preserve zero cavity length. "
        f"""Reloaded: {reloaded_line["c1"].length}.""")


def test_cavi_writer_preserves_nonzero_length_cavity(tmp_path):
    """
    A thick (non-zero-length) cavity should preserve its length through a write
    and reload cycle.
    """
    original_line = _build_cavi_line(length = 0.5)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].length == pytest.approx(0.5), (
        "Writer roundtrip should preserve non-zero cavity length. "
        f"""Original: 0.5, reloaded: {reloaded_line["c1"].length}.""")


########################################
# Voltage via Optics Expression
########################################
def test_cavi_writer_preserves_voltage(tmp_path):
    """
    A cavity voltage should be preserved through a write and reload cycle.
    Voltage is written as optics variable volt_c1 and referenced from the
    lattice file as a deferred expression.
    """
    original_line = _build_cavi_line(voltage = 6.0E6)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].voltage == pytest.approx(6.0E6), (
        "Writer roundtrip should preserve cavity voltage. "
        f"""Original: 6.0E6, reloaded: {reloaded_line["c1"].voltage}.""")


def test_cavi_writer_volt_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the cavity voltage should be accessible as
    named optics variable volt_c1 in the Xsuite environment.
    """
    original_line = _build_cavi_line(voltage = 6.0E6)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["volt_c1"] == pytest.approx(6.0E6), (
        "Optics variable `volt_c1` should exist in the environment after reload "
        "and equal the original voltage. "
        f"""Got: {env["volt_c1"]}.""")


def test_cavi_writer_volt_is_tunable_via_optics_variable(tmp_path):
    """
    The volt_c1 optics variable should remain live after reload: modifying it
    should immediately update the cavity voltage in the line.
    """
    original_line = _build_cavi_line(voltage = 6.0E6)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["volt_c1"] = 8.0E6

    assert reloaded_line["c1"].voltage == pytest.approx(8.0E6), (
        "Modifying optics variable `volt_c1` should update the cavity voltage. "
        f"""Got: {reloaded_line["c1"].voltage}.""")


########################################
# Frequency via Optics Expression with fshift
########################################
def test_cavi_writer_preserves_frequency(tmp_path):
    """
    A cavity frequency should be preserved through a write and reload cycle.
    Frequency is written as `freq_c1 * (1 + fshift)`. With the default
    fshift = 0, the reloaded frequency equals the original.
    """
    original_line = _build_cavi_line(frequency = 352.2E6)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].frequency == pytest.approx(352.2E6), (
        "Writer roundtrip should preserve cavity frequency (with fshift=0). "
        f"""Original: 352.2E6, reloaded: {reloaded_line["c1"].frequency}.""")


def test_cavi_writer_freq_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the base frequency should be accessible as
    named optics variable freq_c1 in the Xsuite environment. The actual cavity
    frequency evaluates as freq_c1 * (1 + fshift).
    """
    original_line = _build_cavi_line(frequency = 352.2E6)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["freq_c1"] == pytest.approx(352.2E6), (
        "Optics variable `freq_c1` should exist in the environment after reload "
        "and equal the original frequency. "
        f"""Got: {env["freq_c1"]}.""")


def test_cavi_writer_frequency_applies_fshift_factor(tmp_path):
    """
    The cavity frequency expression uses the global fshift variable:
    frequency = freq_c1 * (1 + fshift). Modifying fshift in the reloaded
    environment should update all cavity frequencies proportionally. This is
    the global tune shift mechanism for RF systems.
    """
    original_line = _build_cavi_line(frequency = 352.2E6)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["fshift"] = 1.0E-3

    assert reloaded_line["c1"].frequency == pytest.approx(352.2E6 * (1.0 + 1.0E-3)), (
        "Modifying `fshift` should update the cavity frequency via the "
        "`freq_c1 * (1 + fshift)` expression. "
        f"""Expected: {352.2E6 * 1.001}, got: {reloaded_line["c1"].frequency}.""")


########################################
# Phase via Optics Expression
########################################
def test_cavi_writer_preserves_phase(tmp_path):
    """
    A cavity phase should be preserved through a write and reload cycle. Phase
    is written as optics variable phase_c1 and referenced from the lattice file
    as a deferred expression. The value np.pi/2 is used rather than the writer's
    optics-file fallback default of np.pi, so a silent fallback would be caught.
    """
    original_line = _build_cavi_line(phase = np.pi / 2)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].phase == pytest.approx(np.pi / 2), (
        "Writer roundtrip should preserve cavity phase. "
        f"""Original: np.pi/2, reloaded: {reloaded_line["c1"].phase}.""")


def test_cavi_writer_phase_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the cavity phase should be accessible as named
    optics variable phase_c1 in the Xsuite environment. Uses np.pi/2 to
    distinguish a correctly written value from the writer's fallback default
    of np.pi.
    """
    original_line = _build_cavi_line(phase = np.pi / 2)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["phase_c1"] == pytest.approx(np.pi / 2), (
        "Optics variable `phase_c1` should exist in the environment after reload "
        "and equal the original phase. "
        f"""Got: {env["phase_c1"]}.""")


def test_cavi_writer_phase_is_tunable_via_optics_variable(tmp_path):
    """
    The phase_c1 optics variable should remain live after reload: modifying it
    should immediately update the cavity phase in the line.
    """
    original_line = _build_cavi_line(phase = np.pi)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["phase_c1"] = np.pi / 2

    assert reloaded_line["c1"].phase == pytest.approx(np.pi / 2), (
        "Modifying optics variable `phase_c1` should update the cavity phase. "
        f"""Got: {reloaded_line["c1"].phase}.""")


########################################
# All Three Optics Variables Simultaneously
########################################
def test_cavi_writer_all_three_optics_variables_accessible_simultaneously(tmp_path):
    """
    After writing and reloading, all three cavity optics variables (volt_c1,
    freq_c1, phase_c1) should be simultaneously accessible and correct. This
    confirms the complete cavity parameter set is written to the optics file.
    """
    original_line = _build_cavi_line(
        frequency = 352.2E6,
        voltage   = 6.0E6,
        phase     = np.pi)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["volt_c1"] == pytest.approx(6.0E6), (
        f"""Optics variable `volt_c1` should be accessible. Got: {env["volt_c1"]}.""")
    assert env["freq_c1"] == pytest.approx(352.2E6), (
        f"""Optics variable `freq_c1` should be accessible. Got: {env["freq_c1"]}.""")
    assert env["phase_c1"] == pytest.approx(np.pi), (
        f"""Optics variable `phase_c1` should be accessible. Got: {env["phase_c1"]}.""")

    assert reloaded_line["c1"].voltage   == pytest.approx(6.0E6),   (
        f"""Reloaded voltage should equal original. Got: {reloaded_line["c1"].voltage}.""")
    assert reloaded_line["c1"].frequency == pytest.approx(352.2E6), (
        f"""Reloaded frequency should equal original. Got: {reloaded_line["c1"].frequency}.""")
    assert reloaded_line["c1"].phase     == pytest.approx(np.pi),   (
        f"""Reloaded phase should equal original. Got: {reloaded_line["c1"].phase}.""")


########################################
# Precision
########################################
def test_cavi_writer_preserves_voltage_at_full_double_precision(tmp_path):
    """
    A cavity voltage with many significant digits should survive a write and
    reload cycle at full double precision. The optics file writes volt_c1 to
    24 decimal places.
    """
    voltage_precise = 6.123456789012345E6
    original_line = _build_cavi_line(voltage = voltage_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["volt_c1"] == pytest.approx(voltage_precise, rel = 1E-15), (
        "Writer roundtrip should preserve cavity voltage at full double precision. "
        f"""Original: {voltage_precise!r}, reloaded env var: {env["volt_c1"]!r}.""")


def test_cavi_writer_preserves_frequency_at_full_double_precision(tmp_path):
    """
    A cavity frequency with many significant digits should survive a write and
    reload cycle at full double precision.
    """
    freq_precise = 352.123456789012345E6
    original_line = _build_cavi_line(frequency = freq_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["freq_c1"] == pytest.approx(freq_precise, rel = 1E-15), (
        "Writer roundtrip should preserve cavity frequency at full double precision. "
        f"""Original: {freq_precise!r}, reloaded env var: {env["freq_c1"]!r}.""")


def test_cavi_writer_preserves_phase_at_full_double_precision(tmp_path):
    """
    A cavity phase with many significant digits should survive a write and reload
    cycle at full double precision. The optics file writes phase_c1 to 24 decimal
    places.
    """
    phase_precise = np.pi + 0.123456789012345
    original_line = _build_cavi_line(phase = phase_precise)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["phase_c1"] == pytest.approx(phase_precise, rel = 1E-15), (
        "Writer roundtrip should preserve cavity phase at full double precision. "
        f"""Original: {phase_precise!r}, reloaded env var: {env["phase_c1"]!r}.""")


################################################################################
# Multi-Element Behaviour
################################################################################
########################################
# Multiple Cavities
########################################
def test_cavi_writer_preserves_multiple_cavities_independently(tmp_path):
    """
    Multiple cavity elements with different parameters should each preserve
    their individual values independently through a single write and reload
    cycle. Each cavity writes its own optics variables.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Cavity(frequency = 352.2E6, voltage = 6.0E6, phase = np.pi),
            xt.Marker(),
            xt.Cavity(frequency = 704.4E6, voltage = 3.0E6, phase = np.pi / 2),
            xt.Marker(),
        ],
        element_names = ["start", "c1", "mid", "c2", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    env, reloaded_line = _write_and_load(line = line, tmp_path = tmp_path)

    assert reloaded_line["c1"].voltage   == pytest.approx(6.0E6),   (
        f"Writer roundtrip should preserve voltage for `c1`. "
        f"""Original: 6.0E6, reloaded: {reloaded_line["c1"].voltage}.""")
    assert reloaded_line["c1"].frequency == pytest.approx(352.2E6), (
        f"Writer roundtrip should preserve frequency for `c1`. "
        f"""Original: 352.2E6, reloaded: {reloaded_line["c1"].frequency}.""")
    assert reloaded_line["c2"].voltage   == pytest.approx(3.0E6),   (
        f"Writer roundtrip should preserve voltage for `c2`. "
        f"""Original: 3.0E6, reloaded: {reloaded_line["c2"].voltage}.""")
    assert reloaded_line["c2"].frequency == pytest.approx(704.4E6), (
        f"Writer roundtrip should preserve frequency for `c2`. "
        f"""Original: 704.4E6, reloaded: {reloaded_line["c2"].frequency}.""")
    assert env["volt_c1"] == pytest.approx(6.0E6), (
        "Optics variable `volt_c1` should be correct after reload.")
    assert env["volt_c2"] == pytest.approx(3.0E6), (
        "Optics variable `volt_c2` should be correct after reload.")
    assert env["freq_c1"] == pytest.approx(352.2E6), (
        "Optics variable `freq_c1` should be correct after reload.")
    assert env["freq_c2"] == pytest.approx(704.4E6), (
        "Optics variable `freq_c2` should be correct after reload.")


################################################################################
# Harmonic Cavity
################################################################################
def _build_harmonic_cavi_line(harmonic = 400, voltage = 6.0E6, phase = np.pi):
    """
    Build a minimal single-cavity Xsuite line using native harmonic mode.
    harmonic is an integer harmonic number (dimensionless), voltage in V, phase
    in radians. No frequency is set — xtrack derives it from harmonic * f_rev.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Cavity(
            harmonic = harmonic,
            voltage  = voltage,
            phase    = phase), xt.Marker()],
        element_names = ["start", "c1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def test_cavi_writer_preserves_harmonic(tmp_path):
    """
    A cavity built with harmonic mode should roundtrip through the writer with
    its harmonic number preserved.
    """
    original_line = _build_harmonic_cavi_line(harmonic = 400)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["c1"].harmonic == pytest.approx(400.0), (
        f"Writer roundtrip should preserve harmonic. "
        f"""Original: 400, reloaded: {reloaded_line["c1"].harmonic}.""")


def test_cavi_writer_harm_is_accessible_as_optics_variable(tmp_path):
    """
    The optics file should write harm_c1 as a readable environment variable for
    harmonic cavities.
    """
    original_line  = _build_harmonic_cavi_line(harmonic = 400)
    env, _         = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert "harm_c1" in env.vars.keys(), (
        "Optics file should define `harm_c1` for a harmonic cavity.")
    assert env["harm_c1"] == pytest.approx(400.0), (
        f"""Optics variable `harm_c1` should equal 400. Got: {env["harm_c1"]}.""")


def test_cavi_writer_harm_is_tunable_via_optics_variable(tmp_path):
    """
    Modifying harm_c1 in the environment should update the cavity harmonic
    number, verifying it is a live deferred expression.
    """
    original_line       = _build_harmonic_cavi_line(harmonic = 400)
    env, reloaded_line  = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["harm_c1"] = 800
    assert reloaded_line["c1"].harmonic == pytest.approx(800.0), (
        f"Setting env[`harm_c1`] = 800 should update the cavity harmonic. "
        f"""Got: {reloaded_line["c1"].harmonic}.""")


def test_cavi_writer_harmonic_does_not_write_frequency(tmp_path):
    """
    A harmonic cavity should not have a freq_c1 optics variable — the writer
    should write harm_c1 instead of freq_c1.
    """
    original_line  = _build_harmonic_cavi_line(harmonic = 400)
    env, _         = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert "freq_c1" not in env.vars.keys(), (
        "Optics file should NOT define `freq_c1` for a harmonic cavity. "
        "harm_c1 should be written instead.")


def test_cavi_writer_frequency_does_not_write_harmonic(tmp_path):
    """
    A frequency-driven cavity should not have a harm_c1 optics variable.
    """
    original_line  = _build_cavi_line(frequency = 352.2E6)
    env, _         = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert "harm_c1" not in env.vars.keys(), (
        "Optics file should NOT define `harm_c1` for a frequency-driven cavity.")
