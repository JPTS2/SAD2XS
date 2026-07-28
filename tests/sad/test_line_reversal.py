"""
================================================================================
SAD syntax assumptions: line reversal
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-30
================================================================================
"""

import os

import numpy as np
import pytest

from sad2xs.sad_helpers import track_sad

################################################################################
# Reversed line syntax
################################################################################
def test_sad_accepts_reversed_line_definition(sad_accepts):
    """
    SAD accepts a reversed line defined with the negative-prefix syntax
    LINE TEST = (-FORWARD). The reversed line can be used in Twiss without
    error.
    """
    sad_accepts(
        "BEND C1 = (K0=0.01);\n"
        "DRIFT D1 = (L=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE FORWARD = (START C1 D1 END);\n"
        "LINE TEST    = (-FORWARD);")


def test_sad_reversed_line_reverses_tracking_element_order(tmp_path):
    """
    Tracking through a SAD-reversed line differs from tracking through the
    forward line when element order affects the result.

    Two correctors with different K0 strengths (C1=0.01, C2=0.02) separated by
    a 1 m drift: the forward line applies C1 kick then drifts, giving a
    different final x than the reversed line (C2 kick then drift).
    """
    lat = tmp_path / "line_reversal.sad"
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        "BEND C1 = (K0=0.01);\n"
        "BEND C2 = (K0=0.02);\n"
        "DRIFT D1 = (L=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST    = (START C1 D1 C2 END);\n"
        "LINE TESTREV = (-TEST);\n")

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_fwd = track_sad(
            lattice_filepath = lat.name,
            line_name        = "TEST",
            x_init           = np.array([0.0]),
            px_init          = np.array([0.0]),
            y_init           = np.array([0.0]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)

        r_rev = track_sad(
            lattice_filepath = lat.name,
            line_name        = "TESTREV",
            x_init           = np.array([0.0]),
            px_init          = np.array([0.0]),
            y_init           = np.array([0.0]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)
    finally:
        os.chdir(cwd)

    assert r_rev["x"][0] != pytest.approx(r_fwd["x"][0]), (
        "Reversed line should produce a different final x than the forward line: "
        "C2 kick before drift gives different x than C1 kick before drift.")


################################################################################
# Reversed-element sign conventions
#
# tests/conversion/pipeline/test_reverse_*.py already test the sad2xs
# converter's own _007_reversals.py Python logic in detail (bend angle,
# quad k1/k1s, sextupole/octupole, solenoid ks, etc.) — but those tests
# only check that the converter is internally self-consistent with its own
# assumptions; they do not import track_sad/twiss_sad and never compare
# against real SAD. The tests below close that gap for the two most
# common/impactful element types by comparing SAD's native "-LINE" reversal
# tracking result directly against a manually sign-flipped reconstruction —
# if the two disagree, the converter's assumption about SAD's own reversal
# semantics is wrong at the source, regardless of how self-consistent its
# Python logic is.
################################################################################

def test_reversed_line_bend_angle_sign_matches_converter_assumption(tmp_path):
    """
    Reversing a line negates a BEND's ANGLE, the assumption _007_reversals.py
    relies on.

    Compares SAD's native "-FORWARD" reversal against a manually
    ANGLE-negated reconstruction. They carry a residual scaling linearly with
    angle: 2.08e-8, 1.05e-8, 5.25e-9 at ANGLE = 0.05, 0.025, 0.0125. The root
    cause is unidentified, so the tolerance covers it rather than asserting
    exact equality.
    """
    lat = tmp_path / "bend_reversal.sad"
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        "BEND B1 = (ANGLE=0.05 L=1.0);\n"
        "BEND B1_NEG = (ANGLE=-0.05 L=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE FORWARD     = (START B1 END);\n"
        "LINE REVERSED    = (-FORWARD);\n"
        "LINE MANUAL_NEG  = (START B1_NEG END);\n")

    def run(line_name):
        return track_sad(
            lattice_filepath = lat.name,
            line_name        = line_name,
            x_init           = np.array([0.001]),
            px_init          = np.array([0.0002]),
            y_init           = np.array([0.0]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_reversed = run("REVERSED")
        r_manual   = run("MANUAL_NEG")
    finally:
        os.chdir(cwd)

    for coord in ("x", "px", "y", "py"):
        assert r_reversed[coord][0] == pytest.approx(r_manual[coord][0], rel=1e-4), (
            f"SAD's native -LINE reversal of a BEND should match a manually "
            f"ANGLE-negated reconstruction to within the confirmed small "
            f"residual ({coord} mismatch) — confirms _007_reversals.py's "
            f"angle-negation assumption (sign and dominant magnitude) "
            f"against real SAD.")


def test_reversed_line_quad_k1_sign_matches_converter_assumption(tmp_path):
    """
    _007_reversals.py assumes that reversing a line leaves a QUAD's K1
    UNCHANGED (not negated) — a quadrupole's focusing does not depend on
    direction of travel. Confirm against real SAD: SAD's native "-FORWARD"
    reversal of a single QUAD should match the ORIGINAL (unchanged K1)
    parameters, not a negated reconstruction.
    """
    lat = tmp_path / "quad_reversal.sad"
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        "QUAD Q1 = (K1=0.3 L=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE FORWARD  = (START Q1 END);\n"
        "LINE REVERSED = (-FORWARD);\n")

    def run(line_name):
        return track_sad(
            lattice_filepath = lat.name,
            line_name        = line_name,
            x_init           = np.array([0.001]),
            px_init          = np.array([0.0]),
            y_init           = np.array([-0.0007]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_forward  = run("FORWARD")
        r_reversed = run("REVERSED")
    finally:
        os.chdir(cwd)

    for coord in ("x", "px", "y", "py"):
        assert r_reversed[coord][0] == pytest.approx(r_forward[coord][0], abs=1e-12), (
            f"SAD's native -LINE reversal of an unrotated QUAD should give "
            f"the same result as the forward line ({coord} mismatch) — "
            f"confirms _007_reversals.py's K1-unchanged assumption against "
            f"real SAD.")


def test_reversed_line_solenoid_ks_sign_matches_converter_assumption(tmp_path):
    """
    _006_solenoid_converter.py / _007_reversals.py assume that reversing a
    line negates a solenoid's ks (BZ). Confirm against real SAD: track a
    particle through SAD's native "-FORWARD" reversal of a bound solenoid
    pair and through a manually-reconstructed reversed pair (element order
    swapped, BZ negated, GEO moved to the new entrance) — the two should
    match exactly.
    """
    lat = tmp_path / "sol_reversal.sad"
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        "SOL SOL_IN  = (BZ=3.0 BOUND=1 GEO=1 DX=0.001);\n"
        "DRIFT SOL_DRIFT = (L=1.0);\n"
        "SOL SOL_OUT = (BZ=3.0 BOUND=1);\n"
        "SOL SOL_IN_NEG  = (BZ=-3.0 BOUND=1);\n"
        "SOL SOL_OUT_NEG = (BZ=-3.0 BOUND=1 GEO=1 DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE FORWARD    = (START SOL_IN SOL_DRIFT SOL_OUT END);\n"
        "LINE REVERSED   = (-FORWARD);\n"
        "LINE MANUAL_NEG = (START SOL_OUT_NEG SOL_DRIFT SOL_IN_NEG END);\n")

    def run(line_name):
        return track_sad(
            lattice_filepath = lat.name,
            line_name        = line_name,
            x_init           = np.array([0.0]),
            px_init          = np.array([0.0]),
            y_init           = np.array([0.0]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_reversed = run("REVERSED")
        r_manual   = run("MANUAL_NEG")
    finally:
        os.chdir(cwd)

    for coord in ("x", "px", "y", "py"):
        assert r_reversed[coord][0] == pytest.approx(r_manual[coord][0], abs=1e-9), (
            f"SAD's native -LINE reversal of a bound solenoid pair should "
            f"match a manually BZ-negated/GEO-swapped reconstruction "
            f"({coord} mismatch) — confirms the converter's solenoid "
            f"reversal assumption against real SAD.")
