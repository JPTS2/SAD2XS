"""
(Unofficial) SAD to XSuite Converter
"""
################################################################################
# Required Packages
################################################################################
import os
import sad2xs as s2x
import numpy as np
import matplotlib.pyplot as plt

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
s2x.sad_helpers.rebuild_sad_lattice(
    lattice_filepath    = SAD_LATTICE_PATH,
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
    output_filepath     = REBUILT_SAD_LATTICE_PATH)

twp_sad  = s2x.sad_helpers.twiss_sad(
    lattice_filepath        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    calc6d                  = False,
    closed                  = True,
    reverse_element_order   = False,
    reverse_bend_direction  = False,
    additional_commands     = "")
twe_sad  = s2x.sad_helpers.twiss_sad(
    lattice_filepath        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    calc6d                  = False,
    closed                  = True,
    reverse_element_order   = False,
    reverse_bend_direction  = True,
    additional_commands     = "")

################################################################################
# Convert Lattice
################################################################################

########################################
# Positron Ring
########################################
linep   = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = None,
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_bend_direction      = False,
    reverse_charge              = False,
    output_directory            = 'out',
    output_filename             = "fcc_sol_p",
    output_header               = "FCC-ee LCC Solenoid Positron Ring")
linep.replace_all_repeated_elements()

########################################
# Electron Ring
########################################
linee   = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = None,
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_bend_direction      = True,
    reverse_charge              = True,
    output_directory            = 'out',
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
twp = linep.twiss4d()
twe = linee.twiss4d()

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

create_comparison_plots(twp_ip, twp_sad_ip, suptitle = "FCC-ee w/ Solenoid", zero_tol = 1E-10)

################################################################################
# Show plots
################################################################################
plt.show()
