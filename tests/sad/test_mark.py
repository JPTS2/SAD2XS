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
