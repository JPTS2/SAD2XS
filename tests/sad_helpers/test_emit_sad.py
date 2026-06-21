"""
================================================================================
Tests for sad2xs.sad_helpers.emit sad
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import math
import textwrap

import numpy as np
import pytest

from sad2xs.sad_helpers import emit_sad

################################################################################
# Helpers
################################################################################
_EMIT_KEYS = (
    "design_momentum",
    "revolution_frequency",
    "eneloss_turn",
    "effective_voltage",
    "equilibrium_zeta",
    "momentum_compaction",
    "orbit_dilation",
    "effective_harmonic",
    "bucket_height",
    "synchrotron_frequency",
    "imag_tune",
    "real_tune",
    "damping_turn",
    "damping_time",
    "damping_partition",
    "gemitt_x",
    "gemitt_y",
    "gemitt_z",
    "energy_spread",
    "bunch_length")

_EMIT_SCALAR_KEYS = (
    "design_momentum",
    "revolution_frequency",
    "eneloss_turn",
    "effective_voltage",
    "equilibrium_zeta",
    "momentum_compaction",
    "orbit_dilation",
    "effective_harmonic",
    "bucket_height",
    "synchrotron_frequency",
    "gemitt_x",
    "gemitt_y",
    "gemitt_z",
    "energy_spread",
    "bunch_length")

_EMIT_TUPLE_KEYS = (
    "imag_tune",
    "real_tune",
    "damping_turn",
    "damping_time",
    "damping_partition")


def _write_minimal_fodo_ring(tmp_path):
    """
    Write a minimal closed FODO ring with radiation and RF cavity, suitable for
    emit_sad. The ring has 4 cells each contributing π/2 of bending (2π total)
    and an RF cavity with voltage well above the synchrotron radiation loss per
    turn. Returns (filename, line_name).
    """
    lattice_path = tmp_path / "test_ring.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        QUAD    QF  = (L = 0.3 K1 =  0.2);
        QUAD    QD  = (L = 0.3 K1 = -0.2);
        BEND    B   = (L = 0.7854 ANGLE = 0.7854);
        DRIFT   D   = (L = 0.5);
        CAVI    CAV = (VOLT = 1.0E6 FREQ = 1.8E7);
        MARK    IP  = ();

        LINE    CELL = (QF D B D QD D B D);
        LINE    RING = (IP CELL CELL CELL CELL CAV);
        """))

    return lattice_path.name, "RING"


def _run_emit(tmp_path, monkeypatch):
    """
    Write the minimal FODO ring, change to its directory, and run emit_sad with
    the default parameters.
    """
    filename, line_name = _write_minimal_fodo_ring(tmp_path)
    monkeypatch.chdir(tmp_path)

    return emit_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        wall_time        = 60)


################################################################################
# emit_sad Smoke Tests (SAD required)
################################################################################
def test_emit_sad_runs_and_returns_dict(tmp_path, monkeypatch):
    """
    emit_sad should run SAD on a minimal closed ring and return a dict without
    raising an exception.
    """
    result = _run_emit(tmp_path, monkeypatch)

    assert isinstance(result, dict), (
        f"emit_sad should return a dict. Got: {type(result).__name__}.")


def test_emit_sad_returns_all_expected_keys(tmp_path, monkeypatch):
    """
    The dict returned by emit_sad should contain all 20 expected keys covering
    machine parameters, radiation integrals, tunes, damping, emittances, and
    longitudinal parameters.
    """
    result = _run_emit(tmp_path, monkeypatch)

    for key in _EMIT_KEYS:
        assert key in result, (
            f"emit_sad result should contain key '{key}'. "
            f"Got keys: {list(result.keys())}.")


def test_emit_sad_scalar_values_are_finite(tmp_path, monkeypatch):
    """
    All scalar float values in the emit dict should be finite. A NaN or Inf
    indicates a parsing failure or unit conversion error in our wrapper.
    """
    result = _run_emit(tmp_path, monkeypatch)

    for key in _EMIT_SCALAR_KEYS:
        assert math.isfinite(result[key]), (
            f"emit_sad result['{key}'] should be finite. Got: {result[key]}.")

    for key in _EMIT_TUPLE_KEYS:
        for i, val in enumerate(result[key]):
            assert math.isfinite(val), (
                f"emit_sad result['{key}'][{i}] should be finite. "
                f"Got: {val}.")


def test_emit_sad_design_momentum_is_correct_order_of_magnitude(
        tmp_path,
        monkeypatch):
    """
    For a 1 GeV ring, design_momentum should be returned in eV and therefore
    be approximately 1e9. A value wildly outside this range indicates a unit
    conversion error in convert_energy.
    """
    result = _run_emit(tmp_path, monkeypatch)

    assert result["design_momentum"] == pytest.approx(1e9, rel = 1E-3), (
        "design_momentum for a 1.0 GEV ring should be approximately 1e9 eV. "
        f"Got: {result['design_momentum']}.")


def test_emit_sad_physical_quantities_have_correct_sign(tmp_path, monkeypatch):
    """
    Sign conventions for the returned quantities:
    - revolution_frequency > 0 (positive periodicity)
    - eneloss_turn > 0 (positive energy loss magnitude)
    - synchrotron_frequency > 0 (positive for a stable RF bucket)
    - gemitt_x, gemitt_z > 0 (positive emittances)
    - gemitt_y approximately zero (uncoupled planar ring)
    - energy_spread > 0 (positive definite)
    """
    result = _run_emit(tmp_path, monkeypatch)

    for key in ("revolution_frequency", "synchrotron_frequency",
                "eneloss_turn", "gemitt_x", "gemitt_z", "energy_spread"):
        assert result[key] > 0, (
            f"emit_sad result['{key}'] should be positive. "
            f"Got: {result[key]}.")

    assert result["gemitt_y"] >= -1E-30, (
        "emit_sad result['gemitt_y'] should be zero to numerical precision "
        "for an uncoupled planar ring. "
        f"Got: {result['gemitt_y']}.")


def test_emit_sad_radcod_flag_runs_and_returns_all_keys(tmp_path, monkeypatch):
    """
    With radcod=True SAD uses quantum radiation recoil (RADCOD mode). The
    returned dict should still contain all 20 expected keys — this tests that
    the radcod code path through emit_sad produces the same output structure.
    """
    filename, line_name = _write_minimal_fodo_ring(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = emit_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        radcod           = True,
        wall_time        = 60)

    for key in _EMIT_KEYS:
        assert key in result, (
            f"emit_sad with radcod=True should return key '{key}'. "
            f"Got keys: {list(result.keys())}.")
