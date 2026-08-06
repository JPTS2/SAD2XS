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
# Required Packages
################################################################################
import os

import numpy as np
import pytest

from sad2xs.sad_helpers import twiss_sad

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

################################################################################
# ANGLE angle unit suffixes (BEND)
#
# BEND's ANGLE parameter is a separate SAD keyword from QUAD/SEXT/OCT's
# ROTATE, so its unit-suffix handling is verified independently rather than
# assumed to follow from the ROTATE tests above.
################################################################################
def test_angle_without_unit_suffix_is_accepted(sad_accepts):
    """
    SAD accepts a plain numeric ANGLE value with no unit suffix (radians).
    """
    sad_accepts(
        "MARK START = ()\n"
        "     END   = ();\n"
        "MOMENTUM = 1.0 GEV;\n"
        "BEND B = (L = 1.0 ANGLE = 0.1);\n"
        "LINE TEST = (START B END);")


def test_angle_with_rad_suffix_is_accepted(sad_accepts):
    """
    SAD accepts an explicit RAD suffix on ANGLE, treated identically to the
    same value without a suffix.
    """
    sad_accepts(
        "MARK START = ()\n"
        "     END   = ();\n"
        "MOMENTUM = 1.0 GEV;\n"
        "BEND B = (L = 1.0 ANGLE = 0.1 RAD);\n"
        "LINE TEST = (START B END);")


def test_angle_with_deg_suffix_is_accepted(sad_accepts):
    """
    SAD accepts a DEG suffix on ANGLE.
    """
    sad_accepts(
        "MARK START = ()\n"
        "     END   = ();\n"
        "MOMENTUM = 1.0 GEV;\n"
        "BEND B = (L = 1.0 ANGLE = 5 DEG);\n"
        "LINE TEST = (START B END);")


def test_angle_deg_suffix_converts_to_the_same_radian_value(tmp_path):
    """
    ANGLE = 90 DEG should give exactly the same Twiss result as
    ANGLE = pi/2 (radians) — confirming the DEG conversion factor is
    correct, not just that the syntax is accepted.
    """
    def run(angle_expr, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"BEND B = (L=1.0 ANGLE={angle_expr});\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START B END);\n")
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            return twiss_sad(
                lattice_filepath    = lat.name,
                line_name           = "TEST",
                calc6d              = False,
                closed              = False,
                additional_commands = "")
        finally:
            os.chdir(cwd)

    tw_deg = run("90 DEG", "angle_deg.sad")
    tw_rad = run(f"{np.pi / 2:.12f}", "angle_rad.sad")
    assert tw_deg["betx"][-1] == pytest.approx(tw_rad["betx"][-1], rel=1e-6), (
        "ANGLE = 90 DEG should give the same Twiss betx as ANGLE = pi/2 "
        "radians — confirms the DEG-to-radian conversion factor is exact.")
