"""
================================================================================
SAD syntax assumptions: MULT element
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-21
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
# and RF parameters (K. Oide: "almighty, even acceleration can be included").
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
]

@pytest.mark.parametrize("params", ACCEPTED_PARAMS)
def test_mult_accepts(sad_accepts, params):
    """
    SAD's MULT element is the general multipole and should accept every
    Kn/SKn order, geometry, and RF parameter.
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
# kick (SAD's tmultiacc in tmulti.f) -- see docs/sad-behaviour.md. Unlike
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
# scope" decision in docs/design-decisions.md
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
        "docs/design-decisions.md's MULT exclusion should be revisited.")
