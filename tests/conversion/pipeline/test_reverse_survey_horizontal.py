"""
================================================================================
Tests for the reverse_survey_horizontal parameter of the SAD2XS conversion pipeline
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-03
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import pytest
import xtrack as xt
import sad2xs as s2x

from sad2xs.converter._000_helpers import create_sad_soft_quadrupolar_fringe
from sad2xs.converter._007_reversals import (
    _reflect_sad_soft_quadrupolar_fringes)

################################################################################
# SAD Soft Quadrupolar Fringe Reflection
################################################################################
def test_reverse_survey_horizontal_reflects_soft_quadrupolar_fringe(
        write_lattice):
    """The semantic fringe map must follow the body's horizontal mirror."""
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        QUAD Q1=(L=0.5 K1=0.1 F1=0.02 F2=0.01 FRINGE=3
                 DX=0.0012 DY=-0.0008 ROTATE=0.2 DISFRIN=1);
        SOL S1=(BZ=0.1 BOUND=1 GEO=1 DISFRIN=1)
            S2=(BZ=0.1 BOUND=1 DISFRIN=1);
        MARK START=() END=();
        LINE TEST=(START S1 Q1 S2 END);
        """,
        filename = "reverse_horizontal_k1_fringe.sad")
    forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path), output_directory = "N/A",
        _verbose = False, _test_mode = True)
    reflected = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path), output_directory = "N/A",
        reverse_survey_horizontal = True,
        _verbose = False, _test_mode = True)

    for name in ("q1_fringe_in", "q1_fringe_out"):
        assert reflected[name].shift_x == pytest.approx(-forward[name].shift_x)
        assert reflected[name].shift_y == pytest.approx(forward[name].shift_y)
        assert reflected[name].rot_s_rad == pytest.approx(
            -forward[name].rot_s_rad)

        forward_particle = xt.Particles(
            p0c = 1.0E9, x = 1.1e-3, px = -2.0e-4,
            y = -0.7e-3, py = 3.0e-4, zeta = 2.0e-3, delta = 0.01)
        reflected_particle = forward_particle.copy()
        reflected_particle.x  *= -1
        reflected_particle.px *= -1
        forward[name].track(forward_particle)
        reflected[name].track(reflected_particle)
        np.testing.assert_allclose(
            [reflected_particle.x[0], reflected_particle.px[0],
             reflected_particle.y[0], reflected_particle.py[0],
             reflected_particle.zeta[0]],
            [-forward_particle.x[0], -forward_particle.px[0],
             forward_particle.y[0], forward_particle.py[0],
             forward_particle.zeta[0]],
            rtol = 1e-13,
            atol = 1e-15)


def test_fringe_reflection_only_mutates_recognised_line_occurrences():
    """Do not reflect unused fringes or unrelated second-order maps."""
    environment = xt.Environment()
    for name in ("active", "unused"):
        create_sad_soft_quadrupolar_fringe(
            environment,
            name              = name,
            a                 = -3.0E-05,
            b                 = 0.006,
            field_rotation    = 0.2,
            shift_x           = 1.2E-03,
            shift_y           = -0.8E-03)
    environment.new(
        name        = "generic",
        prototype   = xt.SecondOrderTaylorMap,
        shift_x     = 2.0E-03,
        rot_s_rad   = -0.3)
    line = environment.new_line(
        name = "test", components = ["active", "generic"])

    _reflect_sad_soft_quadrupolar_fringes(line, horizontal = True)

    assert environment["active"].shift_x == pytest.approx(-1.2E-03)
    assert environment["active"].rot_s_rad == pytest.approx(0.2)
    assert environment["unused"].shift_x == pytest.approx(1.2E-03)
    assert environment["unused"].rot_s_rad == pytest.approx(-0.2)
    assert environment["generic"].shift_x == pytest.approx(2.0E-03)
    assert environment["generic"].rot_s_rad == pytest.approx(-0.3)

################################################################################
# Default Behaviour
################################################################################
def test_pipeline_reverse_survey_horizontal_false_preserves_bend_angle(write_lattice):
    """
    When reverse_survey_horizontal is not set, the bend angle should retain its
    sign from the SAD definition. SAD ANGLE = 0.1 rad maps directly to Xsuite
    angle = 0.1 rad.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        B1      = (L = 1.0 ANGLE = 0.1);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START B1 END);
        """,
        filename = "rev_bend_dir_default.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        _verbose               = False,
        _test_mode             = True)

    assert line["b1"].angle == pytest.approx(0.1), (
        "Without reverse_survey_horizontal, bend angle should retain SAD ANGLE = 0.1 "
        f"""rad. Got: {line["b1"].angle}.""")


################################################################################
# Bend Adjustments
################################################################################
def test_pipeline_reverse_survey_horizontal_negates_bend_angle_and_edge_angles(write_lattice):
    """
    reverse_survey_horizontal=True should negate the bend angle and both edge angles.
    Asymmetric E1 != E2 makes this test sensitive to the distinction between
    negation and swap: a swap would produce entry=-exit_forward, exit=-entry_forward,
    which differs from the expected negation entry=-entry_forward, exit=-exit_forward.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        B1      = (L = 1.0 ANGLE = 0.1 E1 = 0.5 E2 = 0.25);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START B1 END);
        """,
        filename = "rev_bend_dir_bend.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = True,
        _verbose               = False,
        _test_mode             = True)

    angle_forward  = line_forward["b1"].angle
    entry_forward  = line_forward["b1"].edge_entry_angle
    exit_forward   = line_forward["b1"].edge_exit_angle

    angle_reversed = line_reversed["b1"].angle
    entry_reversed = line_reversed["b1"].edge_entry_angle
    exit_reversed  = line_reversed["b1"].edge_exit_angle

    assert entry_forward != pytest.approx(0.0), (
        "Forward bend entry angle should be non-zero for E1 = 0.5, ANGLE = 0.1.")
    assert exit_forward != pytest.approx(0.0), (
        "Forward bend exit angle should be non-zero for E2 = 0.25, ANGLE = 0.1.")
    assert entry_forward != pytest.approx(exit_forward), (
        "Asymmetric E1 != E2 should produce distinct entry and exit angles.")

    assert angle_reversed == pytest.approx(-angle_forward), (
        "reverse_survey_horizontal=True should negate the bend angle. "
        f"Forward: {angle_forward}, reversed: {angle_reversed}.")
    assert entry_reversed == pytest.approx(-entry_forward), (
        "reverse_survey_horizontal=True should negate the entry edge angle, not swap it. "
        f"Forward entry: {entry_forward}, reversed entry: {entry_reversed}.")
    assert exit_reversed == pytest.approx(-exit_forward), (
        "reverse_survey_horizontal=True should negate the exit edge angle, not swap it. "
        f"Forward exit: {exit_forward}, reversed exit: {exit_reversed}.")


################################################################################
# Quadrupole Adjustments
################################################################################
def test_pipeline_reverse_survey_horizontal_quad_k1_unchanged_and_k1s_negated(write_lattice):
    """
    reverse_survey_horizontal=True should leave k1 unchanged (odd-order normal) and
    negate k1s (odd-order skew). Two quadrupoles cover both sides of the contract:
    a standard QUAD for k1 and a ROTATE=+pi/4 skew QUAD for k1s. The rotation
    maps K1 entirely into k1s (k1 becomes zero for the skew element).
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        QUAD        QN      = (L = 0.5 K1 = 0.2);
        QUAD        QS      = (L = 0.5 K1 = 0.2 ROTATE = 0.785398);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START QN QS END);
        """,
        filename = "rev_bend_dir_quad.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = True,
        _verbose               = False,
        _test_mode             = True)

    k1_forward   = line_forward["qn"].k1
    k1_reversed  = line_reversed["qn"].k1
    k1s_forward  = line_forward["qs"].k1s
    k1s_reversed = line_reversed["qs"].k1s

    assert k1_forward != pytest.approx(0.0), (
        "Forward normal quadrupole k1 should be non-zero for K1 = 0.2.")
    assert k1s_forward != pytest.approx(0.0), (
        "Forward skew quadrupole k1s should be non-zero for K1 = 0.2 with ROTATE = pi/4.")

    assert k1_reversed == pytest.approx(k1_forward), (
        "reverse_survey_horizontal=True should leave k1 unchanged (odd-order normal). "
        f"Forward: {k1_forward}, reversed: {k1_reversed}.")
    assert k1s_reversed == pytest.approx(-k1s_forward), (
        "reverse_survey_horizontal=True should negate k1s (odd-order skew). "
        f"Forward: {k1s_forward}, reversed: {k1s_reversed}.")


################################################################################
# Sextupole Adjustments
################################################################################
def test_pipeline_reverse_survey_horizontal_sext_k2_negated_and_k2s_unchanged(write_lattice):
    """
    reverse_survey_horizontal=True should negate k2 (even-order normal) and leave
    k2s unchanged (even-order skew). Two sextupoles cover both sides: a standard
    SEXT for k2 and a ROTATE=+pi/6 skew SEXT for k2s.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        SEXT        SN      = (L = 0.3 K2 = 0.15);
        SEXT        SS      = (L = 0.3 K2 = 0.15 ROTATE = 0.523599);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START SN SS END);
        """,
        filename = "rev_bend_dir_sext.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = True,
        _verbose               = False,
        _test_mode             = True)

    k2_forward   = line_forward["sn"].k2
    k2_reversed  = line_reversed["sn"].k2
    k2s_forward  = line_forward["ss"].k2s
    k2s_reversed = line_reversed["ss"].k2s

    assert k2_forward != pytest.approx(0.0), (
        "Forward normal sextupole k2 should be non-zero for K2 = 0.15.")
    assert k2s_forward != pytest.approx(0.0), (
        "Forward skew sextupole k2s should be non-zero for K2 = 0.15 with ROTATE = pi/6.")

    assert k2_reversed == pytest.approx(-k2_forward), (
        "reverse_survey_horizontal=True should negate k2 (even-order normal). "
        f"Forward: {k2_forward}, reversed: {k2_reversed}.")
    assert k2s_reversed == pytest.approx(k2s_forward), (
        "reverse_survey_horizontal=True should leave k2s unchanged (even-order skew). "
        f"Forward: {k2s_forward}, reversed: {k2s_reversed}.")


################################################################################
# Octupole Adjustments
################################################################################
def test_pipeline_reverse_survey_horizontal_oct_k3_unchanged_and_k3s_negated(write_lattice):
    """
    reverse_survey_horizontal=True should leave k3 unchanged (odd-order normal) and
    negate k3s (odd-order skew). Two octupoles cover both sides: a standard OCT
    for k3 and a ROTATE=+pi/8 skew OCT for k3s.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        OCT         ON      = (L = 0.3 K3 = 0.1);
        OCT         OS      = (L = 0.3 K3 = 0.1 ROTATE = 0.392699);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START ON OS END);
        """,
        filename = "rev_bend_dir_oct.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = True,
        _verbose               = False,
        _test_mode             = True)

    k3_forward   = line_forward["on"].k3
    k3_reversed  = line_reversed["on"].k3
    k3s_forward  = line_forward["os"].k3s
    k3s_reversed = line_reversed["os"].k3s

    assert k3_forward != pytest.approx(0.0), (
        "Forward normal octupole k3 should be non-zero for K3 = 0.1.")
    assert k3s_forward != pytest.approx(0.0), (
        "Forward skew octupole k3s should be non-zero for K3 = 0.1 with ROTATE = pi/8.")

    assert k3_reversed == pytest.approx(k3_forward), (
        "reverse_survey_horizontal=True should leave k3 unchanged (odd-order normal). "
        f"Forward: {k3_forward}, reversed: {k3_reversed}.")
    assert k3s_reversed == pytest.approx(-k3s_forward), (
        "reverse_survey_horizontal=True should negate k3s (odd-order skew). "
        f"Forward: {k3s_forward}, reversed: {k3s_reversed}.")


################################################################################
# Multipole Adjustments
################################################################################
def test_pipeline_reverse_survey_horizontal_mult_knl_ksl_sign_convention(write_lattice):
    """
    reverse_survey_horizontal=True should apply the even/odd sign rule to the knl
    and ksl arrays of a SAD MULT element:
      knl (even order): negated   ksl (even order): unchanged
      knl (odd order):  unchanged ksl (odd order):  negated
    K1/SK1 (order 1, odd) and K2/SK2 (order 2, even) together cover both rules
    in a single element, verifying all four sign outcomes at once.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MULT        M1      = (L = 0.5 K1 = 0.1 SK1 = 0.05 K2 = 0.08 SK2 = 0.03);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START M1 END);
        """,
        filename = "rev_bend_dir_mult.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = True,
        _verbose               = False,
        _test_mode             = True)

    knl1_fwd = line_forward["m1"].knl[1]
    knl2_fwd = line_forward["m1"].knl[2]
    ksl1_fwd = line_forward["m1"].ksl[1]
    ksl2_fwd = line_forward["m1"].ksl[2]

    knl1_rev = line_reversed["m1"].knl[1]
    knl2_rev = line_reversed["m1"].knl[2]
    ksl1_rev = line_reversed["m1"].ksl[1]
    ksl2_rev = line_reversed["m1"].ksl[2]

    assert knl1_fwd != pytest.approx(0.0), (
        "Forward multipole knl[1] should be non-zero for K1 = 0.1.")
    assert knl2_fwd != pytest.approx(0.0), (
        "Forward multipole knl[2] should be non-zero for K2 = 0.08.")
    assert ksl1_fwd != pytest.approx(0.0), (
        "Forward multipole ksl[1] should be non-zero for SK1 = 0.05.")
    assert ksl2_fwd != pytest.approx(0.0), (
        "Forward multipole ksl[2] should be non-zero for SK2 = 0.03.")

    assert knl1_rev == pytest.approx(knl1_fwd), (
        "reverse_survey_horizontal=True should leave knl[1] unchanged (odd-order normal). "
        f"Forward: {knl1_fwd}, reversed: {knl1_rev}.")
    assert knl2_rev == pytest.approx(-knl2_fwd), (
        "reverse_survey_horizontal=True should negate knl[2] (even-order normal). "
        f"Forward: {knl2_fwd}, reversed: {knl2_rev}.")
    assert ksl1_rev == pytest.approx(-ksl1_fwd), (
        "reverse_survey_horizontal=True should negate ksl[1] (odd-order skew). "
        f"Forward: {ksl1_fwd}, reversed: {ksl1_rev}.")
    assert ksl2_rev == pytest.approx(ksl2_fwd), (
        "reverse_survey_horizontal=True should leave ksl[2] unchanged (even-order skew). "
        f"Forward: {ksl2_fwd}, reversed: {ksl2_rev}.")


################################################################################
# Solenoid Adjustments
################################################################################
def test_pipeline_reverse_survey_horizontal_negates_solenoid_ks(write_lattice):
    """
    reverse_survey_horizontal=True should negate the solenoid field strength ks.
    The reversed ks is compared against the forward conversion to avoid
    dependence on the BZ-to-ks conversion formula.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        SOL         S1      = (L = 0.5 BZ = 0.1);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START S1 END);
        """,
        filename = "rev_bend_dir_solenoid.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = True,
        _verbose               = False,
        _test_mode             = True)

    ks_forward  = line_forward["s1"].ks
    ks_reversed = line_reversed["s1"].ks

    assert ks_forward != pytest.approx(0.0), (
        "Forward solenoid ks should be non-zero for BZ = 0.1.")
    assert ks_reversed == pytest.approx(-ks_forward), (
        "reverse_survey_horizontal=True should negate solenoid ks. "
        f"Forward: {ks_forward}, reversed: {ks_reversed}.")


def test_pipeline_reverse_survey_horizontal_negates_solenoid_ks_with_charge_minus_one(
        write_lattice):
    """
    The charge-dependent and geometric-mirror ks negations compose correctly.

    Asserts the composition arithmetically, in converter code only. SAD has no
    native operator for a whole-lattice geometric mirror, so unlike
    test_pipeline_reverse_element_order_solenoid_physics_matches_sad_with_charge_minus_one
    this file has no real-SAD comparison. That is a known coverage gap.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        CHARGE      = -1;

        SOL         S1      = (L = 0.5 BZ = 0.1);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START S1 END);
        """,
        filename = "rev_survey_solenoid_charge.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = True,
        _verbose               = False,
        _test_mode             = True)

    assert float(line_forward.particle_ref.q0) == pytest.approx(-1.0), (
        "Sanity check: CHARGE=-1 in the SAD file should give q0=-1 on the "
        "converted line's reference particle.")

    ks_forward  = line_forward["s1"].ks
    ks_reversed = line_reversed["s1"].ks

    assert ks_forward != pytest.approx(0.0), (
        "Forward solenoid ks (CHARGE=-1) should be non-zero for BZ = 0.1.")
    assert ks_reversed == pytest.approx(-ks_forward), (
        "reverse_survey_horizontal=True should negate solenoid ks even when "
        "the base ks is already charge-adjusted (CHARGE=-1). "
        f"Forward: {ks_forward}, reversed: {ks_reversed}.")


################################################################################
# Element Offset Adjustments
################################################################################
def test_pipeline_reverse_survey_horizontal_negates_shift_x_and_rot_s_rad_preserves_shift_y(
        write_lattice):
    """
    reverse_survey_horizontal=True should negate shift_x and rot_s_rad but leave
    shift_y unchanged on all magnetic element types. A QUAD with DX, DY, and
    ROTATE parameters exercises this path. ROTATE = 0.1 rad (not ±pi/4) avoids
    the k1-to-k1s mapping so the quadrupole path is taken, not the skew path.
    The forward and reversed conversions are compared rather than hardcoding
    expected values, since the SAD-to-Xsuite sign convention for rot_s_rad
    (= -ROTATE) is an internal detail of the element converter.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        QUAD        QO      = (L = 0.5 K1 = 0.2 DX = 0.01 DY = 0.02 ROTATE = 0.1);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START QO END);
        """,
        filename = "rev_bend_dir_offset.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = True,
        _verbose               = False,
        _test_mode             = True)

    shift_x_fwd   = line_forward["qo"].shift_x
    shift_y_fwd   = line_forward["qo"].shift_y
    rot_s_rad_fwd = line_forward["qo"].rot_s_rad

    shift_x_rev   = line_reversed["qo"].shift_x
    shift_y_rev   = line_reversed["qo"].shift_y
    rot_s_rad_rev = line_reversed["qo"].rot_s_rad

    assert shift_x_fwd != pytest.approx(0.0), (
        "Forward QUAD shift_x should be non-zero for DX = 0.01.")
    assert shift_y_fwd != pytest.approx(0.0), (
        "Forward QUAD shift_y should be non-zero for DY = 0.02.")
    assert rot_s_rad_fwd != pytest.approx(0.0), (
        "Forward QUAD rot_s_rad should be non-zero for ROTATE = 0.1.")

    assert shift_x_rev == pytest.approx(-shift_x_fwd), (
        "reverse_survey_horizontal=True should negate shift_x. "
        f"Forward: {shift_x_fwd}, reversed: {shift_x_rev}.")
    assert shift_y_rev == pytest.approx(shift_y_fwd), (
        "reverse_survey_horizontal=True should leave shift_y unchanged. "
        f"Forward: {shift_y_fwd}, reversed: {shift_y_rev}.")
    assert rot_s_rad_rev == pytest.approx(-rot_s_rad_fwd), (
        "reverse_survey_horizontal=True should negate rot_s_rad. "
        f"Forward: {rot_s_rad_fwd}, reversed: {rot_s_rad_rev}.")


################################################################################
# Reference Shift Adjustment
################################################################################
def test_pipeline_reverse_survey_horizontal_negates_coord_dx_preserves_dy(write_lattice):
    """
    reverse_survey_horizontal=True should negate dx but leave dy unchanged.
    This contrasts with reverse_element_order, which negates both dx and dy.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        COORD       C1      = (DX = 0.01 DY = 0.02);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START C1 END);
        """,
        filename = "rev_bend_dir_coord.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = True,
        _verbose               = False,
        _test_mode             = True)

    dx_forward  = line_forward["c1"].shift_x
    dy_forward  = line_forward["c1"].shift_y
    dx_reversed = line_reversed["c1"].shift_x
    dy_reversed = line_reversed["c1"].shift_y

    assert dx_forward != pytest.approx(0.0), (
        "Forward COORD shift_x should be non-zero for DX = 0.01.")
    assert dy_forward != pytest.approx(0.0), (
        "Forward COORD shift_y should be non-zero for DY = 0.02.")
    assert dx_reversed == pytest.approx(-dx_forward), (
        "reverse_survey_horizontal=True should negate COORD shift_x. "
        f"Forward: {dx_forward}, reversed: {dx_reversed}.")
    assert dy_reversed == pytest.approx(dy_forward), (
        "reverse_survey_horizontal=True should leave COORD shift_y unchanged "
        "(unlike reverse_element_order which negates both shift_x and shift_y). "
        f"Forward: {dy_forward}, reversed: {dy_reversed}.")


################################################################################
# Coordinate Rotation Adjustment
################################################################################
def test_pipeline_reverse_survey_horizontal_coord_chi1_negated_chi2_unchanged_chi3_negated(
        write_lattice):
    """
    reverse_survey_horizontal=True should negate chi1 (rot_y_rad) and chi3
    (rot_s_rad) but leave chi2 (rot_x_rad) unchanged. A single COORD with all
    three components produces elements named c1_chi1, c1_chi2, c1_chi3.
    The chi2 assertion is the non-trivial one: it confirms the asymmetry between
    the three rotation types.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        COORD       C1      = (CHI1 = 0.05 CHI2 = 0.03 CHI3 = 0.02);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START C1 END);
        """,
        filename = "rev_bend_dir_chi.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = True,
        _verbose               = False,
        _test_mode             = True)

    chi1_fwd = line_forward["c1_chi1"].rot_y_rad
    chi2_fwd = line_forward["c1_chi2"].rot_x_rad
    chi3_fwd = line_forward["c1_chi3"].rot_s_rad

    chi1_rev = line_reversed["c1_chi1"].rot_y_rad
    chi2_rev = line_reversed["c1_chi2"].rot_x_rad
    chi3_rev = line_reversed["c1_chi3"].rot_s_rad

    assert chi1_fwd != pytest.approx(0.0), (
        "Forward c1_chi1 rot_y_rad should be non-zero for CHI1 = 0.05.")
    assert chi2_fwd != pytest.approx(0.0), (
        "Forward c1_chi2 rot_x_rad should be non-zero for CHI2 = 0.03.")
    assert chi3_fwd != pytest.approx(0.0), (
        "Forward c1_chi3 rot_s_rad should be non-zero for CHI3 = 0.02.")

    assert chi1_rev == pytest.approx(-chi1_fwd), (
        "reverse_survey_horizontal=True should negate the chi1 rot_y_rad. "
        f"Forward: {chi1_fwd}, reversed: {chi1_rev}.")
    assert chi2_rev == pytest.approx(chi2_fwd), (
        "reverse_survey_horizontal=True should leave chi2 rot_x_rad unchanged. "
        f"Forward: {chi2_fwd}, reversed: {chi2_rev}.")
    assert chi3_rev == pytest.approx(-chi3_fwd), (
        "reverse_survey_horizontal=True should negate the chi3 rot_s_rad. "
        f"Forward: {chi3_fwd}, reversed: {chi3_rev}.")


################################################################################
# Twiss self-consistency
################################################################################
def test_pipeline_reverse_survey_horizontal_twiss_beta_functions_unchanged(write_lattice):
    """
    A horizontal mirror leaves the 4D Twiss beta functions unchanged.

    Compares twiss4d betx and bety at the end of a BEND, QUAD, SEXT, DRIFT
    lattice, with and without the flag. The mirror leaves k1 unchanged and flips
    the signs of k0 and k2, which produces no net change to the linear transfer
    matrix. See docs/converter/line-reversals.md.
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
        filename = "rev_bend_dir_twiss.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_horizontal = True,
        _verbose               = False,
        _test_mode             = True)

    tw_fwd = line_forward.twiss4d(betx=1.0, bety=1.0)
    tw_rev = line_reversed.twiss4d(betx=1.0, bety=1.0)

    betx_fwd = tw_fwd.betx[-1]
    bety_fwd = tw_fwd.bety[-1]
    betx_rev = tw_rev.betx[-1]
    bety_rev = tw_rev.bety[-1]

    assert betx_rev == pytest.approx(betx_fwd, rel=1e-9), (
        "reverse_survey_horizontal=True is a horizontal mirror: betx must be "
        "unchanged. The mirror changes the sign of k0 and k2 but not k1 — the "
        "linear focusing (beta functions) is therefore invariant. "
        f"Forward betx={betx_fwd:.6f}, reversed betx={betx_rev:.6f}.")
    assert bety_rev == pytest.approx(bety_fwd, rel=1e-9), (
        "reverse_survey_horizontal=True is a horizontal mirror: bety must be "
        "unchanged. The mirror changes the sign of k0 and k2 but not k1 — the "
        "linear focusing (beta functions) is therefore invariant. "
        f"Forward bety={bety_fwd:.6f}, reversed bety={bety_rev:.6f}.")


################################################################################
# Canonical Dipole Rotation
################################################################################
@pytest.mark.parametrize(
    "sad_rotation",
    [+np.pi / 2, -np.pi / 2, +np.pi, -np.pi])
def test_reverse_survey_horizontal_keeps_the_canonical_dipole_rotation(
        write_lattice, sad_rotation):
    """
    A reflected dipole must keep the canonical rotation.

    Reflection negates rot_s_rad, which turns the canonical +pi/2 of a
    vertical corrector into -pi/2. The writer then reads it as a skew
    corrector rather than a vertical one.
    """
    lattice_path = write_lattice(
        f"""\
        MOMENTUM    = 1.0 GEV;

        BEND        CV          = (
            L       = 0.5
            ANGLE   = 0.0
            K0      = 0.1
            ROTATE  = {sad_rotation}
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START CV END);
        """,
        filename = f"reverse_horizontal_canonical_rotation_{sad_rotation:.6f}.sad")

    reflected = s2x.convert_sad_to_xsuite(
        sad_lattice_path            = str(lattice_path),
        output_directory            = "N/A",
        reverse_survey_horizontal   = True,
        _verbose                    = False,
        _test_mode                  = True)

    assert reflected["cv"].rot_s_rad in (
        pytest.approx(0.0), pytest.approx(np.pi / 2)), (
        "A reflected dipole should keep a canonical rotation of 0 or +pi/2, "
        "with the direction carried by the field sign. Got "
        f"""{reflected["cv"].rot_s_rad}.""")


def test_reverse_survey_horizontal_canonical_rotation_preserves_tracking(
        write_lattice):
    """
    Restoring the canonical rotation must not change the reflected optics.

    The canonical form differs from the reflected one by a pi rotation
    about s, so the two describe the same physical element.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        CV          = (
            L       = 0.5
            ANGLE   = 0.0
            K0      = 0.1
            K1      = 0.02
            DX      = 1.2E-3
            DY      = -0.8E-3
            ROTATE  = 90 DEG
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START CV END);
        """,
        filename = "reverse_horizontal_canonical_rotation_tracking.sad")

    reflected = s2x.convert_sad_to_xsuite(
        sad_lattice_path            = str(lattice_path),
        output_directory            = "N/A",
        reverse_survey_horizontal   = True,
        _verbose                    = False,
        _test_mode                  = True)

    # Clone so the comparison keeps the converted element's tracking model
    element = reflected["cv"]
    reflected.env.new(
        name        = "cv_non_canonical",
        prototype   = "cv",
        k0          = -element.k0,
        rot_s_rad   = -element.rot_s_rad)
    equivalent = reflected.env["cv_non_canonical"]

    canonical_particle      = xt.Particles(
        p0c = 1.0E9, x = 1.1E-3, px = -2.0E-4,
        y = -0.7E-3, py = 3.0E-4, zeta = 2.0E-3, delta = 0.01)
    non_canonical_particle  = canonical_particle.copy()
    element.track(canonical_particle)
    equivalent.track(non_canonical_particle)

    np.testing.assert_allclose(
        [canonical_particle.x[0], canonical_particle.px[0],
         canonical_particle.y[0], canonical_particle.py[0],
         canonical_particle.zeta[0]],
        [non_canonical_particle.x[0], non_canonical_particle.px[0],
         non_canonical_particle.y[0], non_canonical_particle.py[0],
         non_canonical_particle.zeta[0]],
        rtol = 1e-13,
        atol = 1e-15,
        err_msg = "The canonical rotation must track identically to the "
                  "non-canonical form it replaces.")
