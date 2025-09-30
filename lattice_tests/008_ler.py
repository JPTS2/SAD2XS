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
SAD_LATTICE_PATH            = 'lattices/ler.sad'
REBUILT_SAD_LATTICE_PATH    = 'lattices/ler_rebuilt.sad'
LINE_NAME                   = 'ASC'

################################################################################
# Load Reference Data
################################################################################
rebuild_sad_lattice(
    lattice_filename    = SAD_LATTICE_PATH,
    line_name           = LINE_NAME,
    additional_commands = """
LINE["DISFRIN", "ESLP*"]    = 1;
LINE["DISFRIN", "ESRP*"]    = 1;
LINE["F1", "ESLP*"]         = 0;
LINE["F1", "ESRP*"]         = 0;""",
    output_filename     = REBUILT_SAD_LATTICE_PATH)

tw4d_sad    = twiss_sad(
    lattice_filename        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "4d",
    closed                  = True,
    reverse_element_order   = False,
    reverse_bend_direction  = True,
    additional_commands     = "")

tw6d_sad    = twiss_sad(
    lattice_filename        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "6d",
    closed                  = True,
    reverse_element_order   = False,
    reverse_bend_direction  = True,
    additional_commands     = "")

################################################################################
# Convert Lattice
################################################################################
line    = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = REBUILT_SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = [
        "fbmbmp", 'fhbbkp', 'fvbbkp',               # Fake BB Elements
        'vkqc1lp', 'vkqc2lp', 'vkqc1rp', 'vkqc2rp', # FFQ Strengths
        'vrqc1lp', 'vrqc2lp', 'vrqc1rp', 'vrqc2rp', # FFQ Strengths
        'zhqc1lp', 'zhqc2lp', 'zhqc1rp', 'zhqc2rp', # FFQ Corrector Strengths
        'zvqc1lp', 'zvqc2lp', 'zvqc1rp', 'zvqc2rp', # FFQ Corrector Strengths
        'scmrp', 'ocqc1rp', 'ol2tlp'],
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_bend_direction      = True,
    reverse_charge              = False,
    output_directory            = 'out/',
    output_filename             = "ler_giulia",
    output_header               = "SuperKEKB LER Lattice for Giulia Nigrelli")

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
tw4d_xs = line.twiss(
    method              = "4d",
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
tw6d_xs = line.twiss(
    method              = "6d",
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

################################################################################
# Comparison Plots
################################################################################

########################################
# General Comparison Plots
########################################
create_comparison_plots(tw4d_xs, tw4d_sad)

########################################
# IP1 Orbit
########################################
tw_ip1      = tw4d_xs.rows[tw4d_xs.s < 5]
tw_sad_ip1  = tw4d_sad.rows[tw4d_sad.s < 5]
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
tw_ip2      = tw4d_xs.rows[tw4d_xs.s > tw4d_xs.s[-1] - 5]
tw_sad_ip2  = tw4d_sad.rows[tw4d_sad.s > tw4d_sad.s[-1] - 5]
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


################################################################################
# Comparison with RF and Radiation
################################################################################

########################################
# RF, no radiation
########################################
tw0_sad = twiss_sad(
    lattice_filename        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "6d",
    closed                  = False,
    reverse_element_order   = False,
    reverse_bend_direction  = True,
    rf_enabled              = True,
    radiation               = False,
    rad_compensation        = False,
    rad_taper               = False,
    additional_commands     = """LINE["DISFRIN", "ESLP*"] = 1;
LINE["DISFRIN", "ESRP*"] = 1;
LINE["F1", "ESLP*"] = 0;
LINE["F1", "ESRP*"] = 0;""")

line.configure_radiation(model = None)
tw0_xs = line.twiss(
    method              = "6d",
    start               = xt.START,
    end                 = xt.END,
    x                   = tw0_sad.x[0],
    px                  = tw0_sad.px[0],
    y                   = tw0_sad.y[0],
    py                  = tw0_sad.py[0],
    zeta                = tw0_sad.zeta[0],
    delta               = tw0_sad.delta[0],
    betx                = tw0_sad.betx[0],
    bety                = tw0_sad.bety[0],
    alfx                = tw0_sad.alfx[0],
    alfy                = tw0_sad.alfy[0],
    dx                  = tw0_sad.dx[0],
    dy                  = tw0_sad.dy[0],
    dpx                 = tw0_sad.dpx[0],
    dpy                 = tw0_sad.dpy[0])

fig, axs = plt.subplots(1, 2, figsize = (12, 8), sharex = True)
axs[0].plot(tw0_sad.s, tw0_sad.zeta, label = 'SAD', c = "r")
axs[0].plot(tw0_xs.s, tw0_xs.zeta, label = 'XS', c = "b", linestyle = "--")
axs[1].plot(tw0_sad.s, tw0_sad.delta, label = 'SAD', c = "r")
axs[1].plot(tw0_xs.s, tw0_xs.delta, label = 'XS', c = "b", linestyle = "--")
for ax in axs.flat:
    ax.legend()
    ax.grid()
fig.supxlabel('s [m]')
axs[0].set_ylabel('zeta [m]')
axs[1].set_ylabel('delta')

########################################
# RF and radiation
########################################
tw1_sad = twiss_sad(
    lattice_filename        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "6d",
    closed                  = False,
    reverse_element_order   = False,
    reverse_bend_direction  = True,
    rf_enabled              = True,
    radiation               = True,
    rad_compensation        = True,
    rad_taper               = False,
    additional_commands     = """LINE["DISFRIN", "ESLP*"] = 1;
LINE["DISFRIN", "ESRP*"] = 1;
LINE["F1", "ESLP*"] = 0;
LINE["F1", "ESRP*"] = 0;""")

line.configure_radiation(model = "mean")
tw1_xs = line.twiss(
    method              = "6d",
    start               = xt.START,
    end                 = xt.END,
    x                   = tw1_sad.x[0],
    px                  = tw1_sad.px[0],
    y                   = tw1_sad.y[0],
    py                  = tw1_sad.py[0],
    zeta                = tw1_sad.zeta[0],
    delta               = tw1_sad.delta[0],
    betx                = tw1_sad.betx[0],
    bety                = tw1_sad.bety[0],
    alfx                = tw1_sad.alfx[0],
    alfy                = tw1_sad.alfy[0],
    dx                  = tw1_sad.dx[0],
    dy                  = tw1_sad.dy[0],
    dpx                 = tw1_sad.dpx[0],
    dpy                 = tw1_sad.dpy[0])

fig, axs = plt.subplots(1, 2, figsize = (12, 8), sharex = True)
axs[0].plot(tw1_sad.s, tw1_sad.zeta, label = 'SAD', c = "r")
axs[0].plot(tw1_xs.s, tw1_xs.zeta, label = 'XS', c = "b", linestyle = "--")
axs[1].plot(tw1_sad.s, tw1_sad.delta, label = 'SAD', c = "r")
axs[1].plot(tw1_xs.s, tw1_xs.delta, label = 'XS', c = "b", linestyle = "--")
for ax in axs.flat:
    ax.legend()
    ax.grid()
fig.supxlabel('s [m]')
axs[0].set_ylabel('zeta [m]')
axs[1].set_ylabel('delta')

########################################
# RF and radiation, adjusted lag
########################################
tw2_sad = twiss_sad(
    lattice_filename        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "6d",
    closed                  = False,
    reverse_element_order   = False,
    reverse_bend_direction  = True,
    rf_enabled              = True,
    radiation               = True,
    rad_compensation        = True,
    rad_taper               = True,
    additional_commands     = """LINE["DISFRIN", "ESLP*"] = 1;
LINE["DISFRIN", "ESRP*"] = 1;
LINE["F1", "ESLP*"] = 0;
LINE["F1", "ESRP*"] = 0;
LINE["PHI", "CA*"] -= 0.23;""")

line2   = line.copy()
tt      = line2.get_table(attr = True)
cavis   = tt.rows["ca.*"]
for cavi in cavis.name:
    line2[cavi].lag -= np.rad2deg(0.23)
tw2_xs = line2.twiss(
    method              = "6d",
    start               = xt.START,
    end                 = xt.END,
    x                   = tw2_sad.x[0],
    px                  = tw2_sad.px[0],
    y                   = tw2_sad.y[0],
    py                  = tw2_sad.py[0],
    zeta                = tw2_sad.zeta[0],
    delta               = tw2_sad.delta[0],
    betx                = tw2_sad.betx[0],
    bety                = tw2_sad.bety[0],
    alfx                = tw2_sad.alfx[0],
    alfy                = tw2_sad.alfy[0],
    dx                  = tw2_sad.dx[0],
    dy                  = tw2_sad.dy[0],
    dpx                 = tw2_sad.dpx[0],
    dpy                 = tw2_sad.dpy[0])

fig, axs = plt.subplots(1, 2, figsize = (12, 8), sharex = True)
axs[0].plot(tw2_sad.s, tw2_sad.zeta, label = 'SAD', c = "r")
axs[0].plot(tw2_xs.s, tw2_xs.zeta, label = 'XS', c = "b", linestyle = "--")
axs[1].plot(tw2_sad.s, tw2_sad.delta, label = 'SAD', c = "r")
axs[1].plot(tw2_xs.s, tw2_xs.delta, label = 'XS', c = "b", linestyle = "--")
for ax in axs.flat:
    ax.legend()
    ax.grid()
fig.supxlabel('s [m]')
axs[0].set_ylabel('zeta [m]')
axs[1].set_ylabel('delta')

########################################
# RF and radiation closed
########################################
tw3_sad = twiss_sad(
    lattice_filename        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "6d",
    closed                  = True,
    reverse_element_order   = False,
    reverse_bend_direction  = True,
    rf_enabled              = True,
    radiation               = True,
    rad_compensation        = True,
    rad_taper               = True,
    additional_commands     = """LINE["DISFRIN", "ESLP*"] = 1;
LINE["DISFRIN", "ESRP*"] = 1;
LINE["F1", "ESLP*"] = 0;
LINE["F1", "ESRP*"] = 0;""")

line2   = line.copy()
line2.replace_all_repeated_elements()
line2.build_tracker()
line2.compensate_radiation_energy_loss()
tw3_xs = line2.twiss(method = "6d")

fig, axs = plt.subplots(1, 2, figsize = (12, 8), sharex = True)
axs[0].plot(tw3_sad.s, tw3_sad.zeta, label = 'SAD', c = "r")
axs[0].plot(tw3_xs.s, tw3_xs.zeta, label = 'XS', c = "b", linestyle = "--")
axs[1].plot(tw3_sad.s, tw3_sad.delta, label = 'SAD', c = "r")
axs[1].plot(tw3_xs.s, tw3_xs.delta, label = 'XS', c = "b", linestyle = "--")
for ax in axs.flat:
    ax.legend()
    ax.grid()
fig.supxlabel('s [m]')
axs[0].set_ylabel('zeta [m]')
axs[1].set_ylabel('delta')

################################################################################
# Show plots
################################################################################
plt.show()

