"""
================================================================================
SAD syntax assumptions: LINE definitions
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-24
================================================================================
"""

################################################################################
# Line names containing the substring "line"
################################################################################
def test_line_name_containing_line_substring_is_accepted(sad_accepts):
    """
    SAD accepts a line whose name contains 'line' as a substring. The word
    'line' in the identifier must not be treated as the LINE keyword.
    """
    sad_accepts(
        "MARK START = ()\n"
        "     END   = ();\n"
        "DRIFT D1 = (L=1.0);\n"
        "LINE MYLINE = (START D1 END);\n"
        "LINE TEST = (MYLINE);")


def test_nested_line_reference_containing_line_substring_is_accepted(sad_accepts):
    """
    SAD accepts a reference to a line whose name contains 'line' as a substring
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
