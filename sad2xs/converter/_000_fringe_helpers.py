"""
================================================================================
Shared SAD K1 Soft-Edge Fringe Helpers
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-08-29
================================================================================
"""

import numpy as np
import xtrack as xt


def sad_akang(k1: float, sk1: float = 0.0, length: float = 1.0) -> float:
    """Return SAD ``akang`` for the integrated complex K1+iSK1 field."""
    value = complex(k1, sk1) * length
    if value.imag == 0.0:
        return np.pi / 2.0 if value.real < 0.0 else 0.0
    return 0.5 * np.arctan2(value.imag, value.real)


def sad_k1_fringe_taylor_coeffs(
        a: float, b: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build the unrotated zero-BZ SAD K1 soft-edge Taylor coefficients.

    This is the second-order expansion of SAD's non-polynomial fringe kick
    about delta=0. Call it with the face's signed map coefficient: ``a`` at an
    entrance and ``-a`` at an exit; ``b`` is unchanged. The expansion uses
    Xsuite ``pzeta`` as SAD ``delta``, which is exact only as beta0 approaches
    one. It is validated for the electron/positron lattices targeted here, not
    for lower-beta0 species.
    """
    ea, eam = np.exp(a), np.exp(-a)

    k = np.zeros(6)
    R = np.zeros((6, 6))
    T = np.zeros((6, 6, 6))

    R[0, 0] = ea
    R[0, 1] = b
    R[1, 1] = eam
    R[2, 2] = eam
    R[2, 3] = -b
    R[3, 3] = ea
    R[4, 4] = 1.0
    R[5, 5] = 1.0

    T[0, 0, 5] = T[0, 5, 0] = -a * ea / 2.0
    T[0, 1, 5] = T[0, 5, 1] = -b
    T[1, 1, 5] = T[1, 5, 1] = a * eam / 2.0
    T[2, 2, 5] = T[2, 5, 2] = a * eam / 2.0
    T[2, 3, 5] = T[2, 5, 3] = b
    T[3, 3, 5] = T[3, 5, 3] = -a * ea / 2.0
    T[4, 1, 1] = -b * eam * (1.0 + a / 2.0)
    T[4, 3, 3] = b * ea * (1.0 - a / 2.0)
    T[4, 0, 1] = T[4, 1, 0] = -a / 2.0
    T[4, 2, 3] = T[4, 3, 2] = a / 2.0
    return k, R, T


def rotate_sad_k1_fringe_taylor_map(
        frame_rotation: float,
        k: np.ndarray,
        R: np.ndarray,
        T: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Conjugate a SAD K1 fringe map into the external transverse frame.

    ``frame_rotation`` is SAD's ``ROTATE + akang(K1+i*SK1)`` angle, used with
    SAD's sign directly. It is independent of the opposite sign convention
    used by Xsuite's ``rot_s_rad`` element field.
    """
    c, s = np.cos(frame_rotation), np.sin(frame_rotation)
    rotate_in = np.eye(6)
    rotate_in[0, 0], rotate_in[0, 2] = c, -s
    rotate_in[1, 1], rotate_in[1, 3] = c, -s
    rotate_in[2, 0], rotate_in[2, 2] = s, c
    rotate_in[3, 1], rotate_in[3, 3] = s, c
    rotate_out = rotate_in.T

    k_new = rotate_out @ k
    R_new = rotate_out @ R @ rotate_in
    T_new = np.einsum("ia,abc,bj,ck->ijk", rotate_out, T, rotate_in, rotate_in)
    return k_new, R_new, T_new


def new_sad_k1_fringe_map(
        environment: xt.Environment,
        name: str,
        a: float,
        b: float,
        frame_rotation: float) -> None:
    """Create one zero-BZ SAD K1 fringe map with reversal metadata."""
    k, R, T = rotate_sad_k1_fringe_taylor_map(
        frame_rotation, *sad_k1_fringe_taylor_coeffs(a, b))
    environment.new(
        name        = name,
        prototype   = xt.SecondOrderTaylorMap,
        length      = 0.0,
        k           = k,
        R           = R,
        T           = T,
        _sad_k1_fringe_a              = a,
        _sad_k1_fringe_b              = b,
        _sad_k1_fringe_frame_rotation = frame_rotation)


def get_sad_k1_fringe_metadata(element) -> tuple[float, float, float] | None:
    """Read current metadata, accepting the pre-0.4 legacy QUAD names."""
    if hasattr(element, "_sad_k1_fringe_a"):
        return (
            element._sad_k1_fringe_a,
            element._sad_k1_fringe_b,
            element._sad_k1_fringe_frame_rotation)
    if hasattr(element, "_sad_quad_fringe_a"):
        return (
            element._sad_quad_fringe_a,
            element._sad_quad_fringe_b,
            element._sad_quad_fringe_theta)
    return None


def set_sad_k1_fringe_a(element, a: float) -> None:
    """Update the active metadata spelling after a reversal."""
    if hasattr(element, "_sad_k1_fringe_a"):
        element._sad_k1_fringe_a = a
    else:
        element._sad_quad_fringe_a = a
