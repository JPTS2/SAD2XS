"""
================================================================================
Tests for sad2xs.sad_helpers.transfer matrix sad
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

from tests.support.lattices import write_minimal_transfer_lattice
from sad2xs.sad_helpers import transfer_matrix_sad

################################################################################
# Helpers
################################################################################
def _run_transfer_matrix(tmp_path, monkeypatch, **kwargs):
    """
    Write the minimal drift transfer-line lattice, change to its directory,
    and run transfer_matrix_sad with wall_time=30. Extra keyword arguments are
    forwarded to transfer_matrix_sad (e.g. start_element, end_element).
    """
    filename, line_name = write_minimal_transfer_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    return transfer_matrix_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        wall_time        = 30,
        **kwargs)


################################################################################
# Input Validation Tests (SAD not required)
################################################################################
def test_transfer_matrix_sad_raises_if_start_given_without_end():
    """
    Providing start_element without end_element is ambiguous and should raise
    a ValueError immediately, before any subprocess call.
    """
    with pytest.raises(ValueError, match = "end_element"):
        transfer_matrix_sad(
            lattice_filepath = "dummy.sad",
            line_name        = "LINE",
            start_element    = "START",
            end_element      = None)


def test_transfer_matrix_sad_raises_if_end_given_without_start():
    """
    Providing end_element without start_element is ambiguous and should raise
    a ValueError immediately, before any subprocess call.
    """
    with pytest.raises(ValueError, match = "start_element"):
        transfer_matrix_sad(
            lattice_filepath = "dummy.sad",
            line_name        = "LINE",
            start_element    = None,
            end_element      = "END")


################################################################################
# transfer_matrix_sad Smoke Tests (SAD required)
################################################################################
def test_transfer_matrix_sad_runs_and_returns_ndarray(tmp_path, monkeypatch):
    """
    transfer_matrix_sad should run SAD on a minimal transfer-line lattice and
    return a numpy ndarray without raising an exception.
    """
    tm = _run_transfer_matrix(tmp_path, monkeypatch)

    assert isinstance(tm, np.ndarray), (
        "transfer_matrix_sad should return a numpy ndarray. "
        f"Got: {type(tm).__name__}.")


def test_transfer_matrix_sad_returns_4x4_matrix(tmp_path, monkeypatch):
    """
    transfer_matrix_sad should return a 4×4 matrix. SAD's CALC4D computes the
    4D linear transfer map in (x, px, y, py) phase space.
    """
    tm = _run_transfer_matrix(tmp_path, monkeypatch)

    assert tm.shape == (4, 4), (
        "transfer_matrix_sad should return a (4, 4) matrix. "
        f"Got shape: {tm.shape}.")


def test_transfer_matrix_sad_values_are_finite(tmp_path, monkeypatch):
    """
    All entries of the transfer matrix should be finite. A NaN or Inf indicates
    a parsing failure in the Mathematica {{...}} → Python conversion.
    """
    tm = _run_transfer_matrix(tmp_path, monkeypatch)

    assert np.all(np.isfinite(tm)), (
        "transfer_matrix_sad should return a matrix with all finite values. "
        f"Got:\n{tm}.")


def test_transfer_matrix_sad_drift_matches_analytic_result(tmp_path, monkeypatch):
    """
    For a 1 m drift, the analytic 4D transfer matrix is:
        [[1, 1, 0, 0],
         [0, 1, 0, 0],
         [0, 0, 1, 1],
         [0, 0, 0, 1]]
    The off-diagonal entries M[0,1] = M[2,3] = L = 1.0 encode the drift
    length. Deviations indicate a unit or parsing error.
    """
    tm = _run_transfer_matrix(tmp_path, monkeypatch)

    expected = np.array([
        [1.0, 1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 0.0, 1.0]])

    assert tm == pytest.approx(expected, abs = 1E-6), (
        "Transfer matrix for a 1 m drift should match the analytic result. "
        f"Got:\n{tm}\nExpected:\n{expected}.")


def test_transfer_matrix_sad_is_symplectic(tmp_path, monkeypatch):
    """
    The 4D transfer matrix of any lossless element satisfies det(M) = 1
    (symplecticity). A determinant far from 1 indicates a non-physical or
    incorrectly parsed result.
    """
    tm  = _run_transfer_matrix(tmp_path, monkeypatch)
    det = np.linalg.det(tm)

    assert det == pytest.approx(1.0, abs = 1E-9), (
        "Transfer matrix of a lossless lattice should have det = 1. "
        f"Got det: {det}.")


def test_transfer_matrix_sad_explicit_start_and_end_elements(
        tmp_path,
        monkeypatch):
    """
    Passing start_element=`START` and end_element=`END` should produce the same
    analytic 1 m drift matrix as the default index-based path, confirming that
    the named-element TransferMatrix["START", "END"] code path is wired correctly
    and covers the same lattice extent.
    """
    tm = _run_transfer_matrix(
        tmp_path, monkeypatch,
        start_element = "START",
        end_element   = "END")

    expected = np.array([
        [1.0, 1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 0.0, 1.0]])

    assert tm.shape == (4, 4), (
        "Explicit start/end call should return a (4, 4) matrix. "
        f"Got shape: {tm.shape}.")
    assert tm == pytest.approx(expected, abs = 1E-6), (
        "Explicit start/end call should match the analytic 1 m drift matrix. "
        f"Got:\n{tm}\nExpected:\n{expected}.")
