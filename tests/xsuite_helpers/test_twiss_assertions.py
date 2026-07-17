"""
================================================================================
Tests for sad2xs.xsuite_helpers.twiss_assertions
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-17
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import pytest
import xtrack as xt

from sad2xs.xsuite_helpers import assert_xsuite_matches_sad_twiss

################################################################################
# Helpers
################################################################################
def _table(**columns):
    n   = len(next(iter(columns.values())))
    return xt.Table({"name": np.array([f"e{i}" for i in range(n)]), **columns})

################################################################################
# assert_xsuite_matches_sad_twiss
################################################################################
def test_matching_values_pass():
    sad     = _table(betx = np.array([1.0, 2.0, 3.0]))
    xsuite  = _table(betx = np.array([1.0, 2.0, 3.0]))

    assert_xsuite_matches_sad_twiss(
        xsuite, sad, tolerances = {"betx": dict(atol = 1E-9, rtol = 1E-9)})

def test_out_of_tolerance_raises():
    sad     = _table(betx = np.array([1.0, 2.0, 3.0]))
    xsuite  = _table(betx = np.array([1.0, 2.0, 3.5]))

    with pytest.raises(AssertionError):
        assert_xsuite_matches_sad_twiss(
            xsuite, sad, tolerances = {"betx": dict(atol = 1E-4, rtol = 1E-4)})

def test_xsuite_column_overrides_remaps_column_name():
    """The Edwards-Teng use case: the Xsuite side reports the same physical
    quantity under a different column name."""
    sad     = _table(betx = np.array([1.0, 2.0]))
    xsuite  = _table(betx_edw_teng = np.array([1.0, 2.0]))

    with pytest.raises(AttributeError):
        assert_xsuite_matches_sad_twiss(
            xsuite, sad, tolerances = {"betx": dict(atol = 1E-9, rtol = 1E-9)})

    assert_xsuite_matches_sad_twiss(
        xsuite, sad,
        tolerances              = {"betx": dict(atol = 1E-9, rtol = 1E-9)},
        xsuite_column_overrides = {"betx": "betx_edw_teng"})

def test_zeta_baseline_is_subtracted_before_comparison():
    """`zeta` has no common reference point between SAD and Xsuite -- a
    constant offset between the two sides must not fail the assertion."""
    sad     = _table(zeta = np.array([0.0, 1.0, 2.0]))
    xsuite  = _table(zeta = np.array([5.0, 6.0, 7.0]))

    assert_xsuite_matches_sad_twiss(
        xsuite, sad, tolerances = {"zeta": dict(atol = 1E-9, rtol = 1E-9)})
