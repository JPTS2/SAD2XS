"""
================================================================================
Xsuite Helpers: Twiss Assertions
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
import xtrack as xt

################################################################################
# Default per-column tolerances
################################################################################
DEFAULT_TWISS_TOLERANCES   = {
    "x":     dict(atol = 1E-7,  rtol = 1E-3),
    "px":    dict(atol = 1E-8,  rtol = 1E-3),
    "y":     dict(atol = 1E-7,  rtol = 1E-3),
    "py":    dict(atol = 1E-8,  rtol = 1E-3),
    "zeta":  dict(atol = 1E-9,  rtol = 1E-3),
    "delta": dict(atol = 1E-12, rtol = 1E-3),
    "betx":  dict(atol = 1E-4,  rtol = 1E-3),
    "bety":  dict(atol = 1E-4,  rtol = 1E-3),
    "alfx":  dict(atol = 1E-4,  rtol = 1E-3),
    "alfy":  dict(atol = 1E-4,  rtol = 1E-3),
    "dx":    dict(atol = 1E-5,  rtol = 1E-3),
    "dpx":   dict(atol = 1E-6,  rtol = 1E-3),
    "dy":    dict(atol = 1E-5,  rtol = 1E-3),
    "dpy":   dict(atol = 1E-6,  rtol = 1E-3),
    "mux":   dict(atol = 1E-6,  rtol = 1E-3),
    "muy":   dict(atol = 1E-6,  rtol = 1E-3)}

# zeta has no common reference point between SAD and Xsuite -- compare the
# change along the line instead of the absolute value.
_BASELINE_SUBTRACTED_COLUMNS   = {"zeta"}

################################################################################
# Assert two aligned twiss tables agree
################################################################################
def assert_xsuite_matches_sad_twiss(
        xsuite_aligned:             xt.Table,
        sad_aligned:                xt.Table,
        *,
        tolerances:                 dict[str, dict[str, float]] | None  = None,
        xsuite_column_overrides:    dict[str, str] | None               = None) -> None:
    """
    Assert an Xsuite/SAD twiss pair agrees column by column, within
    per-column tolerance.

    Parameters
    ----------
    xsuite_aligned, sad_aligned : xt.Table
        Same-length, row-matched tables, e.g. from
        `align_xsuite_twiss_with_sad_twiss`.
    tolerances : dict, optional
        SAD column name -> `{"atol": ..., "rtol": ...}`. Defaults to
        `DEFAULT_TWISS_TOLERANCES`.
    xsuite_column_overrides : dict, optional
        SAD column name -> Xsuite column name, for columns compared under a
        different name on the Xsuite side (e.g. `{"betx": "betx_edw_teng"}`
        for coupled Edwards-Teng optics).

    Raises
    ------
    AssertionError
        If any column's values disagree beyond its tolerance.
    """
    tolerances               = tolerances or DEFAULT_TWISS_TOLERANCES
    xsuite_column_overrides  = xsuite_column_overrides or {}

    for sad_column, tol in tolerances.items():
        xsuite_column   = xsuite_column_overrides.get(sad_column, sad_column)
        xs_values       = np.asarray(getattr(xsuite_aligned, xsuite_column), dtype = float)
        sad_values      = np.asarray(getattr(sad_aligned, sad_column), dtype = float)

        if sad_column in _BASELINE_SUBTRACTED_COLUMNS:
            xs_values   = xs_values - xs_values[0]
            sad_values  = sad_values - sad_values[0]

        np.testing.assert_allclose(
            xs_values, sad_values,
            atol    = tol["atol"],
            rtol    = tol["rtol"],
            err_msg = (
                f"""Xsuite "{xsuite_column}" disagrees with SAD "{sad_column}" """
                "beyond tolerance."))
