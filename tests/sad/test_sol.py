"""
================================================================================
SAD syntax assumptions: SOL element
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
# Structural probes: SOL pairing and BOUND requirement
#
# From fcc_sol_dummy.sad: SOL is a zero-length fringe element. The physical
# length lives in a DRIFT placed between an entrance SOL (GEO=1) and an exit
# SOL (no GEO). BOUND=1 is required on the entrance and exit SOL elements.
# Internal SOL elements (if any) do not require BOUND.
#
# Minimum valid pattern: SOL(GEO=1, BOUND=1) + DRIFT + SOL(BOUND=1)
################################################################################
def test_sol_single_no_bound_rejects(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_single_element_rejects(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 END);")

def test_sol_pair_no_drift_accepts(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 SL2 END);")

def test_sol_pair_with_drift_and_geo_accepts(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_three_element_inner_no_bound_accepts(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1);\n"
        "DRIFT D0 = (L=0.5);\n"
        "SOL SL_MID = (BZ=0.1);\n"
        "DRIFT D1 = (L=0.5);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL_MID D1 SL2 END);")

################################################################################
# Accepted parameters (SOL + DRIFT + SOL with GEO=1 on entrance as baseline)
################################################################################
def test_sol_accepts_bz(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_accepts_dx(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, DX=0.001);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_accepts_dy(sad_accepts):
    sad_accepts(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, DY=0.001);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")


################################################################################
# Rejected parameters
################################################################################
def test_sol_rejects_angle(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, ANGLE=0.01);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_k0(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, K0=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_sk0(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, SK0=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_k1(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, K1=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_sk1(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, SK1=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_k2(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, K2=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_sk2(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, SK2=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_k3(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, K3=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_sk3(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, SK3=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_k4(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, K4=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_sk4(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, SK4=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_harm(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, HARM=1000);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_freq(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, FREQ=400E6);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")

def test_sol_rejects_rotate(sad_rejects):
    sad_rejects(
        "SOL SL1 = (BZ=0.1, BOUND=1, GEO=1, ROTATE=0.1);\n"
        "DRIFT D0 = (L=1.0);\n"
        "SOL SL2 = (BZ=0.0, BOUND=1);\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START SL1 D0 SL2 END);")
