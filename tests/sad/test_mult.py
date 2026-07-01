"""
================================================================================
SAD syntax assumptions: MULT element
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
# MULT is the general multipole element — accepts all Kn/SKn, geometry,
# and RF parameters (K. Oide: "almighty, even acceleration can be included").
################################################################################
def test_mult_accepts_angle(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_k0(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 K0=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_sk0(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 SK0=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_k1(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 K1=0.2);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_sk1(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 SK1=0.2);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_k2(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 K2=0.5);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_sk2(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 SK2=0.5);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_k3(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 K3=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_sk3(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 SK3=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_k4(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 K4=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_sk4(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 SK4=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_dx(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_dy(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 DY=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_rotate(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 ROTATE=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_harm(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 HARM=1000);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

def test_mult_accepts_freq(sad_accepts):
    sad_accepts(
        "MULT M1 = (L=1.0 FREQ=400E6);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

################################################################################
# Rejected parameters
################################################################################
def test_mult_rejects_bz(sad_rejects):
    sad_rejects(
        "MULT M1 = (L=1.0 BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

################################################################################
# Effect on Twiss and tracking
#
# MULT's K1 field acts as a quadrupole (same as QUAD's K1, see test_quad.py):
# it both focuses the beam (changes Twiss betx) and gives a direct px kick
# on an off-axis particle in tracking. This establishes that MULT's field
# parameters are physically live, not just syntactically accepted.
################################################################################
def test_mult_k1_affects_twiss(tmp_path):
    """
    K1 on a MULT element changes Twiss betx, same as QUAD's K1.
    """
    def run(k1, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"MULT M = (L=1.0 K1={k1});\n"
            "DRIFT D = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START D M D END);\n")
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

    tw_ref = run(0.0, "mult_k1_0_twiss.sad")
    tw_k1  = run(0.5, "mult_k1_nonzero_twiss.sad")
    assert tw_k1["betx"][-1] != pytest.approx(tw_ref["betx"][-1]), (
        "K1 on a MULT element should focus the beam and change Twiss betx.")

def test_mult_k1_gives_linear_kick(tmp_path):
    """
    K1 on a MULT element gives a direct px kick on an off-axis particle
    (px kick = -K1*x), the direct-kick complement to the Twiss test above.
    """
    def run(k1, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"MULT M = (L=1.0 K1={k1});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START M END);\n")
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

    r_ref = run(0.0, "mult_k1_0_track.sad")
    r_k1  = run(0.5, "mult_k1_nonzero_track.sad")
    assert r_k1["px"][0] != pytest.approx(r_ref["px"][0]), (
        "K1 on a MULT element should deflect an off-axis particle (kick = -K1*x).")

def test_mult_k0_gives_orbit_kick(tmp_path):
    """
    K0 on a MULT element gives a direct px kick on an on-axis particle
    (bend-like orbit kick, same as BEND's K0 corrector — see test_bend.py).
    """
    def run(k0, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"MULT M = (L=1.0 K0={k0});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START M END);\n")
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

    r_ref = run(0.00, "mult_k0_0_track.sad")
    r_k0  = run(0.01, "mult_k0_nonzero_track.sad")
    assert r_k0["px"][0] != pytest.approx(r_ref["px"][0]), (
        "K0 on a MULT element should give a nonzero orbit kick, same as "
        "BEND's K0 corrector.")

def test_mult_k2_has_no_effect_on_twiss_at_zero_orbit(tmp_path):
    """
    K2 on a MULT element has exactly zero effect on Twiss betx at zero
    orbit — same reasoning as SEXT's K2 (see test_sext.py): the reference
    particle stays at x=0, so its linear neighbourhood is unaffected.
    """
    def run(k2, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"MULT M = (L=1.0 K2={k2});\n"
            "DRIFT D = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START D M D END);\n")
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

    tw_ref = run(0.0, "mult_k2_0_twiss.sad")
    tw_k2  = run(0.5, "mult_k2_nonzero_twiss.sad")
    assert tw_k2["betx"][-1] == pytest.approx(tw_ref["betx"][-1], abs=1e-9), (
        "K2 on a MULT element should have no effect on Twiss betx at zero orbit.")

def test_mult_k2_gives_quadratic_kick(tmp_path):
    """
    K2 on a MULT element gives a px kick proportional to K2*x^2 on an
    off-axis particle (sextupole-like, same as SEXT's K2 — see test_sext.py).
    """
    def run(k2, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"MULT M = (L=1.0 K2={k2});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START M END);\n")
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

    r_ref = run(0.0, "mult_k2_0_track.sad")
    r_k2  = run(0.5, "mult_k2_nonzero_track.sad")
    assert r_k2["px"][0] != pytest.approx(r_ref["px"][0]), (
        "K2 on a MULT element should deflect an off-axis particle "
        "(kick proportional to K2*x^2).")

def test_mult_k3_has_no_effect_on_twiss_at_zero_orbit(tmp_path):
    """
    K3 on a MULT element has exactly zero effect on Twiss betx at zero
    orbit — same reasoning as OCT's K3 (see test_oct.py).
    """
    def run(k3, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"MULT M = (L=1.0 K3={k3});\n"
            "DRIFT D = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START D M D END);\n")
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

    tw_ref = run(0.0, "mult_k3_0_twiss.sad")
    tw_k3  = run(1.0, "mult_k3_nonzero_twiss.sad")
    assert tw_k3["betx"][-1] == pytest.approx(tw_ref["betx"][-1], abs=1e-9), (
        "K3 on a MULT element should have no effect on Twiss betx at zero orbit.")

def test_mult_k3_gives_cubic_kick(tmp_path):
    """
    K3 on a MULT element gives a px kick proportional to K3*x^3 on an
    off-axis particle (octupole-like, same as OCT's K3 — see test_oct.py).
    """
    def run(k3, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"MULT M = (L=1.0 K3={k3});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START M END);\n")
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

    r_ref = run(0.0, "mult_k3_0_track.sad")
    r_k3  = run(1.0, "mult_k3_nonzero_track.sad")
    assert r_k3["px"][0] != pytest.approx(r_ref["px"][0]), (
        "K3 on a MULT element should deflect an off-axis particle "
        "(kick proportional to K3*x^3).")
