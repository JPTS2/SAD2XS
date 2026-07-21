"""
================================================================================
Example 005: FCC-ee Solenoid Lattice Conversion
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
import numpy as np
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

twp_sad  = s2x.sad_helpers.twiss_sad(
    lattice_filepath            = REBUILT_SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    calc6d                      = False,
    closed                      = True,
    rfsw                        = True,
    reverse_element_order       = False,
    reverse_survey_horizontal   = False,
    additional_commands         = "")
twe_sad  = s2x.sad_helpers.twiss_sad(
    lattice_filepath            = REBUILT_SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    calc6d                      = False,
    closed                      = True,
    rfsw                        = True,
    reverse_element_order       = False,
    reverse_survey_horizontal   = True,
    additional_commands         = "")

################################################################################
# Convert Lattice
################################################################################

########################################
# Positron Ring
########################################
linep   = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = REBUILT_SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = None,
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_survey_horizontal   = False,
    reverse_charge_sign         = False,
    output_directory            = OUTPUT_DIR,
    output_filename             = "fcc_sol_p",
    output_header               = "FCC-ee LCC Solenoid Positron Ring")
linep.replace_all_repeated_elements()

########################################
# Electron Ring
########################################
linee   = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = REBUILT_SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = None,
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_survey_horizontal   = True,
    reverse_charge_sign         = True,
    output_directory            = OUTPUT_DIR,
    output_filename             = "fcc_sol_e",
    output_header               = "FCC-ee LCC Solenoid Electron Ring")
linee.replace_all_repeated_elements()

########################################
# Delete rebuilt line
########################################
os.remove(REBUILT_SAD_LATTICE_PATH)

########################################
# Get tables
########################################
ttp = linep.get_table(attr = True)
tte = linee.get_table(attr = True)

########################################
# Twiss (with ET to compare with SAD)
########################################
twp_xs  = linep.twiss4d(coupling_edw_teng = True)
twe_xs  = linee.twiss4d(coupling_edw_teng = True)

########################################
# Survey
########################################
svp = linep.survey(theta0 = 0 + 15E-3)
sve = linee.survey(theta0 = -np.pi - 15E-3)

########################################
# Compute SAD s
########################################
twp_xs["s_sad"] = compute_s_sad(twp_xs)
twe_xs["s_sad"] = compute_s_sad(twe_xs)
svp["s_sad"]    = compute_s_sad(svp)
sve["s_sad"]    = compute_s_sad(sve)

########################################
# Align Xsuite Twiss with SAD Twiss
########################################
twp_xs_aligned, twp_sad_aligned    = align_xsuite_twiss_with_sad_twiss(
    xsuite_twiss    = twp_xs,
    sad_twiss       = twp_sad,
    s_tol           = 1E-3)
twe_xs_aligned, twe_sad_aligned    = align_xsuite_twiss_with_sad_twiss(
    xsuite_twiss    = twe_xs,
    sad_twiss       = twe_sad,
    s_tol           = 1E-3)

########################################
# Run comparison assertions
########################################
if RUN_ASSERTS:
    assert_xsuite_matches_sad_twiss(
        xsuite_aligned          = twp_xs_aligned,
        sad_aligned             = twp_sad_aligned,
        xsuite_column_overrides = EDWARDS_TENG_COLUMNS)
    assert_xsuite_matches_sad_twiss(
        xsuite_aligned          = twe_xs_aligned,
        sad_aligned             = twe_sad_aligned,
        xsuite_column_overrides = EDWARDS_TENG_COLUMNS)

################################################################################
# Comparison Plots
################################################################################

########################################
# General Comparison Plots
########################################
plot_xsuite_sad_comparison(
    xsuite_aligned          = twp_xs_aligned,
    sad_aligned             = twp_sad_aligned,
    xsuite_column_overrides = EDWARDS_TENG_COLUMNS)
# plot_xsuite_sad_comparison(
#     xsuite_aligned          = twe_xs_aligned,
#     sad_aligned             = twe_sad_aligned,
#     xsuite_column_overrides = EDWARDS_TENG_COLUMNS)

########################################
# IR Comparison Plots
########################################
plot_xsuite_sad_comparison(
    xsuite_aligned          = twp_xs_aligned,
    sad_aligned             = twp_sad_aligned,
    xsuite_column_overrides = EDWARDS_TENG_COLUMNS,
    ele_start               = "BC2.2",
    ele_stop                = "LD2.3")

########################################
# Overall Survey
########################################
fig = plt.figure(figsize = (8, 4))
plt.plot(svp.Z, svp.X, color = "r")
plt.plot(sve.Z, sve.X, color = "b")
plt.xlabel("Z [m]")
plt.ylabel("X [m]")
fig.suptitle("FCC-ee w/ Solenoid: Survey")
fig.align_labels()
fig.align_titles()

########################################
# IR Survey
########################################
fig = plt.figure(figsize = (8, 4))
plt.plot(svp.Z, svp.X, color = "r")
plt.plot(sve.Z, sve.X, color = "b")
plt.xlabel("Z [m]")
plt.ylabel("X [m]")
plt.xlim( -2000, 2000)
plt.ylim(-100, 10)
fig.suptitle("FCC-ee w/ Solenoid: IR Survey")
fig.align_labels()
fig.align_titles()

################################################################################
# Show plots
################################################################################
if SHOW_PLOTS:
    plt.show()
else:
    plt.close("all")
