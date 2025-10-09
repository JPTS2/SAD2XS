"""
(Unofficial) SAD to XSuite Converter: Optics Writer
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-10-2025
"""

################################################################################
# Import Packages
################################################################################
import xtrack as xt
from datetime import date

from ..types import ConfigLike

from ..output_writer._002_bend import create_bend_optics_file_information
from ..output_writer._003_corr import create_corrector_optics_file_information
from ..output_writer._004_quad import create_quadrupole_optics_file_information
from ..output_writer._005_sext import create_sextupole_optics_file_information
from ..output_writer._006_oct import create_octupole_optics_file_information
from ..output_writer._009_cavity import create_cavity_optics_file_information
from ..output_writer._010_refshift import create_refshift_optics_file_information

today   = date.today()

################################################################################
# Write the optics file
################################################################################
def write_optics(
        line:                       xt.Line,
        output_filename:            str,
        output_directory:           str,
        output_header:              str,
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
    # Initialise the lattice file
    ########################################
    optics_file_string = f'''"""
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

################################################################################
# Create Environment
################################################################################
env = xt.get_environment(verbose = True)

################################################################################
# Update Strengths
################################################################################
env.vars.update(default_to_zero = True,
'''

    ########################################
    # Get the line table
    ########################################
    line_table  = line.get_table(attr = True)

    ########################################
    # Bends
    ########################################
    optics_file_string  += create_bend_optics_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Correctors
    ########################################
    optics_file_string  += create_corrector_optics_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Quadrupoles
    ########################################
    optics_file_string  += create_quadrupole_optics_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Sextupoles
    ########################################
    optics_file_string  += create_sextupole_optics_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Octupoles
    ########################################
    optics_file_string  += create_octupole_optics_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Cavities
    ########################################
    optics_file_string  += create_cavity_optics_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Reference Shifts
    ########################################
    optics_file_string  += create_refshift_optics_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Close the string
    ########################################
    optics_file_string  += ''')
'''

    ########################################
    # Write to file
    ########################################
    with open(f"{output_directory}/{output_filename}_import_optics.py", 'w') as f:
        f.write(optics_file_string)
