"""
================================================================================
Tests for sad2xs.xsuite_helpers.twiss_alignment
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

from sad2xs.xsuite_helpers import align_xsuite_twiss_with_sad_twiss, compute_s_sad

################################################################################
# Helpers
################################################################################
def _table(names, s):
    """
    Build a minimal xt.Table with just name/s columns, for alignment tests.
    """
    return xt.Table({"name": np.array(names), "s": np.array(s, dtype = float)})

################################################################################
# align_xsuite_twiss_with_sad_twiss -- pass 1: exact name match
################################################################################
def test_exact_name_match():
    """
    An identical name/s on both sides should match directly via pass 1
    (exact name), with no fallback needed.
    """
    sad     = _table(["m1", "q1", "m2"], [0.0, 1.0, 2.0])
    xsuite  = _table(["m1", "q1", "m2"], [0.0, 1.0, 2.0])

    xs_aligned, sad_aligned    = align_xsuite_twiss_with_sad_twiss(
        xsuite, sad, use_s_sad = False)

    assert list(sad_aligned.name) == ["m1", "q1", "m2"]
    assert list(xs_aligned.name)  == ["m1", "q1", "m2"]

################################################################################
# Pass 2: SAD's dot-suffixed family name
################################################################################
def test_dot_suffixed_family_match():
    """
    Both sides already carry SAD's own `.N` repeat suffix (a real element
    repeated, e.g. same-length gap-filling drifts) -- pass 1 must defer to
    pass 2's pooled/ranked matching rather than string-matching by luck.
    """
    sad     = _table(["d1.0", "d1.1"], [0.5, 1.5])
    xsuite  = _table(["d1.0", "d1.1"], [0.5, 1.5])

    xs_aligned, sad_aligned    = align_xsuite_twiss_with_sad_twiss(
        xsuite, sad, use_s_sad = False)

    assert list(sad_aligned.name) == ["d1.0", "d1.1"]
    assert list(xs_aligned.name)  == ["d1.0", "d1.1"]

################################################################################
# Pass 3: solenoid-interior rename
################################################################################
def test_solenoid_interior_rename_match():
    """
    A SAD element renamed on the Xsuite side with a `_{neighbour}` suffix
    (solenoid-interior rename) should still match, via pass 3's
    string-prefix search.
    """
    sad     = _table(["es1"], [3.0])
    xsuite  = _table(["es1_esr0"], [3.0])

    xs_aligned, sad_aligned    = align_xsuite_twiss_with_sad_twiss(
        xsuite, sad, use_s_sad = False)

    assert list(sad_aligned.name) == ["es1"]
    assert list(xs_aligned.name)  == ["es1_esr0"]

################################################################################
# Failure modes
################################################################################
def test_unmatched_sad_element_raises():
    """
    A SAD element with no Xsuite counterpart at all should raise
    AssertionError naming it, not silently drop it.
    """
    sad     = _table(["ghost"], [9.0])
    xsuite  = _table(["other"], [9.0])

    with pytest.raises(AssertionError, match = "ghost"):
        align_xsuite_twiss_with_sad_twiss(xsuite, sad, use_s_sad = False)

def test_s_tol_rejection_raises():
    """A name match that fails the s_tol check counts as unmatched, not a
    silent pass-through."""
    sad     = _table(["q1"], [1.0])
    xsuite  = _table(["q1"], [2.0])

    with pytest.raises(AssertionError, match = "q1"):
        align_xsuite_twiss_with_sad_twiss(
            xsuite, sad, use_s_sad = False, s_tol = 1E-9)

################################################################################
# excluded_elements
################################################################################
def test_excluded_elements_drops_unmatched_sad_element():
    """
    A SAD element with no Xsuite match raises by default, but is dropped
    from the comparison instead once listed in excluded_elements.
    """
    sad     = _table(["keep", "drop"], [0.0, 1.0])
    xsuite  = _table(["keep"], [0.0])

    with pytest.raises(AssertionError):
        align_xsuite_twiss_with_sad_twiss(xsuite, sad, use_s_sad = False)

    xs_aligned, sad_aligned    = align_xsuite_twiss_with_sad_twiss(
        xsuite, sad, use_s_sad = False, excluded_elements = ["drop"])

    assert list(sad_aligned.name) == ["keep"]
    assert list(xs_aligned.name)  == ["keep"]

################################################################################
# compute_s_sad
################################################################################
def test_compute_s_sad_adds_back_timedelay_jump_only():
    """
    The artificial `zeta` jump right after a sad2xs-generated TimeDelay
    (solenoid-boundary `_dz` piece / reference-energy `_ref_zeta_update`) is
    added back into `s`; zeta's evolution everywhere else is left alone.
    """
    xsuite  = xt.TwissTable({
        "name": np.array(["a", "sol_dz", "b"]),
        "s":    np.array([0.0, 1.0, 1.0]),
        "zeta": np.array([0.0, 0.0, 0.5])})

    s_sad   = compute_s_sad(xsuite)

    np.testing.assert_allclose(s_sad, [0.0, 1.0, 1.5])

def test_compute_s_sad_none_without_zeta_column():
    """
    compute_s_sad should return None when the Xsuite twiss table has no
    zeta column (e.g. an open-line 4D twiss without a real 6D/RF setup).
    """
    xsuite  = xt.TwissTable({
        "name": np.array(["a", "b"]),
        "s":    np.array([0.0, 1.0])})

    assert compute_s_sad(xsuite) is None

def test_compute_s_sad_none_with_non_finite_zeta():
    """
    compute_s_sad should return None when the zeta column contains a
    non-finite value (e.g. NaN).
    """
    xsuite  = xt.TwissTable({
        "name": np.array(["a", "b"]),
        "s":    np.array([0.0, 1.0]),
        "zeta": np.array([0.0, np.nan])})

    assert compute_s_sad(xsuite) is None
