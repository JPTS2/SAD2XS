"""
================================================================================
SAD syntax assumptions: BEND element
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
# Accepted / Rejected parameters
#
# See tests/sad/README.md's "Parameter matrix" for the accepted/rejected
# table this parametrization transcribes.
################################################################################
ACCEPTED_PARAMS = [
    pytest.param("L=1.0 ANGLE=0.01",                     id = "angle"),
    pytest.param("L=1.0 K0=0.01",                        id = "k0"),
    pytest.param("L=1.0 K1=0.2",                         id = "k1"),
    pytest.param("L=1.0 DX=0.001",                       id = "dx"),
    pytest.param("L=1.0 DY=0.001",                       id = "dy"),
    pytest.param("L=1.0 ROTATE=0.1",                     id = "rotate"),
    pytest.param("L=1.0 ANGLE=0.01 F1=0.05",             id = "f1"),
    pytest.param("L=1.0 ANGLE=0.01 F1=0.05 FRINGE=1",    id = "fringe"),
    pytest.param("L=1.0 ANGLE=0.01 FRINGE=1 FB1=0.05",   id = "fb1"),
    pytest.param("L=1.0 ANGLE=0.01 FRINGE=1 FB2=0.05",   id = "fb2"),
]

@pytest.mark.parametrize("params", ACCEPTED_PARAMS)
def test_bend_accepts(sad_accepts, params):
    """
    SAD's BEND element should accept ANGLE, K0, K1, the standard
    misalignment/rotation parameters, and the F1/FRINGE/FB1/FB2 fringe
    parameters.
    """
    sad_accepts(
        f"BEND B1 = ({params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

REJECTED_PARAMS = [
    pytest.param("L=1.0 SK0=0.1",    id = "sk0"),
    pytest.param("L=1.0 SK1=0.1",    id = "sk1"),
    pytest.param("L=1.0 K2=0.1",     id = "k2"),
    pytest.param("L=1.0 SK2=0.1",    id = "sk2"),
    pytest.param("L=1.0 K3=0.1",     id = "k3"),
    pytest.param("L=1.0 SK3=0.1",    id = "sk3"),
    pytest.param("L=1.0 K4=0.1",     id = "k4"),
    pytest.param("L=1.0 SK4=0.1",    id = "sk4"),
    pytest.param("L=1.0 HARM=1000",  id = "harm"),
    pytest.param("L=1.0 FREQ=400E6", id = "freq"),
    pytest.param("L=1.0 BZ=0.1",     id = "bz"),
]

@pytest.mark.parametrize("params", REJECTED_PARAMS)
def test_bend_rejects(sad_rejects, params):
    """
    SAD's BEND element should reject skew/higher-order field
    (SK0/SK1/K2-K4/SK2-SK4), solenoid (BZ), and RF parameters.
    """
    sad_rejects(
        f"BEND B1 = ({params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START B1 END);")

################################################################################
# Thin bend (no length) behaviour
#
# A no-L BEND with ANGLE is a thin/integrated bend. K1 in a no-L BEND is an
# integrated quadrupole strength: it affects BOTH Twiss (linear focusing,
# like QUAD) AND tracking (a direct px kick on an off-axis particle) —
# verified by both tests below.
################################################################################
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

def test_bend_without_length_k1_affects_twiss(tmp_path):
    """
    K1 in a no-L SAD BEND changes Twiss betx, mirroring QUAD's linear
    focusing effect (test_quad_without_length_k1_affects_twiss).
    """
    def run(k1, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"BEND B = (ANGLE=0.0 K1={k1});\n"
            "DRIFT D = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START D B D END);\n")
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

    tw_ref = run(0.0, "bend_k1_0_twiss.sad")
    tw_k1  = run(0.5, "bend_k1_nonzero_twiss.sad")
    assert tw_k1["betx"][-1] != pytest.approx(tw_ref["betx"][-1]), (
        "K1 in a no-L BEND should focus the beam and change Twiss betx, "
        "same as K1 in a no-L QUAD.")

def test_bend_without_length_k1_gives_quadrupole_kick(tmp_path):
    """
    K1 in a no-L SAD BEND is an integrated quadrupole strength: a particle
    with transverse offset x receives a px kick of -K1 * x. Verified via
    tracking as the direct-kick complement to the Twiss test above.
    """
    def run(k1, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"BEND B = (ANGLE=0.0 K1={k1});\n"
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

################################################################################
# Thin corrector (no length) behaviour
#
# A no-L BEND with K0 but no ANGLE is SAD's convention for a corrector
# magnet — an orbit-kick element, not a focusing one. Twiss betx is
# unaffected by K0 alone (confirmed below); the kick is verified via
# tracking, which shows px = K0 directly.
################################################################################
def test_corrector_without_length_is_accepted_by_sad(sad_accepts):
    """
    SAD accepts a BEND used as a corrector (K0 only, no ANGLE, no L).
    The converter should convert this to a thin Multipole, not a Marker.
    """
    sad_accepts(
        "BEND C1 = (K0=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_corrector_without_length_k0_has_no_linear_effect_on_twiss_betx(tmp_path):
    """
    K0 in a no-L BEND corrector is a pure orbit kick, not a focusing term.
    betx is not perfectly invariant (there is a small orbit-displacement
    residual), but that residual is second-order in K0 (scales as K0^2),
    unlike K1's directly linear (first-order) effect on betx (see
    test_bend_without_length_k1_affects_twiss above).
    """
    def run(k0, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"BEND C = (K0={k0});\n"
            "DRIFT D = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START D C D END);\n")
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

    tw_0    = run(0.00, "corr_k0_0_twiss.sad")
    tw_01   = run(0.01, "corr_k0_01_twiss.sad")
    tw_02   = run(0.02, "corr_k0_02_twiss.sad")
    diff_01 = tw_01["betx"][-1] - tw_0["betx"][-1]
    diff_02 = tw_02["betx"][-1] - tw_0["betx"][-1]

    # betx is not exactly invariant under K0 (there is a small residual from
    # the orbit displacement propagating through the downstream drift), but
    # that residual is second-order in K0 (confirmed: doubling K0 roughly
    # quadruples the betx shift, ratio ~4, not ~2) — i.e. K0 provides no
    # LINEAR focusing, unlike K1's directly linear effect (see
    # test_bend_without_length_k1_affects_twiss above).
    assert diff_02 / diff_01 == pytest.approx(4.0, rel=0.05), (
        "The betx shift from K0 should scale quadratically with K0 (ratio "
        "~4 when K0 doubles), confirming K0 has no linear focusing effect — "
        "only a second-order orbit-displacement residual.")

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

################################################################################
# F1/FRINGE soft-edge fringe (ground truth) -- see docs/sad-behaviour.md
################################################################################
def _track_bend_probe(tmp_path, lattice_body, name, y_vals, delta_vals):
    """
    Track a grid of particles (given y/delta, other coordinates zero)
    through a lattice body and return the track_sad result.
    """
    lat = tmp_path / name
    lat.write_text(f"MOMENTUM = 1.0 GEV;\n{lattice_body}\n")
    n = len(y_vals)
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return track_sad(
            lattice_filepath    = lat.name,
            line_name           = "TEST",
            x_init              = np.zeros(n),
            px_init             = np.zeros(n),
            y_init              = y_vals,
            py_init             = np.zeros(n),
            zeta_init           = np.zeros(n),
            delta_init          = delta_vals,
            n_turns             = 1,
            rfsw                = False,
            with_progress       = False)
    finally:
        os.chdir(cwd)

def test_bend_f1_is_inert_without_fringe(tmp_path):
    """
    F1 on an ANGLE!=0 BEND has no effect unless FRINGE is also set
    (nonzero) — matching the SAD manual's "when FRINGE is non-zero, the
    effect of the linear fringe F1 is taken into account". Default
    FRINGE is off.
    """
    y_vals = np.array([0.002])
    delta_vals = np.zeros(1)
    body_no_fringe = "BEND B = (L=2.0 ANGLE=0.2 F1=0.05);\nMARK START=()\n END=();\nLINE TEST=(START B END);"
    body_f1_zero   = "BEND B = (L=2.0 ANGLE=0.2);\nMARK START=()\n END=();\nLINE TEST=(START B END);"
    r_f1     = _track_bend_probe(tmp_path, body_no_fringe, "bend_f1_no_fringe.sad", y_vals, delta_vals)
    r_no_f1  = _track_bend_probe(tmp_path, body_f1_zero, "bend_no_f1.sad", y_vals, delta_vals)
    assert r_f1["py"][0] == pytest.approx(r_no_f1["py"][0], abs=1e-15), (
        "F1 on an ANGLE!=0 BEND should have no effect while FRINGE is unset "
        "(default off) — the fringe kick should be identical to a BEND "
        "with no F1 at all.")

def test_bend_fringe_1_activates_f1(tmp_path):
    """
    FRINGE=1 on an ANGLE!=0 BEND activates the F1 fringe kick.
    """
    y_vals = np.array([0.002])
    delta_vals = np.zeros(1)
    body_fringe_off = "BEND B = (L=2.0 ANGLE=0.2 F1=0.05);\nMARK START=()\n END=();\nLINE TEST=(START B END);"
    body_fringe_on  = "BEND B = (L=2.0 ANGLE=0.2 F1=0.05 FRINGE=1);\nMARK START=()\n END=();\nLINE TEST=(START B END);"
    r_off = _track_bend_probe(tmp_path, body_fringe_off, "bend_fringe_off.sad", y_vals, delta_vals)
    r_on  = _track_bend_probe(tmp_path, body_fringe_on, "bend_fringe_on.sad", y_vals, delta_vals)
    assert r_on["py"][0] != pytest.approx(r_off["py"][0]), (
        "FRINGE=1 on an ANGLE!=0 BEND with F1 set should change the "
        "vertical kick relative to FRINGE unset.")

def test_bend_fringe_mode_gates_entrance_exit(tmp_path):
    """
    FRMD_BEND gating grid against real SAD -- see docs/sad-behaviour.md
    ("BEND F1/FRINGE soft-edge fringe") for the semantic. FB1 != FB2
    makes entrance-only/exit-only/both/neither all numerically distinct.
    """
    y_vals = np.array([0.003])
    delta_vals = np.zeros(1)

    def run(fringe):
        body = (
            f"BEND B = (L=2.0 ANGLE=0.2 FB1=0.15 FB2=0.08 FRINGE={fringe});\n"
            "MARK START=()\n END=();\nLINE TEST=(START B END);")
        return _track_bend_probe(
            tmp_path, body, f"bend_frmd_mode_{fringe}.sad", y_vals, delta_vals)["py"][0]

    neither = run(0)
    entry   = run(-1)
    exit_   = run(-2)
    both    = run(1)

    assert entry != pytest.approx(neither) and entry != pytest.approx(both), (
        "FRINGE=-1 (entrance-only) should differ from both the "
        "both-active and neither-active cases.")
    assert exit_ != pytest.approx(neither) and exit_ != pytest.approx(both), (
        "FRINGE=-2 (exit-only) should differ from both the both-active "
        "and neither-active cases.")
    assert entry != pytest.approx(exit_), (
        "FRINGE=-1 (entrance-only) and FRINGE=-2 (exit-only) should give "
        "different kicks for an asymmetric FB1 != FB2 bend.")

    for fringe in (-3, -4):
        assert run(fringe) == pytest.approx(neither, abs=1e-15), (
            f"FRINGE={fringe} should disable both edges, identically to "
            "FRINGE=0 -- SAD zeroes both fb1 and fb2 for any FRMD_BEND "
            "value <= 0 other than -1/-2.")

    for fringe in (2, 3, 4, 5):
        assert run(fringe) == pytest.approx(both, abs=1e-15), (
            f"FRINGE={fringe} should enable both edges, identically to "
            "FRINGE=1 -- SAD enables both unconditionally for any "
            "positive FRMD_BEND value.")

def test_bend_corrector_fringe_mode_gates_entrance_exit(tmp_path):
    """
    Same grid as test_bend_fringe_mode_gates_entrance_exit, confirmed on
    the K0-only corrector code path (no ANGLE) too, not assumed.
    """
    y_vals = np.array([0.003])
    delta_vals = np.zeros(1)

    def run(fringe):
        body = (
            f"BEND C = (L=0.5 K0=0.05 FB1=0.15 FB2=0.08 FRINGE={fringe});\n"
            "MARK START=()\n END=();\nLINE TEST=(START C END);")
        return _track_bend_probe(
            tmp_path, body, f"corr_frmd_mode_{fringe}.sad", y_vals, delta_vals)["py"][0]

    neither = run(0)
    entry   = run(-1)
    exit_   = run(-2)
    both    = run(1)

    assert entry != pytest.approx(neither) and entry != pytest.approx(both), (
        "FRINGE=-1 (entrance-only) should differ from both the "
        "both-active and neither-active cases.")
    assert exit_ != pytest.approx(neither) and exit_ != pytest.approx(both), (
        "FRINGE=-2 (exit-only) should differ from both the both-active "
        "and neither-active cases.")
    assert entry != pytest.approx(exit_), (
        "FRINGE=-1 (entrance-only) and FRINGE=-2 (exit-only) should give "
        "different kicks for an asymmetric FB1 != FB2 corrector.")

    for fringe in (-3, -4):
        assert run(fringe) == pytest.approx(neither, abs=1e-15), (
            f"FRINGE={fringe} should disable both edges, identically to "
            "FRINGE=0.")

    for fringe in (2, 3):
        assert run(fringe) == pytest.approx(both, abs=1e-15), (
            f"FRINGE={fringe} should enable both edges, identically to "
            "FRINGE=1.")

def test_bend_angle_nonzero_f1_fringe_matches_sad_reference_values(tmp_path):
    """
    Pinned ground truth: L=2.0, ANGLE=0.2, F1=0.05, FRINGE=1, on-momentum
    (delta=0), py(y) at y=0.001/0.002/0.003/0.005. These are real SAD
    binary outputs recorded once and locked in — any future change in
    SAD2XS's understanding of this formula should be checked against a
    fresh SAD run, not against this file.
    """
    y_vals = np.array([0.001, 0.002, 0.003, 0.005])
    delta_vals = np.zeros(4)
    body = "BEND B = (L=2.0 ANGLE=0.2 F1=0.05 FRINGE=1);\nMARK START=()\n END=();\nLINE TEST=(START B END);"
    result = _track_bend_probe(tmp_path, body, "bend_f1_reference.sad", y_vals, delta_vals)

    expected_py = np.array([
        1.66414047e-07, 3.3122696527e-07, 4.92837637e-07, 8.00047913e-07])
    np.testing.assert_allclose(
        result["py"], expected_py, rtol=1e-6,
        err_msg=(
            "SAD's on-momentum py(y) for an ANGLE!=0 BEND with F1/FRINGE "
            "set no longer matches the pinned reference values — SAD's "
            "fringe behaviour may have changed, or this reference lattice "
            "was altered unintentionally."))

def test_corrector_fringe_matches_sad_reference_values(tmp_path):
    """
    Pinned ground truth for the ANGLE=0, K0-only corrector case (the real
    BW*-series wigglers' code path): L=0.5, K0=0.05, FB1=0.03, FB2=0.02,
    FRINGE=1, on-momentum (delta=0), py(y) at y=0.001/0.002/0.003/0.005.
    Real SAD binary outputs, recorded once and locked in.
    """
    y_vals = np.array([0.001, 0.002, 0.003, 0.005])
    delta_vals = np.zeros(4)
    body = "BEND C = (L=0.5 K0=0.05 FRINGE=1 FB1=0.03 FB2=0.02);\nMARK START=()\n END=();\nLINE TEST=(START C END);"
    result = _track_bend_probe(tmp_path, body, "corr_f1_reference.sad", y_vals, delta_vals)

    expected_py = np.array([
        -4.923607804287169e-06, -9.850545721904283e-06,
        -1.4784143852842083e-05, -2.4684641007911894e-05])
    np.testing.assert_allclose(
        result["py"], expected_py, rtol=1e-6,
        err_msg=(
            "SAD's on-momentum py(y) for a K0-only corrector with "
            "FB1/FB2/FRINGE set no longer matches the pinned reference "
            "values — SAD's fringe behaviour may have changed, or this "
            "reference lattice was altered unintentionally."))
