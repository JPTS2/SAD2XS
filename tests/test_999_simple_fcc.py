"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Required Packages
################################################################################
import os
import sad2xs as s2x
import xtrack as xt
import numpy as np
import textwrap
import matplotlib.pyplot as plt
from tqdm import tqdm

from _sad_helpers import sad_twiss, rebuild_sad_lattice
from _test_config import *

################################################################################
# N.B.
################################################################################
# REFERENCE SHIFTS INSIDE THE SOLENOID REGION DON'T WORK
# INSTEAD, WE USE MULTIPOLES TO SHIFT THE BEAM

################################################################################
# Reference PyTest Function
################################################################################
def mock_lattice_test(
        sad_elements_line_string:   str):
    """
    Reference Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """

    ########################################################################
    # Write Test Lattice
    ########################################################################
    with open("test_lattice.sad", "w") as f:
        f.write(textwrap.dedent(f"""\
        MOMENTUM    = 1.0 GEV;
        """))

    with open("test_lattice.sad", "a") as f:
        f.write(sad_elements_line_string)

    ########################################################################
    # Twiss SAD Lattice
    ########################################################################
    tw_sad  = sad_twiss(
        lattice_filename    = 'test_lattice.sad',
        line_name           = 'TEST_LINE')

    ########################################################################
    # Rebuild SAD Lattice
    ########################################################################
    rebuild_sad_lattice(
        lattice_filename    = 'test_lattice.sad',
        line_name           = 'TEST_LINE')

    ########################################################################
    # Convert Lattice
    ########################################################################
    line    = s2x.convert_sad_to_xsuite(
        sad_lattice_path    = 'test_lattice.sad',
        output_directory    = None,
        _verbose            = False,
        _test_mode          = True)
    
    ########################################
    # Twiss XSuite Lattice
    ########################################
    tw_xs   = line.twiss4d(
        _continue_if_lost   = True,
        start               = xt.START,
        end                 = xt.END,
        betx                = 1,
        bety                = 1)

    ########################################################################
    # Diagnostics: Outputs if the test fails
    ########################################################################
    print("SAD")
    tw_sad.cols["s x px y py"].show()
    print("Xsuite")
    tw_xs.cols["s x px y py"].show()

    tw_sad.plot('x y')
    plt.title("SAD")
    tw_xs.plot('x y')
    plt.title("XSuite")
    plt.show()

    ########################################################################
    # Delete test lattice
    ########################################################################
    os.remove("test_lattice.sad")


################################################################################
# Simple FCC Sol style transforms
################################################################################
def test_fcc_h():
    """
    Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """
    mock_lattice_test(
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00)
                        ARC_DRIFT   = (L = 10.0);

            SOL         ES1R        = (BZ = 0   DPX =-.015     BOUND =1  CHI1 =.015     GEO =1 )
                        ES3R        = (BZ = 0   BOUND =1)
                        ES3L        = (BZ = 0   BOUND =1)
                        ES1L        = (BZ = 0   DPX =-.015     BOUND =1  CHI1 =.015    GEO =1 );

            MARK        START       = ()
                        END         = ()
                        IP          = ();

            LINE        TEST_LINE   = (START
                IP
                ES1R SOL_DRIFT ES3R
                ARC_DRIFT
                -ES3L -SOL_DRIFT -ES1L
                IP
                ES1R SOL_DRIFT ES3R
                ARC_DRIFT
                -ES3L -SOL_DRIFT -ES1L
                IP
                END);
            """))

def test_fcc_tt_coll():
    """
    Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """
    mock_lattice_test(
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00)
                        ARC_DRIFT   = (L = 10.0);

            SOL         ES1R        = (BZ = 0   DPX =-.015     BOUND =1  CHI1 =.015     GEO =1 )
                        ES3R        = (BZ = 0   BOUND =1)
                        ES3L        = (BZ = 0   BOUND =1)
                        ES1L        = (BZ = 0   DPX =-.015     BOUND =1  CHI1 =-.015    GEO =1 );

            MARK        START       = ()
                        END         = ()
                        IP          = ();

            LINE        TEST_LINE   = (START
                IP
                ES1R SOL_DRIFT ES3R
                ARC_DRIFT
                -ES3L -SOL_DRIFT -ES1L
                IP
                ES1R SOL_DRIFT ES3R
                ARC_DRIFT
                -ES3L -SOL_DRIFT -ES1L
                IP
                END);
            """))

def test_fcc_sol():
    """
    Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """
    mock_lattice_test(
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00)
                        SHORT_DRIFT = (L = 2.0)
                        ARC_DRIFT   = (L = 10.0);

            SOL         ESR0        = (BZ =-2  DPX =-.02 BOUND =1  CHI1 =-.02     GEO =1)
                        ESR1        = (BZ =0    BOUND =1)
                        ESCR0       = (BZ =-1.999599959991998 BOUND =1 GEO =1 )
                        ESCR1       = (BZ =0   BOUND =1)
                        ESCL1       = (BZ =-1.999599959991998 BOUND =1)
                        ESCL0       = (BZ =0   BOUND =1  GEO =1 )
                        ESL1        = (BZ =0   BOUND =1)
                        ESL0        = (BZ =0   DPX =.02  BOUND =1  CHI1 =.02 GEO =1 );

            MARK        START       = ()
                        END         = ()
                        IP          = ();

            LINE        TEST_LINE   = (START
                IP
                -IP
                -ESR0 - SOL_DRIFT -ESR1
                SHORT_DRIFT
                ESCR0 SOL_DRIFT ESCR1
                ARC_DRIFT
                ESCL1 SOL_DRIFT ESCL0
                SHORT_DRIFT
                ESL1 SOL_DRIFT ESL0
                IP
                -IP
                -ESR0 - SOL_DRIFT -ESR1
                SHORT_DRIFT
                ESCR0 SOL_DRIFT ESCR1
                ARC_DRIFT
                ESCL1 SOL_DRIFT ESCL0
                SHORT_DRIFT
                ESL1 SOL_DRIFT ESL0
                IP
                END);
            """))
