"""
Unofficial SAD to XSuite Lattice Converter
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-27
"""

################################################################################
# Required Packages
################################################################################
import logging

import xtrack as xt

from .config import Config
from ._logging import set_log_level
from .helpers import log_section_heading, species_from_mass_and_charge

from .converter._001_parser import parse_sad_file
from .converter._002_element_exclusion import exclude_elements
from .converter._003_expression_converter import convert_expressions
from .converter._004_element_converter import convert_elements
from .converter._005_line_converter import convert_lines
from .converter._006_solenoid_converter import convert_solenoids, solenoid_reference_shift_corrections
from .converter._007_reversals import reverse_line_survey_horizontal, reverse_line_element_order
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
        output_filename:                str | None  = None,
        line_name:                      str | None  = None,
        output_header:                  str         = "SAD to XSuite Lattice Conversion",
        excluded_elements:              list | None = None,
        user_multipole_replacements:    dict | None = None,
        reverse_element_order:          bool        = False,
        reverse_survey_horizontal:         bool        = False,
        reverse_charge_sign:                 bool        = False,
        install_apertures_as_markers:   bool        = False,
        **kwargs):
    
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
    log_section_heading("Parsing SAD File", mode = 'section')

    parsed_lattice_data = parse_sad_file(
        sad_lattice_path              = sad_lattice_path,
        config                        = config,
        install_apertures_as_markers  = install_apertures_as_markers)

    ############################################################################
    # Remove Excluded elements
    ############################################################################
    log_section_heading("Removing Excluded Elements", mode = 'section')

    parsed_lattice_data = exclude_elements(
        parsed_lattice_data = parsed_lattice_data,
        excluded_elements   = excluded_elements)
    
    ############################################################################
    # Check if apertures should become markers
    ############################################################################
    if install_apertures_as_markers:
        log_section_heading("Converting apertures to markers", mode = 'section')

        if "apert" in parsed_lattice_data['elements']:
            if "mark" in parsed_lattice_data['elements']:
                merged = {
                    **parsed_lattice_data['elements']["apert"],
                    **parsed_lattice_data['elements']["mark"]}    # Mark takes precedence
                parsed_lattice_data['elements']["mark"] = merged
            else:
                parsed_lattice_data['elements']["mark"] = \
                    parsed_lattice_data['elements']["apert"]

            parsed_lattice_data['elements'].pop("apert")

    ############################################################################
    # Build Environment
    ############################################################################
    log_section_heading("Building Environment", mode = 'section')

    env = xt.Environment()

    ############################################################################
    # Convert Expressions
    ############################################################################
    log_section_heading("Converting Expressions", mode = 'section')

    convert_expressions(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env)

    ########################################
    # Apply reverse_charge_sign before element conversion so brho is correct
    ########################################
    if reverse_charge_sign:
        env['q0'] = -env['q0']

    ########################################
    # Add reference particle from globals
    ########################################
    species = species_from_mass_and_charge(env['mass0'], env['q0'])
    if species is not None:
        env.particle_ref = xt.Particles(species, p0c=env['p0c'])
    else:
        env.particle_ref = xt.Particles(
            p0c     = env['p0c'],
            q0      = env['q0'],
            mass0   = env['mass0'])

    ############################################################################
    # Convert Elements
    ############################################################################
    log_section_heading("Converting Elements", mode = 'section')

    convert_elements(
        parsed_lattice_data         = parsed_lattice_data,
        environment                 = env,
        user_multipole_replacements = user_multipole_replacements,
        config                      = config)

    ############################################################################
    # Convert Lines
    ############################################################################
    log_section_heading("Converting Lines", mode = 'section')

    convert_lines(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env)
    
    ########################################
    # Select the line
    ########################################
    log_section_heading("Selecting Line", mode = 'subsection')

    if line_name is not None:
        line = env.lines[line_name.lower()]
        logger.info(f"Selected line: {line_name}")
    else:
        line_lengths    = {line: env.lines[line].get_length() for line in env.lines}
        
        # If several are the same length, check also number of elements (thin elements)
        if max(line_lengths.values()) != 0:
            longest_line    = max(line_lengths, key = lambda line: line_lengths[line])
        else:
            line_lengths    = {line: len(env.lines[line].element_names) for line in env.lines}
            longest_line    = max(line_lengths, key = lambda line: line_lengths[line])
        
        line            = env.lines[longest_line]

        logger.info(f"Selected line: {longest_line}")

    ############################################################################
    # Solenoid Corrections
    ############################################################################
    log_section_heading("Performing Solenoid Corrections", mode = 'section')

    ########################################
    # Convert elements between solenoids
    ########################################
    log_section_heading("Converting Elements between Solenoids", mode = 'subsection')
    convert_solenoids(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env,
        config              = config)
    
    ########################################
    # Correct solenoid reference shifts
    ########################################
    log_section_heading("Correcting Solenoid Reference Shifts", mode = 'subsection')
    solenoid_reference_shift_corrections(
        line                    = line,
        parsed_lattice_data     = parsed_lattice_data,
        environment             = env,
        reverse_line            = reverse_element_order,
        config                  = config)
    
    ################################################################################
    # Configure Modelling Mode
    ################################################################################
    log_section_heading("Configuring Element Modelling", mode = 'section')

    ########################################
    # Set integrators
    ########################################
    log_section_heading("Configuring Integrators", mode = 'subsection')


    tt          = line.get_table()
    tt_drift    = tt.rows[tt.element_type == 'Drift']
    tt_bend     = tt.rows[tt.element_type == 'Bend']
    tt_quad     = tt.rows[tt.element_type == 'Quadrupole']
    tt_sext     = tt.rows[tt.element_type == 'Sextupole']
    tt_oct      = tt.rows[tt.element_type == 'Octupole']
    tt_mult     = tt.rows[tt.element_type == 'Multipole']
    tt_sol      = tt.rows[tt.element_type == 'Solenoid']
    tt_cavi     = tt.rows[tt.element_type == 'Cavity']

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
    log_section_heading("Configuring Bend Model", mode = 'subsection')

    line.configure_bend_model(edge = config.EDGE_MODEL_BEND)

    ############################################################################
    # Line reversals
    ############################################################################
    if reverse_element_order:
        log_section_heading("Reversing Element order of Line", mode = 'section')
        line = reverse_line_element_order(line)

    if reverse_survey_horizontal:
        log_section_heading("Reversing Bend Directions of Line", mode = 'section')
        line = reverse_line_survey_horizontal(line)

    ############################################################################
    # Handle Offset Markers
    ############################################################################
    log_section_heading("Converting Offset Markers", mode = 'section')

    line, offset_marker_locations   = convert_offset_markers(
        line                = line,
        parsed_lattice_data = parsed_lattice_data)

    ############################################################################
    # Breakpoint for testing
    ############################################################################
    if config._test_mode:
        log_section_heading("Converter Breakpoint: Test mode active", mode = 'section')
        return line

    ############################################################################
    # Output files
    ############################################################################

    ########################################
    # Filename
    ########################################
    if output_filename is None:
        output_filename = sad_lattice_path.split('/')[-1].replace('.sad', '')
    else:
        assert isinstance(output_filename, str), "output_filename must be a string"

    ########################################
    # Lattice
    ########################################
    log_section_heading("Generating Lattice File", mode = 'section')

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
    log_section_heading("Generating Optics File", mode = 'section')

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
    env.call(f"{output_directory}/{output_filename}.py")
    env.call(f"{output_directory}/{output_filename}_import_optics.py")
    line    = env.lines["line"]

    ############################################################################
    # Complete message
    ############################################################################
    log_section_heading("Conversion Complete", mode = 'section')

    ############################################################################
    # Return the line
    ############################################################################
    return line
