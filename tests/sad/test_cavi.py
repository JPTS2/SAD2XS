"""
================================================================================
SAD syntax assumptions: CAVI element
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
def test_cavi_accepts_volt(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5 VOLT=0.5);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_freq(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5 FREQ=400E6);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_harm(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5 HARM=1000);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_phi(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5 PHI=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_dx(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5 DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_dy(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5 DY=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_rotate(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5 ROTATE=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

################################################################################
# Rejected parameters
################################################################################
def test_cavi_rejects_angle(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_k0(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 K0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_sk0(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 SK0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_k1(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 K1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_sk1(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 SK1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_k2(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 K2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_sk2(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 SK2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_k3(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 K3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_sk3(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 SK3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_k4(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 K4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_sk4(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 SK4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_bz(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5 BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

################################################################################
# Effect on Twiss and tracking
#
# VOLT does not perturb the 4D Twiss reference orbit (the cavity sits on the
# zero-momentum orbit in CALC4D — a real SAD/COD limitation, not a bug),
# but it does give a real, nonzero energy deviation in single-particle
# tracking. Both are asserted explicitly so neither is left as an
# unverified assumption.
################################################################################
def test_cavi_volt_does_not_affect_twiss_orbit_in_calc4d(tmp_path):
    """
    In CALC4D, VOLT should not perturb the Twiss reference orbit x: no
    off-momentum kick is applied to the reference particle in this mode.
    """
    def run(volt, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"CAVI C1 = (L=0.5 VOLT={volt} FREQ=400E6);\n"
            "DRIFT D1 = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START C1 D1 END);\n")
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

    tw_ref  = run(0.0, "cavi_volt_0_twiss.sad")
    tw_volt = run(1e5, "cavi_volt_nonzero_twiss.sad")
    assert tw_volt["x"][-1] == pytest.approx(tw_ref["x"][-1], abs=1e-9), (
        "VOLT should not perturb the Twiss reference orbit x in CALC4D.")

def test_cavi_volt_gives_nonzero_energy_deviation_in_tracking(tmp_path):
    """
    A single pass through a CAVI with VOLT != 0 should give a nonzero energy
    deviation (delta != 0) in tracking, confirming VOLT is physically live,
    not just syntactically accepted. Uses PHI = pi/4 at low momentum,
    matching the known-working setup verified in test_reference_particle.py
    (PHI = 0 was tried first and gave delta = 0 here — that combination
    needs separate investigation before being asserted as "on-crest").
    """
    def run(volt, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 0.1 GEV;\n"
            f"CAVI C1 = (L=1.0 VOLT={volt:.0f} FREQ=100000000 PHI={np.pi / 4:.6f});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START C1 END);\n")
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
                with_progress       = False)
        finally:
            os.chdir(cwd)

    r_ref  = run(0.0, "cavi_volt_0_track.sad")
    r_volt = run(1e5, "cavi_volt_nonzero_track.sad")
    assert r_volt["delta"][0] != pytest.approx(r_ref["delta"][0], abs=1e-9), (
        "VOLT != 0 should give a nonzero energy deviation in tracking.")
