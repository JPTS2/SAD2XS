"""
================================================================================
SAD syntax assumptions: LINE definitions
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-08
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest

################################################################################
# Line names containing the substring "line"
################################################################################
def test_line_name_containing_line_substring_is_accepted(sad_accepts):
    """
    SAD accepts a line whose name contains `line` as a substring. The word
    `line` in the identifier must not be treated as the LINE keyword.
    """
    sad_accepts(
        "MARK START = ()\n"
        "     END   = ();\n"
        "DRIFT D1 = (L=1.0);\n"
        "LINE MYLINE = (START D1 END);\n"
        "LINE TEST = (MYLINE);")


def test_nested_line_reference_containing_line_substring_is_accepted(sad_accepts):
    """
    SAD accepts a reference to a line whose name contains `line` as a substring
    when that line is itself nested inside another line definition.
    """
    sad_accepts(
        "MARK START = ()\n"
        "     END   = ();\n"
        "DRIFT D1 = (L=1.0);\n"
        "LINE MYLINE = (START D1 END);\n"
        "LINE INNERLINE = (MYLINE);\n"
        "LINE TEST = (INNERLINE);")


################################################################################
# LINE keyword split across a newline
################################################################################
def test_line_keyword_with_newline_before_name_is_accepted(sad_accepts):
    """
    SAD accepts a LINE definition where the keyword and the name are separated
    by a newline and indentation rather than a single space.
    """
    sad_accepts(
        "MARK START = ()\n"
        "     END   = ();\n"
        "DRIFT D1 = (L=1.0);\n"
        "LINE\n"
        "    TEST_LINE = (START D1 END);\n"
        "LINE TEST = (TEST_LINE);")


################################################################################
# "N*NAME" repetition
################################################################################
# A repetition count may precede a subline or a plain element name. A "-" may
# sit on either side of the "*", and one on each side cancels. See
# docs/reference/sad-behaviour.md for what each form expands to.
REPETITION_LATTICE = (
    "MARK START = ()\n"
    "     END   = ();\n"
    "DRIFT D1 = (L=1.0);\n"
    "QUAD  QF = (L=0.5 K1=0.1);\n"
    "LINE CELL = (D1 QF);\n"
    "LINE TEST = (START {component} END);")

@pytest.mark.parametrize("component", [
    "4*CELL",       # subline
    "4*D1",         # plain element
    "2 * CELL",     # whitespace around the "*"
    "-2*CELL",      # reversal sign before the count
    "2*-CELL",      # reversal sign before the name
    "-2*-CELL"])    # a sign in both positions
def test_repetition_forms_are_accepted(sad_accepts, component):
    """
    SAD accepts a repetition count before a subline or an element name, with
    or without whitespace around the "*", and with a reversal "-" in either
    or both positions.
    """
    sad_accepts(REPETITION_LATTICE.format(component = component))


def test_inline_parenthesised_group_is_rejected(sad_rejects):
    """
    SAD does not allow an anonymous ``(D1 QF)`` group inside a LINE.

    Multiple components must be given a subline name before that group can be
    referenced or repeated.
    """
    sad_rejects(REPETITION_LATTICE.format(component = "(D1 QF)"))


@pytest.mark.parametrize("component", [
    "0*CELL",       # zero count
    "2*(D1 QF)"])   # repetition of an anonymous inline group
def test_malformed_repetition_forms_are_rejected(sad_rejects, component):
    """
    SAD rejects a zero repetition count and repetition of an anonymous group.

    A valid repetition count may only precede an element or subline name.
    """
    sad_rejects(REPETITION_LATTICE.format(component = component))
