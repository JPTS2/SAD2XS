"""
================================================================================
Tests for SAD parser deferred expressions
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
from sad2xs.converter._003_expression_converter import (
    convert_expressions,
    parse_expression)

def parse_and_convert_expressions(lattice_path, config = None):
    """
    Parse a SAD file and convert its deferred expressions to an environment.
    """
    if config is None:
        config = Config(_verbose = False)

    parsed = parse_sad_file(str(lattice_path), config)
    environment = xt.Environment()
    convert_expressions(
        parsed_lattice_data = parsed,
        environment         = environment,
        config              = config)
    return parsed, environment

################################################################################
# Direct Expression Parsing
################################################################################
def test_parse_expression_converts_numeric_types():
    """
    Expression parsing should convert numeric-like inputs to floats.
    """
    assert parse_expression(1) == pytest.approx(1.0), (
        "Integer expressions should convert to floats.")
    assert parse_expression(1.5) == pytest.approx(1.5), (
        "Float expressions should be returned unchanged.")
    assert parse_expression(" 2.5 ") == pytest.approx(2.5), (
        "Numeric strings should convert to floats after stripping whitespace.")

def test_parse_expression_preserves_symbolic_text():
    """
    Non-numeric expressions should be stripped but otherwise preserved.
    """
    assert parse_expression(" l0 + dl ") == "l0 + dl", (
        "Symbolic expression text should be stripped and preserved.")

def test_parse_expression_rejects_unsupported_types():
    """
    Unsupported expression input types should fail clearly.
    """
    with pytest.raises(TypeError, match = "Unsupported type"):
        parse_expression(["l0"])

################################################################################
# Deferred Expression Parsing
################################################################################
def test_deferred_expressions_are_parsed_separately_from_globals(write_lattice):
    """
    Non-special assignments should be parsed as deferred expressions.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        KBASE = 0.2;
        DK = KBASE / 2;
        """,
        filename = "deferred_expression_parsing.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["expressions"]["kbase"] == pytest.approx(0.2), (
        "Numeric deferred expressions should parse as floats.")
    assert parsed["expressions"]["dk"] == "kbase / 2", (
        "Symbolic deferred expressions should preserve their expression text.")
    assert "kbase" not in parsed["globals"], (
        "Ordinary deferred expressions should not be stored as globals.")

def test_scientific_notation_deferred_expression_parses_as_float(write_lattice):
    """
    Scientific-notation deferred expressions should classify as numeric floats
    at parse time, not fall through to the symbolic-expression string branch.

    A prior narrower numeric fast-path (accepting only digits, '.', and '-')
    stored values like '1.0e9' as strings. They still resolved correctly one
    stage later via parse_expression()'s float() call, but the parser's own
    classification was wrong — which matters for helpers such as
    is_effectively_zero() that treat any string as unconditionally non-zero.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A = 1.0E9;
        B = -2.5e-3;
        """,
        filename = "deferred_expression_scientific_notation.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert isinstance(parsed["expressions"]["a"], float), (
        "Scientific-notation deferred expressions should parse directly as "
        "floats, not remain classified as symbolic-expression strings.")
    assert parsed["expressions"]["a"] == pytest.approx(1.0E9)
    assert isinstance(parsed["expressions"]["b"], float), (
        "Negative scientific-notation deferred expressions should also parse "
        "directly as floats.")
    assert parsed["expressions"]["b"] == pytest.approx(-2.5E-3)

################################################################################
# Deferred Expression Conversion
################################################################################
def test_deferred_numeric_forms_convert_to_environment(write_lattice):
    """
    SAD-supported numeric forms should convert to numeric environment values.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A = +1.0;
        B = 1E-3;
        C = .5;
        D = 1.;
        """,
        filename = "deferred_expression_numeric_forms.sad")

    _, environment = parse_and_convert_expressions(lattice_path)

    assert environment["a"] == pytest.approx(1.0), (
        "Explicit plus-sign numeric expressions should convert to floats.")
    assert environment["b"] == pytest.approx(1.0E-3), (
        "Scientific-notation expressions should convert to floats.")
    assert environment["c"] == pytest.approx(0.5), (
        "Leading-decimal numeric expressions should convert to floats.")
    assert environment["d"] == pytest.approx(1.0), (
        "Trailing-decimal numeric expressions should convert to floats.")

def test_compact_deferred_expression_assignments_convert(write_lattice):
    """
    Deferred expressions without spaces around '=' should be supported.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A=1.0;
        B=A+1.0;
        """,
        filename = "deferred_expression_compact_assignment.sad")

    _, environment = parse_and_convert_expressions(lattice_path)

    assert environment["a"] == pytest.approx(1.0), (
        "Compact base assignments should convert to the environment.")
    assert environment["b"] == pytest.approx(2.0), (
        "Compact dependent assignments should resolve in the environment.")

def test_multiline_deferred_expression_converts(write_lattice):
    """
    SAD-supported multiline deferred expressions should convert correctly.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A = 1.0 +
            2.0;
        """,
        filename = "deferred_expression_multiline.sad")

    _, environment = parse_and_convert_expressions(lattice_path)

    assert environment["a"] == pytest.approx(3.0), (
        "Multiline deferred expressions should preserve and evaluate the full "
        "expression.")

def test_deferred_expression_dependency_chain_converts_to_environment(write_lattice):
    """
    Expression dependencies should resolve in dependency order.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A = 1.0;
        B = A + 1.0;
        C = B + 1.0;
        """,
        filename = "deferred_expression_dependency_chain.sad")

    _, environment = parse_and_convert_expressions(lattice_path)

    assert environment["a"] == pytest.approx(1.0), (
        "Base expression should convert to the environment.")
    assert environment["b"] == pytest.approx(2.0), (
        "First dependent expression should resolve in the environment.")
    assert environment["c"] == pytest.approx(3.0), (
        "Second dependent expression should resolve in the environment.")

def test_ten_step_deferred_expression_dependency_chain_converts(write_lattice):
    """
    A ten-step dependency chain should convert fully.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A1 = 1.0;
        A2 = A1 + 1.0;
        A3 = A2 + 1.0;
        A4 = A3 + 1.0;
        A5 = A4 + 1.0;
        A6 = A5 + 1.0;
        A7 = A6 + 1.0;
        A8 = A7 + 1.0;
        A9 = A8 + 1.0;
        A10 = A9 + 1.0;
        """,
        filename = "deferred_expression_ten_step_dependency.sad")

    _, environment = parse_and_convert_expressions(lattice_path)

    assert environment["a10"] == pytest.approx(10.0), (
        "Ten-step deferred expression chains should resolve fully.")

def test_eleven_step_deferred_expression_dependency_chain_converts(write_lattice):
    """
    Dependency resolution should not be limited by the current 10-pass loop.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A1 = 1.0;
        A2 = A1 + 1.0;
        A3 = A2 + 1.0;
        A4 = A3 + 1.0;
        A5 = A4 + 1.0;
        A6 = A5 + 1.0;
        A7 = A6 + 1.0;
        A8 = A7 + 1.0;
        A9 = A8 + 1.0;
        A10 = A9 + 1.0;
        A11 = A10 + 1.0;
        """,
        filename = "deferred_expression_eleven_step_dependency.sad")

    _, environment = parse_and_convert_expressions(lattice_path)

    assert environment["a11"] == pytest.approx(11.0), (
        "Deferred expression dependency resolution should handle chains longer "
        "than ten expressions.")

def test_out_of_order_deferred_expression_dependencies_convert(write_lattice):
    """
    Out-of-order dependencies should resolve after repeated conversion passes.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        C = B + 1.0;
        A = 1.0;
        B = A + 1.0;
        """,
        filename = "deferred_expression_out_of_order.sad")

    _, environment = parse_and_convert_expressions(lattice_path)

    assert environment["c"] == pytest.approx(3.0), (
        "Out-of-order expression dependencies should resolve after repeated "
        "conversion passes.")

def test_element_expression_uses_converted_deferred_expression(write_lattice):
    """
    Converted deferred expressions should be usable by element expressions.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A = 1.0;
        B = A + 1.0;
        DRIFT D1 = (L = B);
        """,
        filename = "deferred_expression_used_by_element.sad")

    parsed, environment = parse_and_convert_expressions(lattice_path)
    environment.new(
        name      = "d1",
        prototype = xt.Drift,
        length    = parsed["elements"]["drift"]["d1"]["l"])

    assert environment["d1"].length == pytest.approx(2.0), (
        "Element parameters should resolve converted deferred expressions.")

def test_intrinsic_function_deferred_expression_converts(write_lattice):
    """
    SAD intrinsic functions in deferred expressions should convert.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 4.0;
        A = SQRT(L0);
        """,
        filename = "deferred_expression_intrinsic_function.sad")

    _, environment = parse_and_convert_expressions(lattice_path)

    assert environment["a"] == pytest.approx(2.0), (
        "SAD intrinsic function expressions should resolve in the environment.")

def test_unresolved_deferred_expression_dependency_raises_clear_error(write_lattice):
    """
    Missing dependencies should raise a clear conversion error.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A = MISSING + 1.0;
        """,
        filename = "deferred_expression_unresolved.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))
    environment = xt.Environment()

    with pytest.raises(ValueError, match = "Not all expressions"):
        convert_expressions(
            parsed_lattice_data = parsed,
            environment         = environment,
            config              = Config(_verbose = False))

def test_circular_deferred_expression_dependency_raises_clear_error(write_lattice):
    """
    Circular expression dependencies should not be silently accepted.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        A = B + 1.0;
        B = A + 1.0;
        """,
        filename = "deferred_expression_circular.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))
    environment = xt.Environment()

    with pytest.raises(ValueError, match = "Not all expressions"):
        convert_expressions(
            parsed_lattice_data = parsed,
            environment         = environment,
            config              = Config(_verbose = False))
