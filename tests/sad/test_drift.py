"""
================================================================================
SAD syntax assumptions: DRIFT element
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

from sad2xs.sad_helpers import track_sad, twiss_sad

################################################################################
# Rejected parameters
# DRIFT accepts only L — no misalignment parameters.
################################################################################
def test_drift_rejects_dx(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_dy(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 DY=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_rotate(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 ROTATE=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_angle(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_k0(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 K0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_sk0(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 SK0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_k1(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 K1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_sk1(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 SK1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_k2(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 K2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_sk2(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 SK2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_k3(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 K3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_sk3(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 SK3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_k4(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 K4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_sk4(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 SK4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_bz(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_harm(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 HARM=1000);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

def test_drift_rejects_freq(sad_rejects):
    sad_rejects(
        "DRIFT D1 = (L=1.0 FREQ=400E6);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);")

################################################################################
# Effect on Twiss and tracking
#
# DRIFT's only parameter, L, determines the total line length in Twiss and
# leaves a particle's transverse coordinates geometrically propagated (not
# perturbed) in tracking.
################################################################################
def test_drift_length_matches_l_parameter(tmp_path):
    """
    A DRIFT's L parameter should determine the total Twiss s-coordinate.
    """
    lat = tmp_path / "test.sad"
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        "DRIFT D1 = (L=2.5);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        tw = twiss_sad(
            lattice_filepath    = lat.name,
            line_name           = "TEST",
            calc6d              = False,
            closed              = False,
            additional_commands = "")
    finally:
        os.chdir(cwd)
    assert tw["s"][-1] == pytest.approx(2.5), (
        "DRIFT L=2.5 should give a total line length of 2.5.")

def test_drift_applies_correct_transverse_map_in_tracking(tmp_path):
    """
    A DRIFT should geometrically propagate a particle without perturbing it:
    for x0=0, px0=1e-3 through a 1 m drift, x_final = x0 + px0*L = 1e-3 and
    px is unchanged.
    """
    lat = tmp_path / "test.sad"
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        "DRIFT D1 = (L=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START D1 END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = track_sad(
            lattice_filepath    = lat.name,
            line_name           = "TEST",
            x_init              = np.array([0.0]),
            px_init             = np.array([1e-3]),
            y_init              = np.array([0.0]),
            py_init             = np.array([0.0]),
            zeta_init           = np.array([0.0]),
            delta_init          = np.array([0.0]),
            n_turns             = 1,
            rfsw                = False,
            with_progress       = False)
    finally:
        os.chdir(cwd)
    assert result["x"][0] == pytest.approx(1e-3, abs=1e-9), (
        "After a 1 m drift with px0=1e-3, x should be px0*L = 1e-3.")
    assert result["px"][0] == pytest.approx(1e-3, abs=1e-12), (
        "A drift should not change px.")
