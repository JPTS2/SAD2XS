"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Required Packages
################################################################################
import os
os.environ["XSUITE_VERBOSE"] = "1"

import sad2xs as s2x
import xtrack as xt

from _sad_helpers import twiss_sad
from _test_config import *

########################################################################
# Twiss SAD Lattice
########################################################################
tw_sad  = twiss_sad(
    lattice_filename        = 'test_lattice.sad',
    line_name               = 'TEST_LINE',
    method                  = "4d",
    closed                  = False,
    reverse_element_order   = False,
    reverse_bend_direction  = False,
    additional_commands     = "")

########################################################################
# Convert Lattice
########################################################################
line    = s2x.convert_sad_to_xsuite(
    sad_lattice_path    = 'test_lattice.sad',
    output_directory    = None,
    _verbose            = True,
    _test_mode          = True)

########################################
# Twiss XSuite Lattice
########################################
print("Running Twiss now")
line.discard_tracker()
line.build_tracker(compile = False)
tw_xs   = line.twiss4d(
    _continue_if_lost   = True,
    start               = xt.START,
    end                 = xt.END,
    betx                = 1,
    bety                = 1)
