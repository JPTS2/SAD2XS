"""
================================================================================
SAD syntax assumptions: OCT element
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
def test_oct_accepts_k3(sad_accepts):
    sad_accepts(
        "OCT O1 = (L=1.0 K3=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_accepts_dx(sad_accepts):
    sad_accepts(
        "OCT O1 = (L=1.0 DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_accepts_dy(sad_accepts):
    sad_accepts(
        "OCT O1 = (L=1.0 DY=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_accepts_rotate(sad_accepts):
    sad_accepts(
        "OCT O1 = (L=1.0 ROTATE=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

################################################################################
# Rejected parameters
################################################################################
def test_oct_rejects_angle(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_k0(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 K0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_sk0(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 SK0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_k1(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 K1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_sk1(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 SK1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_k2(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 K2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_sk2(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 SK2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_sk3(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 SK3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_k4(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 K4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_sk4(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 SK4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_harm(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 HARM=1000);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_freq(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 FREQ=400E6);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_bz(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0 BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

################################################################################
# Thin oct (no length) behaviour
################################################################################
def test_oct_without_length_is_accepted_by_sad(sad_accepts):
    """
    SAD accepts an OCT with K3 but no L parameter (thin/integrated octupole).
    The converter handles this via ele_vars.get('l', 0.0) defaulting to zero.
    """
    sad_accepts(
        "OCT O1 = (K3=0.05);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_without_length_k3_has_no_effect_on_twiss_at_zero_orbit(tmp_path):
    """
    K3 in a no-L SAD OCT has exactly zero effect on Twiss betx at zero orbit:
    the reference particle stays at x=0 (an octupole has no dipole term), so
    its linear neighbourhood is the identity regardless of K3 — same
    reasoning as SEXT's K2 (see test_sext.py).
    """
    def run(k3, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"OCT O = (K3={k3});\n"
            "DRIFT D = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START D O D END);\n")
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

    tw_ref = run(0.0, "oct_k3_0_twiss.sad")
    tw_k3  = run(1.0, "oct_k3_nonzero_twiss.sad")
    assert tw_k3["betx"][-1] == pytest.approx(tw_ref["betx"][-1], abs=1e-9), (
        "K3 in a no-L OCT should have no effect on Twiss betx at zero orbit.")

def test_oct_without_length_k3_gives_cubic_kick(tmp_path):
    """
    K3 in a no-L SAD OCT is an integrated octupole strength: an off-axis
    particle receives a px kick proportional to K3*x^3 — verified via
    tracking, the direct-kick complement to the Twiss test above.
    """
    def run(k3, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"OCT O = (K3={k3});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START O END);\n")
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

    r_ref = run(0.0, "oct_k3_0.sad")
    r_k3  = run(1.0, "oct_k3_nonzero.sad")
    assert r_k3["px"][0] != pytest.approx(r_ref["px"][0]), (
        "K3 in a no-L OCT should deflect an off-axis particle "
        "(integrated kick proportional to K3*x^3).")
