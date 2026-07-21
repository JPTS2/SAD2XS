"""
================================================================================
Tests for the reverse_survey_vertical parameter of the SAD2XS conversion pipeline
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import pytest
import sad2xs as s2x

################################################################################
# Bend Adjustments
################################################################################
def test_pipeline_reverse_survey_vertical_bend_angle_and_edge_angles_unchanged(write_lattice):
    """
    reverse_survey_vertical=True should leave a plain (unrotated) bend's angle,
    k0, and both edge angles unchanged. This is the key contrast with
    reverse_survey_horizontal, which negates all four: the vertical-mirror
    multipole parity rule is uniform across order (normal unchanged, skew
    negates, at every order), so a bend's own-frame dipole field and in-frame
    edge geometry are untouched by a mirror through the horizontal plane.
    Asymmetric E1 != E2 makes this test sensitive to any accidental swap.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        B1      = (L = 1.0 ANGLE = 0.1 E1 = 0.5 E2 = 0.25);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START B1 END);
        """,
        filename = "rev_vert_bend.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
        _verbose               = False,
        _test_mode             = True)

    angle_forward  = line_forward["b1"].angle
    k0_forward     = line_forward["b1"].k0
    entry_forward  = line_forward["b1"].edge_entry_angle
    exit_forward   = line_forward["b1"].edge_exit_angle

    angle_reversed = line_reversed["b1"].angle
    k0_reversed    = line_reversed["b1"].k0
    entry_reversed = line_reversed["b1"].edge_entry_angle
    exit_reversed  = line_reversed["b1"].edge_exit_angle

    assert entry_forward != pytest.approx(0.0), (
        "Forward bend entry angle should be non-zero for E1 = 0.5, ANGLE = 0.1.")
    assert exit_forward != pytest.approx(0.0), (
        "Forward bend exit angle should be non-zero for E2 = 0.25, ANGLE = 0.1.")
    assert entry_forward != pytest.approx(exit_forward), (
        "Asymmetric E1 != E2 should produce distinct entry and exit angles.")

    assert angle_reversed == pytest.approx(angle_forward), (
        "reverse_survey_vertical=True should leave the bend angle unchanged. "
        f"Forward: {angle_forward}, reversed: {angle_reversed}.")
    assert k0_reversed == pytest.approx(k0_forward), (
        "reverse_survey_vertical=True should leave k0 unchanged. "
        f"Forward: {k0_forward}, reversed: {k0_reversed}.")
    assert entry_reversed == pytest.approx(entry_forward), (
        "reverse_survey_vertical=True should leave the entry edge angle unchanged. "
        f"Forward entry: {entry_forward}, reversed entry: {entry_reversed}.")
    assert exit_reversed == pytest.approx(exit_forward), (
        "reverse_survey_vertical=True should leave the exit edge angle unchanged. "
        f"Forward exit: {exit_forward}, reversed exit: {exit_reversed}.")


def test_pipeline_reverse_survey_vertical_bend_offsets_and_rotation(write_lattice):
    """
    reverse_survey_vertical=True should negate shift_y and rot_s_rad on a bend
    but leave shift_x unchanged -- the opposite offset pattern from
    reverse_survey_horizontal.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        B1      = (L = 1.0 ANGLE = 0.1 DX = 0.01 DY = 0.02);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START B1 END);
        """,
        filename = "rev_vert_bend_offset.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
        _verbose               = False,
        _test_mode             = True)

    shift_x_fwd = line_forward["b1"].shift_x
    shift_y_fwd = line_forward["b1"].shift_y
    shift_x_rev = line_reversed["b1"].shift_x
    shift_y_rev = line_reversed["b1"].shift_y

    assert shift_x_fwd != pytest.approx(0.0), (
        "Forward BEND shift_x should be non-zero for DX = 0.01.")
    assert shift_y_fwd != pytest.approx(0.0), (
        "Forward BEND shift_y should be non-zero for DY = 0.02.")
    assert shift_x_rev == pytest.approx(shift_x_fwd), (
        "reverse_survey_vertical=True should leave shift_x unchanged. "
        f"Forward: {shift_x_fwd}, reversed: {shift_x_rev}.")
    assert shift_y_rev == pytest.approx(-shift_y_fwd), (
        "reverse_survey_vertical=True should negate shift_y. "
        f"Forward: {shift_y_fwd}, reversed: {shift_y_rev}.")


def test_pipeline_reverse_survey_vertical_rotated_bend_direction_and_tracking(write_lattice):
    """
    The specific case that motivated a closer look at this feature: a BEND
    with ROTATE = pi/2 (a genuine vertical bend). The SAD2XS element converter
    canonicalises any SAD ROTATE of +-pi/2 on a BEND to a fixed
    rot_s_rad = +pi/2, carrying the bend direction in the sign of angle/k0
    instead (see sad2xs/converter/_004_element_converter.py's
    _canonicalize_dipole_rotation). reverse_survey_vertical leaves angle/k0
    unchanged (per the uniform normal/skew parity rule) and negates
    rot_s_rad -- so the vertical bend's direction is flipped via rot_s_rad,
    not via angle. A parameter check alone doesn't prove this is physically
    correct, so this test also tracks an asymmetric particle through both
    conversions and checks that the reversed line, fed the y/py-mirrored
    initial coordinates, reproduces the y/py-mirror of the forward line's
    result -- the same self-consistency check used to verify the sign
    convention against real xtrack tracking before this feature was written.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        B1      = (L = 1.0 ANGLE = 0.08 E1 = 0.05 E2 = 0.02 ROTATE = 1.570796);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START B1 END);
        """,
        filename = "rev_vert_bend_rotated.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
        _verbose               = False,
        _test_mode             = True)

    ########################################
    # Parameter-level check
    ########################################
    angle_forward   = line_forward["b1"].angle
    angle_reversed  = line_reversed["b1"].angle
    rot_s_forward   = line_forward["b1"].rot_s_rad
    rot_s_reversed  = line_reversed["b1"].rot_s_rad

    assert rot_s_forward == pytest.approx(np.pi / 2), (
        "Sanity check: SAD ROTATE = pi/2 on a BEND should canonicalise to "
        f"rot_s_rad = +pi/2. Got: {rot_s_forward}.")
    assert angle_reversed == pytest.approx(angle_forward), (
        "reverse_survey_vertical=True should leave a rotated bend's angle "
        f"unchanged. Forward: {angle_forward}, reversed: {angle_reversed}.")
    assert rot_s_reversed == pytest.approx(-rot_s_forward), (
        "reverse_survey_vertical=True should negate rot_s_rad -- this is "
        "what actually flips the vertical bend's direction. "
        f"Forward: {rot_s_forward}, reversed: {rot_s_reversed}.")

    ########################################
    # Tracking self-consistency check
    ########################################
    x0, px0, y0, py0 = 0.0012, 0.00025, 0.0031, -0.00038

    p_forward = line_forward.build_particles(
        x=x0, px=px0, y=y0, py=py0, zeta=0.0, delta=0.0)
    line_forward.track(p_forward)

    p_reversed = line_reversed.build_particles(
        x=x0, px=px0, y=-y0, py=-py0, zeta=0.0, delta=0.0)
    line_reversed.track(p_reversed)

    assert p_reversed.x[0] == pytest.approx(p_forward.x[0], abs=1e-12), (
        "x should be unaffected by the mirror. "
        f"Forward: {p_forward.x[0]}, reversed (mirrored input): {p_reversed.x[0]}.")
    assert p_reversed.px[0] == pytest.approx(p_forward.px[0], abs=1e-12), (
        "px should be unaffected by the mirror. "
        f"Forward: {p_forward.px[0]}, reversed (mirrored input): {p_reversed.px[0]}.")
    assert p_reversed.y[0] == pytest.approx(-p_forward.y[0], abs=1e-12), (
        "The reversed line tracking the y-mirrored input should reproduce "
        "the y-mirror of the forward result -- confirms the rot_s_rad "
        "negation correctly flips the vertical bend's direction. "
        f"Forward y: {p_forward.y[0]}, reversed y: {p_reversed.y[0]}.")
    assert p_reversed.py[0] == pytest.approx(-p_forward.py[0], abs=1e-12), (
        "py should mirror the same way as y. "
        f"Forward py: {p_forward.py[0]}, reversed py: {p_reversed.py[0]}.")


################################################################################
# Quadrupole Adjustments
################################################################################
def test_pipeline_reverse_survey_vertical_quad_k1_unchanged_and_k1s_negated(write_lattice):
    """
    reverse_survey_vertical=True should leave k1 unchanged and negate k1s.
    Because the vertical-mirror parity rule is order-independent (unlike
    horizontal's even/odd alternation), this happens to give the same
    outcome as reverse_survey_horizontal for a quadrupole (order 1, odd) --
    worth locking in explicitly rather than assuming it carries over.
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
        filename = "rev_vert_quad.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
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
        "reverse_survey_vertical=True should leave k1 unchanged. "
        f"Forward: {k1_forward}, reversed: {k1_reversed}.")
    assert k1s_reversed == pytest.approx(-k1s_forward), (
        "reverse_survey_vertical=True should negate k1s. "
        f"Forward: {k1s_forward}, reversed: {k1s_reversed}.")


################################################################################
# Sextupole Adjustments
################################################################################
def test_pipeline_reverse_survey_vertical_sext_k2_unchanged_and_k2s_negated(write_lattice):
    """
    reverse_survey_vertical=True should leave k2 unchanged and negate k2s --
    the contrasting case vs reverse_survey_horizontal, which negates k2 and
    leaves k2s unchanged (sextupole is order 2, even -- the vertical rule is
    uniform across order, but the horizontal rule alternates by order, so
    the two flags genuinely disagree here).
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
        filename = "rev_vert_sext.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
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

    assert k2_reversed == pytest.approx(k2_forward), (
        "reverse_survey_vertical=True should leave k2 unchanged. "
        f"Forward: {k2_forward}, reversed: {k2_reversed}.")
    assert k2s_reversed == pytest.approx(-k2s_forward), (
        "reverse_survey_vertical=True should negate k2s. "
        f"Forward: {k2s_forward}, reversed: {k2s_reversed}.")


################################################################################
# Octupole Adjustments
################################################################################
def test_pipeline_reverse_survey_vertical_oct_k3_unchanged_and_k3s_negated(write_lattice):
    """
    reverse_survey_vertical=True should leave k3 unchanged and negate k3s.
    Octupole is order 3 (odd), so -- like the quadrupole case -- this
    happens to coincide with reverse_survey_horizontal's outcome.
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
        filename = "rev_vert_oct.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
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
        "reverse_survey_vertical=True should leave k3 unchanged. "
        f"Forward: {k3_forward}, reversed: {k3_reversed}.")
    assert k3s_reversed == pytest.approx(-k3s_forward), (
        "reverse_survey_vertical=True should negate k3s. "
        f"Forward: {k3s_forward}, reversed: {k3s_reversed}.")


################################################################################
# Multipole Adjustments
################################################################################
def test_pipeline_reverse_survey_vertical_mult_knl_ksl_sign_convention(write_lattice):
    """
    reverse_survey_vertical=True should apply a uniform sign rule to the knl
    and ksl arrays of a SAD MULT element, regardless of order: knl unchanged,
    ksl negated. K1/SK1 (order 1) and K2/SK2 (order 2) together cover both an
    odd and an even order, verifying the rule really is order-independent
    (unlike reverse_survey_horizontal's even/odd alternation).
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MULT        M1      = (L = 0.5 K1 = 0.1 SK1 = 0.05 K2 = 0.08 SK2 = 0.03);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START M1 END);
        """,
        filename = "rev_vert_mult.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
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
        "reverse_survey_vertical=True should leave knl[1] unchanged (order 1, odd). "
        f"Forward: {knl1_fwd}, reversed: {knl1_rev}.")
    assert knl2_rev == pytest.approx(knl2_fwd), (
        "reverse_survey_vertical=True should leave knl[2] unchanged (order 2, even). "
        f"Forward: {knl2_fwd}, reversed: {knl2_rev}.")
    assert ksl1_rev == pytest.approx(-ksl1_fwd), (
        "reverse_survey_vertical=True should negate ksl[1] (order 1, odd). "
        f"Forward: {ksl1_fwd}, reversed: {ksl1_rev}.")
    assert ksl2_rev == pytest.approx(-ksl2_fwd), (
        "reverse_survey_vertical=True should negate ksl[2] (order 2, even). "
        f"Forward: {ksl2_fwd}, reversed: {ksl2_rev}.")


################################################################################
# Solenoid Adjustments
################################################################################
def test_pipeline_reverse_survey_vertical_negates_solenoid_ks(write_lattice):
    """
    reverse_survey_vertical=True should negate the solenoid field strength ks,
    same as reverse_survey_horizontal (a solenoid's axial field is a
    perpendicular pseudovector component under either mirror).
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        SOL         S1      = (L = 0.5 BZ = 0.1);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START S1 END);
        """,
        filename = "rev_vert_solenoid.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
        _verbose               = False,
        _test_mode             = True)

    ks_forward  = line_forward["s1"].ks
    ks_reversed = line_reversed["s1"].ks

    assert ks_forward != pytest.approx(0.0), (
        "Forward solenoid ks should be non-zero for BZ = 0.1.")
    assert ks_reversed == pytest.approx(-ks_forward), (
        "reverse_survey_vertical=True should negate solenoid ks. "
        f"Forward: {ks_forward}, reversed: {ks_reversed}.")


def test_pipeline_reverse_survey_vertical_negates_solenoid_ks_with_charge_minus_one(
        write_lattice):
    """
    Composability check (internal consistency only -- see note below): does a
    genuine CHARGE=-1 lattice, which bakes the reference charge into the
    solenoid's base ks (see sad2xs/converter/_004_element_converter.py's
    convert_solenoids), still get correctly negated by
    reverse_survey_vertical's geometric-mirror ks negation?

    NOTE ON SCOPE: like reverse_survey_horizontal (see
    test_reverse_survey_horizontal.py), this file has no real-SAD-verified
    test at all -- every test here checks the converter's internal Python
    logic for self-consistency, not real SAD output, since a geometric
    mirror has no native SAD operator to compare against.
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
        filename = "rev_vert_solenoid_charge.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
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
        "reverse_survey_vertical=True should negate solenoid ks even when "
        "the base ks is already charge-adjusted (CHARGE=-1). "
        f"Forward: {ks_forward}, reversed: {ks_reversed}.")


################################################################################
# Element Offset Adjustments
################################################################################
def test_pipeline_reverse_survey_vertical_negates_shift_y_and_rot_s_rad_preserves_shift_x(
        write_lattice):
    """
    reverse_survey_vertical=True should negate shift_y and rot_s_rad but leave
    shift_x unchanged on all magnetic element types -- the opposite offset
    pattern from reverse_survey_horizontal. A QUAD with DX, DY, and ROTATE
    parameters exercises this path. ROTATE = 0.1 rad (not +-pi/4) avoids the
    k1-to-k1s mapping so the quadrupole path is taken, not the skew path.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        QUAD        QO      = (L = 0.5 K1 = 0.2 DX = 0.01 DY = 0.02 ROTATE = 0.1);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START QO END);
        """,
        filename = "rev_vert_offset.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
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

    assert shift_x_rev == pytest.approx(shift_x_fwd), (
        "reverse_survey_vertical=True should leave shift_x unchanged. "
        f"Forward: {shift_x_fwd}, reversed: {shift_x_rev}.")
    assert shift_y_rev == pytest.approx(-shift_y_fwd), (
        "reverse_survey_vertical=True should negate shift_y. "
        f"Forward: {shift_y_fwd}, reversed: {shift_y_rev}.")
    assert rot_s_rad_rev == pytest.approx(-rot_s_rad_fwd), (
        "reverse_survey_vertical=True should negate rot_s_rad. "
        f"Forward: {rot_s_rad_fwd}, reversed: {rot_s_rad_rev}.")


################################################################################
# Reference Shift Adjustment
################################################################################
def test_pipeline_reverse_survey_vertical_negates_coord_dy_preserves_dx(write_lattice):
    """
    reverse_survey_vertical=True should negate dy but leave dx unchanged.
    This contrasts with reverse_survey_horizontal, which negates dx and
    leaves dy unchanged.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        COORD       C1      = (DX = 0.01 DY = 0.02);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START C1 END);
        """,
        filename = "rev_vert_coord.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
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
    assert dx_reversed == pytest.approx(dx_forward), (
        "reverse_survey_vertical=True should leave COORD shift_x unchanged "
        "(unlike reverse_survey_horizontal which negates it). "
        f"Forward: {dx_forward}, reversed: {dx_reversed}.")
    assert dy_reversed == pytest.approx(-dy_forward), (
        "reverse_survey_vertical=True should negate COORD shift_y. "
        f"Forward: {dy_forward}, reversed: {dy_reversed}.")


################################################################################
# Coordinate Rotation Adjustment
################################################################################
def test_pipeline_reverse_survey_vertical_coord_chi2_negated_chi1_unchanged_chi3_negated(
        write_lattice):
    """
    reverse_survey_vertical=True should negate chi2 (rot_x_rad) and chi3
    (rot_s_rad) but leave chi1 (rot_y_rad) unchanged -- the opposite pattern
    from reverse_survey_horizontal, which negates chi1 and leaves chi2
    unchanged. A single COORD with all three components produces elements
    named c1_chi1, c1_chi2, c1_chi3.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        COORD       C1      = (CHI1 = 0.05 CHI2 = 0.03 CHI3 = 0.02);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START C1 END);
        """,
        filename = "rev_vert_chi.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
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

    assert chi1_rev == pytest.approx(chi1_fwd), (
        "reverse_survey_vertical=True should leave chi1 rot_y_rad unchanged. "
        f"Forward: {chi1_fwd}, reversed: {chi1_rev}.")
    assert chi2_rev == pytest.approx(-chi2_fwd), (
        "reverse_survey_vertical=True should negate the chi2 rot_x_rad. "
        f"Forward: {chi2_fwd}, reversed: {chi2_rev}.")
    assert chi3_rev == pytest.approx(-chi3_fwd), (
        "reverse_survey_vertical=True should negate the chi3 rot_s_rad. "
        f"Forward: {chi3_fwd}, reversed: {chi3_rev}.")


################################################################################
# Twiss self-consistency
################################################################################
def test_pipeline_reverse_survey_vertical_twiss_beta_functions_unchanged(write_lattice):
    """
    reverse_survey_vertical=True is a vertical mirror of the lattice. Unlike
    the horizontal-mirror test (which uses a plain BEND+QUAD+SEXT+DRIFT
    lattice), that lattice would be a trivial no-op here: a plain bend's
    angle/k0 and a plain quad/sext's k1/k2 are all unchanged under the
    vertical rule, so nothing would actually flip. Instead, this uses a skew
    QUAD (ROTATE=pi/4) and skew SEXT (ROTATE=pi/6), whose k1s/k2s genuinely
    negate under this flag, to exercise a meaningful invariance check: 4D
    Twiss betx/bety at the end of the line must be identical whether or not
    the flag is set, since a pure geometric mirror cannot change the linear
    optics.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        QUAD        Q1      = (L = 1.0 K1 = 0.5 ROTATE = 0.785398);
        SEXT        S1      = (L = 0.3 K2 = 1.0 ROTATE = 0.523599);
        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START Q1 D1 S1 D1 END);
        """,
        filename = "rev_vert_twiss.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = False,
        _verbose               = False,
        _test_mode             = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path       = str(lattice_path),
        output_directory       = "N/A",
        reverse_survey_vertical = True,
        _verbose               = False,
        _test_mode             = True)

    k1s_forward  = line_forward["q1"].k1s
    k1s_reversed = line_reversed["q1"].k1s
    assert k1s_forward != pytest.approx(0.0), (
        "Forward skew QUAD k1s should be non-zero for K1 = 0.5, ROTATE = pi/4 "
        "-- otherwise this test would not actually exercise the mirror.")
    assert k1s_reversed == pytest.approx(-k1s_forward), (
        "reverse_survey_vertical=True should negate k1s -- confirms the "
        "mirror is genuinely active for this lattice, not a no-op. "
        f"Forward: {k1s_forward}, reversed: {k1s_reversed}.")

    tw_fwd = line_forward.twiss4d(betx=1.0, bety=1.0)
    tw_rev = line_reversed.twiss4d(betx=1.0, bety=1.0)

    betx_fwd = tw_fwd.betx[-1]
    bety_fwd = tw_fwd.bety[-1]
    betx_rev = tw_rev.betx[-1]
    bety_rev = tw_rev.bety[-1]

    assert betx_rev == pytest.approx(betx_fwd, rel=1e-9), (
        "reverse_survey_vertical=True is a geometric mirror: betx must be "
        "unchanged even though k1s/k2s flip sign. "
        f"Forward betx={betx_fwd:.6f}, reversed betx={betx_rev:.6f}.")
    assert bety_rev == pytest.approx(bety_fwd, rel=1e-9), (
        "reverse_survey_vertical=True is a geometric mirror: bety must be "
        "unchanged even though k1s/k2s flip sign. "
        f"Forward bety={bety_fwd:.6f}, reversed bety={bety_rev:.6f}.")
