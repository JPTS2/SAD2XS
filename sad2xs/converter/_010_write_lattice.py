"""
(Unofficial) SAD to XSuite Converter: Lattice Writer
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-12-2025
"""

################################################################################
# Import Packages
################################################################################
from datetime import date
import xtrack as xt

from ..types import ConfigLike

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
from ..output_writer._011_aperture import create_aperture_lattice_file_information
from ..output_writer._012_marker import create_marker_lattice_file_information
from ..output_writer._013_line import create_line_lattice_file_information
from ..output_writer._014_model import create_model_lattice_file_information
from ..output_writer._015_offset_markers import create_offset_marker_lattice_file_information

today   = date.today()

################################################################################
# Write the lattice file
################################################################################
def write_lattice(
        line:                       xt.Line,
        output_filename:            str,
        output_directory:           str | None,
        output_header:              str,
        offset_marker_locations:    dict | None,
        config:                     ConfigLike | None):
    """
    Write the outputs to the specified files.
    
    Parameters:
    line (xt.Line): The xtrack line object.
    output_filename (str): The base name for the output files.
    header (str): The header for the output files.
    """

    ########################################
    # If it's not run through the converter, create config
    ########################################
    if config is None:
        from ..config import Config
        config  = Config()

    ########################################
    # If it's not a SAD2XS lattice, may not have right variables
    ########################################
    try:
        line["p0c"]
    except KeyError:
        line["p0c"]     = line.particle_ref.p0c                 # type: ignore

    try:
        line["mass0"]
    except KeyError:
        line["mass0"]   = line.particle_ref.mass0               # type: ignore

    try:
        line["q0"]
    except KeyError:
        line["q0"]      = line.particle_ref.q0                  # type: ignore

    try:
        line["fshift"]
    except KeyError:
        line["fshift"]  = 0.0

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
env["mass0"]    = {line["mass0"]}
env["p0c"]      = {line["p0c"]}
env["q0"]       = {line["q0"]}
env["fshift"]   = {line["fshift"]}

########################################
# Reference Particle
########################################
env.particle_ref    = xt.Particles(
    mass0   = env["mass0"],
    p0c     = env["p0c"],
    q0      = env["q0"])

################################################################################
# Import lattice
################################################################################
'''
 
    ########################################
    # Get the line table
    ########################################
    line_table  = line.get_table(attr = True)

    ########################################
    # Prepare for removal of - signs where not needed
    ########################################
    element_names   = line_table.name

    minus_elements  = line_table.rows["-.*"].name
    for minus_element in minus_elements:
        root_name   = minus_element.split("::")[0][1:]
        plus_eles   = [name.startswith(root_name) for name in element_names]

        if any(plus_eles):
            plus_name   = element_names[plus_eles][0]
            type_minus  = line_table["element_type", minus_element]
            type_plus   = line_table["element_type", plus_name]

            assert type_minus == type_plus, \
                "Element types for element and its negative do not match"

    ########################################
    # Drifts
    ########################################
    lattice_file_string += create_drift_lattice_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Bends
    ########################################
    lattice_file_string += create_bend_lattice_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Correctors
    ########################################
    lattice_file_string += create_corrector_lattice_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Quadrupoles
    ########################################
    lattice_file_string += create_quadrupole_lattice_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Sextupoles
    ########################################
    lattice_file_string += create_sextupole_lattice_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Octupoles
    ########################################
    lattice_file_string += create_octupole_lattice_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Multipoles
    ########################################
    lattice_file_string += create_multipole_lattice_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Solenoids
    ########################################
    lattice_file_string += create_solenoid_lattice_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Cavities
    ########################################
    lattice_file_string += create_cavity_lattice_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Reference Shifts
    ########################################
    lattice_file_string += create_refshift_lattice_file_information(
        line_table  = line_table,
        config      = config)

    ########################################
    # Apertures
    ########################################
    lattice_file_string += create_aperture_lattice_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Markers
    ########################################
    lattice_file_string += create_marker_lattice_file_information(
        line_table              = line_table,
        offset_marker_locations = offset_marker_locations,
        config                  = config)

    ########################################
    # Line
    ########################################
    lattice_file_string += create_line_lattice_file_information(
        line_table  = line_table,
        config      = config)

    ########################################
    # Modelling
    ########################################
    lattice_file_string += create_model_lattice_file_information(
        config      = config)

    ########################################
    # Offset Markers
    ########################################
    if offset_marker_locations is not None:
        lattice_file_string += create_offset_marker_lattice_file_information(
            offset_marker_locations = offset_marker_locations,
            config                  = config)

    ########################################
    # Write to file
    ########################################
    with open(f"{output_directory}/{output_filename}.py", "w", encoding = "utf-8") as f:
        f.write(lattice_file_string)
