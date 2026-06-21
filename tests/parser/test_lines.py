"""
================================================================================
Tests for SAD parser line handling
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
from sad2xs.config import Config
from sad2xs.converter._001_parser import parse_sad_file

################################################################################
# Line Separators
################################################################################
def test_line_definitions_accept_whitespace_commas_and_mixed_separators(write_lattice):
    """
    Line contents should support SAD definitions with or without commas.
    """
    lattice_path = write_lattice(
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
    assert parsed["lines"]["ring_ws"] == expected, (
        "Whitespace-separated line contents should parse in order.")
    assert parsed["lines"]["ring_comma_space"] == expected, (
        "Comma-and-space-separated line contents should parse in order.")
    assert parsed["lines"]["ring_comma_tight"] == expected, (
        "Tightly comma-separated line contents should parse in order.")
    assert parsed["lines"]["ring_mixed"] == expected, (
        "Mixed comma and whitespace line contents should parse in order.")

def test_multiline_line_definition_parses_components_in_order(write_lattice):
    """
    Line definitions should support components split across physical lines.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        LINE RING = (
            A
            B,
            C
        );
        """,
        filename = "multiline_line.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["lines"]["ring"] == ["a", "b", "c"], (
        "Multiline line definitions should preserve component order.")

def test_multiple_line_definitions_in_one_section_are_parsed(write_lattice):
    """
    A SAD LINE section may contain more than one named line definition.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        LINE SUB = (A B) RING = (SUB C);
        """,
        filename = "multiple_lines_one_section.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["lines"]["sub"] == ["a", "b"], (
        "The first line in a multi-line LINE section should be parsed.")
    assert parsed["lines"]["ring"] == ["sub", "c"], (
        "The second line in a multi-line LINE section should preserve "
        "references literally.")

def test_comma_separated_line_preserves_reversed_components(write_lattice):
    """
    Comma handling should not alter reversed line references.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        LINE SUB = (A B);
        LINE RING_REV = (A, -SUB, C);
        """,
        filename = "line_reversal.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["lines"]["sub"] == ["a", "b"], (
        "Referenced sub-lines should parse before reversal checks.")
    assert parsed["lines"]["ring_rev"] == ["a", "-sub", "c"], (
        "Comma handling should preserve reversed line reference tokens.")

def test_empty_line_definition_is_parsed_as_empty_component_list(write_lattice):
    """
    SAD accepts LINE EMPTY = (); and the parser should preserve it.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        LINE EMPTY = ();
        """,
        filename = "empty_line.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["lines"]["empty"] == [], (
        "Empty SAD line definitions should parse as an empty component list.")

def test_empty_line_reference_is_preserved_in_parent_line(write_lattice):
    """
    References to empty lines should be preserved literally by the parser.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        LINE EMPTY = ();
        LINE RING = (A EMPTY C);
        """,
        filename = "empty_line_reference.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["lines"]["empty"] == [], (
        "The referenced empty line should be available in parsed lines.")
    assert parsed["lines"]["ring"] == ["a", "empty", "c"], (
        "Parent lines should preserve references to empty sub-lines literally.")
