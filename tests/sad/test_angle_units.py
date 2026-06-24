"""
================================================================================
SAD syntax assumptions: angle unit suffixes
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
# ROTATE angle unit suffixes
################################################################################
def test_rotate_without_unit_suffix_is_accepted(sad_accepts):
    """
    SAD accepts a plain numeric ROTATE value with no unit suffix.
    The default unit in SAD for angle parameters is radians.
    """
    sad_accepts(
        "MARK START = ()\n"
        "     END   = ();\n"
        "MOMENTUM = 1.0 GEV;\n"
        "QUAD Q = (L = 1.0 ROTATE = 0.1);\n"
        "LINE TEST = (START Q END);")


def test_rotate_with_rad_suffix_is_accepted(sad_accepts):
    """
    SAD accepts an explicit RAD suffix on ROTATE. The value is in radians
    and should be treated identically to the same value without a suffix.
    """
    sad_accepts(
        "MARK START = ()\n"
        "     END   = ();\n"
        "MOMENTUM = 1.0 GEV;\n"
        "QUAD Q = (L = 1.0 ROTATE = 0.1 RAD);\n"
        "LINE TEST = (START Q END);")


def test_rotate_with_deg_suffix_is_accepted(sad_accepts):
    """
    SAD accepts a DEG suffix on ROTATE. The value is in degrees and SAD
    converts it to radians internally before applying the rotation.
    """
    sad_accepts(
        "MARK START = ()\n"
        "     END   = ();\n"
        "MOMENTUM = 1.0 GEV;\n"
        "QUAD Q = (L = 1.0 ROTATE = 45 DEG);\n"
        "LINE TEST = (START Q END);")
