"""
================================================================================
SAD syntax assumptions: SOL element
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
# Structural probes: SOL pairing and BOUND requirement
#
# From fcc_sol_dummy.sad: SOL is a zero-length fringe element. The physical
# length lives in a DRIFT placed between an entrance SOL (GEO=1) and an exit
# SOL (no GEO). BOUND=1 is required on the entrance and exit SOL elements.
# Internal SOL elements (if any) do not require BOUND.
#
# Minimum valid pattern: SOL(GEO=1, BOUND=1) + DRIFT + SOL(BOUND=1)
################################################################################
def test_sol_single_no_bound_rejects(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_single_element_rejects(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 END);")

def test_sol_pair_no_drift_accepts(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 SL2 END);")

def test_sol_pair_no_geo_rejects(sad_rejects):
    # SAD exits 0 but the Twiss output contains Mathematica undefined symbols
    # (e.g. `medium`, `$DefaultFontWeight`) when GEO is absent — a physics-level
    # failure that twiss_sad now detects and raises as ValueError.
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_pair_with_drift_and_geo_accepts(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_three_element_inner_no_bound_accepts(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1);\n"
        "DRIFT D0 = (L=0.5);\n"
        "SOL SL_MID = (BZ=0.1);\n"
        "DRIFT D1 = (L=0.5);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL_MID D1 SL2 END);")

################################################################################
# Accepted parameters (SOL + DRIFT + SOL with GEO=1 on entrance as baseline)
################################################################################
def test_sol_accepts_bz(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_accepts_dx(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 DX=0.001);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_accepts_dy(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 DY=0.001);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")


################################################################################
# Rejected parameters
################################################################################
def test_sol_rejects_angle(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 ANGLE=0.01);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_k0(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 K0=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_sk0(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 SK0=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_k1(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 K1=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_sk1(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 SK1=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_k2(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 K2=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_sk2(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 SK2=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_k3(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 K3=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_sk3(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 SK3=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_k4(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 K4=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_sk4(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 SK4=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_harm(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 HARM=1000);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_freq(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 FREQ=400E6);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_rotate(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 ROTATE=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

################################################################################
# Effect on Twiss and tracking
#
# A live BZ solenoid permanently rotates x-y coupling into the downstream
# optics (Twiss R1-R4 nonzero from the exit fringe onward — unlike the pure
# geometric GEO/DX frame shift, this coupling is NOT undone by the exit
# fringe, confirmed empirically at SOL_END/SOL_OUT/END all showing the same
# nonzero R1/R4). Tracking independently confirms the same conclusion via a
# direct x->y kick on an off-axis particle.
################################################################################
def test_sol_bz_gives_nonzero_twiss_coupling(tmp_path):
    """
    A live BZ solenoid pair gives nonzero Twiss coupling terms (R1, R4)
    at END; BZ=0 gives exactly zero coupling.
    """
    def run(bz, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"SOL SOL_IN  = (BZ={bz} BOUND=1 GEO=1);\n"
            "DRIFT SOL_DRIFT = (L=1.0);\n"
            f"SOL SOL_OUT = (BZ={bz} BOUND=1);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START SOL_IN SOL_DRIFT SOL_OUT END);\n")
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

    tw_0  = run(0.0, "sol_bz_0_twiss.sad")
    tw_bz = run(3.0, "sol_bz_nonzero_twiss.sad")
    assert tw_0["R1"][-1] == pytest.approx(0.0, abs=1e-9), (
        "BZ=0 should give exactly zero Twiss coupling (R1).")
    assert tw_bz["R1"][-1] != pytest.approx(0.0, abs=1e-9), (
        "A live BZ solenoid should give nonzero Twiss coupling (R1) at END — "
        "unlike the geometric GEO/DX frame shift, coupling is not undone by "
        "the exit fringe.")

def test_sol_bz_gives_nonzero_xy_coupling_in_tracking(tmp_path):
    """
    A live BZ solenoid pair deflects an off-axis (x-offset) particle into y
    during tracking, independently confirming the Twiss coupling result
    above via a direct single-particle check.
    """
    def run(bz, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"SOL SOL_IN  = (BZ={bz} BOUND=1 GEO=1);\n"
            "DRIFT SOL_DRIFT = (L=1.0);\n"
            f"SOL SOL_OUT = (BZ={bz} BOUND=1);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START SOL_IN SOL_DRIFT SOL_OUT END);\n")
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

    r_0  = run(0.0, "sol_bz_0_track.sad")
    r_bz = run(3.0, "sol_bz_nonzero_track.sad")
    assert r_0["y"][0] == pytest.approx(0.0, abs=1e-9), (
        "BZ=0 should give exactly zero x->y coupling in tracking.")
    assert r_bz["y"][0] != pytest.approx(0.0, abs=1e-9), (
        "A live BZ solenoid should deflect an off-axis particle into y "
        "during tracking.")
