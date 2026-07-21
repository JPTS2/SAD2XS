"""
================================================================================
SAD syntax assumptions: reference particle defaults (CHARGE, MASS)
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-21

Notes
-----
Two families of tests:

Solenoid (static-field, 4D Twiss):
    An off-axis solenoid entrance/exit fringe pair is the observable. The
    entrance fringe (GEO=1, DX) shifts the reference frame; the exit fringe
    both undoes that shift AND applies the live BZ field, which is where the
    charge-dependent x->y Larmor coupling actually appears. The coupling is
    read at the SOL_OUT element's own row in the Twiss table (the exit fringe
    element itself — no extra marker needed) and is confirmed to vanish again
    by the END marker, since the pair is designed to restore the nominal
    orbit once the solenoid region is complete. Uses the same SOL_IN /
    SOL_START / SOL_DRIFT / SOL_END / SOL_OUT structure and _sol_orbit_values
    marker-lookup convention as tests/conversion/elements/test_sol.py.

    Earlier versions of this file used single-particle tracking for this
    section (see git history) based on the belief that Twiss "always
    computes for CHARGE=+1". That belief, and the resulting "CHARGE != 1 is
    silently zeroed" conclusions, were re-verified after fixing a lattice
    string comma bug (SAD's LALR parser silently drops parameters after a
    comma inside an element definition, with no nonzero exit code) and were
    found to be checking the wrong row (END, where the effect is designed to
    cancel) rather than the exit-fringe row (SOL_OUT) where it is observable.
    Read at the correct row, Twiss DOES distinguish CHARGE, and does so
    physically sensibly (CHARGE=-1 gives the exact sign-reversed orbit,
    CHARGE=0 gives a clean zero, not a degenerate computation).

RF + dispersion (longitudinal coupling, 4D and 6D Twiss + tracking):
    An RF cavity followed by a BEND converts the cavity energy kick ΔE = qV to
    transverse orbit via dispersion: x ≈ D·δ where δ = ΔE/(β·p₀c). At low
    momentum (0.1 GeV/c) a proton has β ≈ 0.106, giving ~9.4× larger δ than
    a positron (β ≈ 1) for the same energy kick. This makes the orbit at the
    exit a mass-sensitive observable — provided SAD propagates the cavity kick
    into the reference orbit (requires CALC6D or equivalent longitudinal mode).
    SAD's COD-based Twiss does not propagate the cavity kick into the
    reference orbit even in CALC6D (verified below), so the charge/mass
    energy-kick tests use single-particle tracking (track_sad), guarded by
    assert_particle_survived so a lost particle fails loudly rather than
    being silently checked against SAD's lost-particle sentinel coordinates.
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import os

import numpy as np
import pytest

from sad2xs.sad_helpers import track_sad, twiss_sad
from tests.sad.conftest import (
    assert_particle_survived,
    DEFAULT_MOMENTUM_GEV,
    ELECTRON_MASS_MEV,
    PROTON_MASS_MEV,
)

################################################################################
# Shared Constants
#
# ELECTRON_MASS_MEV / PROTON_MASS_MEV / DEFAULT_MOMENTUM_GEV live in
# tests/sad/conftest.py since they are generic physical/default values, not
# specific to this file. BZ / SOL_LENGTH / DX_OFFSET / RF_* below are kept
# local: they are this file's own solenoid/RF lattice design choices, not
# values any other tests/sad/*.py file would need to share.
################################################################################
MOMENTUM_GEV    = DEFAULT_MOMENTUM_GEV
BZ              = 3.0       # solenoid field [T] — strong enough for a clean signal
SOL_LENGTH      = 1.0       # drift length between fringe elements [m]
DX_OFFSET       = 0.001     # solenoid axis offset in x [m]

################################################################################
# Solenoid Lattice Helper
################################################################################
def _solenoid_lattice(momentum_gev, extra_globals=""):
    """
    Build a bound-solenoid lattice with internal markers bracketing the
    drift, matching tests/conversion/elements/test_sol.py's structure and
    naming exactly (SOL_IN / SOL_START / SOL_DRIFT / SOL_END / SOL_OUT).

    SOL_IN carries GEO=1 and the DX offset (shifts the reference frame);
    SOL_OUT is the plain exit fringe that both restores the frame and
    applies the live BZ field — the charge-dependent y coupling appears at
    the SOL_OUT row itself, not at SOL_START/SOL_END (which only bracket
    the field-free drift) and not at END (where the pair has fully closed).
    """
    return (
        f"MOMENTUM = {momentum_gev} GEV;\n"
        f"{extra_globals}"
        f"SOL SOL_IN  = (BZ={BZ} BOUND=1 GEO=1 DX={DX_OFFSET});\n"
        f"DRIFT SOL_DRIFT = (L={SOL_LENGTH});\n"
        f"SOL SOL_OUT = (BZ={BZ} BOUND=1);\n"
        "MARK START = ()\n"
        "     SOL_START = ()\n"
        "     SOL_END   = ()\n"
        "     END   = ();\n"
        "LINE TEST = (START SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);\n"
    )


def _sol_orbit_values(twiss_table, marker):
    """
    Return (y, py) at a named marker from a SAD Twiss table.
    """
    return twiss_table["y", marker], twiss_table["py", marker]


def _run_twiss(tmp_path, lattice_text, name="test.sad"):
    """
    Write `lattice_text` and run twiss_sad on it in 4D open-line mode.
    """
    lattice = tmp_path / name
    lattice.write_text(lattice_text)
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return twiss_sad(
            lattice_filepath    = lattice.name,
            line_name           = "TEST",
            calc6d              = False,
            closed              = False,
            additional_commands = "")
    finally:
        os.chdir(cwd)


################################################################################
# Default reference particle
#
# When CHARGE and MASS are not specified, SAD uses positron defaults
# (CHARGE=+1, MASS=electron mass). Confirmed by Oide (SAD developer, 2026-06-27):
# SAD has never properly supported CHARGE != 1; the convention is positron-only.
################################################################################

def test_sad_default_reference_particle_matches_explicit_positron(tmp_path):
    """
    SAD's default (no CHARGE or MASS) should be identical to an explicit
    positron (CHARGE=1, MASS=electron mass), read at the SOL_OUT exit-fringe
    row where the charge-dependent coupling is observable.
    """
    tw_default  = _run_twiss(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV),
        name="default.sad")

    tw_positron = _run_twiss(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV,
            extra_globals=f"CHARGE = 1;\nMASS = {ELECTRON_MASS_MEV} MEV;\n"),
        name="explicit_positron.sad")

    y_default, _  = _sol_orbit_values(tw_default, "SOL_OUT")
    y_positron, _ = _sol_orbit_values(tw_positron, "SOL_OUT")

    assert y_default == pytest.approx(y_positron, rel=1e-6), (
        "SAD default must match explicit CHARGE=1 / MASS=electron mass. "
        "Any difference would indicate the default is not positron.")


################################################################################
# Charge sign — CHARGE = -1 gives the exact sign-reversed orbit
################################################################################

def test_sad_default_charge_gives_nonzero_y_orbit(tmp_path):
    """
    The default (positron) reference particle should give a nonzero y at the
    SOL_OUT exit-fringe row. This is the baseline for the charge-sensitivity
    tests below.
    """
    tw = _run_twiss(tmp_path, _solenoid_lattice(MOMENTUM_GEV))
    y, _ = _sol_orbit_values(tw, "SOL_OUT")

    assert y != pytest.approx(0.0, abs=1e-9), (
        "Default (positron) Twiss at the SOL_OUT row must give a nonzero y — "
        "the solenoid x->y coupling requires a charged particle.")


def test_sad_charge_minus_one_gives_sign_reversed_y_orbit(tmp_path):
    """
    CHARGE = -1 gives the exact sign-reversed orbit of the positron case at
    the SOL_OUT row: y_electron == -y_positron. SAD does distinguish charge
    sign here — it is not treated as neutral.
    """
    tw_positron = _run_twiss(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV),
        name="positron.sad")

    tw_electron = _run_twiss(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV, extra_globals="CHARGE = -1;\n"),
        name="electron.sad")

    y_positron, _ = _sol_orbit_values(tw_positron, "SOL_OUT")
    y_electron, _ = _sol_orbit_values(tw_electron, "SOL_OUT")

    assert y_positron != pytest.approx(0.0, abs=1e-9), (
        "Positron should give nonzero y from the solenoid coupling.")
    assert y_electron == pytest.approx(-y_positron, rel=1e-6), (
        "CHARGE = -1 should give the exact sign-reversed orbit of the "
        "positron case, not zero.")


################################################################################
# Charge magnitude — integer charge values 0 and 2
################################################################################

def test_sad_charge_zero_gives_zero_coupling(tmp_path):
    """
    CHARGE = 0 gives a clean Twiss computation with zero orbit coupling at
    SOL_OUT (a neutral particle feels no Lorentz force) — this is a valid,
    physically sensible result, not a degenerate computation.
    """
    tw = _run_twiss(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV, extra_globals="CHARGE = 0;\n"))
    y, py = _sol_orbit_values(tw, "SOL_OUT")

    assert y == pytest.approx(0.0, abs=1e-9), (
        "CHARGE = 0 (neutral particle) should give zero y coupling at SOL_OUT.")
    assert py == pytest.approx(0.0, abs=1e-9), (
        "CHARGE = 0 (neutral particle) should give zero py coupling at SOL_OUT.")


def test_sad_charge_two_gives_different_y_orbit(tmp_path):
    """
    CHARGE = 2 gives a different (not simply doubled — the Larmor coupling
    is nonlinear in charge for a strong field) but clearly nonzero orbit at
    SOL_OUT, distinct from both the CHARGE = 1 and CHARGE = 0 cases.
    """
    tw_q1 = _run_twiss(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV),
        name="q1.sad")

    tw_q2 = _run_twiss(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV, extra_globals="CHARGE = 2;\n"),
        name="q2.sad")

    y_q1, _ = _sol_orbit_values(tw_q1, "SOL_OUT")
    y_q2, _ = _sol_orbit_values(tw_q2, "SOL_OUT")

    assert y_q1 != pytest.approx(0.0, abs=1e-9), (
        "CHARGE = 1 should give nonzero y from the solenoid coupling.")
    assert y_q2 != pytest.approx(0.0, abs=1e-9), (
        "CHARGE = 2 should give nonzero y from the solenoid coupling — "
        "not treated as neutral.")
    assert y_q2 != pytest.approx(y_q1, rel=1e-3), (
        "CHARGE = 2 should give a measurably different y from CHARGE = 1 "
        "(the coupling is nonlinear in charge, not a simple doubling).")


################################################################################
# Orbit restoration at END
################################################################################

def test_sad_solenoid_pair_restores_design_orbit_at_end(tmp_path):
    """
    Whatever the coupling at SOL_OUT, the bound solenoid pair is designed to
    restore the nominal (zero) orbit by the END marker. This is checked
    separately from the coupling tests above, mirroring
    test_sol_reference_transform_restores_design_orbit_at_end in
    tests/conversion/elements/test_sol.py: a failure here diagnoses exit
    restoration, not whether the coupling itself exists.
    """
    tw = _run_twiss(tmp_path, _solenoid_lattice(MOMENTUM_GEV))
    y_end, py_end = _sol_orbit_values(tw, "END")

    assert y_end == pytest.approx(0.0, abs=1e-9), (
        "The solenoid pair should restore y to zero by END.")
    assert py_end == pytest.approx(0.0, abs=1e-9), (
        "The solenoid pair should restore py to zero by END.")


################################################################################
# Mass
#
# For a static magnetic lattice at fixed MOMENTUM, the trajectory depends only
# on q/Bρ = q²c/p0c (charge and momentum, not mass). Mass enters only through
# the particle velocity β = p/(E) = p0c/sqrt(p0c² + (mc²)²), which affects
# longitudinal dynamics (time of flight, RF phase) but not static orbit shape.
################################################################################

def test_sad_proton_mass_accepted_by_sad(tmp_path):
    """
    SAD should accept MASS = proton mass. This confirms the MASS parameter
    takes MeV values and that non-electron masses are syntactically valid.
    """
    _run_twiss(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV,
            extra_globals=f"MASS = {PROTON_MASS_MEV} MEV;\n"))


def test_sad_proton_mass_orbit_matches_positron_orbit(tmp_path):
    """
    At fixed MOMENTUM, changing MASS does not change the static magnetic
    orbit at SOL_OUT: the solenoid coupling depends on q/Bρ = q²c/p₀c, not
    on particle mass. Mass sensitivity requires longitudinal dynamics
    (RF/6D) — see the RF tracking tests below.
    """
    tw_positron = _run_twiss(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV),
        name="positron.sad")

    tw_proton = _run_twiss(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV,
            extra_globals=f"MASS = {PROTON_MASS_MEV} MEV;\n"),
        name="proton_mass.sad")

    y_positron, _ = _sol_orbit_values(tw_positron, "SOL_OUT")
    y_proton, _   = _sol_orbit_values(tw_proton, "SOL_OUT")

    assert y_proton == pytest.approx(y_positron, rel=1e-6), (
        "At fixed MOMENTUM, MASS should not affect the static magnetic orbit. "
        "Solenoid coupling depends on q/Bρ = q²c/p0c, not on particle mass.")


################################################################################
# RF + dispersion mass and charge sensitivity
#
# Strategy: CAVI → BEND → DRIFT → END (open line, low momentum).
# The cavity gives energy kick ΔE = q·V·cos(φ). The downstream bend creates
# dispersion D, so the exit orbit is x ≈ D·δ where δ = ΔE/(β·p₀c).
#
# At p₀c = 0.1 GeV/c:
#   positron  β ≈ 1.000,  E₀ ≈   100 MeV   → δ = ΔE / 100 MeV
#   proton    β ≈ 0.106,  E₀ ≈   943 MeV   → δ = ΔE /  10.6 MeV  (~9.4× larger)
#
# The orbit at the exit is therefore a mass-sensitive observable when the
# cavity kick is propagated into the reference orbit. This requires CALC6D
# (or SAD's longitudinal tracking mode) — in pure CALC4D the cavity sits
# on the zero-momentum orbit and creates no orbit perturbation.
#
# CALC6D tests here use calc6d=True and closed=False (INS open-line mode).
################################################################################

RF_MOMENTUM_GEV = 0.1   # low momentum: proton is highly non-relativistic here
RF_VOLT_V       = 1e5   # 100 kV; small enough not to violate the thin-kick approximation


def _rf_lattice(momentum_gev, extra_globals="", volt=RF_VOLT_V):
    """
    Cavity + bend + drift open lattice for RF dispersion orbit tests.
    """
    return (
        f"MOMENTUM = {momentum_gev} GEV;\n"
        f"{extra_globals}"
        f"CAVI CAV1 = (L=1.0 VOLT={volt:.0f} FREQ=100000000 PHI=0.0);\n"
        "BEND B1 = (L=1.0 ANGLE=0.01);\n"
        "DRIFT D1 = (L=2.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START CAV1 B1 D1 END);\n"
    )


def _run_twiss_6d(tmp_path, lattice_text, name="test_rf.sad"):
    """
    Write `lattice_text` and run twiss_sad on it in 6D open-line mode.
    """
    lattice = tmp_path / name
    lattice.write_text(lattice_text)
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return twiss_sad(
            lattice_filepath    = lattice.name,
            line_name           = "TEST",
            calc6d              = True,
            closed              = False,
            additional_commands = "")
    finally:
        os.chdir(cwd)


def _run_twiss_4d(tmp_path, lattice_text, name="test_rf.sad"):
    """
    Write `lattice_text` and run twiss_sad on it in 4D open-line mode.
    """
    lattice = tmp_path / name
    lattice.write_text(lattice_text)
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return twiss_sad(
            lattice_filepath    = lattice.name,
            line_name           = "TEST",
            calc6d              = False,
            closed              = False,
            additional_commands = "")
    finally:
        os.chdir(cwd)


########################################
# 4D baseline: cavity does not perturb the reference orbit
########################################

def test_sad_cavi_does_not_perturb_orbit_in_calc4d(tmp_path):
    """
    In CALC4D, the cavity sits on the zero-momentum reference orbit and
    creates no transverse orbit perturbation. Dispersion (dx) after the bend
    should be non-zero (the bend is a bending magnet), but x should be zero
    because no off-momentum kick is applied to the reference orbit.
    """
    tw = _run_twiss_4d(tmp_path,
        _rf_lattice(RF_MOMENTUM_GEV),
        name="cavi_4d.sad")

    assert tw["x"][-1] == pytest.approx(0.0, abs=1e-9), (
        "In CALC4D, the cavity should not perturb the reference orbit — "
        "no off-momentum kick is applied.")
    assert tw["dx"][-1] != pytest.approx(0.0, abs=1e-9), (
        "The bend after the cavity should create nonzero dispersion dx.")


########################################
# 6D: mass sensitivity via beta-dependent fractional momentum deviation
########################################

def test_sad_calc6d_open_line_does_not_propagate_cavi_kick_into_orbit(tmp_path):
    """
    SAD's CALC6D in INS (open-line) mode computes the linearised optics around
    the reference orbit via COD. COD does not propagate the RF cavity energy
    gain into the transverse reference orbit — the cavity sits on the δ=0
    reference trajectory and the orbit x remains zero even in 6D mode.

    This is expected behaviour: observing RF energy gain requires single-particle
    tracking (TrackParticles / TRPT), not a COD-based Twiss.
    """
    tw_positron = _run_twiss_6d(tmp_path,
        _rf_lattice(RF_MOMENTUM_GEV),
        name="rf6d_x_positron.sad")

    tw_proton   = _run_twiss_6d(tmp_path,
        _rf_lattice(RF_MOMENTUM_GEV,
            extra_globals=f"MASS = {PROTON_MASS_MEV} MEV;\n"),
        name="rf6d_x_proton.sad")

    assert tw_positron["x"][-1] == pytest.approx(0.0, abs=1e-9), (
        "CALC6D open-line COD orbit x should remain zero — "
        "the cavity kick is not propagated into the reference orbit.")
    assert tw_proton["x"][-1] == pytest.approx(0.0, abs=1e-9), (
        "CALC6D open-line COD orbit x should remain zero for proton mass too — "
        "mass sensitivity via RF requires TrackParticles, not COD Twiss.")


################################################################################
# Single-particle tracking (TRPT equivalent) — energy after RF cavity
#
# track_sad wraps SAD's TrackParticles command, which tracks one or more
# particles through the lattice for n_turns passes and returns final
# (x, px, y, py, zeta, delta, state).
#
# For a single pass (n_turns=1) through an open line, delta at the exit is the
# fractional energy deviation acquired from the RF cavity. This is the correct
# observable for mass and charge sensitivity: different species → different
# velocity β → different transit-time phase shift → different cavity energy gain.
#
# Every result here is checked with assert_particle_survived before any delta
# assertion: a lost particle's returned delta is a SAD sentinel value, not a
# physical energy deviation (see conftest.assert_particle_survived).
#
# Phase choice: PHI is the cavity phase for the reference particle.
#   PHI = 0   → on-crest (maximum gain, least phase-sensitive)
#   PHI = π/2 → zero-crossing (cos = 0, no gain — avoid this)
#   PHI = π/4 → cos ≈ 0.71, healthy gain, sensitive to arrival phase shifts
#
# At p₀c = 0.1 GeV/c, mass matters:
#   positron  β ≈ 1.000, transit time T_e = L/c
#   proton    β ≈ 0.106, transit time T_p ≈ 9.4 · T_e
# The different transit times shift the effective cavity phase, changing the
# energy gain — observable as different delta at the end of the line.
################################################################################

RF_PHI_RAD = np.pi / 4   # 45 degrees — neither on-crest nor zero-crossing


def _rf_track_lattice(momentum_gev, extra_globals="",
                      volt=RF_VOLT_V, phi=RF_PHI_RAD):
    """
    Cavity-only open lattice for single-pass energy tracking tests.
    """
    return (
        f"MOMENTUM = {momentum_gev} GEV;\n"
        f"{extra_globals}"
        f"CAVI CAV1 = (L=1.0 VOLT={volt:.0f} FREQ=100000000 PHI={phi:.6f});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START CAV1 END);\n"
    )


def _run_track(tmp_path, lattice_text, name="test_track.sad"):
    """
    Single-pass tracking of the on-axis reference particle. Returns delta.
    """
    lattice = tmp_path / name
    lattice.write_text(lattice_text)
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return track_sad(
            lattice_filepath    = lattice.name,
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


def test_sad_cavi_gives_nonzero_delta_after_single_pass(tmp_path):
    """
    A single pass through a cavity at PHI = π/4 should give a nonzero energy
    deviation (delta ≠ 0) at the exit. This is the baseline for the mass and
    charge tracking tests below.
    """
    result = _run_track(tmp_path,
        _rf_track_lattice(RF_MOMENTUM_GEV),
        name="track_baseline.sad")
    assert_particle_survived(result)

    assert result["delta"][0] != pytest.approx(0.0, abs=1e-9), (
        "A cavity at PHI = π/4 should produce a nonzero energy deviation "
        "after a single pass. If delta = 0, the RF is not active in tracking.")


def test_sad_proton_mass_gives_different_delta_than_positron(tmp_path):
    """
    At p₀c = 0.1 GeV/c, a proton (β ≈ 0.106) spends ~9.4× longer inside the
    cavity than a positron (β ≈ 1). This shifts the effective RF phase and
    changes the energy gain. The exit delta should differ measurably between
    the two species.
    """
    result_positron = _run_track(tmp_path,
        _rf_track_lattice(RF_MOMENTUM_GEV),
        name="track_positron.sad")
    assert_particle_survived(result_positron)

    result_proton   = _run_track(tmp_path,
        _rf_track_lattice(RF_MOMENTUM_GEV,
            extra_globals=f"MASS = {PROTON_MASS_MEV} MEV;\n"),
        name="track_proton.sad")
    assert_particle_survived(result_proton)

    delta_positron  = result_positron["delta"][0]
    delta_proton    = result_proton["delta"][0]

    assert delta_positron != pytest.approx(delta_proton, rel=0.01), (
        "Positron and proton at 0.1 GeV/c have very different transit times "
        "through the cavity (β ≈ 1 vs β ≈ 0.106), so their energy gains and "
        "exit deltas should differ by more than 1 %.")


########################################
# CHARGE dependence of the CAVI energy kick
#
# Mirrors the solenoid CHARGE tests above: CHARGE = -1 gives the exact
# sign-reversed kick (not zero), CHARGE = 2 gives a different, nonlinearly
# scaled but still nonzero kick, and CHARGE = 0 gives exactly zero (a
# neutral particle is not accelerated by an electric field). Confirmed by
# direct measurement (see git history of this file for the diagnostic run):
#   CHARGE = +1: delta = -7.071159e-4
#   CHARGE = -1: delta = +7.071159e-4  (exact sign flip)
#   CHARGE = +2: delta = -2.000026e-3  (not -1.414e-3 = 2x; nonlinear)
#   CHARGE =  0: delta =  0.0          (exact)
########################################

def test_sad_cavi_charge_minus_one_gives_sign_reversed_delta(tmp_path):
    """
    CHARGE = -1 gives the exact sign-reversed energy kick of the positron
    case. SAD does distinguish charge sign here — it is not silently zeroed.
    """
    result_positron = _run_track(tmp_path,
        _rf_track_lattice(RF_MOMENTUM_GEV),
        name="track_q_pos.sad")
    assert_particle_survived(result_positron)

    result_electron = _run_track(tmp_path,
        _rf_track_lattice(RF_MOMENTUM_GEV, extra_globals="CHARGE = -1;\n"),
        name="track_q_neg.sad")
    assert_particle_survived(result_electron)

    delta_positron = result_positron["delta"][0]
    delta_electron = result_electron["delta"][0]

    assert abs(delta_positron) > 1e-4, (
        "Positron should receive the expected cos(PHI)*VOLT/p0c ~= 7.07e-4 "
        "energy kick from the cavity.")
    assert delta_electron == pytest.approx(-delta_positron, rel=1e-6), (
        "CHARGE = -1 should give the exact sign-reversed energy kick of the "
        "positron case, not zero.")


def test_sad_cavi_charge_two_gives_different_delta(tmp_path):
    """
    CHARGE = 2 gives a different (nonlinearly scaled, not simply doubled)
    but clearly nonzero energy kick, distinct from both CHARGE = 1 and
    CHARGE = 0.
    """
    result_q1 = _run_track(tmp_path,
        _rf_track_lattice(RF_MOMENTUM_GEV),
        name="track_q1.sad")
    assert_particle_survived(result_q1)

    result_q2 = _run_track(tmp_path,
        _rf_track_lattice(RF_MOMENTUM_GEV, extra_globals="CHARGE = 2;\n"),
        name="track_q2.sad")
    assert_particle_survived(result_q2)

    delta_q1 = result_q1["delta"][0]
    delta_q2 = result_q2["delta"][0]

    assert delta_q2 != pytest.approx(0.0, abs=1e-9), (
        "CHARGE = 2 should give a nonzero energy kick — not treated as neutral.")
    assert delta_q2 != pytest.approx(delta_q1, rel=1e-3), (
        "CHARGE = 2 should give a measurably different delta from CHARGE = 1 "
        "(the kick is nonlinear in charge, not a simple doubling).")


def test_sad_cavi_charge_zero_gives_zero_delta(tmp_path):
    """
    CHARGE = 0 gives exactly zero energy kick: a neutral particle is not
    accelerated by the cavity's electric field.
    """
    result = _run_track(tmp_path,
        _rf_track_lattice(RF_MOMENTUM_GEV, extra_globals="CHARGE = 0;\n"),
        name="track_q0.sad")
    assert_particle_survived(result)

    assert result["delta"][0] == pytest.approx(0.0, abs=1e-9), (
        "CHARGE = 0 (neutral particle) should give exactly zero energy kick.")
