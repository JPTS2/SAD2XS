"""
================================================================================
Tests for SAD's "N*NAME" repetition syntax in LINE definitions
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-08
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest

import sad2xs as s2x

################################################################################
# Helpers
################################################################################
LATTICE_HEADER = """\
MOMENTUM    = 1.0 GEV;

DRIFT       D1      = (L = 1.0)
            D2      = (L = 2.0);

QUAD        QF      = (L = 0.5 K1 = 0.1);

MARK        START   = ()
            END     = ();

LINE        CELL    = (D1 QF D2);
"""

def _convert(write_lattice, line_body, filename):
    """
    Convert a lattice made of the shared header plus one TEST_LINE body.
    """
    lattice_path = write_lattice(
        LATTICE_HEADER + line_body + "\n",
        filename = filename)

    return s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        line_name         = "TEST_LINE",
        output_directory  = "N/A",
        _verbose          = False,
        _test_mode        = True)

################################################################################
# Repetition Matches Hand-Written Expansion
################################################################################
def test_repeated_subline_matches_hand_written_expansion(write_lattice):
    """
    "N*SUBLINE" is plain repetition in SAD, so a line using it should convert
    to the same Xsuite line as one writing the repetition out by hand.
    """
    repeated = _convert(
        write_lattice,
        "LINE        TEST_LINE = (START 4*CELL END);",
        "repeated_subline.sad")
    manual = _convert(
        write_lattice,
        "LINE        TEST_LINE = (START CELL CELL CELL CELL END);",
        "repeated_subline_manual.sad")

    assert list(repeated.element_names) == list(manual.element_names), (
        "\"4*CELL\" should convert identically to four \"CELL\" references. "
        f"Got: {list(repeated.element_names)} vs "
        f"{list(manual.element_names)}.")

    assert repeated.get_length() == pytest.approx(manual.get_length()), (
        "\"4*CELL\" should have the same length as four \"CELL\" references. "
        f"Got: {repeated.get_length()} vs {manual.get_length()}.")
