"""
================================================================================
SAD syntax assumptions: reference particle defaults (CHARGE, MASS)
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-27

Notes
-----
Two families of tests:

Solenoid (static-field, 4D Twiss):
    An off-axis solenoid is the observable. The x→y coupling from the SOL
    fringe field is proportional to charge, so the y orbit at the exit is a
    clean discriminator for charge sign and magnitude. Mass has no effect in
    a static-field lattice at fixed MOMENTUM (confirmed empirically).

RF + dispersion (longitudinal coupling, 4D and 6D Twiss):
    An RF cavity followed by a BEND converts the cavity energy kick ΔE = qV to
    transverse orbit via dispersion: x ≈ D·δ where δ = ΔE/(β·p₀c). At low
    momentum (0.1 GeV/c) a proton has β ≈ 0.106, giving ~9.4× larger δ than
    a positron (β ≈ 1) for the same energy kick. This makes the orbit at the
    exit a mass-sensitive observable — provided SAD propagates the cavity kick
    into the reference orbit (requires CALC6D or equivalent longitudinal mode).
================================================================================
"""
import os

import numpy as np
import pytest

from sad2xs.sad_helpers import track_sad, twiss_sad

################################################################################
# Baseline lattice
#
# An off-axis solenoid is charge- and mass-sensitive because BZ creates a
# transverse force proportional to q*v x B. The x→y orbit coupling induced by
# an x-offset on the entrance SOL fringe element is directly sensitive to the
# sign and magnitude of CHARGE, making it a clean empirical probe.
#
# Lattice: MOMENTUM + optional CHARGE/MASS + entrance SOL fringe with DX +
# physical DRIFT + exit SOL fringe + MARK START/END + open LINE.
#
# All tests use closed=False (open, insertion mode) and calc6d=False (4D Twiss).
# The observable is tw["y"][-1] — the y orbit at the END marker — which is
# zero for the on-axis reference orbit and acquires a nonzero value purely from
# the x→y coupling driven by the off-axis solenoid.
################################################################################

MOMENTUM_GEV    = 1.0
BZ              = 3.0       # solenoid field [T] — strong enough for clean tracking signal
SOL_LENGTH      = 1.0       # drift length between fringe elements [m]
DX_OFFSET       = 0.001     # solenoid axis offset in x [m]

ELECTRON_MASS_MEV   = 0.51099895    # positron/electron mass
PROTON_MASS_MEV     = 938.27208816  # proton mass


def _solenoid_lattice(momentum_gev, extra_globals=""):
    """Build a standard off-axis solenoid lattice string.

    SL1 and SL2 both carry BZ so the fringe pair is properly formed.
    GEO=1 on SL1 shifts the reference orbit by DX; the pair closes it at END.
    """
    return (
        f"MOMENTUM = {momentum_gev} GEV;\n"
        f"{extra_globals}"
        f"SOL SL1 = (BZ={BZ}, BOUND=1, GEO=1, DX={DX_OFFSET});\n"
        f"DRIFT D0 = (L={SOL_LENGTH});\n"
        f"SOL SL2 = (BZ={BZ}, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);\n"
    )


def _run_twiss(tmp_path, lattice_text, name="test.sad"):
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


def _run_track_solenoid(tmp_path, lattice_text, name="test_sol_track.sad"):
    """Single-pass tracking through the solenoid lattice. Returns y at exit."""
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


################################################################################
# Default reference particle
#
# When CHARGE and MASS are not specified, SAD uses positron defaults
# (CHARGE=+1, MASS=electron mass). Confirmed by Oide (SAD developer, 2026-06-27):
# SAD has never properly supported CHARGE != 1; the convention is positron-only.
#
# We use single-particle tracking (track_sad / TrackParticles) rather than
# Twiss for the charge-sensitivity tests because:
#   - SAD's linear-optics matrix always computes for CHARGE=+1 regardless of
#     the CHARGE global, so Twiss cannot distinguish charge values.
#   - TrackParticles treats CHARGE != 1 as neutral (zero EM coupling), giving
#     a clean observable difference (y = 0 instead of y != 0).
################################################################################

def test_sad_default_reference_particle_matches_explicit_positron(tmp_path):
    """
    SAD's default (no CHARGE or MASS) should be identical to an explicit
    positron (CHARGE=1, MASS=electron mass). Confirmed via single-pass tracking
    through an off-axis solenoid: y at exit should match to machine precision.
    """
    result_default  = _run_track_solenoid(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV),
        name="default.sad")

    result_positron = _run_track_solenoid(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV,
            extra_globals=f"CHARGE = 1;\nMASS = {ELECTRON_MASS_MEV} MEV;\n"),
        name="explicit_positron.sad")

    assert result_default["y"][0] == pytest.approx(result_positron["y"][0], rel=1e-6), (
        "SAD default must match explicit CHARGE=1 / MASS=electron mass. "
        "Any difference would indicate the default is not positron.")


################################################################################
# Charge sign — tracking reveals neutral behaviour for CHARGE != 1
#
# SAD's TrackParticles treats CHARGE != 1 as neutral (zero EM coupling).
# The off-axis solenoid x->y coupling vanishes, giving y = 0 at the exit
# instead of the sign-reversed orbit a real electron ring would produce.
# Confirmed by Oide: SAD supports only CHARGE = +1.
################################################################################

def test_sad_default_charge_gives_nonzero_y_orbit(tmp_path):
    """
    Single-pass tracking through an off-axis solenoid should give a nonzero
    y displacement for the default (positron) reference particle. This is the
    baseline for the charge-sensitivity tests.
    """
    result = _run_track_solenoid(tmp_path, _solenoid_lattice(MOMENTUM_GEV))
    assert result["y"][0] != pytest.approx(0.0, abs=1e-9), (
        "Default (positron) tracking through an off-axis solenoid must give "
        "a nonzero y — the solenoid x->y coupling requires a charged particle.")


def test_sad_charge_minus_one_is_silently_zeroed_in_solenoid(tmp_path):
    """
    SAD treats CHARGE = -1 as neutral in TrackParticles: the off-axis solenoid
    produces y = 0 (no coupling) instead of the expected sign-reversed orbit.
    The positron (default) gives y != 0; CHARGE = -1 gives y = 0.

    Confirmed by Oide (2026-06-27): SAD has never supported non-positron CHARGE.
    Use reverse_charge=True in the SAD2XS converter to simulate electron rings.
    """
    result_positron = _run_track_solenoid(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV),
        name="positron.sad")

    result_electron = _run_track_solenoid(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV, extra_globals="CHARGE = -1;\n"),
        name="electron.sad")

    assert result_positron["y"][0] != pytest.approx(0.0, abs=1e-9), (
        "Positron should give nonzero y from off-axis solenoid coupling.")
    assert result_electron["y"][0] == pytest.approx(0.0, abs=1e-9), (
        "CHARGE = -1 is treated as neutral by SAD — y = 0, not −y_positron.")


################################################################################
# Charge magnitude — integer charge values 0 and 2
################################################################################

def test_sad_charge_zero_causes_degenerate_computation(tmp_path):
    """
    CHARGE = 0 causes SAD's FFS to produce a physically degenerate computation:
    the output file contains Mathematica undefined symbols (e.g. `medium`,
    `$DefaultFontWeight`), which our helper detects and raises as a ValueError.

    SAD does not gracefully support neutral particles — CHARGE = 0 produces
    a degenerate Twiss, not a clean zero-force orbit.
    """
    with pytest.raises(ValueError, match="physically degenerate"):
        _run_twiss(tmp_path,
            _solenoid_lattice(MOMENTUM_GEV, extra_globals="CHARGE = 0;\n"))


def test_sad_charge_two_is_silently_zeroed_in_solenoid(tmp_path):
    """
    SAD treats CHARGE = 2 as neutral in TrackParticles, identically to
    CHARGE = -1. The solenoid y orbit is zero, not doubled as q·BZ would give.

    Together with the CHARGE = -1 test and the cavity tracking test, this
    confirms SAD accepts only CHARGE = +1. Any other value removes EM coupling.
    """
    result_q1 = _run_track_solenoid(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV),
        name="q1.sad")

    result_q2 = _run_track_solenoid(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV, extra_globals="CHARGE = 2;\n"),
        name="q2.sad")

    assert result_q1["y"][0] != pytest.approx(0.0, abs=1e-9), (
        "Default CHARGE = 1 should give nonzero y from off-axis solenoid.")
    assert result_q2["y"][0] == pytest.approx(0.0, abs=1e-9), (
        "CHARGE = 2 is treated as neutral by SAD — y = 0, not 2·y_positron.")


################################################################################
# Mass
#
# For a static magnetic lattice at fixed MOMENTUM, the trajectory depends only
# on q/Bρ = q²c/p0c (charge and momentum, not mass). Mass enters only through
# the particle velocity β = p/(E) = p0c/sqrt(p0c² + (mc²)²), which affects
# longitudinal dynamics (time of flight, RF phase) but not static orbit shape.
#
# We verify empirically whether SAD distinguishes masses in the solenoid orbit.
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
    At fixed MOMENTUM, changing MASS does not change the static magnetic orbit:
    the solenoid coupling depends on q/Bρ = q²c/p₀c, not on particle mass.
    Confirmed via single-pass tracking through the off-axis solenoid.
    Mass sensitivity requires longitudinal dynamics (RF/6D) — see tracking tests.
    """
    result_positron = _run_track_solenoid(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV),
        name="positron.sad")

    result_proton = _run_track_solenoid(tmp_path,
        _solenoid_lattice(MOMENTUM_GEV,
            extra_globals=f"MASS = {PROTON_MASS_MEV} MEV;\n"),
        name="proton_mass.sad")

    assert result_proton["y"][0] == pytest.approx(result_positron["y"][0], rel=1e-6), (
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
    """Cavity + bend + drift open lattice for RF dispersion orbit tests."""
    return (
        f"MOMENTUM = {momentum_gev} GEV;\n"
        f"{extra_globals}"
        f"CAVI CAV1 = (L=1.0, VOLT={volt:.0f}, FREQ=100000000, PHI=0.0);\n"
        "BEND B1 = (L=1.0, ANGLE=0.01);\n"
        "DRIFT D1 = (L=2.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START CAV1 B1 D1 END);\n"
    )


def _run_twiss_6d(tmp_path, lattice_text, name="test_rf.sad"):
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


# ── 4D baseline: cavity does not perturb the reference orbit ──────────────────

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


# ── 6D: mass sensitivity via β-dependent fractional momentum deviation ────────

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

RF_PHI_RAD = np.pi / 4   # 45° — neither on-crest nor zero-crossing


def _rf_track_lattice(momentum_gev, extra_globals="",
                      volt=RF_VOLT_V, phi=RF_PHI_RAD):
    """Cavity-only open lattice for single-pass energy tracking tests."""
    return (
        f"MOMENTUM = {momentum_gev} GEV;\n"
        f"{extra_globals}"
        f"CAVI CAV1 = (L=1.0, VOLT={volt:.0f}, FREQ=100000000, PHI={phi:.6f});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START CAV1 END);\n"
    )


def _run_track(tmp_path, lattice_text, name="test_track.sad"):
    """Single-pass tracking of the on-axis reference particle. Returns delta."""
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

    result_proton   = _run_track(tmp_path,
        _rf_track_lattice(RF_MOMENTUM_GEV,
            extra_globals=f"MASS = {PROTON_MASS_MEV} MEV;\n"),
        name="track_proton.sad")

    delta_positron  = result_positron["delta"][0]
    delta_proton    = result_proton["delta"][0]

    assert delta_positron != pytest.approx(delta_proton, rel=0.01), (
        "Positron and proton at 0.1 GeV/c have very different transit times "
        "through the cavity (β ≈ 1 vs β ≈ 0.106), so their energy gains and "
        "exit deltas should differ by more than 1 %.")


def test_sad_charge_minus_one_is_silently_zeroed_in_cavi(tmp_path):
    """
    SAD silently treats CHARGE = -1 as neutral (no EM coupling) in TrackParticles.
    The cavity gives the positron delta ≈ +0.707·V/p₀c (cos π/4 energy gain),
    but with CHARGE = -1 the exit delta is ≈ 0 — consistent with neutral
    particle behaviour, not the expected −delta_positron sign flip.

    This matches the solenoid finding (CHARGE = -1 → y = 0 instead of −y_default).
    SAD appears to support only CHARGE = +1 (positron). Non-unity CHARGE is
    silently dropped to zero coupling across both magnetic and RF elements.
    """
    result_positron = _run_track(tmp_path,
        _rf_track_lattice(RF_MOMENTUM_GEV),
        name="track_q_pos.sad")

    result_electron = _run_track(tmp_path,
        _rf_track_lattice(RF_MOMENTUM_GEV, extra_globals="CHARGE = -1;\n"),
        name="track_q_neg.sad")

    delta_positron  = result_positron["delta"][0]
    delta_electron  = result_electron["delta"][0]

    assert abs(delta_positron) > 0.1, (
        "Positron should receive a substantial energy kick from the cavity.")
    assert abs(delta_electron) == pytest.approx(0.0, abs=1e-6), (
        "CHARGE = -1 is silently zeroed by SAD. The electron receives no cavity "
        "energy gain (delta ≈ 0) instead of the expected sign-reversed kick. "
        "SAD only supports CHARGE = +1 (positron) as the reference particle.")
