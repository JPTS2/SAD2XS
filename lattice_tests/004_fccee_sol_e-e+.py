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

twp_sad  = twiss_sad(
    lattice_filename        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "4d",
    closed                  = True,
    reverse_element_order   = False,
    reverse_bend_direction  = False,
    additional_commands     = "")
twe_sad  = twiss_sad(
    lattice_filename        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "4d",
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

fig = plt.figure()
plt.plot(svp.Z, svp.X, color = "r")
plt.plot(sve.Z, sve.X, color = "b")

plt.show()
