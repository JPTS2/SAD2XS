"""
================================================================================
Tests for SAD math function expression conversion to Xsuite
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-25
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

################################################################################
# Math function expression conversion
#
# SAD FFS accepts a specific set of math functions. After conversion the
# expressions are evaluated by Xsuite's Python-based environment. The function
# names and semantics must survive the SAD → Xsuite translation correctly.
#
# Key mismatches to verify:
#   SAD LOG(x)  = log base-10  — Python log(x) is natural log — must remap
#   SAD LN(x)   = natural log  — Python has no ln() — must remap
#
# Lattice uses a single MARK so we only need expression conversion, not element
# conversion. The environment value for `a` is checked directly.
################################################################################

@pytest.mark.parametrize("sad_func, argument, expected", [
    ("SQRT", "4.0",    2.0),
    ("SIN",  "1.5708", pytest.approx(1.0, abs=1e-4)),
    ("COS",  "0.0",    1.0),
    ("TAN",  "0.7854", pytest.approx(1.0, abs=1e-4)),
    ("EXP",  "0.0",    1.0),
    ("LOG",  "10.0",   1.0),   # SAD LOG is base-10 — must not become natural log
    ("LN",   "2.7183", pytest.approx(1.0, abs=1e-4)),   # SAD LN is natural log
])
def test_math_function_expression_converts_to_correct_value(
        write_lattice, sad_func, argument, expected):
    """
    Each SAD math function used in a deferred expression must evaluate to the
    same numeric value in Xsuite's environment as it does in SAD itself.
    """
    lattice_path = write_lattice(
        f"""\
        MOMENTUM = 1.0 GEV;
        A = {sad_func}({argument});
        MARK START = ();
        LINE TEST = (START);
        """,
        filename = f"math_func_{sad_func.lower()}.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))
    environment = xt.Environment()
    convert_expressions(
        parsed_lattice_data = parsed,
        environment         = environment)

    assert environment["a"] == expected, (
        f"SAD {sad_func}({argument}) must evaluate to {expected} "
        f"in the Xsuite environment after conversion.")
