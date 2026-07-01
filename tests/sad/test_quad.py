"""
================================================================================
SAD syntax assumptions: QUAD element
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-24
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import os

import numpy as np
import pytest

from sad2xs.sad_helpers import track_sad, twiss_sad

################################################################################
# Accepted parameters
################################################################################
def test_quad_accepts_k1(sad_accepts):
    sad_accepts(
        "QUAD Q1 = (L=1.0 K1=0.2);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_accepts_dx(sad_accepts):
    sad_accepts(
        "QUAD Q1 = (L=1.0 DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_accepts_dy(sad_accepts):
    sad_accepts(
        "QUAD Q1 = (L=1.0 DY=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_accepts_rotate(sad_accepts):
    sad_accepts(
        "QUAD Q1 = (L=1.0 ROTATE=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

################################################################################
# Rejected parameters
################################################################################
def test_quad_rejects_angle(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_k0(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 K0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_sk0(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 SK0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_sk1(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 SK1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_k2(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 K2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_sk2(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 SK2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_k3(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 K3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_sk3(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 SK3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_k4(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 K4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_sk4(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 SK4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_harm(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 HARM=1000);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_freq(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 FREQ=400E6);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_rejects_bz(sad_rejects):
    sad_rejects(
        "QUAD Q1 = (L=1.0 BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

################################################################################
# Thin quad (no length) behaviour
#
# K1 in a no-L QUAD is an integrated quadrupole strength: it affects BOTH
# Twiss (linear focusing) AND tracking (a direct px kick), verified by both
# tests below — same pattern as BEND's K1 (see test_bend.py).
################################################################################
def test_quad_without_length_is_accepted_by_sad(sad_accepts):
    """
    SAD accepts a QUAD with K1 but no L parameter (thin/integrated quadrupole).
    The converter handles this via ele_vars.get('l', 0.0) defaulting to zero.
    """
    sad_accepts(
        "QUAD Q1 = (K1=0.2);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_without_length_k1_affects_twiss(tmp_path):
    """
    K1 in a no-L SAD QUAD is an integrated quadrupole strength.
    Twiss betx must differ between K1=0 and K1=0.5, confirming the element
    actively focuses the beam rather than acting as a passive placeholder.
    """
    def run(k1, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"QUAD Q = (K1={k1});\n"
            "DRIFT D = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START D Q D END);\n")
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            return twiss_sad(
                lattice_filepath    = lat.name,
                line_name           = "TEST",
                calc6d              = False,
                closed              = False,
                additional_commands = "")
        finally:
            os.chdir(cwd)

    tw_ref = run(0.0, "quad_k1_0.sad")
    tw_k1  = run(0.5, "quad_k1_nonzero.sad")
    assert tw_k1["betx"][-1] != pytest.approx(tw_ref["betx"][-1]), (
        "K1 in a no-L QUAD should focus the beam and change Twiss betx.")

def test_quad_without_length_k1_gives_linear_kick(tmp_path):
    """
    K1 in a no-L SAD QUAD gives a direct px kick on an off-axis particle
    (px kick = -K1*x), verified via tracking as the direct-kick complement
    to the Twiss test above — mirrors BEND's K1 tracking test.
    """
    def run(k1, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"QUAD Q = (K1={k1});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START Q END);\n")
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            return track_sad(
                lattice_filepath    = lat.name,
                line_name           = "TEST",
                x_init              = np.array([0.001]),
                px_init             = np.array([0.0]),
                y_init              = np.array([0.0]),
                py_init             = np.array([0.0]),
                zeta_init           = np.array([0.0]),
                delta_init          = np.array([0.0]),
                n_turns             = 1,
                rfsw                = False,
                with_progress       = False)
        finally:
            os.chdir(cwd)

    r_ref = run(0.0, "quad_k1_0_track.sad")
    r_k1  = run(0.5, "quad_k1_nonzero_track.sad")
    assert r_k1["px"][0] != pytest.approx(r_ref["px"][0]), (
        "K1 in a no-L QUAD should deflect an off-axis particle (kick = -K1*x).")
