"""
================================================================================
SAD syntax assumptions: QUAD element
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
    pytest.param("L=1.0 K1=0.2",                     id = "k1"),
    pytest.param("L=1.0 DX=0.001",                   id = "dx"),
    pytest.param("L=1.0 DY=0.001",                   id = "dy"),
    pytest.param("L=1.0 ROTATE=0.1",                 id = "rotate"),
    pytest.param("L=1.0 K1=0.2 F1=0.02",             id = "f1"),
    pytest.param("L=1.0 K1=0.2 F2=0.01",             id = "f2"),
    pytest.param("L=1.0 K1=0.2 F1=0.02 FRINGE=3",    id = "fringe"),
    pytest.param("L=1.0 K1=0.2 F1K1F=0.02",          id = "f1k1f"),
    pytest.param("L=1.0 K1=0.2 F2K1F=0.01",          id = "f2k1f"),
    pytest.param("L=1.0 K1=0.2 F1K1B=0.02",          id = "f1k1b"),
    pytest.param("L=1.0 K1=0.2 F2K1B=0.01",          id = "f2k1b"),
    pytest.param("L=1.0 K1=0.2 DISFRIN=1",           id = "disfrin"),
]

@pytest.mark.parametrize("params", ACCEPTED_PARAMS)
def test_quad_accepts(sad_accepts, params):
    """
    SAD's QUAD element should accept K1, the standard
    misalignment/rotation parameters, DISFRIN, and the F1/F2/FRINGE
    linear fringe parameters (including the per-side asymmetric
    F1K1F/F2K1F/F1K1B/F2K1B terms).
    """
    sad_accepts(
        f"QUAD Q1 = ({params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

REJECTED_PARAMS = [
    pytest.param("L=1.0 ANGLE=0.01",  id = "angle"),
    pytest.param("L=1.0 K0=0.1",      id = "k0"),
    pytest.param("L=1.0 SK0=0.1",     id = "sk0"),
    pytest.param("L=1.0 SK1=0.1",     id = "sk1"),
    pytest.param("L=1.0 K2=0.1",      id = "k2"),
    pytest.param("L=1.0 SK2=0.1",     id = "sk2"),
    pytest.param("L=1.0 K3=0.1",      id = "k3"),
    pytest.param("L=1.0 SK3=0.1",     id = "sk3"),
    pytest.param("L=1.0 K4=0.1",      id = "k4"),
    pytest.param("L=1.0 SK4=0.1",     id = "sk4"),
    pytest.param("L=1.0 HARM=1000",   id = "harm"),
    pytest.param("L=1.0 FREQ=400E6",  id = "freq"),
    pytest.param("L=1.0 BZ=0.1",      id = "bz"),
    pytest.param("L=1.0 FB1=0.1",     id = "fb1"),
    pytest.param("L=1.0 FB2=0.1",     id = "fb2"),
]

@pytest.mark.parametrize("params", REJECTED_PARAMS)
def test_quad_rejects(sad_rejects, params):
    """
    SAD's QUAD element should reject bending (ANGLE), other-order field
    (K0/K2-K4/SK0-SK4), solenoid (BZ), RF parameters, and BEND's own
    per-edge FB1/FB2 -- QUAD's fringe is F1/F2/F1K1x only.
    """
    sad_rejects(
        f"QUAD Q1 = ({params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

################################################################################
# Thin quad (no length) behaviour
#
# K1 in a no-L QUAD is an integrated quadrupole strength: it affects BOTH
# Twiss (linear focusing) AND tracking (a direct px kick), verified by both
# tests below — same pattern as BEND's K1 (see test_bend.py).
################################################################################
def test_quad_without_length_is_accepted_by_sad(sad_accepts):
    """
    SAD accepts a QUAD with K1 but no L parameter (thin/integrated quadrupole).
    The converter handles this via ele_vars.get(`l`, 0.0) defaulting to zero.
    """
    sad_accepts(
        "QUAD Q1 = (K1=0.2);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START Q1 END);")

def test_quad_without_length_k1_affects_twiss(tmp_path):
    """
    K1 in a no-L SAD QUAD is an integrated quadrupole strength.
    Twiss betx must differ between K1=0 and K1=0.5, confirming the element
    actively focuses the beam rather than acting as a passive placeholder.
    """
    def run(k1, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"QUAD Q = (K1={k1});\n"
            "DRIFT D = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START D Q D END);\n")
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

    tw_ref = run(0.0, "quad_k1_0.sad")
    tw_k1  = run(0.5, "quad_k1_nonzero.sad")
    assert tw_k1["betx"][-1] != pytest.approx(tw_ref["betx"][-1]), (
        "K1 in a no-L QUAD should focus the beam and change Twiss betx.")

def test_quad_without_length_k1_gives_linear_kick(tmp_path):
    """
    K1 in a no-L SAD QUAD gives a direct px kick on an off-axis particle
    (px kick = -K1*x), verified via tracking as the direct-kick complement
    to the Twiss test above — mirrors BEND's K1 tracking test.
    """
    def run(k1, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"QUAD Q = (K1={k1});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START Q END);\n")
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

    r_ref = run(0.0, "quad_k1_0_track.sad")
    r_k1  = run(0.5, "quad_k1_nonzero_track.sad")
    assert r_k1["px"][0] != pytest.approx(r_ref["px"][0]), (
        "K1 in a no-L QUAD should deflect an off-axis particle (kick = -K1*x).")

################################################################################
# F1/F2/FRINGE soft-edge fringe (ground truth) -- see docs/sad-behaviour.md
################################################################################
def _track_quad_probe(tmp_path, lattice_body, name, x_vals, px_vals, y_vals, py_vals):
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

def test_quad_f1_f2_is_inert_without_fringe(tmp_path):
    """
    F1/F2 on a QUAD has no effect unless FRINGE is also set (nonzero) --
    same convention as BEND's F1 (test_bend_f1_is_inert_without_fringe).
    """
    x_vals, px_vals = np.array([1e-3]), np.array([2e-3])
    y_vals, py_vals = np.array([-1.5e-3]), np.array([0.5e-3])
    body_no_fringe = "QUAD Q1 = (L=1.0 K1=0.3 F1=0.02 F2=0.01);\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"
    body_no_f1f2   = "QUAD Q1 = (L=1.0 K1=0.3);\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"
    r_fringe  = _track_quad_probe(tmp_path, body_no_fringe, "quad_f1f2_no_fringe.sad", x_vals, px_vals, y_vals, py_vals)
    r_no_f1f2 = _track_quad_probe(tmp_path, body_no_f1f2, "quad_no_f1f2.sad", x_vals, px_vals, y_vals, py_vals)
    for coord in ("x", "px", "y", "py"):
        assert r_fringe[coord][0] == pytest.approx(r_no_f1f2[coord][0], abs=1e-15), (
            f"F1/F2 on a QUAD should have no effect on {coord} while FRINGE "
            "is unset (default off).")

def test_quad_fringe_3_activates_f1_f2(tmp_path):
    """
    FRINGE=3 on a QUAD activates the F1/F2 fringe kick.
    """
    x_vals, px_vals = np.array([1e-3]), np.array([2e-3])
    y_vals, py_vals = np.array([-1.5e-3]), np.array([0.5e-3])
    body_off = "QUAD Q1 = (L=1.0 K1=0.3 F1=0.02 F2=0.01);\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"
    body_on  = "QUAD Q1 = (L=1.0 K1=0.3 F1=0.02 F2=0.01 FRINGE=3);\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"
    r_off = _track_quad_probe(tmp_path, body_off, "quad_fringe_off.sad", x_vals, px_vals, y_vals, py_vals)
    r_on  = _track_quad_probe(tmp_path, body_on, "quad_fringe_on.sad", x_vals, px_vals, y_vals, py_vals)
    assert r_on["x"][0] != pytest.approx(r_off["x"][0]), (
        "FRINGE=3 on a QUAD with F1/F2 set should change tracking relative "
        "to FRINGE unset.")

def test_quad_fringe_mode_gates_entrance_exit(tmp_path):
    """
    QUAD's FRINGE mode grid against real SAD -- see docs/sad-behaviour.md
    ("QUAD F1/F2/FRINGE soft-edge fringe") for the {1,2,3} semantic, a
    different system from BEND's FRMD_BEND. Asymmetric F1K1F/F1K1B/
    F2K1F/F2K1B makes all cases numerically distinct.
    """
    x_vals, px_vals = np.array([1e-3]), np.array([2e-3])
    y_vals, py_vals = np.array([-1.5e-3]), np.array([0.5e-3])

    def run(fringe):
        body = (
            f"QUAD Q1 = (L=1.0 K1=0.3 F1K1F=0.05 F2K1F=0.02 F1K1B=-0.03 "
            f"F2K1B=-0.01 FRINGE={fringe});\n"
            "MARK START=()\n END=();\nLINE TEST=(START Q1 END);")
        return _track_quad_probe(
            tmp_path, body, f"quad_mfring_{fringe}.sad", x_vals, px_vals, y_vals, py_vals)["x"][0]

    neither = run(0)
    entry   = run(1)
    exit_   = run(2)
    both    = run(3)

    assert entry != pytest.approx(neither) and entry != pytest.approx(both), (
        "FRINGE=1 (entrance-only) should differ from both the "
        "both-active and neither-active cases.")
    assert exit_ != pytest.approx(neither) and exit_ != pytest.approx(both), (
        "FRINGE=2 (exit-only) should differ from both the both-active "
        "and neither-active cases.")
    assert entry != pytest.approx(exit_), (
        "FRINGE=1 (entrance-only) and FRINGE=2 (exit-only) should give "
        "different kicks for asymmetric F1K1F/F1K1B/F2K1F/F2K1B.")

    for fringe in (-3, -1, 4, 5):
        assert run(fringe) == pytest.approx(neither, abs=1e-15), (
            f"FRINGE={fringe} should leave the linear fringe off, "
            "identically to FRINGE=0 -- unlike BEND, QUAD's FRINGE is a "
            "strict {1,2,3} membership test, not sign-graded.")

def test_quad_fringe_mode_also_gates_hard_edge_fringe_sides(tmp_path):
    """
    FRINGE also gates which side of the DISFRIN hard-edge fringe applies
    -- see docs/sad-behaviour.md ("QUAD DISFRIN hard-edge fringe, and
    its interaction with FRINGE"). No F1/F2/F1K1x set here, isolating the
    hard-edge effect alone.
    """
    x_vals, px_vals = np.array([2e-2]), np.array([2e-2])
    y_vals, py_vals = np.array([0.0]), np.array([0.0])

    def run(suffix, name):
        body = f"QUAD Q1 = (L=0.5 K1=0.4{suffix});\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"
        return _track_quad_probe(tmp_path, body, name, x_vals, px_vals, y_vals, py_vals)["px"][0]

    default  = run("", "quad_hardedge_default.sad")
    fringe0  = run(" FRINGE=0", "quad_hardedge_f0.sad")
    fringe1  = run(" FRINGE=1", "quad_hardedge_f1.sad")
    fringe2  = run(" FRINGE=2", "quad_hardedge_f2.sad")
    fringe3  = run(" FRINGE=3", "quad_hardedge_f3.sad")
    fringe4  = run(" FRINGE=4", "quad_hardedge_f4.sad")
    fringem4 = run(" FRINGE=-4", "quad_hardedge_fm4.sad")
    disfrin1 = run(" DISFRIN=1", "quad_hardedge_disfrin.sad")

    assert fringe0 == pytest.approx(default, abs=1e-15), (
        "FRINGE=0 should match FRINGE unset bit-identically.")
    assert fringe3 == pytest.approx(default, abs=1e-15), (
        "FRINGE=3 (both sides active) should leave the hard-edge fringe "
        "unaffected relative to FRINGE unset -- neither side is excluded.")
    assert fringe4 == pytest.approx(default, abs=1e-15), (
        "FRINGE=4 (off-grid for the linear kick) should also leave the "
        "hard-edge fringe unaffected -- only FRINGE==1/2 specifically "
        "exclude a side.")
    assert fringe1 != pytest.approx(default), (
        "FRINGE=1 should disable the EXIT-side hard-edge fringe (as well "
        "as activating the linear fringe entrance-only), changing "
        "tracking relative to FRINGE unset even with no F1/F2 set.")
    assert fringe2 != pytest.approx(default), (
        "FRINGE=2 should disable the ENTRANCE-side hard-edge fringe, "
        "changing tracking relative to FRINGE unset even with no F1/F2 "
        "set.")
    assert fringem4 == pytest.approx(disfrin1, abs=1e-15), (
        "FRINGE<=-4 should disable the hard-edge fringe on BOTH sides "
        "unconditionally, bit-identical to DISFRIN=1.")

def test_quad_f1_f2_matches_sad_reference_values(tmp_path):
    """
    Pinned ground truth: L=1.0, K1=0.3, F1=0.02, F2=0.01, FRINGE=3, four
    asymmetric particle offsets. Real SAD binary outputs, recorded once
    and locked in -- any future change in SAD2XS's understanding of this
    formula should be checked against a fresh SAD run, not against this
    file.
    """
    x_vals  = np.array([1e-3, -2e-3, 3e-3, -1.5e-3])
    px_vals = np.array([2e-3, 1.5e-3, -1e-3, -0.5e-3])
    y_vals  = np.array([-1.5e-3, 2.5e-3, -0.5e-3, 1e-3])
    py_vals = np.array([0.5e-3, -1e-3, 2e-3, 1.5e-3])
    body = "QUAD Q1 = (L=1.0 K1=0.3 F1=0.02 F2=0.01 FRINGE=3);\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"
    result = _track_quad_probe(tmp_path, body, "quad_f1f2_reference.sad", x_vals, px_vals, y_vals, py_vals)

    expected = {
        "x":  [0.0027646062615639413, -0.0002719017042603537,
               0.0016026935113949575, -0.0017572220878945076],
        "px": [0.0014204934595131308, 0.0018497266817731174,
               -0.0017085195897034292, 1.4037153860402687e-06],
        "y":  [-0.0012073498520841902, 0.0018382780271788731,
               0.0015112375695447897, 0.0027185836458856276],
        "py": [0.00010357641823981179, -0.0003647678091417484,
               0.002148070043330325, 0.0020444917558556878],
    }
    for coord, exp in expected.items():
        np.testing.assert_allclose(
            result[coord], exp, rtol = 1e-6,
            err_msg = (
                f"SAD's on-momentum {coord} for a K1>0 QUAD with "
                "F1/F2/FRINGE set no longer matches the pinned reference "
                "values -- SAD's fringe behaviour may have changed, or "
                "this reference lattice was altered unintentionally."))

def test_quad_f1_f2_matches_sad_reference_values_negative_k1(tmp_path):
    """
    Same as test_quad_f1_f2_matches_sad_reference_values but K1<0
    (defocusing) -- pins the sign-asymmetric case that requires SAD's
    internal ROTATE+akang(K1) frame rotation to reproduce (see
    docs/sad-behaviour.md). L=1.0, K1=-0.3, F1=0.02, F2=0.01, FRINGE=3.
    """
    x_vals  = np.array([1e-3, -2e-3, 3e-3, -1.5e-3])
    px_vals = np.array([2e-3, 1.5e-3, -1e-3, -0.5e-3])
    y_vals  = np.array([-1.5e-3, 2.5e-3, -0.5e-3, 1e-3])
    py_vals = np.array([0.5e-3, -1e-3, 2e-3, 1.5e-3])
    body = "QUAD Q1 = (L=1.0 K1=-0.3 F1=0.02 F2=0.01 FRINGE=3);\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"
    result = _track_quad_probe(tmp_path, body, "quad_f1f2_reference_neg_k1.sad", x_vals, px_vals, y_vals, py_vals)

    expected = {
        "x":  [0.0032405003235751544, -0.000739942571683273,
               0.002414699223982366, -0.0022511771370001075],
        "px": [0.0026209127034577335, 0.0010988047128891985,
               -0.00020715240355583095, -0.0010492654169446743],
        "y":  [-0.0008013467078773191, 0.001176267086846478,
               0.0014853211131956546, 0.002286668006520242],
        "py": [0.0008542604235996558, -0.0015659088342059287,
               0.0018483239963007205, 0.0009940644495584074],
    }
    for coord, exp in expected.items():
        np.testing.assert_allclose(
            result[coord], exp, rtol = 1e-6,
            err_msg = (
                f"SAD's on-momentum {coord} for a K1<0 QUAD with "
                "F1/F2/FRINGE set no longer matches the pinned reference "
                "values -- SAD's fringe behaviour may have changed, or "
                "this reference lattice was altered unintentionally."))

def test_quad_f1_f2_skew_matches_sad_reference_values(tmp_path):
    """
    Pinned ground truth for a skewed (ROTATE != 0) QUAD with F1/F2 set --
    confirms the fringe rotates with the element rather than assuming an
    unrotated frame. L=1.0, K1=0.3, F1=0.02, F2=0.01, ROTATE=0.3,
    FRINGE=3. Uses a generic synthetic angle, not any real lattice's
    value.
    """
    x_vals  = np.array([1e-3, -2e-3, 3e-3, -1.5e-3])
    px_vals = np.array([2e-3, 1.5e-3, -1e-3, -0.5e-3])
    y_vals  = np.array([-1.5e-3, 2.5e-3, -0.5e-3, 1e-3])
    py_vals = np.array([0.5e-3, -1e-3, 2e-3, 1.5e-3])
    body = "QUAD Q1 = (L=1.0 K1=0.3 F1=0.02 F2=0.01 ROTATE=0.3 FRINGE=3);\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"
    result = _track_quad_probe(tmp_path, body, "quad_f1f2_reference_skew.sad", x_vals, px_vals, y_vals, py_vals)

    expected = {
        "x":  [0.002691543928200726, -0.0001258765744020436,
               0.0016809238780905527, -0.0016784216222158392],
        "px": [0.0013133949543761624, 0.0021232539460546997,
               -0.0014927765151138237, 0.0002062041862045029],
        "y":  [-0.0010375384027924944, 0.0016483251090365027,
               0.0017382212385288385, 0.0025414090897225555],
        "py": [0.0005080398586279, -0.0006816670424178315,
               0.002545759879393711, 0.001656129928897873],
    }
    for coord, exp in expected.items():
        np.testing.assert_allclose(
            result[coord], exp, rtol = 1e-6,
            err_msg = (
                f"SAD's on-momentum {coord} for a skewed (ROTATE!=0) QUAD "
                "with F1/F2/FRINGE set no longer matches the pinned "
                "reference values -- SAD's fringe behaviour may have "
                "changed, or this reference lattice was altered "
                "unintentionally."))

def test_quad_asymmetric_f1k1_terms_differ_from_symmetric_f1(tmp_path):
    """
    F1K1F/F1K1B (and F2K1F/F2K1B) genuinely differ from an equivalent
    symmetric F1/F2 of the same (entrance) magnitude, once F1K1F !=
    F1K1B -- confirms they are not silently ignored/collapsed to plain
    F1/F2.
    """
    x_vals  = np.array([1e-3, -2e-3, 3e-3, -1.5e-3])
    px_vals = np.array([2e-3, 1.5e-3, -1e-3, -0.5e-3])
    y_vals  = np.array([-1.5e-3, 2.5e-3, -0.5e-3, 1e-3])
    py_vals = np.array([0.5e-3, -1e-3, 2e-3, 1.5e-3])
    body_asymmetric = (
        "QUAD Q1 = (L=1.0 K1=0.3 F1K1F=0.05 F1K1B=-0.03 F2K1F=0.02 "
        "F2K1B=-0.01 FRINGE=3);\n"
        "MARK START=()\n END=();\nLINE TEST=(START Q1 END);")
    body_symmetric_equivalent = (
        "QUAD Q1 = (L=1.0 K1=0.3 F1=0.05 F2=0.02 FRINGE=3);\n"
        "MARK START=()\n END=();\nLINE TEST=(START Q1 END);")
    r_asym = _track_quad_probe(
        tmp_path, body_asymmetric, "quad_asym.sad", x_vals, px_vals, y_vals, py_vals)
    r_sym  = _track_quad_probe(
        tmp_path, body_symmetric_equivalent, "quad_sym_equiv.sad", x_vals, px_vals, y_vals, py_vals)
    assert not np.allclose(r_asym["x"], r_sym["x"]), (
        "F1K1F/F1K1B set asymmetrically should produce different tracking "
        "than an equivalent symmetric F1 of the same (entrance) "
        "magnitude.")

def test_quad_reversed_line_fringe_mode_permutes(tmp_path):
    """
    Pinned reversal-permutation ground truth -- see docs/sad-behaviour.md
    ("QUAD F1/F2/FRINGE soft-edge fringe"): reversed FRINGE=1 must match
    forward FRINGE=2 with F1K1F/F1K1B (and F2K1F/F2K1B) swapped, not just
    the unswapped forward FRINGE=2 (a real ~1.3e-5 discrepancy, checked).
    """
    x_vals, px_vals = np.array([1e-3]), np.array([2e-3])
    y_vals, py_vals = np.array([-1.5e-3]), np.array([0.5e-3])

    body_reversed = (
        "QUAD Q1 = (L=1.0 K1=0.3 F1K1F=0.05 F1K1B=-0.03 F2K1F=0.02 "
        "F2K1B=-0.01 FRINGE=1);\nMARK START=()\n END=();\n"
        "LINE FWD = (START Q1 END);\nLINE TESTREV = (-FWD);")
    lat = tmp_path / "quad_reversed_mode.sad"
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
        "QUAD Q1 = (L=1.0 K1=0.3 F1K1F=-0.03 F1K1B=0.05 F2K1F=-0.01 "
        "F2K1B=0.02 FRINGE=2);\n"
        "MARK START=()\n END=();\nLINE TEST=(START Q1 END);")
    r_forward_swapped = _track_quad_probe(
        tmp_path, body_forward_swapped, "quad_forward_swapped.sad",
        x_vals, px_vals, y_vals, py_vals)

    for coord in ("x", "px", "y", "py"):
        assert r_reversed[coord][0] == pytest.approx(
                r_forward_swapped[coord][0], abs = 1e-12), (
            f"Reversed FRINGE=1 traversal should exactly match forward "
            f"FRINGE=2 with F1K1F/F1K1B (and F2K1F/F2K1B) swapped, on "
            f"{coord} -- SAD's reversal convention for the linear fringe "
            "may have changed.")

def test_quad_f1_f2_composes_additively_with_default_nonlinear_fringe(tmp_path):
    """
    The linear F1/F2 fringe and the default nonlinear (DISFRIN) fringe
    compose (near-)additively at FRINGE=3, where the hard-edge fringe
    stays active on both sides (not true at FRINGE=1/2 -- see
    docs/sad-behaviour.md). L=0.5, K1=0.4, F1=0.03, x0=px0=2E-2.
    """
    x_vals, px_vals = np.array([2e-2]), np.array([2e-2])
    y_vals, py_vals = np.array([0.0]), np.array([0.0])

    body_both       = "QUAD Q1 = (L=0.5 K1=0.4 F1=0.03 FRINGE=3);\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"
    body_linear     = "QUAD Q1 = (L=0.5 K1=0.4 F1=0.03 FRINGE=3 DISFRIN=1);\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"
    body_nonlin_on  = "QUAD Q1 = (L=0.5 K1=0.4);\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"
    body_nonlin_off = "QUAD Q1 = (L=0.5 K1=0.4 DISFRIN=1);\nMARK START=()\n END=();\nLINE TEST=(START Q1 END);"

    r_both       = _track_quad_probe(tmp_path, body_both, "quad_both.sad", x_vals, px_vals, y_vals, py_vals)
    r_linear     = _track_quad_probe(tmp_path, body_linear, "quad_linear.sad", x_vals, px_vals, y_vals, py_vals)
    r_nonlin_on  = _track_quad_probe(tmp_path, body_nonlin_on, "quad_nonlin_on.sad", x_vals, px_vals, y_vals, py_vals)
    r_nonlin_off = _track_quad_probe(tmp_path, body_nonlin_off, "quad_nonlin_off.sad", x_vals, px_vals, y_vals, py_vals)

    nonlinear_effect = r_nonlin_on["x"][0] - r_nonlin_off["x"][0]
    predicted_both   = r_linear["x"][0] + nonlinear_effect
    assert predicted_both == pytest.approx(r_both["x"][0], abs = 1e-8), (
        "The linear F1 fringe and the default nonlinear edge fringe "
        "should compose additively (to within noise) at this offset -- a "
        "meaningfully worse residual would mean the two fringes interact "
        "nonlinearly at scales this repo's converter needs to model.")

################################################################################
# Hard-edge fringe field (DISFRIN) -- see docs/sad-behaviour.md
################################################################################
def test_quad_disfrin_default_matches_explicit_zero(tmp_path):
    """
    DISFRIN unset defaults to DISFRIN=0 (hard-edge fringe enabled) --
    bit-identical output, not just approximately equal.
    """
    def run(disfrin, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"""QUAD Q1 = (L=0.5 K1=0.4{disfrin});\n"""
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START Q1 END);\n")
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            return track_sad(
                lattice_filepath    = lat.name,
                line_name           = "TEST",
                x_init              = np.array([2E-2]),
                px_init             = np.array([2E-2]),
                y_init              = np.array([0.0]),
                py_init             = np.array([0.0]),
                zeta_init           = np.array([0.0]),
                delta_init          = np.array([0.0]),
                n_turns             = 1,
                rfsw                = False,
                with_progress       = False)
        finally:
            os.chdir(cwd)

    r_unset = run("", "quad_disfrin_unset.sad")
    r_zero  = run(" DISFRIN=0", "quad_disfrin_zero.sad")
    assert r_unset["px"][0] == pytest.approx(r_zero["px"][0], abs=1e-15), (
        "DISFRIN unset should default to DISFRIN=0 (hard-edge fringe "
        "enabled), bit-identically.")

def test_quad_disfrin_is_boolean(tmp_path):
    """
    DISFRIN is a strict boolean gate on a QUAD, same as on BEND: any
    nonzero value disables the hard-edge fringe identically.
    """
    def run(disfrin, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"QUAD Q1 = (L=0.5 K1=0.4 DISFRIN={disfrin});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START Q1 END);\n")
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            return track_sad(
                lattice_filepath    = lat.name,
                line_name           = "TEST",
                x_init              = np.array([2E-2]),
                px_init             = np.array([2E-2]),
                y_init              = np.array([0.0]),
                py_init             = np.array([0.0]),
                zeta_init           = np.array([0.0]),
                delta_init          = np.array([0.0]),
                n_turns             = 1,
                rfsw                = False,
                with_progress       = False)
        finally:
            os.chdir(cwd)

    disfrin_1 = run(1, "quad_disfrin_bool_1.sad")["px"][0]
    for disfrin in (2, -1, 3, 0.5):
        r = run(disfrin, f"quad_disfrin_bool_{disfrin}.sad")
        assert r["px"][0] == pytest.approx(disfrin_1, abs=1e-15), (
            f"DISFRIN={disfrin} should disable the hard-edge fringe "
            "identically to DISFRIN=1 -- DISFRIN is boolean, not graded.")

def test_quad_disfrin_hard_edge_matches_sad_reference_values(tmp_path):
    """
    Pinned ground truth: L=0.5, K1=0.4, x=2E-2, px=2E-2 on entry, with the
    hard-edge fringe enabled (DISFRIN=0/unset) and disabled (DISFRIN=1).
    Real SAD binary outputs, recorded once and locked in.
    """
    def run(disfrin, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"""QUAD Q1 = (L=0.5 K1=0.4{disfrin});\n"""
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START Q1 END);\n")
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            return track_sad(
                lattice_filepath    = lat.name,
                line_name           = "TEST",
                x_init              = np.array([2E-2]),
                px_init             = np.array([2E-2]),
                y_init              = np.array([0.0]),
                py_init             = np.array([0.0]),
                zeta_init           = np.array([0.0]),
                delta_init          = np.array([0.0]),
                n_turns             = 1,
                rfsw                = False,
                with_progress       = False)
        finally:
            os.chdir(cwd)

    r_on  = run("", "quad_disfrin_ref_on.sad")
    r_off = run(" DISFRIN=1", "quad_disfrin_ref_off.sad")

    assert r_on["px"][0] == pytest.approx(0.010296769633772317, rel=1e-6), (
        "SAD's px with the hard-edge fringe enabled no longer matches the "
        "pinned reference value.")
    assert r_off["px"][0] == pytest.approx(0.010296838137678514, rel=1e-6), (
        "SAD's px with the hard-edge fringe disabled (DISFRIN=1) no "
        "longer matches the pinned reference value.")
