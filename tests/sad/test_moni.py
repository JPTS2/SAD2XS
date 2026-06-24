"""
================================================================================
SAD syntax assumptions: MONI element
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
# DX/DY/ROTATE are non-obvious: MONI is a physical element and may accept
# misalignment parameters. These tests verify that assumption.
################################################################################
def test_moni_bare_accepts(sad_accepts):
    sad_accepts(
        "MONI MN1 = ();\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MN1 END);")

def test_moni_accepts_dx(sad_accepts):
    sad_accepts(
        "MONI MN1 = (DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MN1 END);")

def test_moni_accepts_dy(sad_accepts):
    sad_accepts(
        "MONI MN1 = (DY=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MN1 END);")

def test_moni_accepts_rotate(sad_accepts):
    sad_accepts(
        "MONI MN1 = (ROTATE=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MN1 END);")

################################################################################
# Rejected parameters
################################################################################
def test_moni_rejects_k0(sad_rejects):
    sad_rejects(
        "MONI MN1 = (K0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MN1 END);")

def test_moni_rejects_k1(sad_rejects):
    sad_rejects(
        "MONI MN1 = (K1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MN1 END);")

def test_moni_rejects_k2(sad_rejects):
    sad_rejects(
        "MONI MN1 = (K2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MN1 END);")

def test_moni_rejects_bz(sad_rejects):
    sad_rejects(
        "MONI MN1 = (BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MN1 END);")

def test_moni_rejects_angle(sad_rejects):
    sad_rejects(
        "MONI MN1 = (ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MN1 END);")

def test_moni_rejects_freq(sad_rejects):
    sad_rejects(
        "MONI MN1 = (FREQ=400E6);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MN1 END);")

def test_moni_rejects_harm(sad_rejects):
    sad_rejects(
        "MONI MN1 = (HARM=1000);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START MN1 END);")
