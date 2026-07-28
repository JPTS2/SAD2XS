"""
================================================================================
Tests for the reverse_element_order parameter of the SAD2XS conversion pipeline
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-24
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import os

import numpy as np
import pytest
import xtrack as xt

import sad2xs as s2x
from sad2xs.sad_helpers import track_sad, rebuild_sad_lattice

################################################################################
# Default Behaviour
################################################################################
def test_pipeline_reverse_element_order_false_preserves_forward_order(write_lattice):
    """
    When reverse_element_order is not set, element names should appear in the
    same order as the SAD LINE definition.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0)
                    D2      = (L = 2.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 D2 END);
        """,
        filename = "rev_elem_order_default.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        _verbose              = False,
        _test_mode            = True)

    assert line.element_names == ["start", "d1", "d2", "end"], (
        "Without reverse_element_order, element names should match the SAD LINE "
        f"definition order. Got: {line.element_names}.")


################################################################################
# Element Order Reversal
################################################################################
def test_pipeline_reverse_element_order_reverses_element_sequence(write_lattice):
    """
    reverse_element_order=True should produce a line whose element sequence is
    the exact reverse of the SAD LINE definition.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0)
                    D2      = (L = 2.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 D2 END);
        """,
        filename = "rev_elem_order_reversed.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    assert list(line.element_names) == ["end", "d2", "d1", "start"], (
        "reverse_element_order=True should reverse the SAD LINE element sequence. "
        f"Got: {list(line.element_names)}.")


def test_pipeline_reverse_element_order_preserves_element_set(write_lattice):
    """
    reverse_element_order=True should not add or remove any elements — the set
    of element names should be identical to the forward conversion.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0)
                    D2      = (L = 2.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 D2 END);
        """,
        filename = "rev_elem_order_set.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    assert set(line.element_names) == {"start", "d1", "d2", "end"}, (
        "reverse_element_order=True should preserve the complete element set. "
        f"Got: {set(line.element_names)}.")


################################################################################
# Bend Edge Angle Adjustment
################################################################################
def test_pipeline_reverse_element_order_swaps_bend_edge_angles(write_lattice):
    """
    reverse_element_order=True should swap the entry and exit edge angles of
    each bend. SAD E1 and E2 map to edge_entry_angle = E1*ANGLE and
    edge_exit_angle = E2*ANGLE respectively.
    With ANGLE=0.1, E1=0.5, E2=0.25:
      forward:  entry = 0.05, exit = 0.025
      reversed: entry = 0.025, exit = 0.05
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        B1      = (L = 1.0 ANGLE = 0.1 E1 = 0.5 E2 = 0.25);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START B1 END);
        """,
        filename = "rev_elem_order_bend_edges.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    assert line["b1"].edge_entry_angle == pytest.approx(0.025), (
        "After reverse_element_order=True, bend entry edge angle should be the "
        "original exit angle (E2*ANGLE = 0.25*0.1 = 0.025). "
        f"""Got: {line["b1"].edge_entry_angle}.""")
    assert line["b1"].edge_exit_angle == pytest.approx(0.05), (
        "After reverse_element_order=True, bend exit edge angle should be the "
        "original entry angle (E1*ANGLE = 0.5*0.1 = 0.05). "
        f"""Got: {line["b1"].edge_exit_angle}.""")


################################################################################
# Bend Fringe Field Adjustment
################################################################################
def test_pipeline_reverse_element_order_swaps_bend_fint_hgap(write_lattice):
    """
    reverse_element_order=True should swap the entry and exit fringe fields
    (fint/hgap) of each bend, exactly as it swaps edge_entry_angle/
    edge_exit_angle. SAD F1/FB1/FB2 map to edge_entry_fint = F1+FB1,
    edge_exit_fint = F1+FB2 (hgap is a fixed 1/12 at both edges).
    With F1=0.24, FB1=0.12, FB2=0.0:
      forward:  entry fint = 0.36, exit fint = 0.24
      reversed: entry fint = 0.24, exit fint = 0.36
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        B1      = (L = 1.0 ANGLE = 0.1 FRINGE = 1 F1 = 0.24 FB1 = 0.12 FB2 = 0.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START B1 END);
        """,
        filename = "rev_elem_order_bend_fringe.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path         = str(lattice_path),
        output_directory         = "N/A",
        reverse_element_order    = True,
        _import_sad_bend_fringes = True,
        _verbose                 = False,
        _test_mode               = True)

    expected_reversed_entry = 0.24
    expected_reversed_exit  = 0.36

    assert line["b1"].edge_entry_fint == pytest.approx(expected_reversed_entry), (
        "After reverse_element_order=True, bend entry fint should be the "
        "original exit value (F1+FB2 = 0.24). "
        f"""Got: {line["b1"].edge_entry_fint}.""")
    assert line["b1"].edge_entry_hgap == pytest.approx(1 / 12), (
        "Bend entry hgap should stay the fixed 1/12 fringe constant. "
        f"""Got: {line["b1"].edge_entry_hgap}.""")
    assert line["b1"].edge_exit_fint == pytest.approx(expected_reversed_exit), (
        "After reverse_element_order=True, bend exit fint should be the "
        "original entry value (F1+FB1 = 0.36). "
        f"""Got: {line["b1"].edge_exit_fint}.""")
    assert line["b1"].edge_exit_hgap == pytest.approx(1 / 12), (
        "Bend exit hgap should stay the fixed 1/12 fringe constant. "
        f"""Got: {line["b1"].edge_exit_hgap}.""")


################################################################################
# Reference Shift Adjustment
################################################################################
def test_pipeline_reverse_element_order_preserves_coord_dx_and_dy(write_lattice):
    """
    reverse_element_order=True must NOT negate the shift_x / shift_y of a
    Translation produced by a SAD COORD element.

    A COORD offset is a geometric property of the beampipe at a fixed physical
    location — it does not change sign when the beam traverses the lattice in
    the opposite direction.  This is in contrast to the solenoid GEO reference-
    frame translations (named *_dxy), which are entry/exit shifts that must swap
    sign when element order is reversed.

    SAD ground truth (verified with LINE TESTREV = (-TEST)):
      Forward  SAD, COORD(DX=0.001), DRIFT: final x = -0.001
      Reversed SAD, COORD(DX=0.001), DRIFT: final x = -0.001  (identical)

    The Xsuite Translation convention is shift_x is SUBTRACTED from x, so
    Translation(shift_x=+0.001) moves x to -0.001.  Negating shift_x in the
    reversed line would give Translation(shift_x=-0.001) → x=+0.001, which
    contradicts SAD.  The shift must therefore be left unchanged.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        COORD       C1      = (DX = 0.01 DY = 0.02);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START C1 END);
        """,
        filename = "rev_elem_order_coord.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = False,
        _verbose              = False,
        _test_mode            = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    dx_forward  = line_forward["c1"].shift_x
    dy_forward  = line_forward["c1"].shift_y
    dx_reversed = line_reversed["c1"].shift_x
    dy_reversed = line_reversed["c1"].shift_y

    assert dx_forward != pytest.approx(0.0), (
        "Forward COORD shift_x should be non-zero for DX = 0.01.")
    assert dy_forward != pytest.approx(0.0), (
        "Forward COORD shift_y should be non-zero for DY = 0.02.")
    assert dx_reversed == pytest.approx(dx_forward), (
        "reverse_element_order=True must NOT negate COORD shift_x: a beampipe "
        "offset is a geometric property that does not flip under line reversal. "
        f"Forward: {dx_forward}, reversed: {dx_reversed}.")
    assert dy_reversed == pytest.approx(dy_forward), (
        "reverse_element_order=True must NOT negate COORD shift_y: a beampipe "
        "offset is a geometric property that does not flip under line reversal. "
        f"Forward: {dy_forward}, reversed: {dy_reversed}.")


################################################################################
# Solenoid Strength Adjustment
################################################################################
def test_pipeline_reverse_element_order_negates_solenoid_ks(write_lattice):
    """
    reverse_element_order=True should negate the solenoid field strength ks.
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
        filename = "rev_elem_order_solenoid.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = False,
        _verbose              = False,
        _test_mode            = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    ks_forward  = line_forward["s1"].ks
    ks_reversed = line_reversed["s1"].ks

    assert ks_forward != pytest.approx(0.0), (
        "Forward solenoid ks should be non-zero for BZ = 0.1.")
    assert ks_reversed == pytest.approx(-ks_forward), (
        "reverse_element_order=True should negate solenoid ks. "
        f"Forward: {ks_forward}, reversed: {ks_reversed}.")


################################################################################
# Parameter Invariance: elements that must NOT change under reversal
################################################################################
def test_pipeline_reverse_element_order_does_not_change_quad_k1(write_lattice):
    """
    Quadrupole k1 must be unchanged by reverse_element_order: the focussing
    strength of a quad is symmetric under beam direction reversal.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        QUAD        Q1      = (L = 1.0 K1 = 0.2);
        MARK        START   = ()
                    END     = ();
        LINE        TEST_LINE = (START Q1 END);
        """,
        filename = "rev_quad_k1.sad")

    line_forward  = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = False,
        _verbose              = False,
        _test_mode            = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    assert line_reversed["q1"].k1 == pytest.approx(line_forward["q1"].k1), (
        "Quadrupole k1 should be unchanged by reverse_element_order. "
        f"""Forward: {line_forward["q1"].k1}, reversed: {line_reversed["q1"].k1}.""")


def test_pipeline_reverse_element_order_does_not_change_sext_k2(write_lattice):
    """
    Sextupole k2 must be unchanged by reverse_element_order.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        SEXT        S1      = (L = 0.5 K2 = 1.0);
        MARK        START   = ()
                    END     = ();
        LINE        TEST_LINE = (START S1 END);
        """,
        filename = "rev_sext_k2.sad")

    line_forward  = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = False,
        _verbose              = False,
        _test_mode            = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    assert line_reversed["s1"].k2 == pytest.approx(line_forward["s1"].k2), (
        "Sextupole k2 should be unchanged by reverse_element_order. "
        f"""Forward: {line_forward["s1"].k2}, reversed: {line_reversed["s1"].k2}.""")


def test_pipeline_reverse_element_order_does_not_change_oct_k3(write_lattice):
    """
    Octupole k3 must be unchanged by reverse_element_order.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        OCT         O1      = (L = 0.5 K3 = 5.0);
        MARK        START   = ()
                    END     = ();
        LINE        TEST_LINE = (START O1 END);
        """,
        filename = "rev_oct_k3.sad")

    line_forward  = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = False,
        _verbose              = False,
        _test_mode            = True)

    line_reversed = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lattice_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    assert line_reversed["o1"].k3 == pytest.approx(line_forward["o1"].k3), (
        "Octupole k3 should be unchanged by reverse_element_order. "
        f"""Forward: {line_forward["o1"].k3}, reversed: {line_reversed["o1"].k3}.""")


################################################################################
# Physics Validation Against SAD
################################################################################
def test_pipeline_reverse_element_order_tracking_matches_sad_reversed_line(tmp_path):
    """
    Xsuite tracking through a line converted with reverse_element_order=True
    should match SAD tracking through the native SAD-reversed line
    (LINE TESTREV = (-TEST)).

    Two correctors with different K0 strengths (C1=0.01, C2=0.02) are separated
    by a 1 m drift. The order in which kicks are applied relative to the drift
    determines the final x coordinate, so the forward and reversed lines give
    distinct x values. The Xsuite reversal must reproduce what SAD computes for
    the reversed line, not merely negate the forward result.
    """
    lattice_content = (
        "MOMENTUM = 1.0 GEV;\n"
        "BEND C1 = (K0=0.01);\n"
        "BEND C2 = (K0=0.02);\n"
        "DRIFT D1 = (L=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST    = (START C1 D1 C2 END);\n"
        "LINE TESTREV = (-TEST);\n")

    lat_path = tmp_path / "rev_physics.sad"
    lat_path.write_text(lattice_content)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_sad = track_sad(
            lattice_filepath = lat_path.name,
            line_name        = "TESTREV",
            x_init           = np.array([0.0]),
            px_init          = np.array([0.0]),
            y_init           = np.array([0.0]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)
    finally:
        os.chdir(cwd)

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lat_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    p = line.build_particles(x=0.0, px=0.0, y=0.0, py=0.0, zeta=0.0, delta=0.0)
    line.track(p)

    assert p.x[0] == pytest.approx(r_sad["x"][0], rel=1e-3), (
        f"Xsuite reversed line x should match SAD reversed line x. "
        f"""Xsuite: {p.x[0]}, SAD: {r_sad["x"][0]}.""")
    assert p.px[0] == pytest.approx(r_sad["px"][0], rel=1e-3), (
        f"Xsuite reversed line px should match SAD reversed line px. "
        f"""Xsuite: {p.px[0]}, SAD: {r_sad["px"][0]}.""")


def test_pipeline_reverse_element_order_bend_poleface_angles_physics_matches_sad(tmp_path):
    """
    A bend with asymmetric poleface angles (E1 ≠ E2) changes the vertical
    focusing depending on which face the beam enters first. Reversing the line
    swaps entry and exit faces: the Xsuite reversal (edge_entry_angle ↔
    edge_exit_angle) must reproduce SAD tracking through the native reversed
    line.
    """
    lattice_content = (
        "MOMENTUM = 1.0 GEV;\n"
        "BEND B1 = (L=1.0 ANGLE=0.05 E1=0.05 E2=0.0);\n"
        "DRIFT D1 = (L=0.5);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST    = (START D1 B1 D1 END);\n"
        "LINE TESTREV = (-TEST);\n")

    lat_path = tmp_path / "rev_poleface.sad"
    lat_path.write_text(lattice_content)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_sad = track_sad(
            lattice_filepath = lat_path.name,
            line_name        = "TESTREV",
            x_init           = np.array([0.0]),
            px_init          = np.array([0.0]),
            y_init           = np.array([1e-3]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)
    finally:
        os.chdir(cwd)

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lat_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    p = line.build_particles(x=0.0, px=0.0, y=1e-3, py=0.0, zeta=0.0, delta=0.0)
    line.track(p)

    assert p.y[0] == pytest.approx(r_sad["y"][0], rel=1e-3), (
        f"Xsuite reversed bend py should match SAD reversed line py. "
        f"""Xsuite: {p.y[0]}, SAD: {r_sad["y"][0]}.""")
    assert p.py[0] == pytest.approx(r_sad["py"][0], abs=1e-9), (
        f"Xsuite reversed bend py should match SAD reversed line py. "
        f"""Xsuite: {p.py[0]}, SAD: {r_sad["py"][0]}.""")


def test_pipeline_reverse_element_order_corrector_fringe_physics_matches_sad(
        tmp_path):
    """
    A K0-only corrector (ANGLE=0 bend) with asymmetric soft-edge fringe
    (FB1 != FB2) changes vertical focusing depending on which face the beam
    enters first, exactly like edge_entry_angle/edge_exit_angle for a bent
    magnet. Reversing the line swaps entry and exit fringe fields: the
    Xsuite reversal (edge_entry_fint/hgap <-> edge_exit_fint/hgap) must
    reproduce SAD tracking through the native reversed line.
    """
    lattice_content = (
        "MOMENTUM = 1.0 GEV;\n"
        "BEND C1 = (L=0.4 K0=0.03 FRINGE=1 FB1=0.08 FB2=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST    = (START C1 END);\n"
        "LINE TESTREV = (-TEST);\n")

    lat_path = tmp_path / "rev_corrector_fringe.sad"
    lat_path.write_text(lattice_content)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_sad = track_sad(
            lattice_filepath = lat_path.name,
            line_name        = "TESTREV",
            x_init           = np.array([0.0]),
            px_init          = np.array([0.0]),
            y_init           = np.array([0.003]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)
    finally:
        os.chdir(cwd)

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path         = str(lat_path),
        output_directory         = "N/A",
        reverse_element_order    = True,
        _import_sad_bend_fringes = True,
        _verbose                 = False,
        _test_mode               = True)

    p = line.build_particles(x=0.0, px=0.0, y=0.003, py=0.0, zeta=0.0, delta=0.0)
    line.track(p)

    assert p.y[0] == pytest.approx(r_sad["y"][0], rel=1e-3), (
        f"Xsuite reversed corrector y should match SAD reversed line y. "
        f"""Xsuite: {p.y[0]}, SAD: {r_sad["y"][0]}.""")
    assert p.py[0] == pytest.approx(r_sad["py"][0], rel=1e-3), (
        f"Xsuite reversed corrector py should match SAD reversed line py. "
        f"""Xsuite: {p.py[0]}, SAD: {r_sad["py"][0]}.""")


def test_pipeline_reverse_element_order_solenoid_physics_matches_sad(tmp_path):
    """
    Reversing a bound solenoid line negates ks and correctly handles the GEO
    reference-frame translations produced by the SAD GEO mechanism.

    SAD computes GEO reference shifts at runtime (Twiss/INS), so the lattice
    must be rebuilt before Xsuite conversion to bake those shifts in as explicit
    Translation elements.  We then verify that:

    1. Xsuite reversed matches SAD forward (orbit should be on-axis: x≈0).
    2. Xsuite reversed matches SAD reversed (coupling direction: sign of y).

    A DX=0.001 offset is included to exercise the sol_in_dxy / sol_out_dxy
    Translation elements that are produced by the GEO mechanism, ensuring that
    the reversal logic handles them correctly.
    """
    lattice_content = """\
MOMENTUM    = 1.0 GEV;

DRIFT       SOL_DRIFT   = (L = 0.5);
SOL         SOL_IN      = (BZ = 0.5 BOUND = 1 GEO = 1 DX = 0.001)
            SOL_OUT     = (BZ = 0.5 BOUND = 1);

MARK        START       = ()
            END         = ();

LINE        TEST        = (START SOL_IN SOL_DRIFT SOL_OUT END);
LINE        TESTREV     = (-TEST);
"""

    lat_path     = tmp_path / "rev_solenoid.sad"
    rebuilt_name = "rev_solenoid_rebuilt.sad"
    lat_path.write_text(lattice_content)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        rebuild_sad_lattice(
            lattice_filepath = lat_path.name,
            line_name        = "TEST",
            output_filepath  = rebuilt_name)

        r_sad = track_sad(
            lattice_filepath = lat_path.name,
            line_name        = "TESTREV",
            x_init           = np.array([1e-4]),
            px_init          = np.array([0.0]),
            y_init           = np.array([0.0]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)
    finally:
        os.chdir(cwd)

    rebuilt_path = tmp_path / rebuilt_name
    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(rebuilt_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    p = line.build_particles(x=1e-4, px=0.0, y=0.0, py=0.0, zeta=0.0, delta=0.0)
    line.track(p)

    assert p.y[0] == pytest.approx(r_sad["y"][0], abs=1e-9), (
        f"Xsuite reversed solenoid y should match SAD reversed line y. "
        f"""Xsuite: {p.y[0]}, SAD: {r_sad["y"][0]}.""")
    assert p.py[0] == pytest.approx(r_sad["py"][0], abs=1e-9), (
        f"Xsuite reversed solenoid py should match SAD reversed line py. "
        f"""Xsuite: {p.py[0]}, SAD: {r_sad["py"][0]}.""")


def test_pipeline_reverse_element_order_solenoid_physics_matches_sad_with_charge_minus_one(
        tmp_path):
    """
    Composability check: does a genuine CHARGE=-1 lattice (which now bakes
    the reference charge into solenoid ks — see
    sad2xs/converter/_004_element_converter.py's convert_solenoids and
    dev/sad_charge/*.sad) still match real SAD after ALSO reversing element
    order (which negates ks a second time, for a different, independent
    reason — see docs/converter/line-reversals.md)?

    Identical to test_pipeline_reverse_element_order_solenoid_physics_matches_sad
    above except for one added line (CHARGE = -1;). If the two ks negations
    (charge-dependent base value, then direction-reversal) don't compose
    correctly, this is the test that would catch it — verified against real
    SAD's own "-LINE" reversal of the same CHARGE=-1 lattice, not just
    internal converter self-consistency.
    """
    lattice_content = """\
MOMENTUM    = 1.0 GEV;
CHARGE      = -1;

DRIFT       SOL_DRIFT   = (L = 0.5);
SOL         SOL_IN      = (BZ = 0.5 BOUND = 1 GEO = 1 DX = 0.001)
            SOL_OUT     = (BZ = 0.5 BOUND = 1);

MARK        START       = ()
            END         = ();

LINE        TEST        = (START SOL_IN SOL_DRIFT SOL_OUT END);
LINE        TESTREV     = (-TEST);
"""

    lat_path     = tmp_path / "rev_solenoid_charge.sad"
    rebuilt_name = "rev_solenoid_charge_rebuilt.sad"
    lat_path.write_text(lattice_content)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        rebuild_sad_lattice(
            lattice_filepath = lat_path.name,
            line_name        = "TEST",
            output_filepath  = rebuilt_name)

        r_sad = track_sad(
            lattice_filepath = lat_path.name,
            line_name        = "TESTREV",
            x_init           = np.array([1e-4]),
            px_init          = np.array([0.0]),
            y_init           = np.array([0.0]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)
    finally:
        os.chdir(cwd)

    rebuilt_path = tmp_path / rebuilt_name
    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(rebuilt_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    assert float(line.particle_ref.q0) == pytest.approx(-1.0), (
        "Sanity check: the converted line's reference particle should be "
        "the electron (q0=-1) specified by CHARGE=-1 in the SAD file.")

    p = line.build_particles(x=1e-4, px=0.0, y=0.0, py=0.0, zeta=0.0, delta=0.0)
    line.track(p)

    assert p.y[0] == pytest.approx(r_sad["y"][0], abs=1e-9), (
        f"Xsuite reversed solenoid y (CHARGE=-1) should match SAD reversed "
        f"""line y. Xsuite: {p.y[0]}, SAD: {r_sad["y"][0]}.""")
    assert p.py[0] == pytest.approx(r_sad["py"][0], abs=1e-9), (
        f"Xsuite reversed solenoid py (CHARGE=-1) should match SAD reversed "
        f"""line py. Xsuite: {p.py[0]}, SAD: {r_sad["py"][0]}.""")


def test_pipeline_reverse_element_order_translation_physics_matches_sad(tmp_path):
    """
    A standalone COORD element converts to an Xsuite Translation.  When the
    element order is reversed, that Translation's shift_x must NOT change sign.

    Physical reasoning
    ------------------
    A COORD offset is a geometric property of the beampipe at a fixed location.
    The pipe is at the same physical position regardless of which direction the
    beam travels, so the reference-frame shift seen by the beam is identical in
    both the forward and the reversed line.

    SAD ground truth — empirically verified with LINE TESTREV = (-TEST)
    ----------------------------------------------------------------------
    Lattice: COORD C1 (DX=0.001) → DRIFT D1 (L=1.0)
    Particle: x=0, px=0 at entrance

      Forward  SAD (C1 → D1): final x = -0.001
      Reversed SAD (D1 → C1): final x = -0.001   ← sign is the SAME

    Xsuite convention: Translation(shift_x=s) subtracts s from x, so
    Translation(shift_x=+0.001) → x = 0 − 0.001 = −0.001.

    In the reversed Xsuite line the COORD still has shift_x=+0.001 (no
    negation), D1 comes first (no change to x), then the Translation gives
    x = −0.001, matching SAD.

    Negating shift_x to −0.001 would give x = 0 − (−0.001) = +0.001, which
    contradicts SAD and is incorrect.

    Note on solenoid GEO translations
    ----------------------------------
    Translations produced by the solenoid GEO mechanism (named *_dxy) ARE
    negated under element-order reversal because they represent entry/exit
    frame shifts that must swap roles when the line is mirrored.  This test
    uses a plain COORD element, which has no *_dxy suffix, to isolate the
    standalone-COORD behaviour.
    """
    lattice_content = (
        "MOMENTUM = 1.0 GEV;\n"
        "COORD C1 = (DX=0.001);\n"
        "DRIFT D1 = (L=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST    = (START C1 D1 END);\n"
        "LINE TESTREV = (-TEST);\n")

    lat_path = tmp_path / "rev_translation.sad"
    lat_path.write_text(lattice_content)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_sad_fwd = track_sad(
            lattice_filepath = lat_path.name,
            line_name        = "TEST",
            x_init           = np.array([0.0]),
            px_init          = np.array([0.0]),
            y_init           = np.array([0.0]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)

        r_sad_rev = track_sad(
            lattice_filepath = lat_path.name,
            line_name        = "TESTREV",
            x_init           = np.array([0.0]),
            px_init          = np.array([0.0]),
            y_init           = np.array([0.0]),
            py_init          = np.array([0.0]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)
    finally:
        os.chdir(cwd)

    # SAD ground truth: forward and reversed give the same final x
    assert r_sad_rev["x"][0] == pytest.approx(r_sad_fwd["x"][0], abs=1e-12), (
        "SAD sanity check: COORD(DX=0.001) should give the same final x in the "
        "forward and reversed lines because the beampipe offset does not change "
        f"""sign under reversal. Forward: {r_sad_fwd["x"][0]}, """
        f"""Reversed: {r_sad_rev["x"][0]}.""")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path      = str(lat_path),
        output_directory      = "N/A",
        reverse_element_order = True,
        _verbose              = False,
        _test_mode            = True)

    p = line.build_particles(x=0.0, px=0.0, y=0.0, py=0.0, zeta=0.0, delta=0.0)
    line.track(p)

    assert p.x[0] == pytest.approx(r_sad_rev["x"][0], abs=1e-9), (
        "Xsuite reversed COORD x must match SAD reversed line x. "
        f"""Xsuite: {p.x[0]:.6e}, SAD forward: {r_sad_fwd["x"][0]:.6e}, """
        f"""SAD reversed: {r_sad_rev["x"][0]:.6e}. """
        "Both SAD values are the same; a sign error in shift_x negation "
        "would produce the opposite sign here.")


################################################################################
# QUAD Linear Fringe Field Adjustment (_import_sad_quad_fringes)
################################################################################
def test_pipeline_reverse_element_order_quad_fringe_matches_sad_reversed_line(tmp_path):
    """
    Xsuite tracking through a reverse_element_order=True conversion of a
    QUAD with asymmetric F1K1F/F1K1B (FRINGE=1, entrance-only) should
    match SAD tracking through the native SAD-reversed line
    (LINE TESTREV = (-TEST)). This is the strongest available check on
    the reversal fix-up: it only passes if BOTH the F1K1F<->F1K1B
    parameter swap AND the FRINGE mode permutation (1<->2) are applied
    together -- see tests/sad/test_quad.py's
    test_quad_reversed_line_fringe_mode_permutes for the SAD-only ground
    truth this mirrors.

    `x`'s tolerance is widened for a known, separate reason, not the
    reversal fixup: rebuilding the reversed element independently (a
    from-scratch forward FRINGE=2 build with F1K1F/F1K1B swapped) gives
    bit-identical results, so that logic is exact. The ~3e-9 residual
    instead comes from the QUAD body -- present at the same size for a
    plain K1-only QUAD with no fringe at all, independent of
    num_multipole_kicks, and tracking SAD's DISFRIN hard-edge kick almost
    exactly (toggling either side shifts the result by the same ~1.2e-9).
    QUAD conversion doesn't gate its edge model on DISFRIN yet -- a
    separate gap to close alongside MULT/cavity model work, not a
    reversal bug.
    """
    lattice_content = (
        "MOMENTUM = 1.0 GEV;\n"
        "QUAD Q1 = (L=1.0 K1=0.3 F1K1F=0.05 F1K1B=-0.03 F2K1F=0.02 "
        "F2K1B=-0.01 FRINGE=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST    = (START Q1 END);\n"
        "LINE TESTREV = (-TEST);\n")

    lat_path = tmp_path / "rev_quad_fringe.sad"
    lat_path.write_text(lattice_content)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_sad = track_sad(
            lattice_filepath = lat_path.name,
            line_name        = "TESTREV",
            x_init           = np.array([1e-3]),
            px_init          = np.array([2e-3]),
            y_init           = np.array([-1.5e-3]),
            py_init          = np.array([0.5e-3]),
            zeta_init        = np.array([0.0]),
            delta_init       = np.array([0.0]),
            n_turns          = 1,
            rfsw             = False,
            with_progress    = False)
    finally:
        os.chdir(cwd)

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path            = str(lat_path),
        output_directory            = "N/A",
        reverse_element_order       = True,
        _import_sad_quad_fringes    = True,
        _verbose                    = False,
        _test_mode                  = True)

    p = xt.Particles(
        "positron", p0c=1.0E9,
        x=1e-3, px=2e-3, y=-1.5e-3, py=0.5e-3, zeta=0.0, delta=0.0)
    line.track(p, num_turns=1)

    # x's measured residual is ~3.05e-9 (QUAD-body/DISFRIN gap, see
    # docstring); bounded with headroom, not loosened past that.
    abs_tol = {"x": 5e-9, "px": 1e-9, "y": 1e-9, "py": 1e-9}
    for coord, sad_val, xs_val in [
            ("x", r_sad["x"][0], p.x[0]), ("px", r_sad["px"][0], p.px[0]),
            ("y", r_sad["y"][0], p.y[0]), ("py", r_sad["py"][0], p.py[0])]:
        assert xs_val == pytest.approx(sad_val, rel=1e-6, abs=abs_tol[coord]), (
            f"Xsuite reverse_element_order=True QUAD fringe tracking "
            f"`{coord}` should match SAD's native -LINE reversed tracking. "
            f"Xsuite: {xs_val:.6e}, SAD: {sad_val:.6e}.")
