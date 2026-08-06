"""
================================================================================
Example 001: FCC-ee ZH Lattice Conversion
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
SAD_LATTICE_PATH            = "lattices/fccee_zh.sad"
LINE_NAME                   = "RING"

# SAD's coupled beta/alpha (Edwards-Teng convention) map to these Xsuite columns
EDWARDS_TENG_COLUMNS   = {
    "betx": "betx_edw_teng", "bety": "bety_edw_teng",
    "alfx": "alfx_edw_teng", "alfy": "alfy_edw_teng"}

################################################################################
# Load Reference Data
################################################################################
tw_sad  = s2x.sad_helpers.twiss_sad(
    lattice_filepath            = SAD_LATTICE_PATH,
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
    sad_lattice_path            = SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = None,
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_survey_horizontal   = False,
    reverse_charge_sign         = False,
    output_directory            = OUTPUT_DIR,
    output_filename             = "fcc_h",
    output_header               = "FCC-ee ZH")

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
    ele_stop                = "QC1R1.1",
    title_prefix            = "First IP")

########################################
# IP2 Orbit
########################################
plot_xsuite_sad_comparison(
    xsuite_aligned          = tw_xs_aligned,
    sad_aligned             = tw_sad_aligned,
    xsuite_column_overrides = EDWARDS_TENG_COLUMNS,
    groups                  = ["orbit_xy", "orbit_pxpy"],
    ele_start               = "LX3.1",
    ele_stop                = "QC1R1.2",
    title_prefix            = "Second IP")

################################################################################
# Show plots
################################################################################
if SHOW_PLOTS:
    plt.show()
else:
    plt.close("all")
