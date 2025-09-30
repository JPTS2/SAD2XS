"""
(Unofficial) SAD to XSuite Converter
"""
################################################################################
# Required Packages
################################################################################
import sad2xs as s2x
import xtrack as xt
import matplotlib.pyplot as plt

from _sad_helpers import twiss_sad
from _misc_helpers import create_comparison_plots

################################################################################
# User Parameters
################################################################################
SAD_LATTICE_PATH    = 'lattices/jparc_mr.sad'
LINE_NAME           = 'RNG'

################################################################################
# Load Reference Data
################################################################################
tw_sad  = twiss_sad(
    lattice_filename        = SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "4d",
    closed                  = True,
    reverse_element_order   = False,
    reverse_bend_direction  = False,
    additional_commands     = "")

################################################################################
# Convert Lattice
################################################################################
line    = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = None,
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_bend_direction      = False,
    reverse_charge              = False,
    output_directory            = 'out/',
    output_filename             = "jparc_mr",
    output_header               = "J-PARC MR")

########################################
# Get table
########################################
tt  = line.get_table(attr = True)

########################################
# Initial Twiss
########################################
tw  = line.twiss4d()

################################################################################
# Comparison Plots
################################################################################

########################################
# General Comparison Plots
########################################
create_comparison_plots(tw, tw_sad)

################################################################################
# Show plots
################################################################################
plt.show()
