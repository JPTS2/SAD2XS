"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Import Packages
################################################################################
from datetime import date

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
        line,
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
    # Add all the other sections
    ########################################
    line_table  = line.get_table(attr = True)

    optics_file_string  += create_bend_optics_file_information(line, line_table)
    optics_file_string  += create_corrector_optics_file_information(line, line_table)
    optics_file_string  += create_quadrupole_optics_file_information(line, line_table)
    optics_file_string  += create_sextupole_optics_file_information(line, line_table)
    optics_file_string  += create_octupole_optics_file_information(line, line_table)
    optics_file_string  += create_cavity_optics_file_information(line, line_table)
    optics_file_string  += create_refshift_optics_file_information(line, line_table)

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
