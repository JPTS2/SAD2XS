"""
(Unofficial) SAD to XSuite Converter: Xsuite Helpers Symplecticity Check
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-17
"""
################################################################################
# Required Packages
################################################################################
import logging

import numpy as np
import xtrack as xt

logger  = logging.getLogger(__name__)

_J  = np.array([
    [0, +1, 0, 0, 0, 0],
    [-1, 0, 0, 0, 0, 0],
    [0, 0, 0, +1, 0, 0],
    [0, 0, -1, 0, 0, 0],
    [0, 0, 0, 0, 0, +1],
    [0, 0, 0, 0, -1, 0]])

################################################################################
# Symplecticity residual: (M.T @ J @ M) - J, zero for a symplectic M
################################################################################
def _residual(M):
    return (M.T @ _J @ M) - _J

################################################################################
# Check symplecticity
################################################################################
def check_symplecticity(twiss, line, *, tt = None, atol = 1E-6):
    """
    Check the one-turn R matrix is symplectic; if it isn't, fall back to an
    element-by-element check to find what breaks it.

    Parameters
    ----------
    twiss : xt.TwissTable
        Must contain `R_matrix` and `steps_R_matrix` (the latter only used
        for the element-by-element fallback).
    line : xt.Line
        Line the twiss was computed on.
    tt : xt.Table, optional
        `line.get_table(attr=True)`, if already available.
    atol : float, optional
        Absolute tolerance on the symplecticity residual.

    Returns
    -------
    (bool, float)
        `(is_symplectic, max_deviation)` for the overall one-turn matrix.
    """
    ########################################
    # Overall one-turn matrix
    ########################################
    residual        = _residual(twiss.R_matrix)
    max_deviation   = np.max(np.abs(residual))
    is_symplectic   = max_deviation < atol

    logger.info(
        f"Overall R matrix symplectic (atol={atol:g}): {is_symplectic} "
        f"(max deviation {max_deviation:.3e})")
    logger.debug("Residual:\n" + "\n".join(
        " ".join(f"{x:+12.5E}" for x in row) for row in residual))

    ########################################
    # Element-by-element, only if the overall check failed
    ########################################
    if not is_symplectic:
        if tt is None:
            tt  = line.get_table(attr = True)

        test_particle   = xt.Particles(
            p0c     = line.particle_ref.p0c,
            mass0   = line.particle_ref.mass0,
            q0      = line.particle_ref.q0)

        # tt's last row is the synthetic "_end_point" marker, with no element
        # after it to pair as a segment end -- skip it on both sides.
        for start_ele, end_ele in zip(tt.name[:-2], tt.name[1:-1]):
            M_ele           = line.get_R_matrix(
                start               = start_ele,
                end                 = end_ele,
                particle_on_co      = test_particle,
                steps               = twiss.steps_R_matrix)["R_matrix"]
            ele_deviation   = np.max(np.abs(_residual(M_ele)))
            if ele_deviation >= atol:
                logger.info(
                    f"Non-symplectic element (atol={atol:g}): {start_ele} "
                    f"(deviation {ele_deviation:.3e})")

    return is_symplectic, max_deviation
