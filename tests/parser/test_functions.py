"""
================================================================================
Tests for SAD parser function expression handling
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
import pytest

from sad2xs.config import Config
from sad2xs.converter._001_parser import parse_sad_file

################################################################################
# SAD Function Definitions
#
# See tests/parser/README.md's "test_functions.py note" for why these are
# rejected outright and why the tests below are consolidated to two.
################################################################################
def test_sad_function_definition_raises_clear_error(write_lattice):
    """
    A SAD function definition should raise a clear, explicit error rather than
    being silently misparsed as a deferred expression.
    """
    lattice_path = write_lattice(
        """\
        FFS;
        MOMENTUM = 1.0 GEV;
        OFFSET = 0.25;
        F[x_] := x + OFFSET;
        """,
        filename = "function_definition_rejected.sad")

    with pytest.raises(ValueError, match = "not supported") as exc_info:
        parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert "line 4" in str(exc_info.value), (
        "The rejection error should cite the source line of the function "
        "definition.")

def test_sad_function_definition_with_module_body_raises_clear_error(write_lattice):
    """
    A SAD function definition with a Module[] body should also be rejected
    clearly, even though the body's internal `;` splits it across sections.
    """
    lattice_path = write_lattice(
        """\
        FFS;
        MOMENTUM = 1.0 GEV;
        OFFSET = 0.25;
        F[x_] := Module[{y}, y = x + OFFSET; y];
        """,
        filename = "function_definition_module_rejected.sad")

    with pytest.raises(ValueError, match = "not supported"):
        parse_sad_file(str(lattice_path), Config(_verbose = False))
