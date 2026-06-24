"""
================================================================================
SAD syntax assumptions: CAVI element
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
def test_cavi_accepts_volt(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5, VOLT=0.5);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_freq(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5, FREQ=400E6);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_harm(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5, HARM=1000);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_phi(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5, PHI=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_dx(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5, DX=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_dy(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5, DY=0.001);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_accepts_rotate(sad_accepts):
    sad_accepts(
        "CAVI C1 = (L=0.5, ROTATE=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

################################################################################
# Rejected parameters
################################################################################
def test_cavi_rejects_angle(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, ANGLE=0.01);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_k0(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, K0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_sk0(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, SK0=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_k1(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, K1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_sk1(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, SK1=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_k2(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, K2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_sk2(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, SK2=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_k3(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, K3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_sk3(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, SK3=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_k4(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, K4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_sk4(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, SK4=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")

def test_cavi_rejects_bz(sad_rejects):
    sad_rejects(
        "CAVI C1 = (L=0.5, BZ=0.1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START C1 END);")
