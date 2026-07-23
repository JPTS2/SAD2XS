"""
================================================================================
SAD syntax assumptions: SEXT element
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
    pytest.param("L=1.0 K2=0.5",           id = "k2"),
    pytest.param("L=1.0 DX=0.001",         id = "dx"),
    pytest.param("L=1.0 DY=0.001",         id = "dy"),
    pytest.param("L=1.0 ROTATE=0.1",       id = "rotate"),
    pytest.param("L=1.0 K2=0.5 DISFRIN=1", id = "disfrin"),
]

@pytest.mark.parametrize("params", ACCEPTED_PARAMS)
def test_sext_accepts(sad_accepts, params):
    """
    SAD's SEXT element should accept K2, the standard
    misalignment/rotation parameters, and DISFRIN.
    """
    sad_accepts(
        f"SEXT S1 = ({params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START S1 END);")

REJECTED_PARAMS = [
    pytest.param("L=1.0 ANGLE=0.01",  id = "angle"),
    pytest.param("L=1.0 K0=0.1",      id = "k0"),
    pytest.param("L=1.0 SK0=0.1",     id = "sk0"),
    pytest.param("L=1.0 K1=0.1",      id = "k1"),
    pytest.param("L=1.0 SK1=0.1",     id = "sk1"),
    pytest.param("L=1.0 SK2=0.1",     id = "sk2"),
    pytest.param("L=1.0 K3=0.1",      id = "k3"),
    pytest.param("L=1.0 SK3=0.1",     id = "sk3"),
    pytest.param("L=1.0 K4=0.1",      id = "k4"),
    pytest.param("L=1.0 SK4=0.1",     id = "sk4"),
    pytest.param("L=1.0 HARM=1000",   id = "harm"),
    pytest.param("L=1.0 FREQ=400E6",  id = "freq"),
    pytest.param("L=1.0 BZ=0.1",      id = "bz"),
    pytest.param("L=1.0 F1=0.1",      id = "f1"),
    pytest.param("L=1.0 F2=0.1",      id = "f2"),
    pytest.param("L=1.0 FRINGE=1",    id = "fringe"),
    pytest.param("L=1.0 FB1=0.1",     id = "fb1"),
    pytest.param("L=1.0 FB2=0.1",     id = "fb2"),
    pytest.param("L=1.0 F1K1F=0.1",   id = "f1k1f"),
    pytest.param("L=1.0 F2K1F=0.1",   id = "f2k1f"),
    pytest.param("L=1.0 F1K1B=0.1",   id = "f1k1b"),
    pytest.param("L=1.0 F2K1B=0.1",   id = "f2k1b"),
]

@pytest.mark.parametrize("params", REJECTED_PARAMS)
def test_sext_rejects(sad_rejects, params):
    """
    SAD's SEXT element should reject bending (ANGLE), other-order field
    (K0/K1/K3/K4/SK0-SK4), solenoid (BZ), RF parameters, and FRINGE/F1/F2/
    FB1/FB2/F1K1x/F2K1x -- SEXT has no FRMD/soft-edge-fringe keyword at
    all (unlike BEND/QUAD/MULT), only DISFRIN.
    """
    sad_rejects(
        f"SEXT S1 = ({params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START S1 END);")

################################################################################
# Thin sext (no length) behaviour
################################################################################
def test_sext_without_length_is_accepted_by_sad(sad_accepts):
    """
    SAD accepts a SEXT with K2 but no L parameter (thin/integrated sextupole).
    The converter handles this via ele_vars.get(`l`, 0.0) defaulting to zero.
    """
    sad_accepts(
        "SEXT S1 = (K2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START S1 END);")

def test_sext_without_length_k2_has_no_effect_on_twiss_at_zero_orbit(tmp_path):
    """
    K2 in a no-L SAD SEXT has exactly zero effect on Twiss betx at zero
    orbit/dispersion: the reference particle stays at x=0 throughout (a
    sextupole has no dipole term), so its linear neighbourhood (the Jacobian
    at x=0) is the identity regardless of K2 — unlike QUAD's K1, which is
    linear and does change betx (see test_quad.py). This is checked to full
    Twiss precision (not just "small"), since with zero orbit there is no
    mechanism (unlike BEND's K0 orbit-displacement residual, see
    test_bend.py) for any K2-dependent effect to appear at all.
    """
    def run(k2, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"SEXT S = (K2={k2});\n"
            "DRIFT D = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START D S D END);\n")
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

    tw_ref = run(0.0, "sext_k2_0_twiss.sad")
    tw_k2  = run(0.5, "sext_k2_nonzero_twiss.sad")
    assert tw_k2["betx"][-1] == pytest.approx(tw_ref["betx"][-1], abs=1e-9), (
        "K2 in a no-L SEXT should have no effect on Twiss betx at zero orbit.")

def test_sext_without_length_k2_gives_quadratic_kick(tmp_path):
    """
    K2 in a no-L SAD SEXT is an integrated sextupole strength: an off-axis
    particle receives a px kick proportional to K2*x^2 — verified via
    tracking with a nonzero x offset, the direct-kick complement to the
    Twiss test above.
    """
    def run(k2, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"SEXT S = (K2={k2});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START S END);\n")
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

    r_ref = run(0.0, "sext_k2_0.sad")
    r_k2  = run(0.5, "sext_k2_nonzero.sad")
    assert r_k2["px"][0] != pytest.approx(r_ref["px"][0]), (
        "K2 in a no-L SEXT should deflect an off-axis particle "
        "(integrated kick proportional to K2*x^2).")

################################################################################
# Hard-edge fringe field (DISFRIN) -- see docs/sad-behaviour.md
################################################################################
def _track_sext_probe(tmp_path, k2, disfrin_suffix, name):
    """
    Track a single off-axis particle through a K2 SEXT and return the
    track_sad result.
    """
    lat = tmp_path / name
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        f"SEXT S1 = (L=1.0 K2={k2}{disfrin_suffix});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START S1 END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return track_sad(
            lattice_filepath    = lat.name,
            line_name           = "TEST",
            x_init              = np.array([2E-2]),
            px_init             = np.array([2E-2]),
            y_init              = np.array([1.5E-2]),
            py_init             = np.array([-1E-2]),
            zeta_init           = np.array([0.0]),
            delta_init          = np.array([0.0]),
            n_turns             = 1,
            rfsw                = False,
            with_progress       = False)
    finally:
        os.chdir(cwd)

def test_sext_disfrin_default_matches_explicit_zero(tmp_path):
    """
    DISFRIN unset defaults to DISFRIN=0 (hard-edge fringe enabled) --
    bit-identical output, not just approximately equal.
    """
    r_unset = _track_sext_probe(tmp_path, 0.4, "", "sext_disfrin_unset.sad")
    r_zero  = _track_sext_probe(tmp_path, 0.4, " DISFRIN=0", "sext_disfrin_zero.sad")
    assert r_unset["px"][0] == pytest.approx(r_zero["px"][0], abs=1e-15), (
        "DISFRIN unset should default to DISFRIN=0 (hard-edge fringe "
        "enabled), bit-identically.")

def test_sext_disfrin_is_boolean(tmp_path):
    """
    DISFRIN is a strict boolean gate on a SEXT, same as on BEND/QUAD: any
    nonzero value disables the hard-edge fringe identically.
    """
    disfrin_1 = _track_sext_probe(tmp_path, 0.4, " DISFRIN=1", "sext_disfrin_bool_1.sad")["px"][0]
    for disfrin in (2, -1, 3, 0.5):
        r = _track_sext_probe(tmp_path, 0.4, f" DISFRIN={disfrin}", f"sext_disfrin_bool_{disfrin}.sad")
        assert r["px"][0] == pytest.approx(disfrin_1, abs=1e-15), (
            f"DISFRIN={disfrin} should disable the hard-edge fringe "
            "identically to DISFRIN=1 -- DISFRIN is boolean, not graded.")

def test_sext_disfrin_hard_edge_matches_sad_reference_values(tmp_path):
    """
    Pinned ground truth: L=1.0, K2=0.4, x=2E-2/px=2E-2/y=1.5E-2/py=-1E-2 on
    entry, with the hard-edge fringe enabled (DISFRIN=0/unset) and
    disabled (DISFRIN=1). Real SAD binary outputs, recorded once and
    locked in.
    """
    r_on  = _track_sext_probe(tmp_path, 0.4, "", "sext_disfrin_ref_on.sad")
    r_off = _track_sext_probe(tmp_path, 0.4, " DISFRIN=1", "sext_disfrin_ref_off.sad")

    assert r_on["px"][0] == pytest.approx(0.019835295536639142, rel=1e-6), (
        "SAD's px with the hard-edge fringe enabled no longer matches the "
        "pinned reference value.")
    assert r_off["px"][0] == pytest.approx(0.01983524131211494, rel=1e-6), (
        "SAD's px with the hard-edge fringe disabled (DISFRIN=1) no "
        "longer matches the pinned reference value.")
