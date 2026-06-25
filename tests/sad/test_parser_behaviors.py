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
import pytest

################################################################################
# Issue #49 — Global keyword prefix collisions
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
