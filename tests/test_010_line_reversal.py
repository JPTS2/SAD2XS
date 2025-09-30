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
# Line reversal test
################################################################################
def test_line_reversal():
    """
    Reference Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """

    ########################################################################
    # Write Test Lattice
    ########################################################################
    with open("test_lattice.sad", "w") as f:
        f.write(textwrap.dedent(f"""\
        MOMENTUM    = 1.0 GEV;
                                
        DRIFT       OUTER_DRIFT = (L = 1.00)
                    SUB_DRIFT   = (L = 2.00);
        
        BEND        TEST_BEND1  = (L = 1.00, ANGLE = 0.01)
                    TEST_BEND2  = (L = 2.00, ANGLE = 0.02);

        MARK        START       = ()
                    END         = ()
                    SUB_START   = ()
                    SUB_END     = ();

        LINE        SUBLINE     = (SUB_START TEST_BEND1 SUB_DRIFT TEST_BEND2 SUB_END)
                    TEST_LINE   = (START -SUBLINE END);
        """))

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

    ########################################################################
    # Delete test lattice
    ########################################################################
    os.remove("test_lattice.sad")

    ########################################################################
    # Assert the names
    ########################################################################
    xs_names    = list(tw_xs.name)
    sad_names   = list(tw_sad.name)

    # Remove the "_end_point"
    xs_names.remove("_end_point")
    # In Xsuite we add minus signs to symbolise the reversal
    xs_names    = [name.strip('-').upper() for name in xs_names]
    # To compare with SAD make uppercase
    xs_names    = [name.upper() for name in xs_names]

    assert len(xs_names) == len(sad_names)
    assert all(x == y for x, y in zip(xs_names, sad_names))
