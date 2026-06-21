"""
================================================================================
Tests for SAD parser element expressions
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
import numpy as np
import pytest
import xtrack as xt

from sad2xs.config import Config
from sad2xs.converter._001_parser import parse_sad_file
from sad2xs.converter._003_expression_converter import convert_expressions
from sad2xs.converter._004_element_converter import convert_drifts

################################################################################
# Element Expressions
################################################################################
def test_element_parameters_accept_spaced_arithmetic_expressions(write_lattice):
    """
    Element values with spaced arithmetic should remain complete expressions.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        DL = 0.25;
        KBASE = 0.8;
        DK = 0.1;
        THETA = 0.02;

        DRIFT D_PLUS = (L = L0 + DL);
        DRIFT D_MINUS = (L = L0 - DL);
        QUAD Q_EXPR = (L = L0 + DL K1 = KBASE - DK ROTATE = 45 DEG);
        BEND B_EXPR = (L = 2 * L0 ANGLE = THETA / 2);
        """,
        filename = "element_spaced_expressions.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d_plus"]["l"] == "l0 + dl"
    assert parsed["elements"]["drift"]["d_minus"]["l"] == "l0 - dl"
    assert parsed["elements"]["quad"]["q_expr"]["l"] == "l0 + dl"
    assert parsed["elements"]["quad"]["q_expr"]["k1"] == "kbase - dk"
    assert parsed["elements"]["quad"]["q_expr"]["rotate"] == pytest.approx(
        np.pi / 4)
    assert parsed["elements"]["bend"]["b_expr"]["l"] == "2 * l0"
    assert parsed["elements"]["bend"]["b_expr"]["angle"] == "theta / 2"

def test_element_parameters_keep_compact_expressions_and_numeric_values(write_lattice):
    """
    Existing compact expressions and plain numeric parameters should be unchanged.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        DL = 0.25;
        KBASE = 0.8;
        DK = 0.1;

        DRIFT D_FLOAT = (L = 1.25);
        DRIFT D_COMPACT = (L = L0+DL);
        QUAD Q_FLOAT = (L = 2.0 K1 = 0.4);
        QUAD Q_COMPACT = (L = L0 K1 = KBASE-DK);
        """,
        filename = "element_compact_expressions.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d_float"]["l"] == pytest.approx(1.25)
    assert parsed["elements"]["drift"]["d_compact"]["l"] == "l0+dl"
    assert parsed["elements"]["quad"]["q_float"]["l"] == pytest.approx(2.0)
    assert parsed["elements"]["quad"]["q_float"]["k1"] == pytest.approx(0.4)
    assert parsed["elements"]["quad"]["q_compact"]["l"] == "l0"
    assert parsed["elements"]["quad"]["q_compact"]["k1"] == "kbase-dk"

def test_spaced_length_expression_can_be_evaluated_in_xsuite_environment(
        write_lattice):
    """
    Parsed spaced expressions should remain usable by Xsuite element creation.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        DL = 0.25;

        DRIFT D_EVAL = (L = L0 + DL);
        """,
        filename = "element_expression_evaluation.sad")

    config = Config(_verbose = False)
    parsed = parse_sad_file(str(lattice_path), config)

    environment = xt.Environment()
    convert_expressions(
        parsed_lattice_data = parsed,
        environment         = environment,
        config              = config)
    convert_drifts(
        parsed_elements = parsed["elements"],
        environment     = environment)

    assert environment["d_eval"].length == pytest.approx(1.25)

def test_element_expression_with_parentheses_is_preserved(write_lattice):
    """
    Parenthesised arithmetic should remain a complete element expression.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        DL = 0.25;

        DRIFT D_PAREN = (L = (L0 + DL) / 2);
        """,
        filename = "element_expression_parentheses.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d_paren"]["l"] == "(l0 + dl) / 2", (
        "Parenthesised element expressions should be preserved as one value.")

def test_element_expression_with_unary_sign_is_preserved(write_lattice):
    """
    Unary signs inside arithmetic expressions should not split parameters.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        DL = 0.25;

        DRIFT D_UNARY = (L = -L0 + DL);
        """,
        filename = "element_expression_unary_sign.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d_unary"]["l"] == "-l0 + dl", (
        "Unary signs should be preserved inside element expressions.")

def test_element_expression_with_math_function_is_preserved(write_lattice):
    """
    Function-style expression text should be preserved by the parser.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 4.0;

        DRIFT D_FUNC = (L = SQRT(L0));
        """,
        filename = "element_expression_math_function.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d_func"]["l"] == "sqrt(l0)", (
        "Function-style element expressions should be preserved in lowercase.")

def test_parenthesised_length_expression_can_be_evaluated_in_xsuite_environment(
        write_lattice):
    """
    Parenthesised parsed expressions should remain usable by Xsuite.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        DL = 0.25;

        DRIFT D_EVAL = (L = (L0 + DL) / 2);
        """,
        filename = "element_expression_parenthesised_evaluation.sad")

    config = Config(_verbose = False)
    parsed = parse_sad_file(str(lattice_path), config)

    environment = xt.Environment()
    convert_expressions(
        parsed_lattice_data = parsed,
        environment         = environment,
        config              = config)
    convert_drifts(
        parsed_elements = parsed["elements"],
        environment     = environment)

    assert environment["d_eval"].length == pytest.approx(0.625), (
        "Parenthesised element expressions should evaluate through Xsuite.")

def test_math_function_length_expression_can_be_evaluated_in_xsuite_environment(
        write_lattice):
    """
    Supported math function expressions should evaluate through Xsuite.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 4.0;

        DRIFT D_EVAL = (L = SQRT(L0));
        """,
        filename = "element_expression_function_evaluation.sad")

    config = Config(_verbose = False)
    parsed = parse_sad_file(str(lattice_path), config)

    environment = xt.Environment()
    convert_expressions(
        parsed_lattice_data = parsed,
        environment         = environment,
        config              = config)
    convert_drifts(
        parsed_elements = parsed["elements"],
        environment     = environment)

    assert environment["d_eval"].length == pytest.approx(2.0), (
        "Supported function expressions should evaluate through Xsuite.")
