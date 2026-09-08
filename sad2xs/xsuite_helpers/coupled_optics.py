"""
================================================================================
Edwards-Teng Coupled Optics
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-08-25
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np

import xtrack.linear_normal_form as lnf

################################################################################
# Edwards-Teng propagation
################################################################################
def _propagate_edwards_teng_arrays(WW, mux, muy, RR_ET0, betx0, alfx0, bety0, alfy0):
    """
    Propagate Edwards-Teng optics element by element.

    Vendored from xtrack 0.111.4, where this was
    `xtrack.twiss.coupling_edw_teng._propagate_edwards_teng` (Apache-2.0,
    the same licence as this project). Xtrack 0.111.5 removed it in favour
    of a periodic-only route, leaving no upstream symbol to call. The
    algorithm is MAD-X's `twcptk` and `twcptk_twiss` (`madx/src/twiss.f90`).

    Kept verbatim apart from its name and this docstring, so it can still
    be diffed against the upstream original. `propagate_edwards_teng` is
    the entry point.
    """
    SS2D = lnf.S[:2, :2]

    RR_ET = RR_ET0.copy()

    n_elem = len(mux)
    betx = np.zeros(n_elem)
    alfx = np.zeros(n_elem)
    bety = np.zeros(n_elem)
    alfy = np.zeros(n_elem)
    r11 = np.zeros(n_elem)
    r12 = np.zeros(n_elem)
    r21 = np.zeros(n_elem)
    r22 = np.zeros(n_elem)

    betx[0] = betx0
    alfx[0] = alfx0
    bety[0] = bety0
    alfy[0] = alfy0
    r11[0] = RR_ET[0, 0]
    r12[0] = RR_ET[0, 1]
    r21[0] = RR_ET[1, 0]
    r22[0] = RR_ET[1, 1]

    for ii in range(n_elem - 1):

        # Build 2D R matrix of the element
        WW1 = WW[ii, :, :]
        WW2 = WW[ii+1, :, :]
        WW1_inv = lnf.S.T @ WW1.T @ lnf.S
        Rot_e_ii = np.zeros((6,6), dtype=np.float64)
        Rot_e_ii[0:2,0:2] = lnf.Rot2D(2*np.pi*(mux[ii+1] - mux[ii]))
        Rot_e_ii[2:4,2:4] = lnf.Rot2D(2*np.pi*(muy[ii+1] - muy[ii]))
        RRe_ii = WW2 @ Rot_e_ii @ WW1_inv

        # Blocks of the R matrix of the element
        AA = RRe_ii[:2, :2]
        BB = RRe_ii[:2, 2:4]
        CC = RRe_ii[2:4, :2]
        DD = RRe_ii[2:4, 2:4]

        # Propagate EE, FF and RR_ET through the element
        # Bases on MAD-X implementation (see madx/src/twiss.f90, subroutine twcptk)

        if np.allclose(BB, 0, atol=1e-12) and np.allclose(CC, 0, atol=1e-12):
            # Case in which the matrix is block diagonal (no coupling in the element)
            EE = AA
            FF = DD
            EEBAR = SS2D @ EE.T @ SS2D.T
            edet = EE[0,0]*EE[1,1] - EE[0,1]*EE[1,0]
            CCDD = -FF @ RR_ET
            RR_ET = -CCDD @ EEBAR / edet
        else:
            RR_ET_BAR = SS2D @ RR_ET.T @ SS2D.T
            EE = AA - BB @ RR_ET
            edet = EE[0,0]*EE[1,1] - EE[0,1]*EE[1,0]
            EEBAR = SS2D @ EE.T @ SS2D.T
            CCDD = CC - DD @ RR_ET
            FF = DD + CC @ RR_ET_BAR
            RR_ET = -CCDD @ EEBAR / edet

        # Propagate Edwards-Teng Twiss parameters through the element
        # Based on MAD-X implementation (see madx/src/twiss.f90, subroutine twcptk_twiss)

        betx1 = betx[ii]
        alfx1 = alfx[ii]
        bety1 = bety[ii]
        alfy1 = alfy[ii]

        Rx11 = EE[0,0]
        Rx12 = EE[0,1]
        Rx21 = EE[1,0]
        Rx22 = EE[1,1]
        detx = Rx11 * Rx22 - Rx12 * Rx21
        tempb = Rx11 * betx1 - Rx12 * alfx1
        tempa = Rx21 * betx1 - Rx22 * alfx1
        alfx2 = - (tempa * tempb + Rx12 * Rx22) / (detx*betx1)
        betx2 =   (tempb * tempb + Rx12 * Rx12) / (detx*betx1)

        Ry11 = FF[0,0]
        Ry12 = FF[0,1]
        Ry21 = FF[1,0]
        Ry22 = FF[1,1]
        dety = Ry11 * Ry22 - Ry12 * Ry21
        tempb = Ry11 * bety1 - Ry12 * alfy1
        tempa = Ry21 * bety1 - Ry22 * alfy1
        alfy2 = - (tempa * tempb + Ry12 * Ry22) / (dety*bety1)
        bety2 =   (tempb * tempb + Ry12 * Ry12) / (dety*bety1)

        betx[ii+1] = betx2
        alfx[ii+1] = alfx2
        r11[ii+1] = RR_ET[0, 0]
        r12[ii+1] = RR_ET[0, 1]
        r21[ii+1] = RR_ET[1, 0]
        r22[ii+1] = RR_ET[1, 1]
        bety[ii+1] = bety2
        alfy[ii+1] = alfy2

    out_dict = {
        'betx': betx,
        'alfx': alfx,
        'bety': bety,
        'alfy': alfy,
        'r11': r11,
        'r12': r12,
        'r21': r21,
        'r22': r22
    }

    return out_dict


def propagate_edwards_teng(
        twiss_table,
        rr_et0  = None,
        betx0   = None,
        alfx0   = None,
        bety0   = None,
        alfy0   = None) -> dict:
    """
    Propagate Edwards-Teng optics along an Xsuite twiss table.

    Propagation runs element by element from the start of the table, so
    this works on an open transfer line. SAD reports coupled beta/alpha in
    Edwards-Teng form.

    **By default this assumes the table starts in an uncoupled region.**
    To start inside a coupled region, such as a detector solenoid, pass
    `rr_et0` and the beta/alpha seeds. Nothing detects a coupled start, so
    wrong seeds give a plausible wrong answer rather than an error.

    Xsuite emits `betx_edw_teng` and friends on an open twiss, but they
    carry no coupling: `g_edw_teng` is 1 throughout, so they are the plain
    values under another name. Its coupled columns need a periodic line.

    Parameters
    ----------
    twiss_table : xtrack TwissTable
        Open-line (or periodic) twiss result; `W_matrix`, `mux` and `muy`
        are consumed.
    rr_et0 : (2, 2) array-like | None, optional
        Edwards-Teng decoupling matrix at the first table row. Defaults to
        zeros, i.e. an uncoupled line start.
    betx0, alfx0, bety0, alfy0 : float | None, optional
        Edwards-Teng optics at the first table row. Defaults to the table's
        plain values, which are identical at an uncoupled start.

    Returns
    -------
    dict
        Arrays over table rows for Edwards-Teng beta/alpha and decoupling
        matrix components.
    """
    if rr_et0 is None:
        rr_et0 = np.zeros((2, 2))
    if betx0 is None:
        betx0 = twiss_table.betx[0]
    if alfx0 is None:
        alfx0 = twiss_table.alfx[0]
    if bety0 is None:
        bety0 = twiss_table.bety[0]
    if alfy0 is None:
        alfy0 = twiss_table.alfy[0]

    return _propagate_edwards_teng_arrays(
        WW      = twiss_table.W_matrix,
        mux     = twiss_table.mux,
        muy     = twiss_table.muy,
        RR_ET0  = np.array(rr_et0, dtype = float),
        betx0   = betx0,
        alfx0   = alfx0,
        bety0   = bety0,
        alfy0   = alfy0)
