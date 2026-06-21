"""
================================================================================
Tests for SAD parser function expression handling
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
from sad2xs.converter._004_element_converter import convert_drifts

def parse_and_convert_expressions(lattice_path, config = None):
    """
    Parse a SAD file and convert its expressions to an environment.
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
# SAD Function Definitions
################################################################################
def test_sad_function_definition_is_preserved(write_lattice):
    """
    SAD FFS function definitions should preserve name, argument, and body.
    """
    lattice_path = write_lattice(
        """\
        FFS;
        MOMENTUM = 1.0 GEV;
        OFFSET = 0.25;
        F[x_] := x + OFFSET;
        """,
        filename = "function_definition_parsing.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert "f[x_]" in parsed["expressions"], (
        "SAD function definitions should preserve the function signature "
        "without the delayed-assignment marker.")
    assert parsed["expressions"]["f[x_]"] == "x + offset", (
        "SAD function definitions should preserve the function body.")

def test_sad_function_definition_with_module_body_is_preserved(write_lattice):
    """
    SAD FFS Module function bodies should be preserved as complete expressions.
    """
    lattice_path = write_lattice(
        """\
        FFS;
        MOMENTUM = 1.0 GEV;
        OFFSET = 0.25;
        F[x_] := Module[{y}, y = x + OFFSET; y];
        """,
        filename = "function_definition_module_parsing.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["expressions"]["f[x_]"] == (
        "module[{y}, y = x + offset; y]"), (
        "SAD Module function bodies should preserve brackets, local variables, "
        "and inner statements.")

################################################################################
# SAD Function Calls
################################################################################
def test_sad_function_call_in_deferred_expression_converts(write_lattice):
    """
    SAD function calls in deferred expressions should resolve through globals.
    """
    lattice_path = write_lattice(
        """\
        FFS;
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        OFFSET = 0.25;
        F[x_] := x + OFFSET;
        A = F[L0];
        """,
        filename = "function_call_deferred_expression.sad")

    _, environment = parse_and_convert_expressions(lattice_path)

    assert environment["a"] == pytest.approx(1.25), (
        "SAD function calls in deferred expressions should resolve to numeric "
        "environment values.")

def test_sad_function_call_in_element_expression_converts(write_lattice):
    """
    SAD function calls in element parameters should resolve during conversion.
    """
    lattice_path = write_lattice(
        """\
        FFS;
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        OFFSET = 0.25;
        F[x_] := x + OFFSET;
        DRIFT D_FUNC = (L = F[L0]);
        """,
        filename = "function_call_element_expression.sad")

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

    assert environment["d_func"].length == pytest.approx(1.25), (
        "SAD function calls in element expressions should resolve to element "
        "parameter values.")

def test_nested_sad_function_call_in_deferred_expression_converts(write_lattice):
    """
    SAD functions should be able to call other SAD functions.
    """
    lattice_path = write_lattice(
        """\
        FFS;
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        F[x_] := x + 0.25;
        G[x_] := F[x] * 2;
        A = G[L0];
        """,
        filename = "function_call_nested_deferred_expression.sad")

    _, environment = parse_and_convert_expressions(lattice_path)

    assert environment["a"] == pytest.approx(2.5), (
        "Nested SAD function calls should resolve in deferred expressions.")
