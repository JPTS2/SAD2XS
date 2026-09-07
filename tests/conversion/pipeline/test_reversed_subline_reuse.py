"""
================================================================================
Tests for reuse of a reversed subline referenced more than once
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-07
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import sad2xs as s2x

################################################################################
# Lattice
################################################################################
# Two separate lines each reverse the same subline. The converter builds one
# "sub_reversed" line for the first reference; the second must reuse it rather
# than build it again.
REPEATED_REVERSED_SUBLINE_LATTICE = """\
MOMENTUM    = 1.0 GEV;

DRIFT       D1      = (L = 1.0)
            D2      = (L = 2.0);

QUAD        Q1      = (L = 0.5 K1 = 0.1);

MARK        START   = ()
            END     = ();

LINE        SUB     = (D1 Q1 D2);

LINE        ARC1    = (START -SUB END);
LINE        ARC2    = (START -SUB END);
"""

################################################################################
# Reuse Across Two Lines
################################################################################
def test_reversed_subline_referenced_by_two_lines_converts(write_lattice):
    """
    Two lines may each reference the same "-SUBLINE". The second reference
    must reuse the reversed subline built for the first, rather than build a
    second line under the same name.
    """
    lattice_path = write_lattice(
        REPEATED_REVERSED_SUBLINE_LATTICE,
        filename = "repeated_reversed_subline.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        line_name         = "ARC1",
        output_directory  = "N/A",
        _verbose          = False,
        _test_mode        = True)

    assert "arc2" in line.env.lines, (
        "Both lines referencing \"-SUB\" should convert. Converted lines: "
        f"{sorted(line.env.lines)}.")


def test_reversed_subline_reused_by_two_lines_keeps_element_order(write_lattice):
    """
    Reusing the reversed subline must not change its contents: both lines
    should contain the subline's elements in reversed order.
    """
    lattice_path = write_lattice(
        REPEATED_REVERSED_SUBLINE_LATTICE,
        filename = "repeated_reversed_subline_order.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        line_name         = "ARC1",
        output_directory  = "N/A",
        _verbose          = False,
        _test_mode        = True)

    expected = ["start", "d2", "q1", "d1", "end"]

    assert list(line.element_names) == expected, (
        f"\"-SUB\" should expand to {expected[1:-1]}. "
        f"Got: {list(line.element_names)}.")

    assert list(line.env.lines["arc2"].element_names) == expected, (
        "The second line reusing \"sub_reversed\" should hold the same "
        f"elements as the first. Got: {list(line.env.lines['arc2'].element_names)}.")
