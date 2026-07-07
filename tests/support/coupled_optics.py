"""
================================================================================
Edwards-Teng coupled optics helpers for open-line SAD comparisons
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-06
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import xtrack as xt

# Deliberate private-API use: this wraps xtrack's existing open-line
# Edwards-Teng propagation. The convention tests pin the semantics against
# native periodic Xtrack columns, uncoupled lines, and SAD.
from xtrack.twiss import _propagate_edwards_teng

################################################################################
# Background
#
# SAD reports coupled beta/alpha in Edwards-Teng form. Xsuite can compute
# Edwards-Teng columns natively for periodic lines, but open-line SAD
# comparisons need this explicit propagation helper.
################################################################################

################################################################################
# Edwards-Teng propagation
################################################################################
def edwards_teng_optics(
        twiss_table,
        rr_et0  = None,
        betx0   = None,
        alfx0   = None,
        bety0   = None,
        alfy0   = None) -> dict:
    """
    Propagate Edwards-Teng optics along an open-line Xsuite Twiss table.

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

    return _propagate_edwards_teng(
        WW      = twiss_table.W_matrix,
        mux     = twiss_table.mux,
        muy     = twiss_table.muy,
        RR_ET0  = np.array(rr_et0, dtype = float),
        betx0   = betx0,
        alfx0   = alfx0,
        bety0   = bety0,
        alfy0   = alfy0)


def edwards_teng_optics_at(twiss_table, element_name, **kwargs) -> dict:
    """
    Edwards-Teng optics of `edwards_teng_optics` at one named element.

    Returns a dict of scalars with the same keys as `edwards_teng_optics`.
    Extra keyword arguments are forwarded (e.g. initial conditions).
    """
    optics  = edwards_teng_optics(twiss_table, **kwargs)
    index   = list(twiss_table.name).index(element_name)
    return {key: values[index] for key, values in optics.items()}


def normalized_r_matrix(r11, r12, r21, r22) -> np.ndarray:
    """
    Normalise an Edwards-Teng decoupling matrix as R / sqrt(1 + det R).

    This is the form SAD reports as R1-R4 (and stores in its Twiss output):
    the raw propagated decoupling matrix divided by the square root of one
    plus its determinant.
    """
    r_matrix = np.array([[r11, r12], [r21, r22]], dtype = float)
    return r_matrix / np.sqrt(1.0 + np.linalg.det(r_matrix))

################################################################################
# Transfer-matrix anchor
################################################################################
def linear_transfer_matrix_4d(
        line,
        p0c     = 1.0E9,
        mass0   = xt.ELECTRON_MASS_EV,
        q0      = 1,
        delta   = 1.0E-7) -> np.ndarray:
    """
    4x4 linear transfer matrix of an Xsuite line by central finite
    differences of tracked coordinates (x, px, y, py).

    Parametrisation-free anchor for coupled-optics comparisons: it involves
    no twiss convention at all, so SAD-vs-Xsuite equality of this matrix
    separates map-level agreement from parametrisation-level agreement.
    """
    matrix = np.zeros((4, 4))
    coordinates = ["x", "px", "y", "py"]

    for column, coordinate in enumerate(coordinates):
        plus_kwargs     = {c: (+delta if c == coordinate else 0.0)
                           for c in coordinates}
        minus_kwargs    = {c: (-delta if c == coordinate else 0.0)
                           for c in coordinates}
        particles_plus  = xt.Particles(
            p0c = p0c, mass0 = mass0, q0 = q0, **plus_kwargs)
        particles_minus = xt.Particles(
            p0c = p0c, mass0 = mass0, q0 = q0, **minus_kwargs)
        line.track(particles_plus)
        line.track(particles_minus)

        for row, out_coordinate in enumerate(coordinates):
            matrix[row, column] = (
                getattr(particles_plus, out_coordinate)[0]
                - getattr(particles_minus, out_coordinate)[0]) / (2 * delta)

    return matrix
