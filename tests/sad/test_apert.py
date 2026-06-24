"""
================================================================================
SAD syntax assumptions: APERT element
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
# Accepted parameters
# APERT supports multiple aperture shapes (ellipse, rect, rectellipse), each
# with their own parameter set. DX, DY, ROTATE are non-obvious.
################################################################################
def test_apert_accepts_ax(sad_accepts):
    sad_accepts(
        "APERT A1 = (AX=0.05);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_accepts_ay(sad_accepts):
    sad_accepts(
        "APERT A1 = (AY=0.03);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_accepts_dx(sad_accepts):
    sad_accepts(
        "APERT A1 = (AX=0.05, AY=0.03, DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_accepts_dy(sad_accepts):
    sad_accepts(
        "APERT A1 = (AX=0.05, AY=0.03, DY=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_accepts_rotate(sad_accepts):
    sad_accepts(
        "APERT A1 = (AX=0.05, AY=0.03, ROTATE=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

################################################################################
# Rejected parameters
# APERT is a geometry element — it has no magnetic field parameters.
################################################################################
def test_apert_rejects_angle(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_k0(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, K0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_sk0(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, SK0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_k1(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, K1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_sk1(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, SK1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_k2(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, K2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_sk2(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, SK2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_k3(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, K3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_sk3(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, SK3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_k4(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, K4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_sk4(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, SK4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_bz(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_harm(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, HARM=1000);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

def test_apert_rejects_freq(sad_rejects):
    sad_rejects(
        "APERT A1 = (AX=0.05, AY=0.03, FREQ=400E6);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")
