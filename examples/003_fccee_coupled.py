"""
================================================================================
Example 003: FCC-ee Coupled Lattice Conversion
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

from sad2xs.xsuite_helpers import (
    align_xsuite_twiss_with_sad_twiss,
    assert_xsuite_matches_sad_twiss,
    compute_s_sad,
    plot_xsuite_sad_comparison,
    DEFAULT_TWISS_TOLERANCES)

# SAD's coupled beta/alpha (Edwards-Teng convention) map to these Xsuite columns
EDWARDS_TENG_COLUMNS   = {
    "betx": "betx_edw_teng", "bety": "bety_edw_teng",
    "alfx": "alfx_edw_teng", "alfy": "alfy_edw_teng"}

# SAD's coupling matrix R1-R4 map onto Xsuite's Edwards-Teng R-matrix columns
# (R11/R12/R21/R22): confirmed by independent derivation in the dev/sad_coupling
# investigation, both agree with SAD's own R1-R4 twiss output to tolerance.
COUPLING_COLUMNS    = {
    "R1": "r11_edw_teng", "R2": "r12_edw_teng",
    "R3": "r21_edw_teng", "R4": "r22_edw_teng"}
COUPLING_TOLERANCES = {column: dict(atol = 1E-4, rtol = 1E-3) for column in COUPLING_COLUMNS}

################################################################################
# User Parameters
################################################################################
SAD_LATTICE_PATH            = "lattices/fccee_coupled.sad"
LINE_NAME                   = "RING"

################################################################################
# Load Reference Data
################################################################################
tw_sad  = s2x.sad_helpers.twiss_sad(
    lattice_filepath            = SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    calc6d                      = False,
    closed                      = True,
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
    output_filename             = "fcc_coupled",
    output_header               = "FCC-ee Coupled Lattice")

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
tw_xs_aligned, tw_sad_aligned  = align_xsuite_twiss_with_sad_twiss(
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
        tolerances              = {**DEFAULT_TWISS_TOLERANCES, **COUPLING_TOLERANCES},
        xsuite_column_overrides = {**EDWARDS_TENG_COLUMNS, **COUPLING_COLUMNS})

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
# Coupling Matrix: SAD R1-R4 vs Xsuite Edwards-Teng
########################################
fig, axs    = plt.subplots(2, 2, figsize = (10, 8), sharex = True)
axs         = axs.flatten()

for ax, (sad_column, xs_column) in zip(axs, COUPLING_COLUMNS.items()):
    ax.plot(tw_sad_aligned.s, getattr(tw_sad_aligned, sad_column), label = "SAD", color = "red")
    ax.plot(tw_xs_aligned.s, getattr(tw_xs_aligned, xs_column), label = "Xsuite (Edwards-Teng)", color = "black", linestyle = "--")
    ax.set_title(sad_column)
    ax.grid()

axs[0].legend()
fig.supxlabel("s [m]")
fig.supylabel("Coupling [m]")
fig.suptitle("FCC-ee Coupled Lattice: SAD R-matrix vs Xsuite Edwards-Teng")
fig.align_labels()

########################################
# Beta Functions: Mais-Ripken vs Edwards-Teng
########################################
# Xsuite's plain betx/bety (Mais-Ripken mode decomposition) is not the
# coupled-optics quantity SAD reports; only the Edwards-Teng columns agree.
fig, axs    = plt.subplots(1, 2, figsize = (10, 4), sharex = True)

for ax, (sad_column, plain_column, et_column) in zip(
        axs, [("betx", "betx", "betx_edw_teng"), ("bety", "bety", "bety_edw_teng")]):
    ax.plot(tw_sad_aligned.s, getattr(tw_sad_aligned, sad_column), label = "SAD", color = "red")
    ax.plot(tw_xs_aligned.s, getattr(tw_xs_aligned, plain_column), label = "Xsuite (Mais-Ripken)", color = "blue", linestyle = ":")
    ax.plot(tw_xs_aligned.s, getattr(tw_xs_aligned, et_column), label = "Xsuite (Edwards-Teng)", color = "black", linestyle = "--")
    ax.set_title(sad_column)
    ax.grid()

axs[0].legend()
fig.supxlabel("s [m]")
fig.supylabel("Beta function [m]")
fig.suptitle("FCC-ee Coupled Lattice: Mais-Ripken vs Edwards-Teng Beta Functions")
fig.align_labels()

################################################################################
# Show plots
################################################################################
if SHOW_PLOTS:
    plt.show()
else:
    plt.close("all")
