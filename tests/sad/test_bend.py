"""
================================================================================
SAD syntax assumptions: BEND element
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-24
================================================================================
"""

import os

import numpy as np
import pytest

from sad2xs.sad_helpers import track_sad, twiss_sad

################################################################################
# Accepted parameters
################################################################################
def test_bend_accepts_angle(sad_accepts):
    sad_accepts(
        "BEND B1 = (L=1.0, ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_accepts_k0(sad_accepts):
    sad_accepts(
        "BEND B1 = (L=1.0, K0=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_accepts_k1(sad_accepts):
    sad_accepts(
        "BEND B1 = (L=1.0, K1=0.2);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_accepts_dx(sad_accepts):
    sad_accepts(
        "BEND B1 = (L=1.0, DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_accepts_dy(sad_accepts):
    sad_accepts(
        "BEND B1 = (L=1.0, DY=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_accepts_rotate(sad_accepts):
    sad_accepts(
        "BEND B1 = (L=1.0, ROTATE=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

################################################################################
# Rejected parameters
################################################################################
def test_bend_rejects_sk0(sad_rejects):
    sad_rejects(
        "BEND B1 = (L=1.0, SK0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_rejects_sk1(sad_rejects):
    sad_rejects(
        "BEND B1 = (L=1.0, SK1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_rejects_k2(sad_rejects):
    sad_rejects(
        "BEND B1 = (L=1.0, K2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_rejects_sk2(sad_rejects):
    sad_rejects(
        "BEND B1 = (L=1.0, SK2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_rejects_k3(sad_rejects):
    sad_rejects(
        "BEND B1 = (L=1.0, K3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_rejects_sk3(sad_rejects):
    sad_rejects(
        "BEND B1 = (L=1.0, SK3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_rejects_k4(sad_rejects):
    sad_rejects(
        "BEND B1 = (L=1.0, K4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_rejects_sk4(sad_rejects):
    sad_rejects(
        "BEND B1 = (L=1.0, SK4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_rejects_harm(sad_rejects):
    sad_rejects(
        "BEND B1 = (L=1.0, HARM=1000);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_rejects_freq(sad_rejects):
    sad_rejects(
        "BEND B1 = (L=1.0, FREQ=400E6);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_rejects_bz(sad_rejects):
    sad_rejects(
        "BEND B1 = (L=1.0, BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_bend_without_length_is_accepted_by_sad(sad_accepts):
    """
    SAD accepts a BEND with a non-zero ANGLE but no L parameter.
    SAD treats it identically to L=0 (thin/integrated bend).
    The converter should match this behaviour rather than raising ValueError.
    """
    sad_accepts(
        "BEND B1 = (ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

def test_corrector_without_length_is_accepted_by_sad(sad_accepts):
    """
    SAD accepts a BEND used as a corrector (K0 only, no ANGLE, no L).
    The converter should convert this to a thin Multipole, not a Marker.
    """
    sad_accepts(
        "BEND C1 = (K0=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_bend_without_length_k1_gives_quadrupole_kick(tmp_path):
    """
    K1 in a no-L SAD BEND is an integrated quadrupole strength: a particle
    with transverse offset x receives a px kick of -K1 * x.
    Verified via SAD tracking rather than Twiss (SAD Twiss does not propagate
    K1 for no-L bends, but tracking does).
    """
    def run(k1, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"BEND B = (ANGLE=0.0, K1={k1});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START B END);\n")
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

    r_ref = run(0.0, "bend_k1_0.sad")
    r_k1  = run(0.5, "bend_k1_nonzero.sad")
    assert r_k1["px"][0] != pytest.approx(r_ref["px"][0]), (
        "K1 in a no-L BEND should deflect an off-axis particle (integrated kick = -K1*x).")

def test_corrector_without_length_k0_gives_orbit_kick(tmp_path):
    """
    K0 in a no-L SAD BEND (corrector) is an integrated horizontal kick.
    A particle tracked on-axis should exit with px = K0.
    """
    def run(k0, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"BEND C = (K0={k0});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START C END);\n")
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            return track_sad(
                lattice_filepath    = lat.name,
                line_name           = "TEST",
                x_init              = np.array([0.0]),
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

    r_ref = run(0.00, "corr_k0_0.sad")
    r_k0  = run(0.01, "corr_k0_nonzero.sad")
    assert r_k0["px"][0] != pytest.approx(r_ref["px"][0]), (
        "K0 in a no-L corrector should produce a nonzero horizontal orbit kick.")
