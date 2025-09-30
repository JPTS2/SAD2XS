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
SAD_LATTICE_PATH    = 'lattices/kek_bte.sad'
LINE_NAME           = 'BTE'

################################################################################
# Load Reference Data
################################################################################
tw4d_sad    = twiss_sad(
    lattice_filename        = SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "4d",
    closed                  = False,
    reverse_element_order   = False,
    reverse_bend_direction  = False,
    additional_commands     = "")
tw6d_sad    = twiss_sad(
    lattice_filename        = SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "6d",
    closed                  = False,
    reverse_element_order   = False,
    reverse_bend_direction  = False,
    additional_commands     = "")

################################################################################
# Convert Lattice
################################################################################
line    = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = [],
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_bend_direction      = False,
    reverse_charge              = True,
    output_directory            = 'out/',
    output_filename             = "kek_bte",
    output_header               = "SuperKEKB BTE")
line.replace_all_repeated_elements()

########################################
# Get table
########################################
tt = line.get_table(attr = True)

########################################
# Twiss
########################################
tw4d    = line.twiss4d(
    start               = xt.START,
    end                 = xt.END,
    x                   = tw4d_sad.x[0],
    px                  = tw4d_sad.px[0],
    y                   = tw4d_sad.y[0],
    py                  = tw4d_sad.py[0],
    betx                = tw4d_sad.betx[0],
    bety                = tw4d_sad.bety[0],
    alfx                = tw4d_sad.alfx[0],
    alfy                = tw4d_sad.alfy[0],
    dx                  = tw4d_sad.dx[0],
    dy                  = tw4d_sad.dy[0],
    dpx                 = tw4d_sad.dpx[0],
    dpy                 = tw4d_sad.dpy[0])

tw6d    = line.twiss(
    start               = xt.START,
    end                 = xt.END,
    x                   = tw6d_sad.x[0],
    px                  = tw6d_sad.px[0],
    y                   = tw6d_sad.y[0],
    py                  = tw6d_sad.py[0],
    betx                = tw6d_sad.betx[0],
    bety                = tw6d_sad.bety[0],
    alfx                = tw6d_sad.alfx[0],
    alfy                = tw6d_sad.alfy[0],
    dx                  = tw6d_sad.dx[0],
    dy                  = tw6d_sad.dy[0],
    dpx                 = tw6d_sad.dpx[0],
    dpy                 = tw6d_sad.dpy[0])

################################################################################
# Comparisons
################################################################################
for tw, tw_sad, mode in zip([tw4d, tw6d], [tw4d_sad, tw6d_sad], ["4D", "6D"]):
    create_comparison_plots(tw, tw_sad)

################################################################################
# Show plots
################################################################################
plt.show()
