"""
================================================================================
SAD syntax assumptions: MARK element
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
# Accepted parameters
# Bare MARK is already relied on by the conftest (START/END). BZ, DX, DY are
# accepted — likely recorded as field/offset annotations rather than physics.
################################################################################
def test_mark_bare_accepts(sad_accepts):
    sad_accepts(
        "MARK MK1 = ();\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_accepts_bz(sad_accepts):
    sad_accepts(
        "MARK MK1 = (BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_accepts_dx(sad_accepts):
    sad_accepts(
        "MARK MK1 = (DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_accepts_dy(sad_accepts):
    sad_accepts(
        "MARK MK1 = (DY=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

################################################################################
# Rejected parameters
################################################################################
def test_mark_rejects_k1(sad_rejects):
    sad_rejects(
        "MARK MK1 = (K1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_k2(sad_rejects):
    sad_rejects(
        "MARK MK1 = (K2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_k3(sad_rejects):
    sad_rejects(
        "MARK MK1 = (K3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_rotate(sad_rejects):
    sad_rejects(
        "MARK MK1 = (ROTATE=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_freq(sad_rejects):
    sad_rejects(
        "MARK MK1 = (FREQ=400E6);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_angle(sad_rejects):
    sad_rejects(
        "MARK MK1 = (ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_k0(sad_rejects):
    sad_rejects(
        "MARK MK1 = (K0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_k4(sad_rejects):
    sad_rejects(
        "MARK MK1 = (K4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_sk0(sad_rejects):
    sad_rejects(
        "MARK MK1 = (SK0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_sk1(sad_rejects):
    sad_rejects(
        "MARK MK1 = (SK1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_sk2(sad_rejects):
    sad_rejects(
        "MARK MK1 = (SK2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_sk3(sad_rejects):
    sad_rejects(
        "MARK MK1 = (SK3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_sk4(sad_rejects):
    sad_rejects(
        "MARK MK1 = (SK4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

def test_mark_rejects_harm(sad_rejects):
    sad_rejects(
        "MARK MK1 = (HARM=1000);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);")

################################################################################
# Effect on Twiss and tracking
#
# MARK is a pure location marker: even with BZ/DX/DY set, it should not
# perturb Twiss or a tracked particle.
################################################################################
def test_mark_does_not_affect_twiss_betx(tmp_path):
    """
    A MARK with DX/DY/BZ set should give the same Twiss betx as a bare MARK
    (compared directly rather than against an assumed absolute value).
    """
    def run(mark_params, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"MARK MK1 = ({mark_params});\n"
            "DRIFT D = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START D MK1 D END);\n")
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

    tw_bare = run("", "mark_bare_twiss.sad")
    tw_set  = run("DX=0.001 DY=0.001 BZ=0.1", "mark_set_twiss.sad")
    assert tw_set["betx"][-1] == pytest.approx(tw_bare["betx"][-1]), (
        "A MARK with DX/DY/BZ set should give the same Twiss betx as a bare MARK.")

def test_mark_does_not_perturb_tracked_particle(tmp_path):
    """
    A MARK with DX/DY/BZ set should not perturb a tracked particle's
    coordinates.
    """
    lat = tmp_path / "test.sad"
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        "MARK MK1 = (DX=0.001 DY=0.001 BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MK1 END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = track_sad(
            lattice_filepath    = lat.name,
            line_name           = "TEST",
            x_init              = np.array([0.001]),
            px_init             = np.array([0.0002]),
            y_init              = np.array([-0.0005]),
            py_init             = np.array([0.0003]),
            zeta_init           = np.array([0.0]),
            delta_init          = np.array([0.0001]),
            n_turns             = 1,
            rfsw                = False,
            with_progress       = False)
    finally:
        os.chdir(cwd)
    for coord, init in (
            ("x", 0.001), ("px", 0.0002), ("y", -0.0005),
            ("py", 0.0003), ("delta", 0.0001)):
        assert result[coord][0] == pytest.approx(init, abs=1e-12), (
            f"A MARK with DX/DY/BZ set should leave {coord} unchanged.")
