"""
================================================================================
Tests for SAD parser repeated definition handling
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

from sad2xs.config import Config
from sad2xs.converter._001_parser import parse_sad_file

################################################################################
# Repeated Globals
################################################################################
def test_repeated_momentum_definition_uses_last_value(write_lattice):
    """
    Repeated MOMENTUM definitions should use the final SAD value.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        MOMENTUM = 2.0 GEV;
        """,
        filename = "repeated_momentum_last_wins.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["p0c"] == pytest.approx(2.0E9), (
        "Repeated MOMENTUM definitions should use the final value.")

def test_repeated_optional_global_definitions_use_last_values(write_lattice):
    """
    Repeated MASS, CHARGE, and FSHIFT definitions should use final values.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        MASS = 0.511 MEV;
        MASS = 1.0 MEV;
        CHARGE = +1.0;
        CHARGE = -1.0;
        FSHIFT = 0.01;
        FSHIFT = 0.02;
        """,
        filename = "repeated_optional_globals_last_wins.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["mass0"] == pytest.approx(1.0E6), (
        "Repeated MASS definitions should use the final value.")
    assert parsed["globals"]["q0"] == pytest.approx(-1.0), (
        "Repeated CHARGE definitions should use the final value.")
    assert parsed["globals"]["fshift"] == pytest.approx(0.02), (
        "Repeated FSHIFT definitions should use the final value.")

################################################################################
# Repeated Deferred Expressions
################################################################################
def test_repeated_deferred_expression_substitutes_previous_value(write_lattice):
    """
    Repeated deferred expressions should substitute the previous value.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A = 1.0;
        A = A + 1.0;
        """,
        filename = "repeated_deferred_expression_substitution.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["expressions"]["a"] == "1.0 + 1.0", (
        "Repeated deferred expressions should substitute the previous value.")

def test_multiple_repeated_deferred_expression_redefinitions_are_substituted(
        write_lattice):
    """
    Multiple repeated deferred expressions should substitute cumulatively.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A = 1.0;
        A = A + 1.0;
        A = A + 1.0;
        """,
        filename = "repeated_deferred_expression_chain_substitution.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["expressions"]["a"] == "1.0 + 1.0 + 1.0", (
        "Multiple repeated deferred expressions should substitute the previous "
        "definition each time.")

################################################################################
# Repeated Lines
################################################################################
def test_repeated_line_definition_uses_last_value(write_lattice):
    """
    Repeated LINE definitions should use the final SAD line contents.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        LINE RING = (A);
        LINE RING = (B C);
        """,
        filename = "repeated_line_last_wins.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["lines"]["ring"] == ["b", "c"], (
        "Repeated LINE definitions should use the final component list.")

################################################################################
# Repeated Elements
################################################################################
def test_repeated_element_definition_same_type_uses_last_value(write_lattice):
    """
    Repeated element definitions of the same type should use the final value.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = (L = 1.0);
        DRIFT D1 = (L = 2.0);
        """,
        filename = "repeated_element_same_type_last_wins.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d1"]["l"] == pytest.approx(2.0), (
        "Repeated element definitions of the same type should use the final "
        "definition.")

def test_repeated_element_definition_same_section_uses_last_value(write_lattice):
    """
    Repeated element definitions in one section should use the final value.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = (L = 1.0) D1 = (L = 2.0);
        """,
        filename = "repeated_element_same_section_last_wins.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d1"]["l"] == pytest.approx(2.0), (
        "Repeated element definitions in one section should use the final "
        "definition.")

def test_repeated_element_name_across_types_raises_clear_error(write_lattice):
    """
    SAD rejects reusing an element name across different element types.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT E1 = (L = 1.0);
        QUAD E1 = (L = 1.0 K1 = 0.2);
        """,
        filename = "repeated_element_name_across_types.sad")

    with pytest.raises(ValueError, match = "e1"):
        parse_sad_file(str(lattice_path), Config(_verbose = False))

################################################################################
# Repeated Element Parameters
################################################################################
def test_repeated_element_parameter_uses_last_value(write_lattice):
    """
    Repeated element parameters should use the final parameter value.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = (L = 1.0 L = 2.0);
        """,
        filename = "repeated_element_parameter_last_wins.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d1"]["l"] == pytest.approx(2.0), (
        "Repeated element parameters should use the final value.")
