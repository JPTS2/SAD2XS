"""
================================================================================
SAD syntax assumptions: MULT element
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

from sad2xs.sad_helpers import track_sad, transfer_matrix_sad, twiss_sad

################################################################################
# Accepted parameters
# MULT is the general multipole element — accepts all Kn/SKn, geometry,
# and RF parameters.
# See tests/sad/README.md's "Parameter matrix" for the full accepted/rejected
# table this parametrization transcribes.
################################################################################
ACCEPTED_PARAMS = [
    pytest.param("L=1.0 ANGLE=0.01",   id = "angle"),
    pytest.param("L=1.0 K0=0.01",      id = "k0"),
    pytest.param("L=1.0 SK0=0.01",     id = "sk0"),
    pytest.param("L=1.0 K1=0.2",       id = "k1"),
    pytest.param("L=1.0 SK1=0.2",      id = "sk1"),
    pytest.param("L=1.0 K2=0.5",       id = "k2"),
    pytest.param("L=1.0 SK2=0.5",      id = "sk2"),
    pytest.param("L=1.0 K3=1.0",       id = "k3"),
    pytest.param("L=1.0 SK3=1.0",      id = "sk3"),
    pytest.param("L=1.0 K4=1.0",       id = "k4"),
    pytest.param("L=1.0 SK4=1.0",      id = "sk4"),
    pytest.param("L=1.0 DX=0.001",     id = "dx"),
    pytest.param("L=1.0 DY=0.001",     id = "dy"),
    pytest.param("L=1.0 ROTATE=0.1",   id = "rotate"),
    pytest.param("L=1.0 HARM=1000",    id = "harm"),
    pytest.param("L=1.0 FREQ=400E6",   id = "freq"),
    pytest.param("L=1.0 FRINGE=1",     id = "fringe"),
    pytest.param("L=1.0 DISFRIN=1",    id = "disfrin"),
    pytest.param("L=1.0 K1=0.2 F1=0.02",   id = "f1"),
    pytest.param("L=1.0 K1=0.2 F2=0.01",   id = "f2"),
    pytest.param("L=1.0 ANGLE=0.1 FB1=0.05", id = "fb1"),
    pytest.param("L=1.0 ANGLE=0.1 FB2=0.05", id = "fb2"),
    pytest.param("L=1.0 K1=0.2 F1K1F=0.02", id = "f1k1f"),
    pytest.param("L=1.0 K1=0.2 F2K1F=0.01", id = "f2k1f"),
    pytest.param("L=1.0 K1=0.2 F1K1B=0.02", id = "f1k1b"),
    pytest.param("L=1.0 K1=0.2 F2K1B=0.01", id = "f2k1b"),
]

@pytest.mark.parametrize("params", ACCEPTED_PARAMS)
def test_mult_accepts(sad_accepts, params):
    """
    SAD's MULT element is the general multipole and should accept every
    Kn/SKn order, geometry, RF parameter, DISFRIN, and the FRINGE-gated
    F1/F2/FB1/FB2/F1K1F/F2K1F/F1K1B/F2K1B fringe parameters.
    """
    sad_accepts(
        f"MULT M1 = ({params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M1 END);")

################################################################################
# Rejected parameters
################################################################################
def test_mult_rejects_bz(sad_rejects):
    """
    SAD's MULT element should reject BZ -- solenoid field is SOL's own
    parameter, not part of MULT's general multipole/RF set.
    """
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

################################################################################
# RF focusing kick (VOLT) -- transverse coupling ground truth
#
# MULT (and CAVI) elements with VOLT != 0, tracked with RFSW on, apply an
# explicit transverse x/y focusing kick on top of the ordinary multipole
# kick (SAD's tmultiacc in tmulti.f) -- see docs/reference/sad-behaviour.md. Unlike
# the net energy gain (which is exactly zero at PHI=0, SAD's RF
# zero-crossing), this kick is present at every phase and grows further
# away from the crossing.
################################################################################
RF_FOCUS_MOMENTUM_GEV   = 0.05
RF_FOCUS_VOLT           = 2.0E7
RF_FOCUS_FREQ           = 2.856E9
RF_FOCUS_X_TEST         = 1.0E-3

def _mult_rf_focus_kick(tmp_path, phi: float, x: float, name: str) -> dict:
    """
    Track a single on-axis-px particle with transverse offset `x` through
    a VOLT-carrying MULT at RF phase `phi`, with RFSW on.
    """
    lat = tmp_path / name
    lat.write_text(
        f"MOMENTUM = {RF_FOCUS_MOMENTUM_GEV} GEV;\n"
        f"MULT M1 = (L=1.0 VOLT={RF_FOCUS_VOLT:.0f} FREQ={RF_FOCUS_FREQ:.0f} "
        f"PHI={phi:.6f});\n"
        "MARK START = ()\n     END = ();\n"
        "LINE TEST = (START M1 END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return track_sad(
            lattice_filepath    = lat.name,
            line_name           = "TEST",
            x_init              = np.array([x]),
            px_init             = np.array([0.0]),
            y_init              = np.array([0.0]),
            py_init             = np.array([0.0]),
            zeta_init           = np.array([0.0]),
            delta_init          = np.array([0.0]),
            n_turns             = 1,
            rfsw                = True,
            with_progress       = False)
    finally:
        os.chdir(cwd)

def test_mult_volt_gives_rf_focusing_kick_at_zero_crossing(tmp_path):
    """
    A VOLT-carrying MULT gives a nonzero x -> px kick even at PHI=0, SAD's
    RF zero-crossing, where the net energy gain is exactly zero. The
    focusing kick is not tied to net acceleration itself.
    """
    r0 = _mult_rf_focus_kick(tmp_path, 0.0, 0.0, "rf_focus_zero_x0.sad")
    r1 = _mult_rf_focus_kick(
        tmp_path, 0.0, RF_FOCUS_X_TEST, "rf_focus_zero_x1.sad")

    assert r0["delta"][0] == pytest.approx(0.0, abs=1e-9), (
        "PHI=0 should give exactly zero net energy gain (SAD's RF "
        "zero-crossing) -- otherwise this isn't testing the zero-crossing "
        "case at all.")
    assert r1["px"][0] != pytest.approx(r0["px"][0]), (
        "A VOLT-carrying MULT should give a nonzero x -> px kick even at "
        "the RF zero-crossing (PHI=0).")

def test_mult_rf_focusing_kick_grows_away_from_zero_crossing(tmp_path):
    """
    The RF-focusing kick (see test above) is not constant across RF phase:
    it grows substantially moving away from the zero-crossing towards the
    accelerating crest, tracking the entry/exit momentum mismatch SAD's
    vcorr coefficient depends on (tmulti.f) -- not a simple on/off-by-phase
    effect.
    """
    def kick(phi, tag):
        r0 = _mult_rf_focus_kick(tmp_path, phi, 0.0, f"rf_focus_{tag}_x0.sad")
        r1 = _mult_rf_focus_kick(
            tmp_path, phi, RF_FOCUS_X_TEST, f"rf_focus_{tag}_x1.sad")
        return r1["px"][0] - r0["px"][0]

    kick_crossing = kick(0.0, "crossing")
    kick_crest    = kick(np.pi / 2, "crest")

    assert abs(kick_crest) > 10 * abs(kick_crossing), (
        "The RF-focusing kick should grow substantially moving away from "
        "the zero-crossing (PHI=0) towards the accelerating crest "
        "(PHI=pi/2), not stay roughly constant across phase.")

################################################################################
# K0/SK0 dipole fringe (transfer-matrix ground truth)
################################################################################
K0_FRINGE_TEST_VALUE  = 0.05
L_FRINGE_TEST_VALUE   = 0.5
DIPOLE_FRINGE_M43     = -K0_FRINGE_TEST_VALUE**2 / L_FRINGE_TEST_VALUE

def _mult_transfer_matrix(tmp_path, params: str, name: str) -> np.ndarray:
    """
    4x4 SAD transfer matrix of a single-MULT transfer line whose MULT has
    the given parameter string.
    """
    lat = tmp_path / name
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        f"MULT M = ({params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START M END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return transfer_matrix_sad(
            lattice_filepath = lat.name,
            line_name        = "TEST")
    finally:
        os.chdir(cwd)

def test_mult_k0_has_dipole_fringe_by_default(tmp_path):
    """
    A K0-only MULT carries m43 = -K0^2/L in its default linear map.
    """
    tm = _mult_transfer_matrix(
        tmp_path,
        f"L={L_FRINGE_TEST_VALUE} K0={K0_FRINGE_TEST_VALUE}",
        "mult_k0_fringe_default.sad")
    assert tm[3, 2] == pytest.approx(DIPOLE_FRINGE_M43, abs = 1e-12), (
        "A MULT with only K0 should carry the dipole fringe term "
        "m43 = -K0^2/L exactly in its default linear map.")
    assert tm[1, 0] == pytest.approx(0.0, abs = 1e-12), (
        "A MULT with only K0 should have no horizontal focusing term m21.")

def test_mult_fringe_1_removes_k0_dipole_fringe(tmp_path):
    """
    FRINGE=1 on a K0-only MULT removes the dipole fringe block.
    """
    tm = _mult_transfer_matrix(
        tmp_path,
        f"L={L_FRINGE_TEST_VALUE} K0={K0_FRINGE_TEST_VALUE} FRINGE=1",
        "mult_k0_fringe_1.sad")
    assert tm[3, 2] == pytest.approx(0.0, abs = 1e-15), (
        "FRINGE=1 on a K0-only MULT should remove the dipole fringe "
        "focusing term m43 exactly.")
    assert tm[3, 3] == pytest.approx(1.0, abs = 1e-12), (
        "FRINGE=1 on a K0-only MULT should restore m44 to exactly 1 "
        "(the whole fringe block vanishes, not just the focusing term).")

@pytest.mark.parametrize("fringe_value", [0, 2, 3, -1])
def test_mult_other_fringe_values_keep_k0_dipole_fringe(tmp_path, fringe_value):
    """
    Tested FRINGE values other than 1 keep the K0 dipole fringe term.
    """
    tm = _mult_transfer_matrix(
        tmp_path,
        f"L={L_FRINGE_TEST_VALUE} K0={K0_FRINGE_TEST_VALUE} FRINGE={fringe_value}",
        f"mult_k0_fringe_{fringe_value}.sad")
    assert tm[3, 2] == pytest.approx(DIPOLE_FRINGE_M43, abs = 1e-12), (
        f"FRINGE={fringe_value} on a K0-only MULT should keep the dipole "
        "fringe term m43 = -K0^2/L, identical to an unset FRINGE.")

def test_mult_disfrin_does_not_control_k0_dipole_fringe(tmp_path):
    """
    DISFRIN=1 leaves the K0 dipole fringe term untouched.
    """
    tm = _mult_transfer_matrix(
        tmp_path,
        f"L={L_FRINGE_TEST_VALUE} K0={K0_FRINGE_TEST_VALUE} DISFRIN=1",
        "mult_k0_disfrin_1.sad")
    assert tm[3, 2] == pytest.approx(DIPOLE_FRINGE_M43, abs = 1e-12), (
        "DISFRIN=1 on a K0-only MULT should leave the dipole fringe term "
        "m43 = -K0^2/L in place — DISFRIN does not control it.")

def test_mult_sk0_dipole_fringe_mirrors_in_horizontal_plane(tmp_path):
    """
    SK0 mirrors the K0 dipole-fringe behaviour into m21.
    """
    tm_default = _mult_transfer_matrix(
        tmp_path,
        f"L={L_FRINGE_TEST_VALUE} SK0={K0_FRINGE_TEST_VALUE}",
        "mult_sk0_fringe_default.sad")
    assert tm_default[1, 0] == pytest.approx(DIPOLE_FRINGE_M43, abs = 1e-12), (
        "A MULT with only SK0 should carry the mirrored dipole fringe term "
        "m21 = -SK0^2/L exactly in its default linear map.")
    tm_fringe_1 = _mult_transfer_matrix(
        tmp_path,
        f"L={L_FRINGE_TEST_VALUE} SK0={K0_FRINGE_TEST_VALUE} FRINGE=1",
        "mult_sk0_fringe_1.sad")
    assert tm_fringe_1[1, 0] == pytest.approx(0.0, abs = 1e-15), (
        "FRINGE=1 on an SK0-only MULT should remove the mirrored dipole "
        "fringe term m21 exactly.")

################################################################################
# K0 dipole fringe with a real nonzero FB1/FB2 -- see the "MULT is out of
# scope" decision in docs/development/design-decisions.md
################################################################################
def test_mult_k0_fringe_with_nonzero_fb_does_not_match_equivalent_bend(tmp_path):
    """
    A K0-only MULT and the equivalent K0-only BEND (same L/K0/FRINGE/
    FB1/FB2) should give clearly different py(y) -- MULT does not route
    through the same fringe formula as BEND.
    """
    L, K0, FB1, FB2 = 0.4, 0.03, 0.025, 0.018
    y_vals = np.array([0.002])
    delta_vals = np.zeros(1)

    def run(elem_type, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"{elem_type} M = (L={L} K0={K0} FRINGE=1 FB1={FB1} FB2={FB2});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START M END);\n")
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            return track_sad(
                lattice_filepath    = lat.name,
                line_name           = "TEST",
                x_init              = np.zeros(1),
                px_init             = np.zeros(1),
                y_init              = y_vals,
                py_init             = np.zeros(1),
                zeta_init           = np.zeros(1),
                delta_init          = delta_vals,
                n_turns             = 1,
                rfsw                = False,
                with_progress       = False)
        finally:
            os.chdir(cwd)

    r_mult = run("MULT", "mult_fb_probe.sad")
    r_bend = run("BEND", "bend_fb_probe.sad")
    ratio = r_mult["py"][0] / r_bend["py"][0]
    assert not (0.9 < ratio < 1.1), (
        "A K0-only MULT and the equivalent K0-only BEND, both with the "
        "same FRINGE/FB1/FB2, should NOT give closely matching py(y) -- "
        f"got ratio={ratio:.4f}. If this now passes (ratio near 1), MULT "
        "may have started sharing BEND's fringe formula and "
        "docs/development/design-decisions.md's MULT exclusion should be revisited.")

################################################################################
# F1/F2/FRINGE quad-style soft-edge fringe (ground truth) -- see
# docs/reference/sad-behaviour.md
################################################################################
def _track_mult_probe(tmp_path, lattice_body, name, x_vals, px_vals, y_vals, py_vals):
    """
    Track a grid of particles through a lattice body and return the
    track_sad result.
    """
    lat = tmp_path / name
    lat.write_text(f"MOMENTUM = 1.0 GEV;\n{lattice_body}\n")
    n = len(x_vals)
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return track_sad(
            lattice_filepath    = lat.name,
            line_name           = "TEST",
            x_init              = x_vals,
            px_init             = px_vals,
            y_init              = y_vals,
            py_init             = py_vals,
            zeta_init           = np.zeros(n),
            delta_init          = np.zeros(n),
            n_turns             = 1,
            rfsw                = False,
            with_progress       = False)
    finally:
        os.chdir(cwd)

def test_mult_k1_f1_f2_is_inert_without_fringe(tmp_path):
    """
    F1/F2 on a K1 MULT has no effect unless FRINGE is also set -- same
    convention as QUAD's F1/F2 (test_quad.py).
    """
    x_vals, px_vals = np.array([1e-3]), np.array([2e-3])
    y_vals, py_vals = np.array([-1.5e-3]), np.array([0.5e-3])
    body_no_fringe = "MULT M1 = (L=1.0 K1=0.3 F1=0.02 F2=0.01);\nMARK START=()\n END=();\nLINE TEST=(START M1 END);"
    body_no_f1f2   = "MULT M1 = (L=1.0 K1=0.3);\nMARK START=()\n END=();\nLINE TEST=(START M1 END);"
    r_fringe  = _track_mult_probe(tmp_path, body_no_fringe, "mult_f1f2_no_fringe.sad", x_vals, px_vals, y_vals, py_vals)
    r_no_f1f2 = _track_mult_probe(tmp_path, body_no_f1f2, "mult_no_f1f2.sad", x_vals, px_vals, y_vals, py_vals)
    for coord in ("x", "px", "y", "py"):
        assert r_fringe[coord][0] == pytest.approx(r_no_f1f2[coord][0], abs=1e-15), (
            f"F1/F2 on a K1 MULT should have no effect on {coord} while "
            "FRINGE is unset (default off).")

def test_mult_k1_fringe_mode_gates_entrance_exit(tmp_path):
    """
    MULT's FRINGE (mfring) for the K1 quad-style fringe uses the SAME
    {1,2,3} numbering as QUAD's own FRINGE (0=neither, 1=entrance-only,
    2=exit-only, 3=both) -- confirmed against the real binary with
    genuinely asymmetric F1K1F/F1K1B/F2K1F/F2K1B.
    """
    x_vals, px_vals = np.array([1e-3]), np.array([2e-3])
    y_vals, py_vals = np.array([-1.5e-3]), np.array([0.5e-3])

    def run(fringe):
        body = (
            f"MULT M1 = (L=1.0 K1=0.3 F1K1F=0.05 F2K1F=0.02 F1K1B=-0.03 "
            f"F2K1B=-0.01 FRINGE={fringe});\n"
            "MARK START=()\n END=();\nLINE TEST=(START M1 END);")
        return _track_mult_probe(
            tmp_path, body, f"mult_k1_mfring_{fringe}.sad", x_vals, px_vals, y_vals, py_vals)["x"][0]

    neither, entry, exit_, both = run(0), run(1), run(2), run(3)
    assert entry != pytest.approx(neither) and entry != pytest.approx(both), (
        "FRINGE=1 (entrance-only) should differ from both the "
        "both-active and neither-active cases.")
    assert exit_ != pytest.approx(neither) and exit_ != pytest.approx(both), (
        "FRINGE=2 (exit-only) should differ from both the both-active "
        "and neither-active cases.")
    assert entry != pytest.approx(exit_), (
        "FRINGE=1 (entrance-only) and FRINGE=2 (exit-only) should give "
        "different kicks for asymmetric F1K1F/F1K1B/F2K1F/F2K1B.")

def test_mult_k1_f1_f2_matches_sad_reference_values(tmp_path):
    """
    Pinned ground truth: L=1.0, K1=0.3, F1=0.02, F2=0.01, FRINGE=3.
    Matches the equivalent QUAD reference values exactly
    (test_quad_f1_f2_matches_sad_reference_values) -- a K1-only MULT with
    no other order content is physically a QUAD.
    """
    x_vals, px_vals = np.array([1e-3]), np.array([2e-3])
    y_vals, py_vals = np.array([-1.5e-3]), np.array([0.5e-3])
    body = "MULT M1 = (L=1.0 K1=0.3 F1=0.02 F2=0.01 FRINGE=3);\nMARK START=()\n END=();\nLINE TEST=(START M1 END);"
    result = _track_mult_probe(tmp_path, body, "mult_f1f2_reference.sad", x_vals, px_vals, y_vals, py_vals)

    expected = {
        "x":  0.0027646062615639413,
        "px": 0.0014204934595131308,
        "y":  -0.0012073498520841902,
        "py": 0.0001035764182398119,
    }
    for coord, exp in expected.items():
        assert result[coord][0] == pytest.approx(exp, rel=1e-6), (
            f"SAD's on-momentum {coord} for a K1>0 MULT with F1/F2/FRINGE "
            "set no longer matches the pinned reference value -- SAD's "
            "fringe behaviour may have changed, or this reference lattice "
            "was altered unintentionally.")

def test_mult_reversed_line_fringe_mode_permutes(tmp_path):
    """
    Same reversal finding as QUAD (test_quad_reversed_line_fringe_mode_permutes):
    traversing a `-LINE` reversed MULT with FRINGE=1 (entrance-only,
    asymmetric F1K1F/F1K1B) gives EXACTLY the same result as traversing
    the same MULT forward with FRINGE=2 and F1K1F/F1K1B (and F2K1F/F2K1B)
    swapped.
    """
    x_vals, px_vals = np.array([1e-3]), np.array([2e-3])
    y_vals, py_vals = np.array([-1.5e-3]), np.array([0.5e-3])

    body_reversed = (
        "MULT M1 = (L=1.0 K1=0.3 F1K1F=0.05 F1K1B=-0.03 F2K1F=0.02 "
        "F2K1B=-0.01 FRINGE=1);\nMARK START=()\n END=();\n"
        "LINE FWD = (START M1 END);\nLINE TESTREV = (-FWD);")
    lat = tmp_path / "mult_reversed_mode.sad"
    lat.write_text(f"MOMENTUM = 1.0 GEV;\n{body_reversed}\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_reversed = track_sad(
            lattice_filepath    = lat.name,
            line_name           = "TESTREV",
            x_init              = x_vals.copy(),
            px_init             = px_vals.copy(),
            y_init              = y_vals.copy(),
            py_init             = py_vals.copy(),
            zeta_init           = np.zeros(1),
            delta_init          = np.zeros(1),
            n_turns             = 1,
            rfsw                = False,
            with_progress       = False)
    finally:
        os.chdir(cwd)

    body_forward_swapped = (
        "MULT M1 = (L=1.0 K1=0.3 F1K1F=-0.03 F1K1B=0.05 F2K1F=-0.01 "
        "F2K1B=0.02 FRINGE=2);\n"
        "MARK START=()\n END=();\nLINE TEST=(START M1 END);")
    r_forward_swapped = _track_mult_probe(
        tmp_path, body_forward_swapped, "mult_forward_swapped.sad",
        x_vals, px_vals, y_vals, py_vals)

    for coord in ("x", "px", "y", "py"):
        assert r_reversed[coord][0] == pytest.approx(
                r_forward_swapped[coord][0], abs = 1e-12), (
            f"Reversed FRINGE=1 traversal should exactly match forward "
            f"FRINGE=2 with F1K1F/F1K1B (and F2K1F/F2K1B) swapped, on "
            f"{coord} -- SAD's reversal convention for the linear fringe "
            "may have changed.")

################################################################################
# FB1/FB2 dipole-style soft-edge fringe (ground truth) -- see
# docs/reference/sad-behaviour.md
################################################################################
def test_mult_fb1_fb2_is_inert_without_fringe(tmp_path):
    """
    FB1/FB2 on an ANGLE/K0 MULT has no effect unless FRINGE is also set.
    """
    y_vals, py_vals = np.array([0.003]), np.array([0.0])
    body_no_fringe = "MULT M1 = (L=1.0 ANGLE=0.1 K0=0.1 FB1=0.05 FB2=0.03);\nMARK START=()\n END=();\nLINE TEST=(START M1 END);"
    body_no_fb     = "MULT M1 = (L=1.0 ANGLE=0.1 K0=0.1);\nMARK START=()\n END=();\nLINE TEST=(START M1 END);"
    r_fringe = _track_mult_probe(tmp_path, body_no_fringe, "mult_fb_no_fringe.sad", np.zeros(1), np.zeros(1), y_vals, py_vals)
    r_no_fb  = _track_mult_probe(tmp_path, body_no_fb, "mult_no_fb.sad", np.zeros(1), np.zeros(1), y_vals, py_vals)
    assert r_fringe["py"][0] == pytest.approx(r_no_fb["py"][0], abs=1e-15), (
        "FB1/FB2 on an ANGLE/K0 MULT should have no effect while FRINGE "
        "is unset (default off).")

def test_mult_fb1_fb2_fringe_mode_gates_entrance_exit(tmp_path):
    """
    MULT's FB1/FB2 dipole-style fringe uses the SAME {1,2,3} FRINGE
    numbering as its own K1 quad-style fringe (and QUAD's FRINGE) --
    NOT BEND's own FRMD_BEND sign-based scheme. Confirmed against the
    real binary with asymmetric FB1 != FB2.
    """
    def run(fringe):
        body = (
            f"MULT M1 = (L=1.0 ANGLE=0.1 K0=0.1 FB1=0.05 FB2=0.03 "
            f"FRINGE={fringe});\n"
            "MARK START=()\n END=();\nLINE TEST=(START M1 END);")
        return _track_mult_probe(
            tmp_path, body, f"mult_fb_mfring_{fringe}.sad",
            np.zeros(1), np.zeros(1), np.array([0.003]), np.zeros(1))["py"][0]

    neither, entry, exit_, both = run(0), run(1), run(2), run(3)
    assert entry != pytest.approx(neither) and entry != pytest.approx(both), (
        "FRINGE=1 (entrance-only) should differ from both the "
        "both-active and neither-active cases.")
    assert exit_ != pytest.approx(neither) and exit_ != pytest.approx(both), (
        "FRINGE=2 (exit-only) should differ from both the both-active "
        "and neither-active cases.")
    assert entry != pytest.approx(exit_), (
        "FRINGE=1 (entrance-only) and FRINGE=2 (exit-only) should give "
        "different kicks for asymmetric FB1 != FB2.")

def test_mult_fb1_fb2_matches_sad_reference_values(tmp_path):
    """
    Pinned ground truth: L=1.0, ANGLE=0.1, K0=0.1, FB1=0.05, FB2=0.03,
    FRINGE=3, on-momentum, y=0.003. Real SAD binary output, recorded once
    and locked in.
    """
    result = _track_mult_probe(
        tmp_path,
        "MULT M1 = (L=1.0 ANGLE=0.1 K0=0.1 FB1=0.05 FB2=0.03 FRINGE=3);\nMARK START=()\n END=();\nLINE TEST=(START M1 END);",
        "mult_fb_reference.sad", np.zeros(1), np.zeros(1), np.array([0.003]), np.zeros(1))

    expected = {
        "x":  -0.049958304181885405,
        "px": -0.09983343461694201,
        "y":  0.0030009856014852707,
        "py": -5.865889601443156e-05,
    }
    for coord, exp in expected.items():
        assert result[coord][0] == pytest.approx(exp, rel=1e-6), (
            f"SAD's on-momentum {coord} for an ANGLE/K0 MULT with "
            "FB1/FB2/FRINGE set no longer matches the pinned reference "
            "value -- SAD's fringe behaviour may have changed, or this "
            "reference lattice was altered unintentionally.")

################################################################################
# DISFRIN hard-edge fringe, and its interaction with FRINGE (ground truth)
# -- see docs/reference/sad-behaviour.md
################################################################################
def test_mult_disfrin_default_matches_explicit_zero(tmp_path):
    """
    DISFRIN unset defaults to DISFRIN=0 (hard-edge fringe enabled) --
    bit-identical output, not just approximately equal.
    """
    r_unset = _track_mult_probe(tmp_path, "MULT M1 = (L=0.5 K1=0.4);\nMARK START=()\n END=();\nLINE TEST=(START M1 END);",
                                 "mult_disfrin_unset.sad", np.array([2e-2]), np.array([2e-2]), np.zeros(1), np.zeros(1))
    r_zero  = _track_mult_probe(tmp_path, "MULT M1 = (L=0.5 K1=0.4 DISFRIN=0);\nMARK START=()\n END=();\nLINE TEST=(START M1 END);",
                                 "mult_disfrin_zero.sad", np.array([2e-2]), np.array([2e-2]), np.zeros(1), np.zeros(1))
    assert r_unset["px"][0] == pytest.approx(r_zero["px"][0], abs=1e-15), (
        "DISFRIN unset should default to DISFRIN=0 (hard-edge fringe "
        "enabled), bit-identically.")

def test_mult_disfrin_is_boolean(tmp_path):
    """
    DISFRIN is a strict boolean gate on a MULT, same as on BEND/QUAD/
    SEXT/OCT: any nonzero value disables the hard-edge fringe identically.
    """
    def run(disfrin):
        body = f"MULT M1 = (L=0.5 K1=0.4 DISFRIN={disfrin});\nMARK START=()\n END=();\nLINE TEST=(START M1 END);"
        return _track_mult_probe(tmp_path, body, f"mult_disfrin_bool_{disfrin}.sad",
                                  np.array([2e-2]), np.array([2e-2]), np.zeros(1), np.zeros(1))["px"][0]

    disfrin_1 = run(1)
    for disfrin in (2, -1, 3, 0.5):
        assert run(disfrin) == pytest.approx(disfrin_1, abs=1e-15), (
            f"DISFRIN={disfrin} should disable the hard-edge fringe "
            "identically to DISFRIN=1 -- DISFRIN is boolean, not graded.")

def test_mult_disfrin_hard_edge_matches_sad_reference_values(tmp_path):
    """
    Pinned ground truth: L=0.5, K1=0.4, x=px=2E-2, with the hard-edge
    fringe enabled (DISFRIN=0/unset) and disabled (DISFRIN=1). Matches
    the equivalent QUAD reference values exactly.
    """
    r_on  = _track_mult_probe(tmp_path, "MULT M1 = (L=0.5 K1=0.4);\nMARK START=()\n END=();\nLINE TEST=(START M1 END);",
                               "mult_disfrin_ref_on.sad", np.array([2e-2]), np.array([2e-2]), np.zeros(1), np.zeros(1))
    r_off = _track_mult_probe(tmp_path, "MULT M1 = (L=0.5 K1=0.4 DISFRIN=1);\nMARK START=()\n END=();\nLINE TEST=(START M1 END);",
                               "mult_disfrin_ref_off.sad", np.array([2e-2]), np.array([2e-2]), np.zeros(1), np.zeros(1))
    assert r_on["px"][0] == pytest.approx(0.010296769633772317, rel=1e-6), (
        "SAD's px with the hard-edge fringe enabled no longer matches "
        "the pinned reference value.")
    assert r_off["px"][0] == pytest.approx(0.010296838137678514, rel=1e-6), (
        "SAD's px with the hard-edge fringe disabled (DISFRIN=1) no "
        "longer matches the pinned reference value.")

def test_mult_fringe_mode_also_gates_hard_edge_fringe_sides(tmp_path):
    """
    Same interaction as QUAD -- see docs/reference/sad-behaviour.md. Unlike QUAD,
    MULT has no FRINGE<=-4 master-disable for the hard-edge fringe.
    """
    def run(suffix, name):
        body = f"MULT M1 = (L=0.5 K1=0.4{suffix});\nMARK START=()\n END=();\nLINE TEST=(START M1 END);"
        return _track_mult_probe(tmp_path, body, name,
                                  np.array([2e-2]), np.array([2e-2]), np.zeros(1), np.zeros(1))["px"][0]

    default = run("", "mult_hardedge_default.sad")
    assert run(" FRINGE=0", "mult_hardedge_f0.sad") == pytest.approx(default, abs=1e-15)
    assert run(" FRINGE=3", "mult_hardedge_f3.sad") == pytest.approx(default, abs=1e-15), (
        "FRINGE=3 (both sides active) should leave the hard-edge fringe "
        "unaffected relative to FRINGE unset.")
    assert run(" FRINGE=1", "mult_hardedge_f1.sad") != pytest.approx(default), (
        "FRINGE=1 should disable the EXIT-side hard-edge fringe, "
        "changing tracking relative to FRINGE unset even with no F1/F2 "
        "set.")
    assert run(" FRINGE=2", "mult_hardedge_f2.sad") != pytest.approx(default), (
        "FRINGE=2 should disable the ENTRANCE-side hard-edge fringe, "
        "changing tracking relative to FRINGE unset even with no F1/F2 "
        "set.")
    assert run(" FRINGE=-4", "mult_hardedge_fm4.sad") == pytest.approx(default, abs=1e-15), (
        "UNLIKE QUAD, MULT's hard-edge fringe has no FRINGE<=-4 "
        "master-disable -- FRINGE=-4 should leave both sides fully "
        "active, matching FRINGE unset exactly (not DISFRIN=1, which "
        "would disable both).")
