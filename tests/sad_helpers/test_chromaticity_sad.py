"""
================================================================================
Tests for sad2xs.sad_helpers.chromaticity sad
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
import textwrap

import numpy as np
import pytest

from sad2xs.sad_helpers import chromaticity_sad
from sad2xs.sad_helpers.chromaticity import generate_off_momentum_tune_function

################################################################################
# Helpers
################################################################################
def _write_minimal_fodo_ring(tmp_path):
    """
    Write a minimal closed FODO ring suitable for chromaticity_sad. The ring
    has 4 cells each contributing π/2 of bending (2π total). Returns
    (filename, line_name).
    """
    lattice_path = tmp_path / "test_ring.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        QUAD    QF  = (L = 0.3, K1 =  1.5);
        QUAD    QD  = (L = 0.3, K1 = -1.5);
        BEND    B   = (L = 0.7854, ANGLE = 0.7854);
        DRIFT   D   = (L = 0.5);
        MARK    IP  = ();

        LINE    CELL = (QF D B D QD D B D);
        LINE    RING = (IP CELL CELL CELL CELL);
        """))

    return lattice_path.name, "RING"


def _run_chromaticity(tmp_path, monkeypatch, **kwargs):
    """
    Write the minimal FODO ring, change to its directory, and run
    chromaticity_sad with the default parameters. Extra keyword arguments are
    forwarded to chromaticity_sad (e.g. compute_higher_orders=True).
    """
    filename, line_name = _write_minimal_fodo_ring(tmp_path)
    monkeypatch.chdir(tmp_path)

    return chromaticity_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        wall_time        = 60,
        **kwargs)


################################################################################
# Command Generation Tests (SAD not required)
################################################################################
def test_generate_off_momentum_tune_function_returns_string():
    """
    generate_off_momentum_tune_function should return a non-empty string
    containing the SAD macro definition.
    """
    result = generate_off_momentum_tune_function()

    assert isinstance(result, str), (
        "generate_off_momentum_tune_function should return a str. "
        f"Got: {type(result).__name__}.")
    assert len(result) > 0, (
        "generate_off_momentum_tune_function should return a non-empty string.")


def test_generate_off_momentum_tune_function_defines_calculate_off_momentum_tune():
    """
    The returned string should define a SAD function named
    CalculateOffMomentumTune. This function is called in chromaticity_sad to
    scan the tune as a function of momentum deviation.
    """
    result = generate_off_momentum_tune_function()

    assert "CalculateOffMomentumTune[x_]" in result, (
        "generate_off_momentum_tune_function should define "
        "'CalculateOffMomentumTune[x_]'. "
        f"Got: {result[:200]!r}.")


def test_generate_off_momentum_tune_function_includes_tune_phase_advances():
    """
    The macro string should include the SAD Twiss keys NX and NY used to
    extract the horizontal and vertical phase advances (tunes) at each
    off-momentum point.
    """
    result = generate_off_momentum_tune_function()

    for key in ("NX", "NY"):
        assert key in result, (
            f"generate_off_momentum_tune_function should reference Twiss key "
            f"'{key}'. Got: {result[:200]!r}.")


################################################################################
# chromaticity_sad Smoke Tests (SAD required)
################################################################################
def test_chromaticity_sad_runs_and_returns_dict(tmp_path, monkeypatch):
    """
    chromaticity_sad should run SAD on a minimal closed ring and return a dict
    without raising an exception.
    """
    result = _run_chromaticity(tmp_path, monkeypatch)

    assert isinstance(result, dict), (
        f"chromaticity_sad should return a dict. Got: {type(result).__name__}.")


def test_chromaticity_sad_returns_expected_keys(tmp_path, monkeypatch):
    """
    The returned dict should contain all seven expected keys: dp, qx, qy for
    the scan data; dqx_linear, dqy_linear for the linear fit; and
    higher_order_qx, higher_order_qy for the optional higher-order fit.
    """
    result = _run_chromaticity(tmp_path, monkeypatch)

    for key in ("dp", "qx", "qy", "dqx_linear", "dqy_linear",
                "higher_order_qx", "higher_order_qy"):
        assert key in result, (
            f"chromaticity_sad result should contain key '{key}'. "
            f"Got keys: {list(result.keys())}.")


def test_chromaticity_sad_dp_scan_has_correct_length_and_range(
        tmp_path,
        monkeypatch):
    """
    With the default dp_extent=0.01 and dp_step=0.001, the scan runs from
    -0.01 to +0.01 inclusive, giving 21 points. The first and last dp values
    should match the extent — this confirms the dp_extent parameter is wired
    through correctly into the SAD Table command.
    """
    result = _run_chromaticity(tmp_path, monkeypatch)

    assert len(result["dp"]) == 21, (
        "Default dp scan (-0.01 to +0.01 step 0.001) should give 21 points. "
        f"Got: {len(result['dp'])}.")
    assert result["dp"][0] == pytest.approx(-0.01), (
        f"First dp value should be -0.01. Got: {result['dp'][0]}.")
    assert result["dp"][-1] == pytest.approx(0.01), (
        f"Last dp value should be +0.01. Got: {result['dp'][-1]}.")


def test_chromaticity_sad_custom_dp_extent_changes_scan_length(
        tmp_path,
        monkeypatch):
    """
    Passing dp_extent=0.005 and dp_step=0.001 should give a scan from -0.005
    to +0.005 (11 points). This confirms that dp_extent and dp_step are
    forwarded correctly into the SAD Table command and not silently ignored.
    """
    result = _run_chromaticity(
        tmp_path, monkeypatch, dp_extent = 0.005, dp_step = 0.001)

    assert len(result["dp"]) == 11, (
        "dp scan with extent=0.005 and step=0.001 should give 11 points. "
        f"Got: {len(result['dp'])}.")
    assert result["dp"][0] == pytest.approx(-0.005), (
        f"First dp value should be -0.005. Got: {result['dp'][0]}.")
    assert result["dp"][-1] == pytest.approx(0.005), (
        f"Last dp value should be +0.005. Got: {result['dp'][-1]}.")


def test_chromaticity_sad_scan_values_are_finite(tmp_path, monkeypatch):
    """
    All values in the dp, qx, qy arrays and the dqx_linear, dqy_linear scalars
    should be finite. A NaN indicates a failed tune calculation at some dp point
    (e.g., dynamic aperture loss or unstable motion).
    """
    result = _run_chromaticity(tmp_path, monkeypatch)

    for key in ("dp", "qx", "qy"):
        assert np.all(np.isfinite(result[key])), (
            f"chromaticity_sad result['{key}'] should contain only finite "
            f"values. Got: {result[key]}.")
    for key in ("dqx_linear", "dqy_linear"):
        assert np.isfinite(result[key]), (
            f"chromaticity_sad result['{key}'] should be finite. "
            f"Got: {result[key]}.")


def test_chromaticity_sad_natural_chromaticity_is_negative(
        tmp_path,
        monkeypatch):
    """
    A FODO ring with no sextupoles has negative natural chromaticity in both
    planes. A positive dq indicates a sign error in the polynomial fit or in
    the dp axis convention.
    """
    result = _run_chromaticity(tmp_path, monkeypatch)

    assert result["dqx_linear"] < 0, (
        "Natural chromaticity dqx_linear should be negative for a bare FODO "
        f"ring. Got: {result['dqx_linear']}.")
    assert result["dqy_linear"] < 0, (
        "Natural chromaticity dqy_linear should be negative for a bare FODO "
        f"ring. Got: {result['dqy_linear']}.")


def test_chromaticity_sad_higher_order_is_none_by_default(
        tmp_path,
        monkeypatch):
    """
    When compute_higher_orders is False (the default), higher_order_qx and
    higher_order_qy should both be None.
    """
    result = _run_chromaticity(tmp_path, monkeypatch)

    assert result["higher_order_qx"] is None, (
        "higher_order_qx should be None when compute_higher_orders=False. "
        f"Got: {result['higher_order_qx']}.")
    assert result["higher_order_qy"] is None, (
        "higher_order_qy should be None when compute_higher_orders=False. "
        f"Got: {result['higher_order_qy']}.")


def test_chromaticity_sad_higher_order_computed_when_requested(
        tmp_path,
        monkeypatch):
    """
    When compute_higher_orders=True, higher_order_qx and higher_order_qy
    should be numpy arrays of polynomial coefficients with 4 entries (orders
    0 through 3, since the default higher-order degree is 3).
    """
    result = _run_chromaticity(
        tmp_path, monkeypatch, compute_higher_orders = True)

    assert result["higher_order_qx"] is not None, (
        "higher_order_qx should not be None when compute_higher_orders=True.")
    assert result["higher_order_qy"] is not None, (
        "higher_order_qy should not be None when compute_higher_orders=True.")
    assert len(result["higher_order_qx"]) == 4, (
        "higher_order_qx should have 4 coefficients (degree 3 polynomial). "
        f"Got length: {len(result['higher_order_qx'])}.")
    assert len(result["higher_order_qy"]) == 4, (
        "higher_order_qy should have 4 coefficients (degree 3 polynomial). "
        f"Got length: {len(result['higher_order_qy'])}.")
    assert np.all(np.isfinite(result["higher_order_qx"])), (
        "higher_order_qx coefficients should all be finite. "
        f"Got: {result['higher_order_qx']}.")
    assert np.all(np.isfinite(result["higher_order_qy"])), (
        "higher_order_qy coefficients should all be finite. "
        f"Got: {result['higher_order_qy']}.")
