"""
================================================================================
Tests for the reverse_element_order parameter of the SAD2XS conversion pipeline
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-15
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import sad2xs as s2x

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
        f"Got: {line['b1'].edge_entry_angle}.")
    assert line["b1"].edge_exit_angle == pytest.approx(0.05), (
        "After reverse_element_order=True, bend exit edge angle should be the "
        "original entry angle (E1*ANGLE = 0.5*0.1 = 0.05). "
        f"Got: {line['b1'].edge_exit_angle}.")


################################################################################
# Reference Shift Adjustment
################################################################################
def test_pipeline_reverse_element_order_negates_coord_dx_and_dy(write_lattice):
    """
    reverse_element_order=True should negate the dx and dy of each XYShift
    produced by a SAD COORD element. The reversed values are compared against
    the forward conversion to avoid dependence on internal sign conventions.
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

    dx_forward  = line_forward["c1"].dx
    dy_forward  = line_forward["c1"].dy
    dx_reversed = line_reversed["c1"].dx
    dy_reversed = line_reversed["c1"].dy

    assert dx_forward != pytest.approx(0.0), (
        "Forward COORD dx should be non-zero for DX = 0.01.")
    assert dy_forward != pytest.approx(0.0), (
        "Forward COORD dy should be non-zero for DY = 0.02.")
    assert dx_reversed == pytest.approx(-dx_forward), (
        "reverse_element_order=True should negate COORD dx. "
        f"Forward: {dx_forward}, reversed: {dx_reversed}.")
    assert dy_reversed == pytest.approx(-dy_forward), (
        "reverse_element_order=True should negate COORD dy. "
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
