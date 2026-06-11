"""
================================================================================
Tests for SAD parser line names
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-11
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import textwrap

from sad2xs.config import Config
from sad2xs.converter._001_parser import parse_sad_file

################################################################################
# Helpers
################################################################################
def write_lattice(tmp_path, content, filename = "test_lattice.sad"):
    """
    Write a temporary SAD lattice file for parser tests.
    """
    lattice_path = tmp_path / filename
    lattice_path.write_text(textwrap.dedent(content))
    return lattice_path

################################################################################
# Names Containing Line
################################################################################
def test_line_name_containing_line_is_preserved(tmp_path):
    """
    Line names containing the substring line should not be altered.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        LINE MYLINE = (A B);
        """,
        filename = "line_name_contains_line.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert "myline" in parsed["lines"], (
        "Line names containing 'line' should be preserved as dictionary keys.")
    assert parsed["lines"]["myline"] == ["a", "b"], (
        "Line names containing 'line' should preserve their components.")

def test_line_reference_containing_line_is_preserved(tmp_path):
    """
    References to lines containing the substring line should not be altered.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        LINE MYLINE = (A B);
        LINE RING = (MYLINE C);
        """,
        filename = "line_reference_contains_line.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["lines"]["ring"] == ["myline", "c"], (
        "Parser output should preserve nested line references literally; "
        "flattening belongs in conversion, not parsing.")

def test_reversed_line_reference_containing_line_is_preserved(tmp_path):
    """
    Reversed line references containing line should keep the minus token.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        LINE MYLINE = (A B);
        LINE RING = (-MYLINE C);
        """,
        filename = "reversed_line_reference_contains_line.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["lines"]["ring"] == ["-myline", "c"], (
        "Reversed references to names containing 'line' should preserve the "
        "minus token and full referenced name.")
