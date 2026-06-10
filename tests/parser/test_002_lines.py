"""
(Unofficial) SAD to XSuite Converter

Tests for SAD parser line handling.
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
# Line Separators
################################################################################
def test_line_definitions_accept_whitespace_commas_and_mixed_separators(tmp_path):
    """
    Line contents should support SAD definitions with or without commas.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        LINE RING_WS = (A B C);
        LINE RING_COMMA_SPACE = (A, B, C);
        LINE RING_COMMA_TIGHT = (A,B,C);
        LINE RING_MIXED = (A, B C);
        """,
        filename = "line_separators.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    expected = ["a", "b", "c"]
    assert parsed["lines"]["ring_ws"] == expected
    assert parsed["lines"]["ring_comma_space"] == expected
    assert parsed["lines"]["ring_comma_tight"] == expected
    assert parsed["lines"]["ring_mixed"] == expected

def test_comma_separated_line_preserves_reversed_components(tmp_path):
    """
    Comma handling should not alter reversed line references.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        LINE SUB = (A B);
        LINE RING_REV = (A, -SUB, C);
        """,
        filename = "line_reversal.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["lines"]["sub"] == ["a", "b"]
    assert parsed["lines"]["ring_rev"] == ["a", "-sub", "c"]
