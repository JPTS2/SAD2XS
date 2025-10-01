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
SAD_LATTICE_PATH            = 'lattices/fccee_sol.sad'
REBUILT_SAD_LATTICE_PATH    = 'lattices/fccee_sol_rebuilt.sad'
LINE_NAME                   = 'RING'

################################################################################
# Load Reference Data
################################################################################
rebuild_sad_lattice(
    lattice_filename    = SAD_LATTICE_PATH,
    line_name           = LINE_NAME,
    additional_commands = """
LINE["DISFRIN", "ESL*"]     = 1;
LINE["DISFRIN", "ESR*"]     = 1;
LINE["DISFRIN", "ESCR*"]    = 1;
LINE["DISFRIN", "ESCL*"]    = 1;
LINE["F1", "ESL*"]          = 0;
LINE["F1", "ESR*"]          = 0;
LINE["F1", "ESCL*"]         = 0;
LINE["F1", "ESCR*"]         = 0;""",
    output_filename     = REBUILT_SAD_LATTICE_PATH)

print("Lattice Rebuilt")

tw_sad  = twiss_sad(
    lattice_filename        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "4d",
    closed                  = True,
    reverse_element_order   = False,
    reverse_bend_direction  = False,
    additional_commands     = "")

print("Twiss acquired")

################################################################################
# Convert Lattice
################################################################################
line    = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = REBUILT_SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = None,
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_bend_direction      = False,
    reverse_charge              = False,
    output_directory            = 'out',
    output_filename             = "fcc_sol",
    output_header               = "FCC-ee LCC With Solenoid")

########################################
# Delete rebuilt line
########################################
os.remove(REBUILT_SAD_LATTICE_PATH)

########################################
# Get table
########################################
tt = line.get_table(attr = True)

########################################
# Initial Twiss
########################################
tw      = line.twiss4d()

########################################
# Calculate SAD s
########################################
ds              = np.concatenate([[0], tw.s[1:] - tw.s[:-1]])
dzeta           = np.concatenate([[0], tw.zeta[1:] - tw.zeta[:-1]])
# Ignore the dzeta at ZetaShift elements
zeta_shifts     = tt.element_type == "ZetaShift"
zeta_shifts     = np.concatenate([[0], zeta_shifts[:-1]])
dzeta           = np.where(zeta_shifts, 0, dzeta)

s_sad           = np.zeros_like(tw.s)
for i in range(1, len(s_sad)):
    s_sad[i]    = s_sad[i-1] + ds[i] - dzeta[i]
tw["s_sad"]     = s_sad

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
tw_ip1      = tw.rows[tw.s < 2.5]
tw_sad_ip1  = tw_sad.rows[tw_sad.s < 2.5]
tt_ip1      = tt.rows[tt.s < 2.5]

fig, axs = plt.subplots(3, 2, figsize = (12, 8), sharex = True)

axs[0, 0].plot(tw_sad_ip1.s, tw_sad_ip1.x, label = 'SAD', c = "r")
axs[0, 0].plot(tw_ip1.s_sad, tw_ip1.x, label = 'XS', c = "b", linestyle = "--")

axs[0, 1].plot(tw_sad_ip1.s, tw_sad_ip1.px, label = 'SAD', c = "r")
axs[0, 1].plot(tw_ip1.s_sad, tw_ip1.px, label = 'XS', c = "b", linestyle = "--")

axs[1, 0].plot(tw_sad_ip1.s, tw_sad_ip1.y, label = 'SAD', c = "r")
axs[1, 0].plot(tw_ip1.s_sad, tw_ip1.y, label = 'XS', c = "b", linestyle = "--")

axs[1, 1].plot(tw_sad_ip1.s, tw_sad_ip1.py, label = 'SAD', c = "r")
axs[1, 1].plot(tw_ip1.s_sad, tw_ip1.py, label = 'XS', c = "b", linestyle = "--")

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
tw_ip2      = tw.rows[(tw.s > 22662) & (tw.s < 22667)]
tw_sad_ip2  = tw_sad.rows[(tw_sad.s > 22662) & (tw_sad.s < 22667)]
tt_ip2      = tt.rows[(tt.s > 22662) & (tt.s < 22667)]

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
