"""
================================================================================
SAD syntax assumptions: SEXT element
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-17
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
    pytest.param("L=1.0 K2=0.5",     id = "k2"),
    pytest.param("L=1.0 DX=0.001",   id = "dx"),
    pytest.param("L=1.0 DY=0.001",   id = "dy"),
    pytest.param("L=1.0 ROTATE=0.1", id = "rotate"),
]

@pytest.mark.parametrize("params", ACCEPTED_PARAMS)
def test_sext_accepts(sad_accepts, params):
    """
    SAD's SEXT element should accept K2 and the standard
    misalignment/rotation parameters.
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
]

@pytest.mark.parametrize("params", REJECTED_PARAMS)
def test_sext_rejects(sad_rejects, params):
    """
    SAD's SEXT element should reject bending (ANGLE), other-order field
    (K0/K1/K3/K4/SK0-SK4), solenoid (BZ), and RF parameters.
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
    The converter handles this via ele_vars.get('l', 0.0) defaulting to zero.
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
