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
