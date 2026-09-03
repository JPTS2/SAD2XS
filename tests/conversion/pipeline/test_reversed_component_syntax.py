"""
================================================================================
Tests for SAD's per-element "-NAME" reversal syntax (create_reversed_component)
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-01
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
from sad2xs.sad_helpers import track_sad, transfer_matrix_sad
from tests.support.coupled_optics import linear_transfer_matrix_4d

################################################################################
# Direction-Symmetric Elements: Reused, Not Cloned
################################################################################
def test_reversed_component_drift_is_reused_not_cloned(write_lattice):
    """
    A per-element "-NAME" reference to a Drift (direction-symmetric) should
    simply reuse the original element, not create a "-NAME"-prefixed clone.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START -D1 END);
        """,
        filename = "reversed_component_drift.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        _verbose          = False,
        _test_mode        = True)

    assert list(line.element_names) == ["start", "d1", "end"], (
        "A per-element \"-D1\" reference should reuse \"d1\" directly, not "
        f"introduce a \"-d1\" clone. Got: {list(line.element_names)}.")


def test_reversed_component_quad_k1_unchanged(write_lattice):
    """
    A per-element "-NAME" reference to a Quadrupole should not change k1
    (direction-symmetric, same as reverse_element_order — see
    test_pipeline_reverse_element_order_does_not_change_quad_k1).
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        QUAD        Q1      = (L = 1.0 K1 = 0.2);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START -Q1 END);
        """,
        filename = "reversed_component_quad.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        _verbose          = False,
        _test_mode        = True)

    assert line["q1"].k1 == pytest.approx(0.2), (
        "A per-element \"-Q1\" reference should not change k1. "
        f"""Got: {line["q1"].k1}.""")


########################################
# Soft Quadrupolar Fringe Reversal
########################################
@pytest.mark.parametrize(
    "element_definition",
    [
        "QUAD Q1=(L=1 K1=0.3 F1K1F=0.05 F1K1B=-0.03 "
        "F2K1F=0.02 F2K1B=-0.01 FRINGE=1 DISFRIN=1);",
        "MULT Q1=(L=1 K1=0.3 F1K1F=0.05 F1K1B=-0.03 "
        "F2K1F=0.02 F2K1B=-0.01 FRINGE=1 DISFRIN=1);",
    ],
    ids = ["quad", "mult"])
def test_reversed_component_soft_quadrupolar_fringe_matches_sad(
        tmp_path,
        element_definition):
    """A per-element reversal must reverse the active fringe face."""
    lattice_content = (
        "MOMENTUM=1 GEV;\n"
        f"{element_definition}\n"
        "MARK START=() END=();\n"
        "LINE TEST=(START -Q1 END);\n")
    lattice_path = tmp_path / "reversed_soft_quadrupolar_fringe.sad"
    lattice_path.write_text(lattice_content)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        sad_matrix = transfer_matrix_sad(lattice_path.name, "TEST")
    finally:
        os.chdir(cwd)

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name = "TEST",
        SIMPLIFY_MULTIPOLES = False,
        _verbose = False,
        _test_mode = True)

    np.testing.assert_allclose(
        linear_transfer_matrix_4d(line),
        sad_matrix,
        rtol = 3e-6,
        atol = 1e-6,
        err_msg = (
            "A per-element reversed soft quadrupolar fringe should match "
            "SAD's -NAME transfer map within the known thick-MULT body "
            "integration residual."))


@pytest.mark.parametrize(
    "element_definition",
    [
        "QUAD Q1=(L=1 K1=0.3 F1K1F=0.05 F2K1F=0.02 "
        "FRINGE=1 DISFRIN=1);",
        "MULT Q1=(L=1 K1=0.3 F1K1F=0.05 F2K1F=0.02 "
        "FRINGE=1 DISFRIN=1);",
    ],
    ids = ["quad", "mult"])
def test_forward_and_reversed_soft_quadrupolar_fringe_occurrences_match_sad(
        tmp_path,
        element_definition):
    """A reversed occurrence must not mutate a shared forward fringe map."""
    lattice_path = tmp_path / "mixed_soft_quadrupolar_fringe_directions.sad"
    lattice_path.write_text(
        "MOMENTUM=1 GEV;\n"
        f"{element_definition}\n"
        "MARK START=() END=();\n"
        "LINE TEST=(START Q1 -Q1 END);\n")

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        sad_matrix = transfer_matrix_sad(lattice_path.name, "TEST")
    finally:
        os.chdir(cwd)

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = str(lattice_path),
        output_directory    = "N/A",
        line_name           = "TEST",
        SIMPLIFY_MULTIPOLES = False,
        _verbose            = False,
        _test_mode          = True)

    assert "q1_fringe_in" in line.element_names
    assert "-q1_fringe_in" in line.element_names
    np.testing.assert_allclose(
        linear_transfer_matrix_4d(line),
        sad_matrix,
        rtol = 3e-6,
        atol = 2e-6,
        err_msg = (
            "Forward and -NAME occurrences should retain distinct soft "
            "quadrupolar face maps and match SAD."))


################################################################################
# Solenoid Strength Adjustment
################################################################################
def test_reversed_component_solenoid_negates_ks(write_lattice):
    """
    A per-element "-NAME" reference to a UniformSolenoid should negate ks,
    exactly as reverse_element_order=True does (see
    test_pipeline_reverse_element_order_negates_solenoid_ks).

    create_reversed_component clones a genuinely-reversed element under its
    dash-prefixed name (only direction-symmetric types drop the dash and
    reuse the original), so the clone is "-s1", not "s1".
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        SOL         S1      = (L = 0.5 BZ = 0.1);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START -S1 END);
        """,
        filename = "reversed_component_solenoid.sad")

    line_forward = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        _verbose          = False,
        _test_mode        = True)

    ks_reversed = line_forward["-s1"].ks

    # Compare against the same SOL converted with no reversal at all.
    lattice_path_fwd = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        SOL         S1      = (L = 0.5 BZ = 0.1);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START S1 END);
        """,
        filename = "reversed_component_solenoid_fwd.sad")

    line_plain = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path_fwd),
        output_directory  = "N/A",
        _verbose          = False,
        _test_mode        = True)

    ks_forward = line_plain["s1"].ks

    assert ks_forward != pytest.approx(0.0), (
        "Forward solenoid ks should be non-zero for BZ = 0.1.")
    assert ks_reversed == pytest.approx(-ks_forward), (
        "A per-element \"-S1\" reference should negate solenoid ks. "
        f"Forward: {ks_forward}, reversed: {ks_reversed}.")


################################################################################
# Bend Edge Angle Adjustment
################################################################################
def test_reversed_component_bend_swaps_edge_angles(write_lattice):
    """
    A per-element "-NAME" reference to a Bend swaps the entry and exit edge
    angles, as reverse_element_order does.

    With ANGLE=0.1, E1=0.5, E2=0.25 the forward entry/exit are 0.05/0.025 and
    the reversed are 0.025/0.05. Asserts on the dash-prefixed clone "-b1",
    which create_reversed_component builds while leaving "b1" untouched. Whole
    line equivalent: test_pipeline_reverse_element_order_swaps_bend_edge_angles.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        B1      = (L = 1.0 ANGLE = 0.1 E1 = 0.5 E2 = 0.25);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START -B1 END);
        """,
        filename = "reversed_component_bend_edges.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        _verbose          = False,
        _test_mode        = True)

    assert line["-b1"].edge_entry_angle == pytest.approx(0.025), (
        "After a per-element \"-B1\" reference, bend entry edge angle should "
        "be the original exit angle (E2*ANGLE = 0.25*0.1 = 0.025). "
        f"""Got: {line["-b1"].edge_entry_angle}.""")
    assert line["-b1"].edge_exit_angle == pytest.approx(0.05), (
        "After a per-element \"-B1\" reference, bend exit edge angle should "
        "be the original entry angle (E1*ANGLE = 0.5*0.1 = 0.05). "
        f"""Got: {line["-b1"].edge_exit_angle}.""")


################################################################################
# Bend Fringe Field Adjustment
################################################################################
def test_reversed_component_bend_swaps_fint_hgap(write_lattice):
    """
    A per-element "-NAME" reference to a Bend swaps the entry and exit fringe
    fields, as reverse_element_order does.

    With F1=0.24, FB1=0.12, FB2=0.0 the forward entry/exit fint are 0.36/0.24
    and the reversed are 0.24/0.36. Asserts on the dash-prefixed clone "-b1".
    Whole line equivalent:
    test_pipeline_reverse_element_order_swaps_bend_fint_hgap.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        BEND        B1      = (L = 1.0 ANGLE = 0.1 FRINGE = 1 F1 = 0.24 FB1 = 0.12 FB2 = 0.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START -B1 END);
        """,
        filename = "reversed_component_bend_fringe.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path         = str(lattice_path),
        output_directory         = "N/A",
        _import_sad_bend_fringes = True,
        _verbose                 = False,
        _test_mode               = True)

    expected_reversed_entry = 0.24
    expected_reversed_exit  = 0.36

    assert line["-b1"].edge_entry_fint == pytest.approx(expected_reversed_entry), (
        "After a per-element \"-B1\" reference, bend entry fint should be "
        "the original exit value (F1+FB2 = 0.24). "
        f"""Got: {line["-b1"].edge_entry_fint}.""")
    assert line["-b1"].edge_entry_hgap == pytest.approx(1 / 12), (
        "Bend entry hgap should stay the fixed 1/12 fringe constant. "
        f"""Got: {line["-b1"].edge_entry_hgap}.""")
    assert line["-b1"].edge_exit_fint == pytest.approx(expected_reversed_exit), (
        "After a per-element \"-B1\" reference, bend exit fint should be "
        "the original entry value (F1+FB1 = 0.36). "
        f"""Got: {line["-b1"].edge_exit_fint}.""")
    assert line["-b1"].edge_exit_hgap == pytest.approx(1 / 12), (
        "Bend exit hgap should stay the fixed 1/12 fringe constant. "
        f"""Got: {line["-b1"].edge_exit_hgap}.""")


################################################################################
# Physics Validation Against SAD
################################################################################
def test_reversed_component_bend_poleface_physics_matches_sad(tmp_path):
    """
    A per-element "-NAME" reference to a bend with asymmetric poleface angles
    (E1 != E2) should reproduce SAD's own tracking through the identical
    per-element-reversed line -- confirming SAD treats "-NAME" as equivalent
    to a genuine direction reversal (not merely a naming convention), and
    that the converter's edge-angle swap already handles this correctly.
    """
    lattice_content = (
        "MOMENTUM = 1.0 GEV;\n"
        "BEND B1 = (L=1.0 ANGLE=0.05 E1=0.05 E2=0.0);\n"
        "DRIFT D1 = (L=0.5);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 -B1 D1 END);\n")

    lat_path = tmp_path / "reversed_component_poleface_physics.sad"
    lat_path.write_text(lattice_content)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_sad = track_sad(
            lattice_filepath = lat_path.name,
            line_name        = "TEST",
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
        sad_lattice_path  = str(lat_path),
        output_directory  = "N/A",
        _verbose          = False,
        _test_mode        = True)

    p = xt.Particles("positron", p0c = 1.0E9, x = 0.0, px = 0.0, y = 1e-3, py = 0.0)
    line.track(p, num_turns = 1)

    assert p.y[0] == pytest.approx(r_sad["y"][0], rel = 1e-6), (
        "Xsuite's per-element \"-B1\" reference should match SAD's own "
        f"""per-element-reversed tracking. Xsuite: {p.y[0]}, SAD: {r_sad["y"][0]}.""")
    assert p.py[0] == pytest.approx(r_sad["py"][0], rel = 1e-6), (
        "Xsuite's per-element \"-B1\" reference should match SAD's own "
        f"""per-element-reversed tracking. Xsuite: {p.py[0]}, SAD: {r_sad["py"][0]}.""")


def test_reversed_component_bend_fringe_physics_matches_sad(tmp_path):
    """
    A per-element reversed bend with asymmetric fringe reproduces SAD's own
    tracking through the equivalent reversed line.

    Uses ANGLE=0.05 to engage the edge-fringe term, with E1=E2=0 to isolate
    fint from the edge-angle swap. The rel=1e-6 tolerance is chosen to catch a
    missing swap: without it the result matches SAD's forward y instead, which
    differs from the reversed y by ~6e-5 relative.
    """
    lattice_content = (
        "MOMENTUM = 1.0 GEV;\n"
        "BEND B1 = (L=1.0 ANGLE=0.05 E1=0 E2=0 FRINGE=1 FB1=0.15 FB2=0.0);\n"
        "DRIFT D1 = (L=0.5);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 -B1 D1 END);\n")

    lat_path = tmp_path / "reversed_component_fringe_physics.sad"
    lat_path.write_text(lattice_content)

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        r_sad = track_sad(
            lattice_filepath = lat_path.name,
            line_name        = "TEST",
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
        sad_lattice_path         = str(lat_path),
        output_directory         = "N/A",
        _import_sad_bend_fringes = True,
        _verbose                 = False,
        _test_mode               = True)

    p = xt.Particles("positron", p0c = 1.0E9, x = 0.0, px = 0.0, y = 1e-3, py = 0.0)
    line.track(p, num_turns = 1)

    assert p.y[0] == pytest.approx(r_sad["y"][0], rel = 1e-6), (
        "Xsuite's per-element \"-B1\" reference should match SAD's own "
        f"""per-element-reversed tracking. Xsuite: {p.y[0]}, """
        f"""SAD: {r_sad["y"][0]}.""")
