"""
================================================================================
SAD syntax assumptions: SOL element
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-23
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
# See tests/sad/README.md's "SOL structural requirement" for the
# pairing/BOUND/GEO rules these probes check.
################################################################################
def test_sol_single_no_bound_rejects(sad_rejects):
    """
    A SOL with BZ but no BOUND is not part of a bound pair and should be
    rejected.
    """
    sad_rejects(
        "SOL SL1 = (BZ=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_single_element_rejects(sad_rejects):
    """
    A single BOUND SOL with no matching partner (unpaired) should be
    rejected.
    """
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 END);")

def test_sol_pair_no_drift_accepts(sad_accepts):
    """
    A BOUND SOL pair with no elements between them (zero-length solenoid
    region) should be accepted.
    """
    sad_accepts(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 SL2 END);")

def test_sol_pair_no_geo_rejects(sad_rejects):
    """
    A BOUND SOL pair with no GEO=1 on the entrance solenoid should be
    rejected: SAD exits 0, but the Twiss output contains Mathematica
    undefined symbols (e.g. `medium`, `$DefaultFontWeight`) -- a
    physics-level failure that twiss_sad detects and raises as ValueError.
    """
    sad_rejects(
        "SOL SL1 = (BZ=0.1 BOUND=1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_pair_with_drift_and_geo_accepts(sad_accepts):
    """
    A BOUND SOL pair with a drift between them and GEO=1 on the entrance
    should be accepted.
    """
    sad_accepts(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_three_element_inner_no_bound_accepts(sad_accepts):
    """
    A BOUND SOL pair with a third, un-BOUND SOL nested between them (an
    interior field-only solenoid) should be accepted.
    """
    sad_accepts(
        "SOL SL1 = (BZ=0.1 BOUND=1 GEO=1);\n"
        "DRIFT D0 = (L=0.5);\n"
        "SOL SL_MID = (BZ=0.1);\n"
        "DRIFT D1 = (L=0.5);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL_MID D1 SL2 END);")

################################################################################
# Accepted / Rejected parameters (SOL + DRIFT + SOL with GEO=1 on entrance as
# baseline)
#
# See tests/sad/README.md's "Parameter matrix" for the accepted/rejected
# table this parametrization transcribes.
################################################################################
ACCEPTED_PARAMS = [
    pytest.param("",              "",           id = "bz"),
    pytest.param(" DX=0.001",     "",           id = "dx"),
    pytest.param(" DY=0.001",     "",           id = "dy"),
    pytest.param(" DISFRIN=1",    " DISFRIN=1", id = "disfrin"),
    pytest.param(" F1=0.05",      "",           id = "f1"),
]

@pytest.mark.parametrize("sl1_extra,sl2_extra", ACCEPTED_PARAMS)
def test_sol_accepts(sad_accepts, sl1_extra, sl2_extra):
    """
    SAD's SOL element should accept BZ, DX, DY, DISFRIN, and F1 (a
    red herring for the orbital fringe kick -- SAD's own documentation
    states F1 only affects the emittance/radiation calculation) in a
    valid BOUND pair.
    """
    sad_accepts(
        f"SOL SL1 = (BZ=0.1 BOUND=1 GEO=1{sl1_extra});\n"
        "DRIFT D0 = (L=1.0);\n"
        f"SOL SL2 = (BZ=0.0 BOUND=1{sl2_extra});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

REJECTED_PARAMS = [
    pytest.param("ANGLE=0.01",  id = "angle"),
    pytest.param("K0=0.1",      id = "k0"),
    pytest.param("SK0=0.1",     id = "sk0"),
    pytest.param("K1=0.1",      id = "k1"),
    pytest.param("SK1=0.1",     id = "sk1"),
    pytest.param("K2=0.1",      id = "k2"),
    pytest.param("SK2=0.1",     id = "sk2"),
    pytest.param("K3=0.1",      id = "k3"),
    pytest.param("SK3=0.1",     id = "sk3"),
    pytest.param("K4=0.1",      id = "k4"),
    pytest.param("SK4=0.1",     id = "sk4"),
    pytest.param("HARM=1000",   id = "harm"),
    pytest.param("FREQ=400E6",  id = "freq"),
    pytest.param("ROTATE=0.1",  id = "rotate"),
    pytest.param("F2=0.1",      id = "f2"),
    pytest.param("FRINGE=1",    id = "fringe"),
    pytest.param("FB1=0.1",     id = "fb1"),
    pytest.param("FB2=0.1",     id = "fb2"),
    pytest.param("F1K1F=0.1",   id = "f1k1f"),
    pytest.param("F2K1F=0.1",   id = "f2k1f"),
    pytest.param("F1K1B=0.1",   id = "f1k1b"),
    pytest.param("F2K1B=0.1",   id = "f2k1b"),
]

@pytest.mark.parametrize("param", REJECTED_PARAMS)
def test_sol_rejects(sad_rejects, param):
    """
    SAD's SOL element should reject bending (ANGLE), field-order
    (K0-K4/SK0-SK4), rotation, RF parameters, and FRINGE/F2/FB1/FB2/
    F1K1x -- SOL has no FRMD/soft-edge-fringe keyword at all (only F1,
    which is itself a no-op for the orbital kick, and DISFRIN).
    """
    sad_rejects(
        f"SOL SL1 = (BZ=0.1 BOUND=1 GEO=1 {param});\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0 BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

################################################################################
# Effect on Twiss and tracking
#
# See tests/sad/README.md's "SOL's BZ" bullet for why this coupling persists
# past the exit fringe, unlike a pure geometric GEO/DX frame shift.
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

################################################################################
# Hard-edge fringe field (DISFRIN) -- see docs/reference/sad-behaviour.md
################################################################################
def _track_sol_disfrin_probe(tmp_path, bz, disfrin_suffix, name):
    """
    Track a single off-axis particle through a BOUND SOL pair and return
    the track_sad result.
    """
    lat = tmp_path / name
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        f"SOL SOL_IN  = (BZ={bz} BOUND=1 GEO=1{disfrin_suffix});\n"
        "DRIFT SOL_DRIFT = (L=1.0);\n"
        f"SOL SOL_OUT = (BZ={bz} BOUND=1{disfrin_suffix});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SOL_IN SOL_DRIFT SOL_OUT END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return track_sad(
            lattice_filepath    = lat.name,
            line_name           = "TEST",
            x_init              = np.array([0.02]),
            px_init             = np.array([0.01]),
            y_init              = np.array([0.015]),
            py_init             = np.array([-0.008]),
            zeta_init           = np.array([0.0]),
            delta_init          = np.array([0.0]),
            n_turns             = 1,
            rfsw                = False,
            with_progress       = False)
    finally:
        os.chdir(cwd)

def test_sol_disfrin_default_matches_explicit_zero(tmp_path):
    """
    DISFRIN unset defaults to DISFRIN=0 (hard-edge fringe enabled) --
    bit-identical output, not just approximately equal.
    """
    r_unset = _track_sol_disfrin_probe(tmp_path, 3.0, "", "sol_disfrin_unset.sad")
    r_zero  = _track_sol_disfrin_probe(tmp_path, 3.0, " DISFRIN=0", "sol_disfrin_zero.sad")
    assert r_unset["px"][0] == pytest.approx(r_zero["px"][0], abs=1e-15), (
        "DISFRIN unset should default to DISFRIN=0 (hard-edge fringe "
        "enabled), bit-identically.")

def test_sol_disfrin_is_boolean(tmp_path):
    """
    DISFRIN is a strict boolean gate on a SOL, same as on BEND/QUAD/
    SEXT/OCT/MULT: any nonzero value disables the hard-edge fringe
    identically.
    """
    disfrin_1 = _track_sol_disfrin_probe(tmp_path, 3.0, " DISFRIN=1", "sol_disfrin_bool_1.sad")["px"][0]
    for disfrin in (2, -1, 3, 0.5):
        r = _track_sol_disfrin_probe(tmp_path, 3.0, f" DISFRIN={disfrin}", f"sol_disfrin_bool_{disfrin}.sad")
        assert r["px"][0] == pytest.approx(disfrin_1, abs=1e-15), (
            f"DISFRIN={disfrin} should disable the hard-edge fringe "
            "identically to DISFRIN=1 -- DISFRIN is boolean, not graded.")

def test_sol_disfrin_hard_edge_matches_sad_reference_values(tmp_path):
    """
    Pinned ground truth: BZ=3.0 solenoid pair, x=0.02/px=0.01/y=0.015/
    py=-0.008 on entry, with the hard-edge fringe enabled (DISFRIN=0/
    unset) and disabled (DISFRIN=1). Real SAD binary outputs, recorded
    once and locked in.
    """
    r_on  = _track_sol_disfrin_probe(tmp_path, 3.0, "", "sol_disfrin_ref_on.sad")
    r_off = _track_sol_disfrin_probe(tmp_path, 3.0, " DISFRIN=1", "sol_disfrin_ref_off.sad")

    assert r_on["px"][0] == pytest.approx(0.00018003589294800595, rel=1e-6), (
        "SAD's px with the hard-edge fringe enabled no longer matches "
        "the pinned reference value.")
    assert r_off["px"][0] == pytest.approx(0.00018036706284639748, rel=1e-6), (
        "SAD's px with the hard-edge fringe disabled (DISFRIN=1) no "
        "longer matches the pinned reference value.")
