"""
================================================================================
SAD syntax assumptions: CAVI element
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-29
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
    pytest.param("L=0.5 VOLT=0.5",    id = "volt"),
    pytest.param("L=0.5 FREQ=400E6",  id = "freq"),
    pytest.param("L=0.5 HARM=1000",   id = "harm"),
    pytest.param("L=0.5 PHI=0.1",     id = "phi"),
    pytest.param("L=0.5 DX=0.001",    id = "dx"),
    pytest.param("L=0.5 DY=0.001",    id = "dy"),
    pytest.param("L=0.5 ROTATE=0.1",  id = "rotate"),
    pytest.param("L=0.5 VOLT=0.5 FRINGE=1",  id = "fringe"),
    pytest.param("L=0.5 VOLT=0.5 DISFRIN=1", id = "disfrin"),
    pytest.param("L=0.5 VOLT=0.5 V1=0.1",    id = "v1"),
    pytest.param("L=0.5 VOLT=0.5 V20=0.1",   id = "v20"),
    pytest.param("L=0.5 VOLT=0.5 V11=0.1",   id = "v11"),
    pytest.param("L=0.5 VOLT=0.5 V02=0.1",   id = "v02"),
]

@pytest.mark.parametrize("params", ACCEPTED_PARAMS)
def test_cavi_accepts(sad_accepts, params):
    """
    SAD's CAVI element should accept VOLT, FREQ, HARM, PHI, the standard
    misalignment/rotation parameters, FRINGE, DISFRIN, and the transverse
    RF-multipole coefficients V1/V20/V11/V02.
    """
    sad_accepts(
        f"CAVI C1 = ({params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

REJECTED_PARAMS = [
    pytest.param("L=0.5 ANGLE=0.01", id = "angle"),
    pytest.param("L=0.5 K0=0.1",     id = "k0"),
    pytest.param("L=0.5 SK0=0.1",    id = "sk0"),
    pytest.param("L=0.5 K1=0.1",     id = "k1"),
    pytest.param("L=0.5 SK1=0.1",    id = "sk1"),
    pytest.param("L=0.5 K2=0.1",     id = "k2"),
    pytest.param("L=0.5 SK2=0.1",    id = "sk2"),
    pytest.param("L=0.5 K3=0.1",     id = "k3"),
    pytest.param("L=0.5 SK3=0.1",    id = "sk3"),
    pytest.param("L=0.5 K4=0.1",     id = "k4"),
    pytest.param("L=0.5 SK4=0.1",    id = "sk4"),
    pytest.param("L=0.5 BZ=0.1",     id = "bz"),
    pytest.param("L=0.5 F1=0.1",     id = "f1"),
    pytest.param("L=0.5 F2=0.1",     id = "f2"),
    pytest.param("L=0.5 FB1=0.1",    id = "fb1"),
    pytest.param("L=0.5 FB2=0.1",    id = "fb2"),
    pytest.param("L=0.5 F1K1F=0.1",  id = "f1k1f"),
    pytest.param("L=0.5 F2K1F=0.1",  id = "f2k1f"),
    pytest.param("L=0.5 F1K1B=0.1",  id = "f1k1b"),
    pytest.param("L=0.5 F2K1B=0.1",  id = "f2k1b"),
]

@pytest.mark.parametrize("params", REJECTED_PARAMS)
def test_cavi_rejects(sad_rejects, params):
    """
    SAD's CAVI element should reject bending (ANGLE), multipole
    (K0-K4/SK0-SK4/BZ) field parameters, and the QUAD/BEND/MULT-style
    linear soft-edge fringe parameters (F1/F2/FB1/FB2/F1K1x) -- CAVI's own
    fringe is a distinct mechanism gated by FRINGE/DISFRIN alone (see
    docs/reference/sad-behaviour.md).
    """
    sad_rejects(
        f"CAVI C1 = ({params});\n"
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

################################################################################
# FRINGE/DISFRIN RF edge-focusing kick (ground truth) -- see
# docs/reference/sad-behaviour.md
################################################################################
def _track_cavi_probe(tmp_path, extra, name):
    """
    Track a single off-axis, off-crest particle through a VOLT CAVI and
    return the track_sad result.
    """
    lat = tmp_path / name
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        f"CAVI C1 = (L=0.5 VOLT=5E7 FREQ=5E8 PHI=0.3{extra});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return track_sad(
            lattice_filepath    = lat.name,
            line_name           = "TEST",
            x_init              = np.array([0.03]),
            px_init             = np.array([0.01]),
            y_init              = np.array([0.02]),
            py_init             = np.array([-0.005]),
            zeta_init           = np.array([0.0]),
            delta_init          = np.array([0.0]),
            n_turns             = 1,
            rfsw                = True,
            with_progress       = False)
    finally:
        os.chdir(cwd)

def test_cavi_disfrin_default_matches_explicit_zero(tmp_path):
    """
    DISFRIN unset defaults to DISFRIN=0 (edge-focusing kick enabled) --
    bit-identical output, not just approximately equal.
    """
    r_unset = _track_cavi_probe(tmp_path, "", "cavi_disfrin_unset.sad")
    r_zero  = _track_cavi_probe(tmp_path, " DISFRIN=0", "cavi_disfrin_zero.sad")
    assert r_unset["px"][0] == pytest.approx(r_zero["px"][0], abs=1e-15), (
        "DISFRIN unset should default to DISFRIN=0 (edge-focusing kick "
        "enabled), bit-identically.")

def test_cavi_disfrin_is_boolean(tmp_path):
    """
    DISFRIN is a strict boolean gate on a CAVI, same as on the other
    elements: any nonzero value disables the edge-focusing kick
    identically.
    """
    disfrin_1 = _track_cavi_probe(tmp_path, " DISFRIN=1", "cavi_disfrin_bool_1.sad")["px"][0]
    for disfrin in (2, -1, 3, 0.5):
        r = _track_cavi_probe(tmp_path, f" DISFRIN={disfrin}", f"cavi_disfrin_bool_{disfrin}.sad")
        assert r["px"][0] == pytest.approx(disfrin_1, abs=1e-15), (
            f"DISFRIN={disfrin} should disable the edge-focusing kick "
            "identically to DISFRIN=1 -- DISFRIN is boolean, not graded.")

def test_cavi_fringe_mode_gates_entrance_exit(tmp_path):
    """
    CAVI's FRINGE mode grid against real SAD -- see docs/reference/sad-behaviour.md
    ("CAVI FRINGE/DISFRIN RF edge-focusing kick") for the numbering, a
    third distinct system from BEND's and QUAD's/MULT's.
    """
    def run(fringe):
        return _track_cavi_probe(tmp_path, f" FRINGE={fringe}", f"cavi_mode_{fringe}.sad")["px"][0]

    both    = run(0)
    entry   = run(1)
    exit_   = run(2)
    neither = run(-1)

    assert entry != pytest.approx(both) and entry != pytest.approx(neither), (
        "FRINGE=1 (entrance-only) should differ from both the "
        "both-active and neither-active cases.")
    assert exit_ != pytest.approx(both) and exit_ != pytest.approx(neither), (
        "FRINGE=2 (exit-only) should differ from both the both-active "
        "and neither-active cases.")
    assert entry != pytest.approx(exit_), (
        "FRINGE=1 (entrance-only) and FRINGE=2 (exit-only) should give "
        "different kicks.")

    for fringe in (3, 4):
        assert run(fringe) == pytest.approx(both, abs=1e-15), (
            f"FRINGE={fringe} should enable both edges, identically to "
            "FRINGE=0/unset -- unlike QUAD/MULT, CAVI's FRINGE is not a "
            "strict {1,2,3} membership test; any value other than "
            "exactly 1 or 2 (and non-negative) leaves both edges active.")

    assert run(-4) == pytest.approx(neither, abs=1e-15), (
        "FRINGE=-4 should disable both edges, identically to FRINGE=-1 "
        "-- any negative FRINGE value is CAVI's master-disable, matching "
        "DISFRIN=1.")

def test_cavi_fringe_disfrin_matches_sad_reference_values(tmp_path):
    """
    Pinned ground truth: L=0.5, VOLT=5E7, FREQ=5E8, PHI=0.3,
    x=0.03/px=0.01/y=0.02/py=-0.005 on entry, with the edge-focusing kick
    enabled (default) and disabled (DISFRIN=1). Real SAD binary outputs,
    recorded once and locked in.
    """
    r_on  = _track_cavi_probe(tmp_path, "", "cavi_ref_on.sad")
    r_off = _track_cavi_probe(tmp_path, " DISFRIN=1", "cavi_ref_off.sad")

    assert r_on["px"][0] == pytest.approx(0.009922189769497153, rel=1e-6), (
        "SAD's px with the edge-focusing kick enabled no longer matches "
        "the pinned reference value.")
    assert r_off["px"][0] == pytest.approx(0.009999997876124751, rel=1e-6), (
        "SAD's px with the edge-focusing kick disabled (DISFRIN=1) no "
        "longer matches the pinned reference value.")
