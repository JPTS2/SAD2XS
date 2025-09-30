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
import matplotlib.pyplot as plt

from _sad_helpers import twiss_sad, rebuild_sad_lattice
from _misc_helpers import create_comparison_plots

################################################################################
# User Parameters
################################################################################
SAD_LATTICE_PATH            = 'lattices/her.sad'
REBUILT_SAD_LATTICE_PATH    = 'lattices/her_rebuilt.sad'
LINE_NAME                   = 'ASCE'

################################################################################
# Load Reference Data
################################################################################
rebuild_sad_lattice(
    lattice_filename    = SAD_LATTICE_PATH,
    line_name           = LINE_NAME,
    additional_commands = """
LINE["DISFRIN", "ESLE*"]    = 1;
LINE["DISFRIN", "ESRE*"]    = 1;
LINE["F1", "ESLE*"]         = 0;
LINE["F1", "ESRE*"]         = 0;""",
    output_filename     = REBUILT_SAD_LATTICE_PATH)

tw_sad  = twiss_sad(
    lattice_filename        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "4d",
    closed                  = True,
    reverse_element_order   = True,
    reverse_bend_direction  = False,
    additional_commands     = "")

################################################################################
# Convert Lattice
################################################################################
line    = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = REBUILT_SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = [
        'fhbbke', 'fvbbke',                         # Fake BB Elements
        'vkqc1le', 'vkqc2le', 'vkqc1re', 'vkqc2re', # FFQ Strengths
        'vrqc1le', 'vrqc2le', 'vrqc1re', 'vrqc2re', # FFQ Strengths
        'zhqc1le', 'zhqc2le', 'zhqc1re', 'zhqc2re', # FFQ Corrector Strengths
        'zvqc1le', 'zvqc2le', 'zvqc1re', 'zvqc2re', # FFQ Corrector Strengths
        'scmre', 'ocqc1re', 'ol2tle'],
    user_multipole_replacements = None,
    reverse_element_order       = True,
    reverse_bend_direction      = False,
    reverse_charge              = False,
    output_directory            = 'out/',
    output_filename             = "her",
    output_header               = "SuperKEKB HER")

########################################
# Delete rebuilt line
########################################
os.remove(REBUILT_SAD_LATTICE_PATH)

########################################
# Get table
########################################
tt = line.get_table(attr = True)

########################################
# Twiss
########################################
tw      = line.twiss4d(
    start               = xt.START,
    end                 = xt.END,
    x                   = tw_sad.x[0],
    px                  = tw_sad.px[0],
    y                   = tw_sad.y[0],
    py                  = tw_sad.py[0],
    betx                = tw_sad.betx[0],
    bety                = tw_sad.bety[0],
    alfx                = tw_sad.alfx[0],
    alfy                = tw_sad.alfy[0],
    dx                  = tw_sad.dx[0],
    dy                  = tw_sad.dy[0],
    dpx                 = tw_sad.dpx[0],
    dpy                 = tw_sad.dpy[0])

################################################################################
# Comparison Plots
################################################################################

########################################
# General Comparison Plots
########################################
create_comparison_plots(tw, tw_sad)

########################################
# IP1 Orbit
########################################
tw_ip1      = tw.rows[tw.s < 5]
tw_sad_ip1  = tw_sad.rows[tw_sad.s < 5]
tt_ip1      = tt.rows[tt.s < 5]

fig, axs = plt.subplots(3, 2, figsize = (12, 8), sharex = True)

axs[0, 0].plot(tw_sad_ip1.s, tw_sad_ip1.x, label = 'SAD', c = "r")
axs[0, 0].plot(tw_ip1.s, tw_ip1.x, label = 'XS', c = "b", linestyle = "--")

axs[0, 1].plot(tw_sad_ip1.s, tw_sad_ip1.px, label = 'SAD', c = "r")
axs[0, 1].plot(tw_ip1.s, tw_ip1.px, label = 'XS', c = "b", linestyle = "--")

axs[1, 0].plot(tw_sad_ip1.s, tw_sad_ip1.y, label = 'SAD', c = "r")
axs[1, 0].plot(tw_ip1.s, tw_ip1.y, label = 'XS', c = "b", linestyle = "--")

axs[1, 1].plot(tw_sad_ip1.s, tw_sad_ip1.py, label = 'SAD', c = "r")
axs[1, 1].plot(tw_ip1.s, tw_ip1.py, label = 'XS', c = "b", linestyle = "--")

axs[2, 0].step(tt_ip1.s, tt_ip1.ks, where = 'post', label = 'XS')
axs[2, 1].step(tt_ip1.s, tt_ip1.ks, where = 'post', label = 'XS')

fig.supxlabel('s [m]')
axs[0, 0].set_ylabel('x [m]')
axs[1, 0].set_ylabel('y [m]')
axs[2, 0].set_ylabel('ks')
axs[0, 1].set_ylabel('px')
axs[1, 1].set_ylabel('py')
axs[2, 1].set_ylabel('ks')
fig.suptitle('First IP')

for ax in axs.flat:
    ax.legend()
    ax.grid()

########################################
# IP2 Orbit
########################################
tw_ip2      = tw.rows[tw.s > tw.s[-1] - 5]
tw_sad_ip2  = tw_sad.rows[tw_sad.s > tw_sad.s[-1] - 5]
tt_ip2      = tt.rows[tt.s > tt.s[-1] - 5]

fig, axs = plt.subplots(3, 2, figsize = (12, 8), sharex = True)

axs[0, 0].plot(tw_sad_ip2.s, tw_sad_ip2.x, label = 'SAD', c = "r")
axs[0, 0].plot(tw_ip2.s, tw_ip2.x, label = 'XS', c = "b", linestyle = "--")

axs[0, 1].plot(tw_sad_ip2.s, tw_sad_ip2.px, label = 'SAD', c = "r")
axs[0, 1].plot(tw_ip2.s, tw_ip2.px, label = 'XS', c = "b", linestyle = "--")

axs[1, 0].plot(tw_sad_ip2.s, tw_sad_ip2.y, label = 'SAD', c = "r")
axs[1, 0].plot(tw_ip2.s, tw_ip2.y, label = 'XS', c = "b", linestyle = "--")

axs[1, 1].plot(tw_sad_ip2.s, tw_sad_ip2.py, label = 'SAD', c = "r")
axs[1, 1].plot(tw_ip2.s, tw_ip2.py, label = 'XS', c = "b", linestyle = "--")

axs[2, 0].step(tt_ip2.s, tt_ip2.ks, where = 'post', label = 'XS')
axs[2, 1].step(tt_ip2.s, tt_ip2.ks, where = 'post', label = 'XS')

fig.supxlabel('s [m]')
axs[0, 0].set_ylabel('x [m]')
axs[1, 0].set_ylabel('y [m]')
axs[2, 0].set_ylabel('ks')
axs[0, 1].set_ylabel('px')
axs[1, 1].set_ylabel('py')
axs[2, 1].set_ylabel('ks')
fig.suptitle('Second IP')

for ax in axs.flat:
    ax.legend()
    ax.grid()

################################################################################
# Show plots
################################################################################
plt.show()
