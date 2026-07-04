"""
(Unofficial) SAD to XSuite Converter: Expression Converter
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-12-2025
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
    Docstring for convert_expressions

    :param parsed_lattice_data: Description
    :type parsed_lattice_data: dict
    :param environment: Description
    :type environment: xt.Environment
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
            f"'{var_name} = {parsed_expressions[var_name]}'"
            for var_name in unresolved)
        raise ValueError(
            "Not all expressions could be evaluated. "
            "Please check your SAD lattice for invalid expression syntax. "
            f"Unresolved: {unresolved_detail}")

    logger.info(f"Converted {len(converted_expressions)} deferred expressions")
