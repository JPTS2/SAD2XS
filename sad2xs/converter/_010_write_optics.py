"""
================================================================================
Optics Writer
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-21
================================================================================
"""

################################################################################
# Import Packages
################################################################################
import logging
from datetime import date

import xtrack as xt

from ..types import ConfigLike

from ..output_writer._002_bend import create_bend_optics_file_information
from ..output_writer._003_corr import create_corrector_optics_file_information
from ..output_writer._004_quad import create_quadrupole_optics_file_information
from ..output_writer._005_sext import create_sextupole_optics_file_information
from ..output_writer._006_oct import create_octupole_optics_file_information
from ..output_writer._009_cavity import create_cavity_optics_file_information
from ..output_writer._010_refshift import create_refshift_optics_file_information
from ..output_writer._011_aperture import create_aperture_optics_file_information

logger  = logging.getLogger(__name__)

today   = date.today()

################################################################################
# Write the optics file
################################################################################
def write_optics(
        line:                       xt.Line,
        output_filename:            str,
        output_directory:           str,
        output_header:              str,
        config:                     ConfigLike | None) -> None:
    """
    Write a companion "import optics" Python file for a converted line.

    Generates a `.py` file that, when executed against the
    environment produced by loading the file `write_lattice` wrote,
    calls `env.vars.update(...)` with every live optics variable
    (bend/corrector/quadrupole/sextupole/octupole strengths, cavity
    RF parameters, reference shifts, aperture bounds) as a single
    keyword-argument block. Kept separate from the lattice file itself
    so a user can re-import just the strengths onto an already-loaded
    line without rebuilding its structure.

    Parameters
    ----------
    line : xt.Line
        The converted line to write optics variables for.
    output_filename : str
        Base filename (without extension) for the generated `.py`
        file.
    output_directory : str
        Directory to write the file into.
    output_header : str
        Header text stamped into the generated file, above the
        standard "Converted using the SAD2XS Converter" block.
    config : ConfigLike or None
        Converter configuration. If None, a default `Config()` is
        used (the path taken when `write_optics` is called directly,
        outside `convert_sad_to_xsuite`).
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
    optics_file_string = f"""\"\"\"
{output_header}
================================================================================
Converted using the SAD2XS Converter
Authors:    J. Salvesen
Contact:    john.salvesen@cern.ch
================================================================================
Conversion Date: {today.strftime("%d/%m/%Y")}
\"\"\"

################################################################################
# Import Packages
################################################################################
import xtrack as xt

################################################################################
# Create Environment
################################################################################
env = xt.get_environment()

################################################################################
# Update Strengths
################################################################################
env.vars.update(default_to_zero = True,
"""

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
    # Apertures
    ########################################
    optics_file_string  += create_aperture_optics_file_information(
        line        = line,
        line_table  = line_table,
        config      = config)

    ########################################
    # Close the string
    ########################################
    optics_file_string  += """)
"""

    ########################################
    # Write to file
    ########################################
    output_path = f"{output_directory}/{output_filename}.py"
    with open(output_path, "w", encoding = "utf-8") as f:
        f.write(optics_file_string)

    logger.info(f"Optics file written: {output_path}")
