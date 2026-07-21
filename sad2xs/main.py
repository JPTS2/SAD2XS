"""
================================================================================
Main Conversion Entry Point
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
# Required Packages
################################################################################
import logging
from typing import Any

import xtrack as xt

from .config import Config
from ._logging import set_log_level
from .helpers import (
    log_section_heading,
    species_from_mass_and_charge,
    suppressed_xtrack_progress,
)

from .converter._001_parser import parse_sad_file
from .converter._002_element_exclusion import exclude_elements
from .converter._003_expression_converter import convert_expressions
from .converter._004_element_converter import convert_elements
from .converter._005_line_converter import convert_lines
from .converter._006_solenoid_converter import convert_solenoids, solenoid_reference_shift_corrections
from .converter._007_reversals import reverse_line_survey_horizontal, reverse_line_survey_vertical, reverse_line_element_order
from .converter._008_offset_markers import convert_offset_markers
from .converter._009_write_lattice import write_lattice
from .converter._010_write_optics import write_optics

logger  = logging.getLogger(__name__)

################################################################################
# Overall Function
################################################################################
def convert_sad_to_xsuite(
        sad_lattice_path:               str,
        output_directory:               str,
        output_filename:                str | None              = None,
        line_name:                      str | None              = None,
        output_header:                  str                     = \
            "SAD to XSuite Lattice Conversion",
        excluded_elements:              list[str] | None        = None,
        user_multipole_replacements:    dict[str, str] | None   = None,
        reverse_element_order:          bool                    = False,
        reverse_survey_horizontal:      bool                    = False,
        reverse_survey_vertical:        bool                    = False,
        reverse_charge_sign:            bool                    = False,
        install_apertures_as_markers:   bool                    = False,
        **kwargs: Any) -> xt.Line:
    """
    Convert a SAD lattice file to an Xsuite line, in one call.

    Parses the SAD file, builds an Xsuite environment, and converts every
    expression, element, and line. Applies solenoid reference-shift
    corrections and configures per-element-type integrator models, then
    writes the result to lattice and optics files on disk and reloads it
    from those files, so the returned line matches the generated output.

    If ``_test_mode`` is set (via a keyword argument, see `Config`), the
    in-memory line is returned immediately after conversion, before any
    files are written -- used by the test suite to avoid disk I/O per
    test.

    Parameters
    ----------
    sad_lattice_path : str
        Path to the input SAD lattice file.
    output_directory : str
        Directory to write the generated lattice and optics files into.
    output_filename : str or None, optional
        Base filename for the generated output files. Defaults to the
        input filename (without its ``.sad`` extension) when not given.
    line_name : str or None, optional
        SAD line name to select for conversion. Defaults to the longest
        line in the lattice (by length, or by element count for
        all-thin lines) when not given.
    output_header : str, optional
        Header text stamped into the generated lattice and optics files.
    excluded_elements : list or None, optional
        Element names to drop from the parsed lattice before conversion.
    user_multipole_replacements : dict or None, optional
        Per-element overrides controlling how specific elements convert
        to multipoles.
    reverse_element_order : bool, optional
        Reverse the element order of the selected line.
    reverse_survey_horizontal : bool, optional
        Reverse the bend directions of the selected line (horizontal
        survey mirroring).
    reverse_survey_vertical : bool, optional
        Reverse the bend directions of the selected line (vertical
        survey mirroring).
    reverse_charge_sign : bool, optional
        Flip the sign of the reference particle's charge.
    install_apertures_as_markers : bool, optional
        Convert APERT elements to MARK elements instead of aperture
        objects.
    **kwargs
        Forwarded to `Config` to override converter configuration
        defaults (e.g. element models, integrators, tolerances).

    Returns
    -------
    xt.Line
        The converted Xsuite line, reloaded from the generated output
        files (or the in-memory line directly, if ``_test_mode`` is set).
    """
    ############################################################################
    # Load config
    ############################################################################
    config  = Config(**kwargs)

    ########################################
    # Verbosity shorthand: only ever raises the output level
    ########################################
    if config._verbose and logger.getEffectiveLevel() > logging.INFO:
        set_log_level("info")

    ############################################################################
    # Introduction Printout
    ############################################################################
    logger.info(config.ASCII_LOGO)
    logger.info(f"Processing SAD file: {sad_lattice_path}")

    ############################################################################
    # Parse Lattice
    ############################################################################
    log_section_heading("Parsing SAD File", mode = "section")

    parsed_lattice_data = parse_sad_file(
        sad_lattice_path              = sad_lattice_path,
        config                        = config,
        install_apertures_as_markers  = install_apertures_as_markers)

    ############################################################################
    # Remove Excluded elements
    ############################################################################
    log_section_heading("Removing Excluded Elements", mode = "section")

    parsed_lattice_data = exclude_elements(
        parsed_lattice_data = parsed_lattice_data,
        excluded_elements   = excluded_elements)
    
    ############################################################################
    # Check if apertures should become markers
    ############################################################################
    if install_apertures_as_markers:
        log_section_heading("Converting apertures to markers", mode = "section")

        if "apert" in parsed_lattice_data["elements"]:
            if "mark" in parsed_lattice_data["elements"]:
                merged = {
                    **parsed_lattice_data["elements"]["apert"],
                    **parsed_lattice_data["elements"]["mark"]}    # Mark takes precedence
                parsed_lattice_data["elements"]["mark"] = merged
            else:
                parsed_lattice_data["elements"]["mark"] = \
                    parsed_lattice_data["elements"]["apert"]

            parsed_lattice_data["elements"].pop("apert")

    ############################################################################
    # Build Environment
    ############################################################################
    log_section_heading("Building Environment", mode = "section")

    env = xt.Environment()

    ############################################################################
    # Convert Expressions
    ############################################################################
    log_section_heading("Converting Expressions", mode = "section")

    convert_expressions(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env)

    ############################################################################
    # Convert Elements
    ############################################################################
    # Must run before reverse_charge_sign below -- see docs/line-reversals.md.
    log_section_heading("Converting Elements", mode = "section")

    convert_elements(
        parsed_lattice_data         = parsed_lattice_data,
        environment                 = env,
        user_multipole_replacements = user_multipole_replacements,
        config                      = config)

    ########################################
    # Apply reverse_charge_sign after element conversion
    ########################################
    if reverse_charge_sign:
        env["q0"] = -env["q0"]

    ########################################
    # Add reference particle from globals
    ########################################
    species = species_from_mass_and_charge(env["mass0"], env["q0"])
    if species is not None:
        env.particle_ref = xt.Particles(species, p0c = env["p0c"])
    else:
        env.particle_ref = xt.Particles(
            p0c     = env["p0c"],
            q0      = env["q0"],
            mass0   = env["mass0"])

    ############################################################################
    # Convert Lines
    ############################################################################
    log_section_heading("Converting Lines", mode = "section")

    convert_lines(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env)
    
    ########################################
    # Select the line
    ########################################
    log_section_heading("Selecting Line", mode = "section")

    if line_name is not None:
        line            = env.lines[line_name.lower()]
        selected_line   = line_name
    else:
        line_lengths    = {line: env.lines[line].get_length() for line in env.lines}

        # If several are the same length, check also number of elements (thin elements)
        if max(line_lengths.values()) != 0:
            longest_line    = max(line_lengths, key = lambda line: line_lengths[line])
        else:
            line_lengths    = {line: len(env.lines[line].element_names) for line in env.lines}
            longest_line    = max(line_lengths, key = lambda line: line_lengths[line])

        line            = env.lines[longest_line]
        selected_line   = longest_line

    logger.info(
        f"Selected line: {selected_line} "
        f"({len(line.element_names)} elements, {line.get_length():.3f} m)")

    ############################################################################
    # Solenoid Corrections
    ############################################################################
    log_section_heading("Performing Solenoid Corrections", mode = "section")

    ########################################
    # Convert elements between solenoids
    ########################################
    log_section_heading("Converting Elements between Solenoids", mode = "section")
    convert_solenoids(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env,
        config              = config)
    
    ########################################
    # Correct solenoid reference shifts
    ########################################
    log_section_heading("Correcting Solenoid Reference Shifts", mode = "section")
    solenoid_reference_shift_corrections(
        line                    = line,
        parsed_lattice_data     = parsed_lattice_data,
        environment             = env,
        reverse_line            = reverse_element_order,
        config                  = config)
    
    ################################################################################
    # Configure Modelling Mode
    ################################################################################
    log_section_heading("Configuring Element Modelling", mode = "section")

    ########################################
    # Set integrators
    ########################################
    log_section_heading("Configuring Integrators", mode = "section")


    tt          = line.get_table()
    tt_drift    = tt.rows[tt.element_type == "Drift"]
    tt_bend     = tt.rows[tt.element_type == "Bend"]
    tt_quad     = tt.rows[tt.element_type == "Quadrupole"]
    tt_sext     = tt.rows[tt.element_type == "Sextupole"]
    tt_oct      = tt.rows[tt.element_type == "Octupole"]
    tt_mult     = tt.rows[tt.element_type == "Multipole"]
    tt_sol      = tt.rows[tt.element_type == "Solenoid"]
    tt_cavi     = tt.rows[tt.element_type == "Cavity"]

    line.set(
        tt_drift,
        model               = config.MODEL_DRIFT)
    line.set(
        tt_bend,
        model               = config.MODEL_BEND,
        integrator          = config.INTEGRATOR_BEND,
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_BEND)
    line.set(
        tt_quad,
        model               = config.MODEL_QUAD,
        integrator          = config.INTEGRATOR_QUAD,
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_QUAD)
    line.set(
        tt_sext,
        model               = config.MODEL_SEXT,
        integrator          = config.INTEGRATOR_SEXT,
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_SEXT)
    line.set(
        tt_oct,
        model               = config.MODEL_OCT,
        integrator          = config.INTEGRATOR_OCT,
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_OCT)
    line.set(
        tt_mult,
        model               = config.MODEL_MULT,
        integrator          = config.INTEGRATOR_MULT,
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_MULT)
    line.set(
        tt_sol,
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_SOL)
    line.set(
        tt_cavi,
        model               = config.MODEL_CAVI,
        integrator          = config.INTEGRATOR_CAVI,
        absolute_time       = config.ABSOLUTE_TIME_CAVI)
    
    ########################################
    # Set bend edges
    ########################################
    log_section_heading("Configuring Bend Model", mode = "section")

    line.configure_bend_model(edge = config.EDGE_MODEL_BEND)

    ########################################
    # Set quad edges
    ########################################
    log_section_heading("Configuring Quadrupole Model", mode = "section")

    line.configure_quadrupole_model(edge = config.EDGE_MODEL_QUAD)

    ############################################################################
    # Line reversals
    ############################################################################
    if reverse_element_order:
        log_section_heading("Reversing Element order of Line", mode = "section")
        line = reverse_line_element_order(line)
        logger.info(f"Reversed element order ({len(line.element_names)} elements)")

    if reverse_survey_horizontal:
        log_section_heading("Reversing Bend Directions of Line", mode = "section")
        line = reverse_line_survey_horizontal(line)

    if reverse_survey_vertical:
        log_section_heading("Reversing Bend Directions of Line (Vertical)", mode = "section")
        line = reverse_line_survey_vertical(line)

    ############################################################################
    # Handle Offset Markers
    ############################################################################
    log_section_heading("Converting Offset Markers", mode = "section")

    line, offset_marker_locations   = convert_offset_markers(
        line                = line,
        parsed_lattice_data = parsed_lattice_data)

    ############################################################################
    # Breakpoint for testing
    ############################################################################
    if config._test_mode:
        log_section_heading("Converter Breakpoint: Test mode active", mode = "section")
        return line

    ############################################################################
    # Output files
    ############################################################################
    log_section_heading("Generating Output Files", mode = "banner")

    ########################################
    # Filename
    ########################################
    if output_filename is None:
        output_filename = sad_lattice_path.split("/")[-1].replace(".sad", "")
    else:
        assert isinstance(output_filename, str), "output_filename must be a string"

    ########################################
    # Lattice
    ########################################
    log_section_heading("Generating Lattice File", mode = "section")

    write_lattice(
        line                        = line,
        offset_marker_locations     = offset_marker_locations,
        output_filename             = output_filename,
        output_directory            = output_directory,
        output_header               = output_header,
        config                      = config)
    
    ########################################
    # Import optics
    ########################################
    log_section_heading("Generating Optics File", mode = "section")

    write_optics(
        line                        = line,
        output_filename             = f"{output_filename}_import_optics",
        output_directory            = output_directory,
        output_header               = output_header,
        config                      = config)

    ############################################################################
    # Delete and re-initialise
    ############################################################################

    ########################################
    # Delete messy import environment
    ########################################
    del env
    del line

    ########################################
    # Cleanly load from the generated files
    ########################################
    env     = xt.Environment()
    with suppressed_xtrack_progress(active = not logger.isEnabledFor(logging.INFO)):
        env.call(f"{output_directory}/{output_filename}.py")
        env.call(f"{output_directory}/{output_filename}_import_optics.py")
    line    = env.lines["line"]

    ############################################################################
    # Complete message
    ############################################################################
    log_section_heading("Conversion Complete", mode = "banner")

    ############################################################################
    # Return the line
    ############################################################################
    return line
