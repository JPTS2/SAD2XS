"""
================================================================================
Example 004: FCC-ee Solenoid Lattice Conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-17
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import os
from _runtime import DEFAULT_OUTPUT_DIR, configure_example_runtime

SHOW_PLOTS  = globals().get("SHOW_PLOTS", True)
RUN_ASSERTS = globals().get("RUN_ASSERTS", True)
OUTPUT_DIR  = configure_example_runtime(
    output_dir = globals().get("OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

import sad2xs as s2x
s2x.set_log_level("info")
import matplotlib.pyplot as plt

from sad2xs.xsuite_helpers import align_xsuite_twiss_with_sad_twiss, \
    assert_xsuite_matches_sad_twiss, compute_s_sad, plot_xsuite_sad_comparison

################################################################################
# User Parameters
################################################################################
SAD_LATTICE_PATH            = "lattices/fccee_sol.sad"
REBUILT_SAD_LATTICE_PATH    = "lattices/fccee_sol_rebuilt.sad"
LINE_NAME                   = "RING"

# SAD's coupled beta/alpha (Edwards-Teng convention) map to these Xsuite columns
EDWARDS_TENG_COLUMNS   = {
    "betx": "betx_edw_teng", "bety": "bety_edw_teng",
    "alfx": "alfx_edw_teng", "alfy": "alfy_edw_teng"}

################################################################################
# Load Reference Data
################################################################################
s2x.sad_helpers.rebuild_sad_lattice(
    lattice_filepath            = SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    additional_commands         = """
LINE["DISFRIN", "ESL*"]     = 1;
LINE["DISFRIN", "ESR*"]     = 1;
LINE["DISFRIN", "ESCR*"]    = 1;
LINE["DISFRIN", "ESCL*"]    = 1;
LINE["F1", "ESL*"]          = 0;
LINE["F1", "ESR*"]          = 0;
LINE["F1", "ESCL*"]         = 0;
LINE["F1", "ESCR*"]         = 0;""",
    output_filepath             = REBUILT_SAD_LATTICE_PATH)

tw_sad  = s2x.sad_helpers.twiss_sad(
    lattice_filepath            = REBUILT_SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    calc6d                      = False,
    closed                      = True,
    rfsw                        = True,
    reverse_element_order       = False,
    reverse_survey_horizontal   = False,
    additional_commands         = "")

################################################################################
# Convert Lattice
################################################################################
line    = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = REBUILT_SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = None,
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_survey_horizontal   = False,
    reverse_charge_sign         = False,
    output_directory            = OUTPUT_DIR,
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
# Twiss (with ET to compare with SAD)
########################################
tw_xs   = line.twiss4d(coupling_edw_teng = True)

########################################
# Compute SAD s
########################################
tw_xs["s_sad"]  = compute_s_sad(tw_xs)

########################################
# Align Xsuite Twiss with SAD Twiss
########################################
tw_xs_aligned, tw_sad_aligned   = align_xsuite_twiss_with_sad_twiss(
    xsuite_twiss    = tw_xs,
    sad_twiss       = tw_sad,
    s_tol           = 1E-3)

########################################
# Run comparison assertions
########################################
if RUN_ASSERTS:
    assert_xsuite_matches_sad_twiss(
        xsuite_aligned          = tw_xs_aligned,
        sad_aligned             = tw_sad_aligned,
        xsuite_column_overrides = EDWARDS_TENG_COLUMNS)

################################################################################
# Comparison Plots
################################################################################

########################################
# General Comparison Plots
########################################
plot_xsuite_sad_comparison(
    xsuite_aligned          = tw_xs_aligned,
    sad_aligned             = tw_sad_aligned,
    xsuite_column_overrides = EDWARDS_TENG_COLUMNS)

########################################
# IP1 Orbit
########################################
plot_xsuite_sad_comparison(
    xsuite_aligned          = tw_xs_aligned,
    sad_aligned             = tw_sad_aligned,
    xsuite_column_overrides = EDWARDS_TENG_COLUMNS,
    groups                  = ["orbit_xy", "orbit_pxpy"],
    ele_stop                = "QD0AR.1",
    title_prefix            = "First IP")

tt_ip1  = tt.rows[tt.s < 2.5]
fig, ax = plt.subplots(figsize = (6, 3))
ax.step(tt_ip1.s, tt_ip1.ks, where = "post", label = "XS")
ax.set_xlabel("s [m]")
ax.set_ylabel("ks")
ax.legend()
ax.grid()
fig.suptitle("First IP: Solenoid Strength")

########################################
# IP2 Orbit
########################################
plot_xsuite_sad_comparison(
    xsuite_aligned          = tw_xs_aligned,
    sad_aligned             = tw_sad_aligned,
    xsuite_column_overrides = EDWARDS_TENG_COLUMNS,
    groups                  = ["orbit_xy", "orbit_pxpy"],
    ele_start               = "D01.2",
    ele_stop                = "QD0AR.2",
    title_prefix            = "Second IP")

tt_ip2  = tt.rows[(tt.s > 22662) & (tt.s < 22667)]
fig, ax = plt.subplots(figsize = (6, 3))
ax.step(tt_ip2.s, tt_ip2.ks, where = "post", label = "XS")
ax.set_xlabel("s [m]")
ax.set_ylabel("ks")
ax.legend()
ax.grid()
fig.suptitle("Second IP: Solenoid Strength")

################################################################################
# Show plots
################################################################################
if SHOW_PLOTS:
    plt.show()
else:
    plt.close("all")
