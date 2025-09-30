"""
(Unofficial) SAD to XSuite Converter

Global and Deferred Expression Converter
"""

################################################################################
# Required Packages
################################################################################
import xtrack as xt

from .._globals import print_section_heading

################################################################################
# Parsing of strings and floats
################################################################################
def parse_expression(expression):
    """
    Try to convert s to float; if that fails, return s stripped
    """
    if type(expression) is float:
        return expression
    elif type(expression) is int:
        return float(expression)
    elif type(expression) is str:
        expression_stripped  = expression.strip()
        try:
            return float(expression_stripped)
        except ValueError:
            return expression_stripped
    else:
        raise TypeError(f"Unsupported type: {type(expression)}. Expected str, int, or float.")

################################################################################
# Convert Deferred Expressions
################################################################################
def convert_expressions(
        parsed_lattice_data:    dict,
        environment:            xt.Environment,
        verbose:                bool                = False) -> None:

    ########################################
    # Get the required data
    ########################################
    parsed_globals      = parsed_lattice_data['globals']
    parsed_expressions  = parsed_lattice_data['expressions']
    
    ########################################
    # Create global variables
    ########################################
    if verbose:
        print_section_heading("Converting Global Variable Expressions", mode = 'subsection')

    # Variables may depend on other variables, so have to parse them in order
    # Here, just try a few times to parse them
    converted_globals = []
    for i in range(10):
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
        raise ValueError("Not all global variables could be parsed. Check the input data.")

    ########################################
    # Create expressions
    ########################################
    if verbose:
        print_section_heading("Converting Deferred Expressions", mode = 'subsection')

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
            except KeyError:
                continue

    if len(converted_expressions) != len(parsed_expressions):
        raise ValueError("Not all expressions could be parsed. Check the input data.")