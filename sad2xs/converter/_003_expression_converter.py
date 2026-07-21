"""
================================================================================
Expression Converter
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-20
================================================================================
"""

################################################################################
# Required Packages
################################################################################
import logging

import xtrack as xt

from ..helpers import log_section_heading
from ._000_helpers import parse_expression

logger  = logging.getLogger(__name__)

################################################################################
# Convert Deferred Expressions
################################################################################
def convert_expressions(
        parsed_lattice_data:    dict,
        environment:            xt.Environment) -> None:
    """
    Convert SAD globals and deferred expressions into live xdeps
    expressions in the Xsuite environment.

    Global variables and deferred expressions may reference each other
    in any order, so each group is retried up to 10 times, registering
    whichever entries successfully resolve on each pass, until either
    every entry converts or no further progress is possible.

    Parameters
    ----------
    parsed_lattice_data : dict
        Parsed lattice data, as returned by `parse_sad_file`.
    environment : xt.Environment
        The Xsuite environment to register variables and expressions
        into.

    Raises
    ------
    ValueError
        If any global variable or deferred expression cannot be
        resolved after 10 passes (e.g. a circular or invalid
        reference).
    """

    ########################################
    # Get the required data
    ########################################
    parsed_globals              = parsed_lattice_data["globals"]
    parsed_expressions          = parsed_lattice_data["expressions"]
    parsed_expression_line_nos  = parsed_lattice_data["expression_line_numbers"]

    ########################################
    # Create global variables
    ########################################
    log_section_heading("Converting Global Variable Expressions", mode = "section")

    # Variables may depend on other variables, so have to parse them in order
    # Here, just try a few times to parse them
    converted_globals = []
    for _ in range(10):
        for var_name, var_value in parsed_globals.items():

            if var_name in converted_globals:
                continue

            var_value   = parse_expression(var_value)
            try:
                environment[var_name] = var_value
                converted_globals.append(var_name)
            except KeyError:
                continue

    if len(converted_globals) != len(parsed_globals):
        unparsed = sorted(
            var_name for var_name in parsed_globals
            if var_name not in converted_globals)
        raise ValueError(
            "Not all global variables could be parsed. "
            f"Unparsed: {unparsed}")

    logger.info(f"Converted {len(converted_globals)} global variables")

    ########################################
    # Create expressions
    ########################################
    log_section_heading("Converting Deferred Expressions", mode = "section")

    # Variables may depend on other variables, so have to parse them in order
    # Here, just try a few times to parse them
    converted_expressions = []
    for i in range(10):
        for var_name, var_value in parsed_expressions.items():

            if var_name in converted_expressions:
                continue

            var_value   = parse_expression(var_value)
            try:
                environment[var_name] = var_value
                converted_expressions.append(var_name)
            except Exception:
                continue

    if len(converted_expressions) != len(parsed_expressions):
        unresolved = [
            var_name for var_name in parsed_expressions
            if var_name not in converted_expressions]
        unresolved_detail = "; ".join(
            f"line {parsed_expression_line_nos[var_name]}: "
            f"""\"{var_name} = {parsed_expressions[var_name]}\""""
            for var_name in unresolved)
        raise ValueError(
            "Not all expressions could be evaluated. "
            "Please check your SAD lattice for invalid expression syntax. "
            f"Unresolved: {unresolved_detail}")

    logger.info(f"Converted {len(converted_expressions)} deferred expressions")
