"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Import Packages
################################################################################
from datetime import date

from ..output_writer._001_drift import create_drift_lattice_file_information
from ..output_writer._002_bend import create_bend_lattice_file_information
from ..output_writer._003_corr import create_corrector_lattice_file_information
from ..output_writer._004_quad import create_quadrupole_lattice_file_information
from ..output_writer._005_sext import create_sextupole_lattice_file_information
from ..output_writer._006_oct import create_octupole_lattice_file_information
from ..output_writer._007_mult import create_multipole_lattice_file_information
from ..output_writer._008_sol import create_solenoid_lattice_file_information
from ..output_writer._009_cavity import create_cavity_lattice_file_information
from ..output_writer._010_refshift import create_refshift_lattice_file_information
from ..output_writer._011_marker import create_marker_lattice_file_information
from ..output_writer._012_line import create_line_lattice_file_information
from ..output_writer._013_model import create_model_lattice_file_information
from ..output_writer._014_offset_markers import create_offset_marker_lattice_file_information

today   = date.today()

################################################################################
# Write the lattice file
################################################################################
def write_lattice(
        line,
        offset_marker_locations,
        output_filename,
        output_directory,
        output_header):
    """
    Write the outputs to the specified files.
    
    Parameters:
    line (xt.Line): The xtrack line object.
    output_filename (str): The base name for the output files.
    header (str): The header for the output files.
    """

    ########################################
    # Initialise the lattice file
    ########################################
    lattice_file_string = f'''"""
{output_header}
================================================================================
Converted using the SAD2XS Converter
Authors:    J. Salvesen
Contact:    john.salvesen@cern.ch
================================================================================
Conversion Date: {today.strftime("%d/%m/%Y")}
"""

################################################################################
# Import Packages
################################################################################
import xtrack as xt
import numpy as np

################################################################################
# Create or Get Environment
################################################################################
env = xt.get_environment(verbose = True)
env.vars.default_to_zero = True

########################################
# Key Global Variables
########################################
env["mass"]     = {line.particle_ref.mass0}
env["p0c"]      = {line.particle_ref.p0c[0]}
env["q0"]       = {line.particle_ref.q0}
env["fshift"]   = {line.env["fshift"]}

########################################
# Reference Particle
########################################
env.particle_ref    = xt.Particles(
    mass0   = env["mass"],
    p0c     = env["p0c"],
    q0      = env["q0"])

################################################################################
# Import lattice
################################################################################
'''
    
    ########################################
    # Add all the other sections
    ########################################
    line_table  = line.get_table(attr = True)

    lattice_file_string += create_drift_lattice_file_information(line, line_table)
    lattice_file_string += create_bend_lattice_file_information(line, line_table)
    lattice_file_string += create_corrector_lattice_file_information(line, line_table)
    lattice_file_string += create_quadrupole_lattice_file_information(line, line_table)
    lattice_file_string += create_sextupole_lattice_file_information(line, line_table)
    lattice_file_string += create_octupole_lattice_file_information(line, line_table)
    lattice_file_string += create_multipole_lattice_file_information(line, line_table)
    lattice_file_string += create_solenoid_lattice_file_information(line, line_table)
    lattice_file_string += create_cavity_lattice_file_information(line, line_table)
    lattice_file_string += create_refshift_lattice_file_information(line, line_table)
    lattice_file_string += create_marker_lattice_file_information(line, line_table, offset_marker_locations)
    lattice_file_string += create_line_lattice_file_information(line, line_table)
    lattice_file_string += create_model_lattice_file_information()
    lattice_file_string += create_offset_marker_lattice_file_information(offset_marker_locations)

    ########################################
    # Write to file
    ########################################
    with open(f"{output_directory}/{output_filename}.py", 'w') as f:
        f.write(lattice_file_string)
