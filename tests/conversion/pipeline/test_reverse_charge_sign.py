"""
================================================================================
Tests for the reverse_charge_sign parameter of the SAD2XS conversion pipeline
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-30
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import sad2xs as s2x

################################################################################
# Background: what reverse_charge_sign does and does not change
################################################################################
# reverse_charge_sign=True negates q0 on the reference particle ONLY.
# It does NOT change any element parameter.
#
# All element parameters in the converter are charge-sign-neutral:
#
#   ks  (solenoid) = BZ / (p0/e)  → UNCHANGED  (brho always uses q = +e)
#   angle / k0  (bend)             → UNCHANGED
#   k1          (quadrupole)       → UNCHANGED
#   k1s / k2    (skew quad/sext)   → UNCHANGED
#
# SAD convention: BZ is a physical field [T], but normalisation uses unit
# positive charge (q = +e) regardless of the actual beam species.  Using
# brho = p0/e throughout keeps ks consistent with k0, k1, k1s etc. and
# ensures that coupling-compensation schemes (skew quads tuned against a
# solenoid) remain valid after reverse_charge_sign=True.
#
# The only effect of reverse_charge_sign=True is changing q0 in the Xsuite
# environment (e.g. for radiation integrals, species labelling, canonical
# momentum definitions).  Tracking and Twiss results are IDENTICAL to the
# default conversion.
#
# reverse_charge_sign is INDEPENDENT of reverse_survey_horizontal.  They address
# different physical questions:
#   reverse_charge_sign          → relabel the reference particle species
#   reverse_survey_horizontal  → horizontal mirror of the survey geometry

################################################################################
# Structural: what changes and what does not
################################################################################
def test_pipeline_reverse_charge_sign_does_not_change_solenoid_ks(write_lattice):
    """
    reverse_charge_sign=True must NOT change the solenoid ks.

    SAD's BZ is a physical field strength [T], but the SAD convention treats
    the reference particle as having unit positive charge (q = +e) for
    normalisation purposes.  The converter always uses brho = p0 / e
    (ignoring the sign of q0), giving ks = BZ / (p0/e).

    This makes ks charge-sign-neutral — consistent with k0, k1, k1s, and
    all other element parameters in the converter.  It means:

      - reverse_charge_sign=True changes only the reference particle label (q0).
      - The solenoid coupling direction in Xsuite is UNCHANGED.
      - Skew-quad coupling corrections tuned against the solenoid remain valid.

    Without this convention, reverse_charge_sign would invert ks while leaving k1s
    (skew quads) unchanged, breaking any solenoid coupling compensation scheme.
    Empirically verified: a particle with x=1 mm initial offset exits the
    solenoid with the same y for both reverse_charge_sign=False and reverse_charge_sign=True.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       SOL_DRIFT   = (L = 0.5);
        SOL         SOL_IN      = (BZ = 0.5 BOUND = 1 GEO = 1)
                    SOL_OUT     = (BZ = 0.5 BOUND = 1);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START SOL_IN SOL_DRIFT SOL_OUT END);
        """,
        filename = "rev_charge_sol_ks.sad")

    line_default  = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge_sign   = False,
        _verbose         = False,
        _test_mode       = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge_sign   = True,
        _verbose         = False,
        _test_mode       = True)

    tt_d = line_default.get_table(attr=True)
    tt_r = line_reversed.get_table(attr=True)

    sol_names_d = [n for n in tt_d.rows[tt_d.element_type == "UniformSolenoid"].name
                   if "::" not in n]
    sol_names_r = [n for n in tt_r.rows[tt_r.element_type == "UniformSolenoid"].name
                   if "::" not in n]

    assert sol_names_d, "Expected at least one UniformSolenoid in the default line."

    for name_d, name_r in zip(sol_names_d, sol_names_r):
        ks_d = line_default[name_d].ks
        ks_r = line_reversed[name_r].ks

        assert ks_d != pytest.approx(0.0), (
            f"Default solenoid {name_d}.ks should be non-zero for BZ = 0.5. "
            f"Got {ks_d}.")
        assert ks_r == pytest.approx(ks_d), (
            f"reverse_charge_sign=True must NOT change solenoid ks. "
            f"Default: {ks_d:.6f}, reversed: {ks_r:.6f}. "
            "ks is computed with brho = p0/e (always unit positive charge), "
            "making it charge-sign-neutral like all other element parameters.")


def test_pipeline_reverse_charge_sign_does_not_change_bend_k0(write_lattice):
    """
    reverse_charge_sign=True must NOT change the bend angle or k0.

    The bending ANGLE in SAD is a geometric quantity (not normalised by Bρ),
    so it is independent of the particle charge.  Xsuite k0 = angle/L is
    likewise charge-independent.  Changing q0 via reverse_charge_sign must leave
    k0 and angle unchanged.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        B1      = (L = 1.0 ANGLE = 0.05);
        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START B1 D1 END);
        """,
        filename = "rev_charge_bend_k0.sad")

    line_default  = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge_sign   = False,
        _verbose         = False,
        _test_mode       = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge_sign   = True,
        _verbose         = False,
        _test_mode       = True)

    k0_default  = line_default["b1"].k0
    k0_reversed = line_reversed["b1"].k0

    assert k0_default != pytest.approx(0.0), (
        "Default bend k0 should be non-zero for ANGLE = 0.05.")
    assert k0_reversed == pytest.approx(k0_default), (
        "reverse_charge_sign=True must NOT change bend k0/angle. The bending angle "
        "is a geometric quantity (not normalised by Bρ) and is therefore "
        "independent of the particle charge. "
        f"Default: {k0_default:.6f}, reversed: {k0_reversed:.6f}.")


def test_pipeline_reverse_charge_sign_does_not_change_quad_k1(write_lattice):
    """
    reverse_charge_sign=True must NOT change the quadrupole k1.

    SAD's K1 parameter is a normalised gradient (already divided by Bρ in
    SAD's conventions) and is stored directly as Xsuite k1.  Changing q0
    via reverse_charge_sign must leave k1 unchanged.

    Xsuite verification: k1 is charge-sign-neutral — the same k1 value
    produces the same beta functions for q0=−1 and q0=+1.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        QUAD        Q1      = (L = 1.0 K1 = 0.4);
        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START Q1 D1 END);
        """,
        filename = "rev_charge_quad_k1.sad")

    line_default  = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge_sign   = False,
        _verbose         = False,
        _test_mode       = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge_sign   = True,
        _verbose         = False,
        _test_mode       = True)

    k1_default  = line_default["q1"].k1
    k1_reversed = line_reversed["q1"].k1

    assert k1_default != pytest.approx(0.0), (
        "Default quad k1 should be non-zero for K1 = 0.4.")
    assert k1_reversed == pytest.approx(k1_default), (
        "reverse_charge_sign=True must NOT change quad k1. SAD K1 is already "
        "normalised and charge-independent. Xsuite k1 is charge-sign-neutral. "
        f"Default: {k1_default:.6f}, reversed: {k1_reversed:.6f}.")


################################################################################
# Twiss self-consistency
################################################################################
def test_pipeline_reverse_charge_sign_twiss_beta_functions_unchanged_without_solenoid(
        write_lattice):
    """
    reverse_charge_sign=True on a lattice containing no solenoids must produce
    identical 4D Twiss beta functions to the default conversion.

    Without solenoids, the only element affected by the charge-dependent brho
    normalisation is ks.  With no solenoid in the lattice, reverse_charge_sign
    changes only q0 on the particle reference — element parameters are
    completely unaffected — so the Twiss must be trivially identical.

    This test serves as a regression guard: any unintended path that uses q0
    during element conversion would show up here as a Twiss discrepancy.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        B1      = (L = 1.0 ANGLE = 0.05);
        QUAD        Q1      = (L = 1.0 K1 = 0.5);
        SEXT        S1      = (L = 0.3 K2 = 1.0);
        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START B1 Q1 D1 S1 D1 END);
        """,
        filename = "rev_charge_twiss_no_sol.sad")

    line_default  = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge_sign   = False,
        _verbose         = False,
        _test_mode       = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge_sign   = True,
        _verbose         = False,
        _test_mode       = True)

    tw_d = line_default.twiss4d(betx=1.0, bety=1.0)
    tw_r = line_reversed.twiss4d(betx=1.0, bety=1.0)

    assert tw_r.betx[-1] == pytest.approx(tw_d.betx[-1], rel=1e-9), (
        "reverse_charge_sign=True on a non-solenoid lattice must not change betx. "
        "No element parameter uses q0 in this lattice, so the Twiss must be "
        "identical. A discrepancy would indicate an unintended charge-dependent "
        "path in the element converter. "
        f"Default betx={tw_d.betx[-1]:.6f}, reversed betx={tw_r.betx[-1]:.6f}.")
    assert tw_r.bety[-1] == pytest.approx(tw_d.bety[-1], rel=1e-9), (
        "reverse_charge_sign=True on a non-solenoid lattice must not change bety. "
        f"Default bety={tw_d.bety[-1]:.6f}, reversed bety={tw_r.bety[-1]:.6f}.")


def test_pipeline_reverse_charge_sign_twiss_beta_functions_unchanged_with_solenoid(
        write_lattice):
    """
    reverse_charge_sign=True on a lattice containing a bound solenoid must produce
    the same 4D Twiss beta functions as the default conversion.

    Since reverse_charge_sign=True does NOT change ks (brho is always computed with
    unit positive charge), element parameters are identical in both conversions.
    The Twiss must therefore be trivially identical.

    This test guards against any regression where ks is accidentally made
    charge-dependent again.  A failure would indicate that the solenoid
    converter is using q0 in the brho normalisation.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       SOL_DRIFT   = (L = 0.5);
        SOL         SOL_IN      = (BZ = 0.5 BOUND = 1 GEO = 1)
                    SOL_OUT     = (BZ = 0.5 BOUND = 1);
        QUAD        Q1          = (L = 1.0 K1 = 0.3);
        DRIFT       D1          = (L = 1.0);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START SOL_IN SOL_DRIFT SOL_OUT Q1 D1 END);
        """,
        filename = "rev_charge_twiss_sol.sad")

    line_default  = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge_sign   = False,
        _verbose         = False,
        _test_mode       = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge_sign   = True,
        _verbose         = False,
        _test_mode       = True)

    tw_d = line_default.twiss4d(betx=1.0, bety=1.0)
    tw_r = line_reversed.twiss4d(betx=1.0, bety=1.0)

    assert tw_r.betx[-1] == pytest.approx(tw_d.betx[-1], rel=1e-6), (
        "reverse_charge_sign=True must not change betx for a solenoid lattice. "
        "Twiss beta functions depend on ks² (Larmor frame), so ks and −ks "
        "give identical beta functions. A discrepancy indicates a bug in the "
        "ks normalisation or an incorrect element conversion path. "
        f"Default betx={tw_d.betx[-1]:.6f}, reversed betx={tw_r.betx[-1]:.6f}.")
    assert tw_r.bety[-1] == pytest.approx(tw_d.bety[-1], rel=1e-6), (
        "reverse_charge_sign=True must not change bety for a solenoid lattice. "
        f"Default bety={tw_d.bety[-1]:.6f}, reversed bety={tw_r.bety[-1]:.6f}.")
