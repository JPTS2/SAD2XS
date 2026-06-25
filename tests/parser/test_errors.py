"""
================================================================================
Tests for SAD parser error handling
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import xtrack as xt

from sad2xs.config import Config
from sad2xs.converter._001_parser import parse_sad_file
from sad2xs.converter._003_expression_converter import convert_expressions
from tests.support.config import PROTECTED_ELEMENT_NAMES

################################################################################
# Expression Errors
################################################################################
def test_multiple_equals_in_deferred_expression_raises_clear_error(write_lattice):
    """
    Deferred expressions with multiple '=' characters should fail clearly.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A = B = 1.0;
        """,
        filename = "error_deferred_multiple_equals.sad")

    with pytest.raises(ValueError, match = "Expected format"):
        parse_sad_file(str(lattice_path), Config(_verbose = False))

def test_invalid_deferred_expression_syntax_raises_clear_error(write_lattice):
    """
    A trailing operator ('A = 1.0 +;') is accepted by SAD but silently corrupts
    the value. SAD2XS should fail clearly and direct the user to their SAD lattice.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A = 1.0 + ;
        """,
        filename = "invalid_deferred_expression_syntax.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))
    environment = xt.Environment()

    with pytest.raises(ValueError, match = "SAD lattice"):
        convert_expressions(
            parsed_lattice_data = parsed,
            environment         = environment,
            config              = Config(_verbose = False))

################################################################################
# Command Errors
################################################################################
def test_unknown_assignment_with_parentheses_raises_clear_error(write_lattice):
    """
    Unsupported assignment-like commands should not be parsed ambiguously.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        FOO BAR = (A = 1.0);
        """,
        filename = "error_unknown_assignment_with_parentheses.sad")

    with pytest.raises(ValueError, match = "Expected format"):
        parse_sad_file(str(lattice_path), Config(_verbose = False))

def test_unknown_command_with_parentheses_and_commas_is_ignored(write_lattice):
    """
    Unknown non-assignment commands should be ignored even with punctuation.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        PRINT(1, 2, 3);
        DRIFT D1 = (L = 1.0);
        LINE RING = (D1);
        """,
        filename = "error_unknown_punctuated_command_ignored.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d1"]["l"] == pytest.approx(1.0), (
        "Valid elements after an unknown punctuated command should parse.")
    assert parsed["lines"]["ring"] == ["d1"], (
        "Valid lines after an unknown punctuated command should parse.")

################################################################################
# Line Errors
################################################################################
def test_line_without_equals_is_parsed_correctly(write_lattice):
    """
    SAD accepts LINE definitions without '=' (e.g. 'LINE RING (A B)').
    The converter must handle this and produce the correct element list.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT A = (L = 1.0);
        DRIFT B = (L = 2.0);
        LINE RING (A B);
        """,
        filename = "line_without_equals.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["lines"]["ring"] == ["a", "b"], (
        "LINE without '=' should parse to the correct element list.")

def test_line_without_parentheses_is_parsed_correctly(write_lattice):
    """
    SAD accepts LINE definitions without parentheses (e.g. 'LINE RING = A B').
    The converter must handle this and produce the correct element list.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT A = (L = 1.0);
        DRIFT B = (L = 2.0);
        LINE RING = A B;
        """,
        filename = "line_without_parentheses.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["lines"]["ring"] == ["a", "b"], (
        "LINE without parentheses should parse to the correct element list.")

def test_malformed_line_multiple_equals_raises_clear_error(write_lattice):
    """
    Line definitions with multiple '=' characters should fail clearly.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        LINE RING = A = (B);
        """,
        filename = "error_line_multiple_equals.sad")

    with pytest.raises(ValueError):
        parse_sad_file(str(lattice_path), Config(_verbose = False))

def test_malformed_line_extra_closing_parenthesis_raises_clear_error(write_lattice):
    """
    Line definitions with unmatched closing parentheses should fail clearly.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        LINE RING = (A));
        """,
        filename = "error_line_extra_closing_parenthesis.sad")

    with pytest.raises(ValueError):
        parse_sad_file(str(lattice_path), Config(_verbose = False))

################################################################################
# Element Errors
################################################################################
def test_unsupported_element_keyword_prefix_raises_clear_error(write_lattice):
    """
    Unsupported element commands should not match allowed element prefixes.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFTLONG D1 = (L = 1.0);
        """,
        filename = "error_element_keyword_prefix.sad")

    with pytest.raises(ValueError, match = "Expected format"):
        parse_sad_file(str(lattice_path), Config(_verbose = False))

def test_malformed_element_empty_name_raises_clear_error(write_lattice):
    """
    Element definitions should require a non-empty element name.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT = (L = 1.0);
        """,
        filename = "error_element_empty_name.sad")

    with pytest.raises(ValueError):
        parse_sad_file(str(lattice_path), Config(_verbose = False))

@pytest.mark.parametrize(
    "protected_name",
    sorted(PROTECTED_ELEMENT_NAMES))
def test_protected_element_names_raise_clear_error(
        write_lattice,
        protected_name):
    """
    Element names that collide with protected SAD2XS names should fail early.
    """
    lattice_path = write_lattice(
        f"""\
        MOMENTUM = 1.0 GEV;
        DRIFT {protected_name.upper()} = (L = 1.0);
        """,
        filename = f"error_protected_element_name_{protected_name}.sad")

    with pytest.raises(ValueError, match = "protected|reserved|name"):
        parse_sad_file(str(lattice_path), Config(_verbose = False))

################################################################################
# Unknown Sections
################################################################################
def test_unknown_section_without_assignment_is_ignored(write_lattice):
    """
    Unknown non-assignment commands should not become parsed expressions.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        USE RING;
        DRIFT D1 = (L = 1.0);
        LINE RING = (D1);
        """,
        filename = "error_unknown_section_without_assignment.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert "use ring" not in parsed["expressions"], (
        "Unknown commands without assignment should not be stored as deferred "
        "expressions.")
    assert parsed["lines"]["ring"] == ["d1"], (
        "Valid content after an unknown command should still be parsed.")

def test_unknown_assignment_section_is_deferred_expression(write_lattice):
    """
    Unknown assignment sections should be handled as deferred expressions.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        UNKNOWN_VALUE = 1.25;
        """,
        filename = "error_unknown_assignment_is_expression.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["expressions"]["unknown_value"] == pytest.approx(1.25), (
        "Unknown assignment sections should be parsed as deferred expressions.")
