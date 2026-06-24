"""
================================================================================
SAD syntax assumptions: OCT element
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
################################################################################
def test_oct_accepts_k3(sad_accepts):
    sad_accepts(
        "OCT O1 = (L=1.0, K3=1.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_accepts_dx(sad_accepts):
    sad_accepts(
        "OCT O1 = (L=1.0, DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_accepts_dy(sad_accepts):
    sad_accepts(
        "OCT O1 = (L=1.0, DY=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_accepts_rotate(sad_accepts):
    sad_accepts(
        "OCT O1 = (L=1.0, ROTATE=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

################################################################################
# Rejected parameters
################################################################################
def test_oct_rejects_angle(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_k0(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, K0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_sk0(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, SK0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_k1(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, K1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_sk1(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, SK1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_k2(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, K2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_sk2(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, SK2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_sk3(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, SK3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_k4(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, K4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_sk4(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, SK4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_harm(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, HARM=1000);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_freq(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, FREQ=400E6);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")

def test_oct_rejects_bz(sad_rejects):
    sad_rejects(
        "OCT O1 = (L=1.0, BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START O1 END);")
