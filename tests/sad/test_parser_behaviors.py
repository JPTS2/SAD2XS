"""
================================================================================
SAD syntax assumptions: parser-level behaviours
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-25
================================================================================
"""
import os

import pytest

from sad2xs.config import PROTECTED_ELEMENT_NAMES
from sad2xs.sad_helpers import twiss_sad

################################################################################
# Global keyword prefix collisions
#
# SAD special globals: MOMENTUM, MASS, CHARGE, FSHIFT.
# Names that begin with one of those keywords but are not an exact match
# (e.g. MOMENTUM_OFFSET) should be ordinary user variables, not special globals.
#
# The conftest fixture already prepends "MOMENTUM = 1.0 GEV;" to every lattice.
################################################################################

@pytest.mark.parametrize("name, value", [
    ("MOMENTUM_OFFSET", 1.0),
    ("MASS_SCALE",      1.0),
    ("CHARGE_STATE",    1.0),
    ("FSHIFT_VALUE",    1.0),
])
def test_global_keyword_prefix_collision_is_accepted_as_variable(
        sad_accepts, name, value):
    """
    Names that begin with a SAD global keyword followed by '_...' should be
    accepted as plain user variables, not absorbed as the special global.
    Covers MOMENTUM, MASS, CHARGE, and FSHIFT prefix collisions.
    """
    sad_accepts(
        f"{name} = {value};\n"
        f"DRIFT D1 = (L = {name});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")


################################################################################
# Repeated element names across different element types
#
# SAD rejects reusing the same element name across different element types.
# Same-type repetition (final definition wins) should remain accepted.
################################################################################

def test_repeated_element_name_across_types_is_rejected(sad_rejects):
    """
    SAD should reject a lattice where the same element name is used for two
    different element types.
    """
    sad_rejects(
        "DRIFT E1 = (L = 1.0);\n"
        "QUAD  E1 = (L = 1.0 K1 = 0.2);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START E1 END);")


def test_repeated_element_name_same_type_is_accepted(sad_accepts):
    """
    SAD should accept repeated definitions of the same element name within the
    same element type — the final definition takes effect.
    """
    sad_accepts(
        "DRIFT E1 = (L = 1.0);\n"
        "DRIFT E1 = (L = 2.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START E1 END);")


################################################################################
# Multiline deferred expressions
#
# SAD accepts deferred expressions that span multiple physical lines, treating
# the continuation as part of the same expression until the closing semicolon.
################################################################################

def test_multiline_deferred_expression_is_accepted(sad_accepts):
    """
    SAD accepts a deferred expression split across two lines and evaluates the
    full expression correctly. The result should be usable as an element parameter.
    """
    sad_accepts(
        "A = 1.0 +\n"
        "    2.0;\n"
        "DRIFT D1 = (L = A);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")


################################################################################
# Protected element names (SAD2XS-level guard)
#
# These names collide with Xsuite environment variables created during
# conversion. SAD itself has no restriction on using them as element names —
# the protection is a SAD2XS concern, not a SAD concern.
################################################################################

@pytest.mark.parametrize("protected_name", sorted(PROTECTED_ELEMENT_NAMES))
def test_protected_element_name_is_accepted_by_sad(sad_accepts, protected_name):
    """
    SAD accepts element definitions whose names collide with SAD2XS protected
    names. The SAD2XS guard is needed precisely because SAD does not enforce it.
    """
    sad_accepts(
        f"DRIFT {protected_name.upper()} = (L = 1.0);\n"
        f"MARK START = ()\n     END   = ();\n"
        f"LINE TEST = (START {protected_name.upper()} END);")


def test_fshift_as_element_name_is_rejected_by_sad(sad_rejects):
    """
    FSHIFT is a SAD global keyword: SAD rejects it as an element name.
    It is therefore not in the SAD2XS protected-name set — SAD handles this
    case itself before conversion is ever attempted.
    """
    sad_rejects(
        "DRIFT FSHIFT = (L = 1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START FSHIFT END);")


################################################################################
# Math functions and nested parentheses in element parameters
#
# SAD FFS is Mathematica-based. These tests confirm which built-in math
# functions are accepted in element parameter expressions, and that nested
# parentheses evaluate correctly. Results are verified via the total
# s-coordinate of a drift whose length is the expression under test.
################################################################################

def test_element_parameter_with_nested_parentheses_evaluates_correctly(tmp_path):
    """
    SAD accepts nested parentheses in element parameter values.
    '(L0 + DL) / 2' with L0=2.0, DL=0.5 should give a drift of length 1.25.
    """
    lattice = tmp_path / "test.sad"
    lattice.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        "L0 = 2.0;\n"
        "DL = 0.5;\n"
        "DRIFT D = (L = (L0 + DL) / 2);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        tw = twiss_sad(
            lattice_filepath    = lattice.name,
            line_name           = "TEST",
            calc6d              = False,
            closed              = False,
            additional_commands = "")
    finally:
        os.chdir(cwd)
    assert tw["s"][-1] == pytest.approx(1.25), (
        "Nested parentheses expression '(L0 + DL) / 2' should evaluate to 1.25.")


@pytest.mark.parametrize("func_expr, expected_length", [
    ("SQRT(4.0)",   2.0),
    ("SIN(1.5708)", pytest.approx(1.0, abs=1e-4)),   # sin(π/2) ≈ 1.0
    ("COS(0.0)",    1.0),
    ("TAN(0.7854)", pytest.approx(1.0, abs=1e-4)),   # tan(π/4) ≈ 1.0
    ("EXP(0.0)",    1.0),
    ("LOG(10.0)",   1.0),                             # SAD LOG is base-10
    ("LN(2.7183)",  pytest.approx(1.0, abs=1e-4)),   # SAD LN is natural log
])
def test_element_parameter_math_function_evaluates_correctly(tmp_path, func_expr, expected_length):
    """
    SAD accepts these math functions in element parameter values.
    Each is used as a drift length and verified via twiss s-coordinate.
    Key notes: LOG is base-10 (not natural log); LN is natural log.
    ABS, LOG10, LOG2 are not valid SAD syntax (parser error).
    """
    lattice = tmp_path / "test.sad"
    lattice.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        f"DRIFT D = (L = {func_expr});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        tw = twiss_sad(
            lattice_filepath    = lattice.name,
            line_name           = "TEST",
            calc6d              = False,
            closed              = False,
            additional_commands = "")
    finally:
        os.chdir(cwd)
    assert tw["s"][-1] == expected_length, (
        f"Math function '{func_expr}' should evaluate to {expected_length}.")


@pytest.mark.parametrize("func_expr", [
    "ABS(-3.0)",
    "LOG10(10.0)",
    "LOG2(2.0)",
])
def test_unsupported_math_function_is_rejected_by_sad(sad_rejects, func_expr):
    """
    ABS, LOG10, and LOG2 are not valid SAD FFS function names and are rejected
    with a parser error. SAD's log functions are LOG (base-10) and LN (natural).
    """
    sad_rejects(
        f"DRIFT D = (L = {func_expr});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D END);")


################################################################################
# Malformed LINE definitions
#
# These are invalid SAD syntax — confirming SAD rejects them establishes that
# any SAD2XS error for these inputs is consistent with SAD's own behaviour.
################################################################################

def test_line_without_equals_produces_correct_length(tmp_path):
    """
    SAD accepts LINE definitions without '='. Verify that the resulting line
    still contains the expected element by checking the total s-coordinate.
    """
    lattice = tmp_path / "test.sad"
    lattice.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        "DRIFT D1 = (L = 1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST (START D1 END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        tw = twiss_sad(
            lattice_filepath    = lattice.name,
            line_name           = "TEST",
            calc6d              = False,
            closed              = False,
            additional_commands = "")
    finally:
        os.chdir(cwd)
    assert tw["s"][-1] == pytest.approx(1.0), (
        "LINE without '=' should produce a line with the expected total length.")


def test_line_without_parentheses_produces_correct_length(tmp_path):
    """
    SAD accepts LINE definitions without parentheses. Verify that the resulting
    line still contains the expected element by checking the total s-coordinate.
    """
    lattice = tmp_path / "test.sad"
    lattice.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        "DRIFT D1 = (L = 1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = START D1 END;\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        tw = twiss_sad(
            lattice_filepath    = lattice.name,
            line_name           = "TEST",
            calc6d              = False,
            closed              = False,
            additional_commands = "")
    finally:
        os.chdir(cwd)
    assert tw["s"][-1] == pytest.approx(1.0), (
        "LINE without parentheses should produce a line with the expected total length.")


def test_malformed_line_extra_closing_parenthesis_is_rejected_by_sad(sad_rejects):
    """
    A LINE definition with an unmatched closing parenthesis is invalid SAD syntax.
    """
    sad_rejects(
        "DRIFT D1 = (L = 1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END));")


################################################################################
# Invalid deferred expression syntax
################################################################################

def test_trailing_operator_expression_silently_absorbs_next_token(tmp_path):
    """
    SAD accepts 'A = 1.0 +;' without error but silently absorbs the next
    available numeric token — in this case the beam momentum (1.0 GeV = 1e9 eV
    in SAD internal units) — giving A = 1e9 rather than 1.0. This is a silent
    corruption: the trailing '+' is not a syntax error in SAD but the result is
    meaningless. SAD2XS should catch this and raise a clear error.
    """
    lattice = tmp_path / "test.sad"
    lattice.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        "A = 1.0 +;\n"
        "DRIFT D1 = (L = A);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        tw = twiss_sad(
            lattice_filepath    = lattice.name,
            line_name           = "TEST",
            calc6d              = False,
            closed              = False,
            additional_commands = "")
    finally:
        os.chdir(cwd)
    assert tw["s"][-1] == pytest.approx(1e9), (
        "SAD silently absorbs the momentum value (1e9 eV) into the trailing "
        "'+', producing A = 1e9 rather than 1.0.")


################################################################################
# ON/OFF prefix collisions
#
# SAD simulation commands: ON <flag>, OFF <flag>.
# Variable names that begin with ON or OFF (e.g. ONVALUE, OFFVALUE) must not
# be treated as simulation commands and silently discarded.
################################################################################

@pytest.mark.parametrize("name, value", [
    ("ONVALUE",  1.0),
    ("OFFVALUE", 1.0),
])
def test_on_off_prefix_variable_is_accepted_as_variable(
        sad_accepts, name, value):
    """
    Variable names beginning with ON or OFF should be accepted as plain user
    variables, not silently removed as simulation commands.
    """
    sad_accepts(
        f"{name} = {value};\n"
        f"DRIFT D1 = (L = {name});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

################################################################################
# MOMENTUM requirement
#
# Verify whether SAD itself requires a MOMENTUM statement. The conftest helper
# always prepends MOMENTUM, so this test calls twiss_sad directly.
################################################################################
def test_sad_rejects_lattice_without_momentum(tmp_path):
    """
    SAD should reject a lattice that has no MOMENTUM statement.
    Confirms that the converter's ValueError for missing momentum mirrors SAD's
    own behaviour, and that there is no SAD default momentum to discover.
    """
    import subprocess
    lattice = tmp_path / "no_momentum.sad"
    lattice.write_text(
        "MARK START = ();\n"
        "LINE TEST = (START);\n")

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with pytest.raises((subprocess.CalledProcessError, ValueError)):
            twiss_sad(
                lattice_filepath    = lattice.name,
                line_name           = "TEST",
                calc6d              = False,
                closed              = False,
                additional_commands = "")
    finally:
        os.chdir(cwd)
