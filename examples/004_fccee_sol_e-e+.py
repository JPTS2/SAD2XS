"""
================================================================================
Example 004: FCC-ee Solenoid Lattice Conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-07
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import os
from _example_helpers import (
    DEFAULT_MIN_MATCHED_ELEMENTS,
    DEFAULT_OUTPUT_DIR,
    EDWARDS_TENG_COLUMNS,
    assert_twiss_matches_sad,
    configure_example_runtime,
    create_comparison_plots)

SHOW_PLOTS  = globals().get("SHOW_PLOTS", True)
RUN_ASSERTS = globals().get("RUN_ASSERTS", True)
OUTPUT_DIR  = configure_example_runtime(
    output_dir = globals().get("OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

import sad2xs as s2x
s2x.set_log_level("info")
import numpy as np
import matplotlib.pyplot as plt

################################################################################
# User Parameters
################################################################################
SAD_LATTICE_PATH            = "lattices/fccee_sol.sad"
REBUILT_SAD_LATTICE_PATH    = "lattices/fccee_sol_rebuilt.sad"
LINE_NAME                   = "RING"

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

################################################################################
# Twiss
################################################################################
# SAD reports coupled beta/alpha in the Edwards-Teng convention.
twp = linep.twiss4d(coupling_edw_teng = True)
twe = linee.twiss4d(coupling_edw_teng = True)

if RUN_ASSERTS:
    assert_twiss_matches_sad(
        line                 = linep,
        twiss_xsuite         = twp,
        twiss_sad            = twp_sad,
        min_matched_elements = DEFAULT_MIN_MATCHED_ELEMENTS,
        xsuite_columns       = EDWARDS_TENG_COLUMNS)
    assert_twiss_matches_sad(
        line                 = linee,
        twiss_xsuite         = twe,
        twiss_sad            = twe_sad,
        min_matched_elements = DEFAULT_MIN_MATCHED_ELEMENTS,
        xsuite_columns       = EDWARDS_TENG_COLUMNS)

################################################################################
# Survey
################################################################################
svp = linep.survey(theta0 = 0 + 15E-3)
sve = linee.survey(theta0 = -np.pi - 15E-3)

print("First IP")
print(svp.rows["ip.0"])
print(sve.rows["ip.0"])
print("Second IP")
print(svp.rows["ip.2"])
print(sve.rows["ip.6"])
print("Third IP")
print(svp.rows["ip.4"])
print(sve.rows["ip.4"])
print("Fourth IP")
print(svp.rows["ip.6"])
print(sve.rows["ip.2"])

########################################
# Overall Comparison
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
# IR Comparison
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
# Twiss comparison subsection
################################################################################
twp_ip      = twp.rows[
    (twp.s > (twp["s", "ip.2"] - 20)) & \
     (twp.s < (twp["s", "ip.2"] + 20))]
twp_sad_ip  = twp_sad.rows[
    (twp_sad.s > (twp_sad["s", "IP.3"] - 20)) & \
     (twp_sad.s < (twp_sad["s", "IP.3"] + 20))]

create_comparison_plots(
    twp_ip,
    twp_sad_ip,
    suptitle        = "FCC-ee w/ Solenoid",
    zero_tol        = 1E-10,
    xsuite_columns  = EDWARDS_TENG_COLUMNS)

################################################################################
# Show plots
################################################################################
if SHOW_PLOTS:
    plt.show()
