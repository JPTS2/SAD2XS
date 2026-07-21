"""
================================================================================
Lattice Writer
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
from ..helpers import species_from_mass_and_charge

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

logger  = logging.getLogger(__name__)

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
        config:                     ConfigLike | None) -> None:
    """
    Write a converted line to a self-contained, reloadable Python
    lattice file.

    Generates a `.py` file that reconstructs `line` from scratch when
    executed against a fresh `xt.Environment`: reference-particle
    globals, then one section per element family (drifts, bends,
    correctors, quadrupoles, sextupoles, octupoles, multipoles,
    solenoids, cavities, reference shifts, apertures, markers), then
    the LINE definition and modelling (integrator/model) settings, and
    finally any resolved offset-marker insertion points. Elements are
    grouped by length (see `sad2xs.output_writer._000_helpers`) so
    identical elements are written once and reused via
    `env.new(..., mode="clone")`; a `-`-prefixed element is only
    written if no non-reversed sibling of the same root name exists in
    the line.

    Parameters
    ----------
    line : xt.Line
        The converted line to write. Must already have reference-
        particle globals (mass0/p0c/q0, and fshift) available either
        as line variables or on `line.particle_ref`.
    output_filename : str
        Base filename (without extension) for the generated `.py`
        file.
    output_directory : str or None
        Directory to write the file into.
    output_header : str
        Header text stamped into the generated file, above the
        standard "Converted using the SAD2XS Converter" block.
    offset_marker_locations : dict or None
        Resolved offset-marker insertion points, as returned by
        `sad2xs.converter._008_offset_markers.convert_offset_markers`.
        If given, an "Install Offset Markers" section is appended.
    config : ConfigLike or None
        Converter configuration. If None, a default `Config()` is
        used (the path taken when `write_lattice` is called directly,
        outside `convert_sad_to_xsuite`).

    Raises
    ------
    ValueError
        If a reference-particle global is unavailable from both
        `line`'s variables and `line.particle_ref`.
    """

    ########################################
    # If it's not run through the converter, create config
    ########################################
    if config is None:
        from ..config import Config
        config  = Config()

    ########################################
    # Resolve globals without mutating the input line
    ########################################
    writer_globals = {}
    for variable_name in ("p0c", "mass0", "q0"):
        try:
            value = line[variable_name]
        except KeyError:
            if line.particle_ref is None:
                raise ValueError(
                    f"Cannot write lattice without line variable "
                    f"""\"{variable_name}\" or line.particle_ref.""") from None
            value = getattr(line.particle_ref, variable_name)

        if hasattr(value, "item"):
            value = value.item()
        writer_globals[variable_name] = value

    try:
        fshift = line["fshift"]
    except KeyError:
        fshift = 0.0
    if hasattr(fshift, "item"):
        fshift = fshift.item()
    writer_globals["fshift"] = fshift

    ########################################
    # Determine species string for reference particle
    ########################################
    species             = species_from_mass_and_charge(
        writer_globals["mass0"],
        writer_globals["q0"])
    if species is not None:
        _particle_ref_line = f"""xt.Particles("{species}", p0c=env["p0c"])"""
    else:
        _particle_ref_line = (
            "xt.Particles(\n"
            f"""    mass0   = env["mass0"],\n"""
            f"""    p0c     = env["p0c"],\n"""
            f"""    q0      = env["q0"])""")

    ########################################
    # Initialise the lattice file
    ########################################
    lattice_file_string = f"""\"\"\"
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
import numpy as np

################################################################################
# Create or Get Environment
################################################################################
env = xt.get_environment()
env.vars.default_to_zero = True

########################################
# Key Global Variables
########################################
env["mass0"]    = {writer_globals["mass0"]}
env["p0c"]      = {writer_globals["p0c"]}
env["q0"]       = {writer_globals["q0"]}
env["fshift"]   = {writer_globals["fshift"]}

########################################
# Reference Particle
########################################
env.particle_ref    = {_particle_ref_line}

################################################################################
# Import lattice
################################################################################
"""

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
    output_path = f"{output_directory}/{output_filename}.py"
    with open(output_path, "w", encoding = "utf-8") as f:
        f.write(lattice_file_string)

    logger.info(
        f"Lattice file written: {output_path} "
        f"({len(line.element_names)} elements)")
