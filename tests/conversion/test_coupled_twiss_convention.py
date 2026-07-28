"""
================================================================================
Tests locking in the coupled-twiss comparison convention against SAD
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-28
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import os

import numpy as np
import pytest
import sad2xs as s2x
import xtrack as xt

from sad2xs.sad_helpers import transfer_matrix_sad, twiss_sad
from tests.support.coupled_optics import (
    couplings_sad_4d,
    edwards_teng_optics,
    edwards_teng_optics_at,
    linear_transfer_matrix_4d,
    normalized_r_matrix)

# Agreement and disagreement are both asserted so the convention map cannot
# silently drift. See docs/helpers/sad-helpers.md for the derivation and table.
# Observed agreements are <= 9e-10 (SAD TFS output carries ~10 digits);
# observed disagreements are >= 9e-6. The tolerances sit well clear of both.
ET_VS_SAD_ATOL          = 5.0E-9
TM_SAD_VS_FD_ATOL       = 1.0E-9
R_MATRIX_VS_SAD_ATOL    = 1.0E-8
MISMATCH_FLOOR          = 1.0E-6
SOL_ET_VS_MR_SUM_ATOL   = 1.0E-12

SKEW_QUAD_LATTICE = """\
MOMENTUM    = 1.0 GEV;

MULT        TEST_MULT   = (
    L       = 0.5
    SK1     = -0.03
);

MARK        START       = ()
            END         = ();

LINE        TEST_LINE   = (START TEST_MULT END);
"""

SOLENOID_LATTICE = """\
MOMENTUM    = 1.0 GEV;

DRIFT       SOL_DRIFT   = (L = 1.0);
SOL         SOL_IN      = (BZ = 1.5 BOUND = 1 GEO = 1 DISFRIN = 1)
            SOL_OUT     = (BZ = 1.5 BOUND = 1 DISFRIN = 1);

MARK        START       = ()
            END         = ();

LINE        TEST_LINE   = (START SOL_IN SOL_DRIFT SOL_OUT END);
"""

UNCOUPLED_LATTICE = """\
MOMENTUM    = 1.0 GEV;

MULT        TEST_MULT   = (
    L       = 0.5
    K1      = 0.1
);

MARK        START       = ()
            END         = ();

LINE        TEST_LINE   = (START TEST_MULT END);
"""

################################################################################
# Helpers
################################################################################
def _sad_twiss(lattice_path):
    """
    Run a 4D open-line SAD twiss of TEST_LINE in the current directory.
    """
    return twiss_sad(
        lattice_filepath            = lattice_path.name,
        line_name                   = "TEST_LINE",
        calc6d                      = False,
        closed                      = False,
        reverse_element_order       = False,
        reverse_survey_horizontal   = False,
        rfsw                        = True,
        additional_commands         = "")

def _converted_line(lattice_path):
    """
    Convert the lattice and return the Xsuite line.
    """
    return s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        _verbose            = False,
        _test_mode          = True)

def _xsuite_twiss(line):
    """
    Open-line 4D twiss with the same initial optics SAD uses (betx=bety=1).
    """
    return line.twiss4d(
        _continue_if_lost   = True,
        start               = xt.START,
        end                 = xt.END,
        betx                = 1.0,
        bety                = 1.0)

def _twiss_candidates_at_end(tw_sad, tw_xs):
    """
    Return per-quantity dicts {sad, plain, mr_sum, et} at the END marker.
    """
    et_values   = edwards_teng_optics_at(tw_xs, "end")
    candidates  = {}
    for key in ["betx", "alfx", "bety", "alfy"]:
        candidates[key] = {
            "sad":      tw_sad[key, "END"],
            "plain":    tw_xs[key, "end"],
            "mr_sum":   tw_xs[f"{key}1", "end"] + tw_xs[f"{key}2", "end"],
            "et":       et_values[key],
        }
    return candidates, et_values

def _assert_transfer_matrix_matches_sad(write_lattice, tmp_path,
                                        lattice_text, filename):
    """
    Assert the SAD 4x4 transfer matrix equals the converted line's
    finite-difference transfer matrix — the parametrisation-free anchor.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        lattice_path    = write_lattice(lattice_text, filename = filename)
        tm_sad          = transfer_matrix_sad(
            lattice_filepath    = lattice_path.name,
            line_name           = "TEST_LINE")
        line            = _converted_line(lattice_path)
        tm_xsuite       = linear_transfer_matrix_4d(line)
    finally:
        os.chdir(cwd)

    assert np.allclose(
        tm_sad[:4, :4], tm_xsuite, rtol = 0.0, atol = TM_SAD_VS_FD_ATOL), (
        "SAD and converted-line 4x4 transfer matrices should agree "
        "independent of any twiss parametrisation. Max difference: "
        f"{np.max(np.abs(tm_sad[:4, :4] - tm_xsuite)):.3e}")

def _assert_r_matrix_matches_sad(tw_sad, et_values):
    """
    Assert SAD's R1-R4 equal the normalised Edwards-Teng decoupling matrix.
    """
    r_normalized = normalized_r_matrix(
        et_values["r11"], et_values["r12"],
        et_values["r21"], et_values["r22"])
    sad_r = np.array([
        [tw_sad["R1", "END"], tw_sad["R2", "END"]],
        [tw_sad["R3", "END"], tw_sad["R4", "END"]]])

    assert np.allclose(
        sad_r, r_normalized, rtol = 0.0, atol = R_MATRIX_VS_SAD_ATOL), (
        "SAD's R1-R4 should equal the Edwards-Teng decoupling matrix "
        "normalised as R / sqrt(1 + det R). Max difference: "
        f"{np.max(np.abs(sad_r - r_normalized)):.3e}")

################################################################################
# Helper self-validation (no SAD required)
################################################################################
def _tune_split_coupled_ring():
    """
    Build a small stable FODO ring with one skew quad and split tunes.

    The tunes must be well separated: on the qx = qy difference resonance
    the one-turn Edwards-Teng decomposition degenerates and xtrack's native
    columns are not finite.
    """
    env = xt.Environment()
    env.particle_ref = xt.Particles("electron", p0c = 1.0E9)
    env.new("qf", xt.Quadrupole, k1 = 0.52, length = 0.3)
    env.new("qd", xt.Quadrupole, k1 = -0.5, length = 0.3)
    env.new("dd", xt.Drift, length = 1.0)
    env.new("sq", xt.Quadrupole, k1s = 0.05, length = 0.2)

    components = []
    for _ in range(4):
        components += [
            env.place("qf"), env.place("dd"),
            env.place("qd"), env.place("dd")]
    components.insert(2, env.place("sq"))
    return env.new_line(components = components)

def test_edwards_teng_propagation_matches_native_periodic_ring():
    """
    Seeded with xtrack's native Edwards-Teng values at the first element of
    a coupled periodic ring, the open-line propagation must reproduce the
    native Edwards-Teng columns at every element.
    """
    ring    = _tune_split_coupled_ring()
    tw_ring = ring.twiss4d(coupling_edw_teng = True)

    rr_et0 = np.array([
        [tw_ring.r11_edw_teng[0], tw_ring.r12_edw_teng[0]],
        [tw_ring.r21_edw_teng[0], tw_ring.r22_edw_teng[0]]])
    propagated = edwards_teng_optics(
        tw_ring,
        rr_et0  = rr_et0,
        betx0   = tw_ring.betx_edw_teng[0],
        alfx0   = tw_ring.alfx_edw_teng[0],
        bety0   = tw_ring.bety_edw_teng[0],
        alfy0   = tw_ring.alfy_edw_teng[0])

    for key, native_column in [
            ("betx", tw_ring.betx_edw_teng),
            ("alfx", tw_ring.alfx_edw_teng),
            ("bety", tw_ring.bety_edw_teng),
            ("alfy", tw_ring.alfy_edw_teng),
            ("r11", tw_ring.r11_edw_teng),
            ("r12", tw_ring.r12_edw_teng),
            ("r21", tw_ring.r21_edw_teng),
            ("r22", tw_ring.r22_edw_teng)]:
        assert np.allclose(
            propagated[key], native_column, rtol = 0.0, atol = 1.0E-10), (
            f"Propagated Edwards-Teng {key} should reproduce xtrack's "
            "native periodic Edwards-Teng column at every element. Max "
            f"difference: {np.max(np.abs(propagated[key] - native_column)):.3e}")

def test_couplings_sad_4d_matches_native_edwards_teng_r_matrix():
    """
    Two independent routes to SAD's R1-R4 must agree on a coupled ring.

    `couplings_sad_4d` decouples the one-turn matrix directly
    (M = U^-1 D U). xtrack's native Edwards-Teng columns, normalised by
    `normalized_r_matrix`, reach the same quantity by propagating optics.
    Agreement is evidence for both, since neither shares an implementation
    with the other.
    """
    ring    = _tune_split_coupled_ring()
    tw_ring = ring.twiss4d(coupling_edw_teng = True)

    tw_sad  = couplings_sad_4d(ring.twiss4d())

    for index in range(len(tw_ring.name)):
        expected = normalized_r_matrix(
            tw_ring.r11_edw_teng[index], tw_ring.r12_edw_teng[index],
            tw_ring.r21_edw_teng[index], tw_ring.r22_edw_teng[index])
        actual = np.array([
            [tw_sad.R1[index], tw_sad.R2[index]],
            [tw_sad.R3[index], tw_sad.R4[index]]])

        assert np.allclose(
            np.abs(actual), np.abs(expected),
            rtol = 0.0, atol = R_MATRIX_VS_SAD_ATOL), (
            "One-turn-matrix decoupling and normalised Edwards-Teng "
            f"propagation should give the same R1-R4 at element "
            f"{tw_ring.name[index]}. Got {actual.tolist()} against "
            f"{expected.tolist()}.")


def test_edwards_teng_propagation_reduces_to_plain_twiss_when_uncoupled():
    """
    On an uncoupled transfer line the Edwards-Teng optics must equal the
    plain twiss optics and the decoupling matrix must stay exactly zero.
    """
    env = xt.Environment()
    env.particle_ref = xt.Particles("electron", p0c = 1.0E9)
    env.new("qf", xt.Quadrupole, k1 = 0.52, length = 0.3)
    env.new("qd", xt.Quadrupole, k1 = -0.5, length = 0.3)
    env.new("dd", xt.Drift, length = 1.0)
    line = env.new_line(components = [
        env.place("qf"), env.place("dd"), env.place("qd"), env.place("dd")])

    tw = line.twiss4d(
        start = xt.START, end = xt.END,
        betx = 2.0, alfx = 0.1, bety = 3.0, alfy = -0.2)
    propagated = edwards_teng_optics(tw)

    for key in ["betx", "alfx", "bety", "alfy"]:
        assert np.allclose(
            propagated[key], getattr(tw, key), rtol = 0.0, atol = 1.0E-12), (
            f"Edwards-Teng {key} should equal plain twiss {key} on an "
            "uncoupled line.")
    for key in ["r11", "r12", "r21", "r22"]:
        assert np.all(propagated[key] == 0.0), (
            "The Edwards-Teng decoupling matrix should stay exactly zero "
            "along an uncoupled line.")

################################################################################
# Skew-quad coupling: only Edwards-Teng matches SAD
################################################################################
def test_skew_quad_transfer_matrix_matches_sad(write_lattice, tmp_path):
    """
    The converted skew-quad line's linear map equals SAD's — any twiss
    disagreement below is therefore purely a parametrisation convention.
    """
    _assert_transfer_matrix_matches_sad(
        write_lattice, tmp_path,
        SKEW_QUAD_LATTICE, "coupled_convention_skew_tm.sad")

def test_skew_quad_twiss_convention_grid(write_lattice, tmp_path):
    """
    For skew-quad coupling, only Edwards-Teng beta/alpha matches SAD.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        lattice_path = write_lattice(
            SKEW_QUAD_LATTICE, filename = "coupled_convention_skew.sad")
        tw_sad  = _sad_twiss(lattice_path)
        line    = _converted_line(lattice_path)
        tw_xs   = _xsuite_twiss(line)
    finally:
        os.chdir(cwd)

    candidates, et_values = _twiss_candidates_at_end(tw_sad, tw_xs)

    for key, values in candidates.items():
        assert values["et"] == pytest.approx(
            values["sad"], abs = ET_VS_SAD_ATOL), (
            f"Edwards-Teng {key} should match SAD in a skew-quad coupled "
            "region.")
        assert abs(values["plain"] - values["sad"]) > MISMATCH_FLOOR, (
            f"Plain mode {key} should measurably disagree with SAD in a "
            "skew-quad coupled region — if this now matches, the convention "
            "map has changed and needs re-deriving, not a tolerance edit.")
        assert abs(values["mr_sum"] - values["sad"]) > MISMATCH_FLOOR, (
            f"Mais-Ripken projected-sum {key} should measurably disagree "
            "with SAD in a skew-quad coupled region — if this now matches, "
            "the convention map has changed and needs re-deriving, not a "
            "tolerance edit.")

    _assert_r_matrix_matches_sad(tw_sad, et_values)

################################################################################
# Solenoid coupling: Edwards-Teng matches SAD and coincides with the
# Mais-Ripken projected sums (the rotational-coupling special case)
################################################################################
def test_solenoid_transfer_matrix_matches_sad(write_lattice, tmp_path):
    """
    The converted bound-solenoid line's linear map equals SAD's — any twiss
    disagreement below is therefore purely a parametrisation convention.
    """
    _assert_transfer_matrix_matches_sad(
        write_lattice, tmp_path,
        SOLENOID_LATTICE, "coupled_convention_sol_tm.sad")

def test_solenoid_twiss_convention_grid(write_lattice, tmp_path):
    """
    For solenoid coupling, Edwards-Teng matches SAD and projected sums
    happen to coincide with Edwards-Teng.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        lattice_path = write_lattice(
            SOLENOID_LATTICE, filename = "coupled_convention_sol.sad")
        tw_sad  = _sad_twiss(lattice_path)
        line    = _converted_line(lattice_path)
        tw_xs   = _xsuite_twiss(line)
    finally:
        os.chdir(cwd)

    candidates, et_values = _twiss_candidates_at_end(tw_sad, tw_xs)

    for key, values in candidates.items():
        assert values["et"] == pytest.approx(
            values["sad"], abs = ET_VS_SAD_ATOL), (
            f"Edwards-Teng {key} should match SAD in a solenoid coupled "
            "region.")
        assert values["mr_sum"] == pytest.approx(
            values["et"], abs = SOL_ET_VS_MR_SUM_ATOL), (
            f"Mais-Ripken projected-sum {key} should numerically coincide "
            "with Edwards-Teng for rotational (solenoid) coupling — this "
            "coincidence is why the projected-sum comparison was exact for "
            "solenoids.")
        assert abs(values["plain"] - values["sad"]) > MISMATCH_FLOOR, (
            f"Plain mode {key} should measurably disagree with SAD in a "
            "solenoid coupled region — if this now matches, the convention "
            "map has changed and needs re-deriving, not a tolerance edit.")

    _assert_r_matrix_matches_sad(tw_sad, et_values)

################################################################################
# No coupling: every candidate coincides and matches SAD
################################################################################
def test_uncoupled_transfer_matrix_matches_sad(write_lattice, tmp_path):
    """
    The converted uncoupled line's linear map equals SAD's.
    """
    _assert_transfer_matrix_matches_sad(
        write_lattice, tmp_path,
        UNCOUPLED_LATTICE, "coupled_convention_uncoupled_tm.sad")

def test_uncoupled_twiss_convention_grid(write_lattice, tmp_path):
    """
    With no coupling, plain, projected-sum, and Edwards-Teng values coincide.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        lattice_path = write_lattice(
            UNCOUPLED_LATTICE, filename = "coupled_convention_uncoupled.sad")
        tw_sad  = _sad_twiss(lattice_path)
        line    = _converted_line(lattice_path)
        tw_xs   = _xsuite_twiss(line)
    finally:
        os.chdir(cwd)

    candidates, et_values = _twiss_candidates_at_end(tw_sad, tw_xs)

    for key, values in candidates.items():
        for candidate in ["plain", "mr_sum", "et"]:
            assert values[candidate] == pytest.approx(
                values["sad"], abs = ET_VS_SAD_ATOL), (
                f"With no coupling, {candidate} {key} should match SAD — "
                "all conventions coincide on an uncoupled line.")

    for key in ["r11", "r12", "r21", "r22"]:
        assert et_values[key] == pytest.approx(0.0, abs = 1.0E-12), (
            "The propagated decoupling matrix should be zero on an "
            "uncoupled line.")
    for key in ["R1", "R2", "R3", "R4"]:
        assert tw_sad[key, "END"] == pytest.approx(0.0, abs = 1.0E-12), (
            "SAD should report zero R1-R4 on an uncoupled line.")
