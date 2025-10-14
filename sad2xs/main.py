"""
Unofficial SAD to XSuite Lattice Converter
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-10-2025
"""

################################################################################
# Required Packages
################################################################################
import xtrack as xt

from .config import Config
from .helpers import print_section_heading

from .converter._001_parser import parse_sad_file
from .converter._002_element_exclusion import exclude_elements
from .converter._003_expression_converter import convert_expressions
from .converter._004_element_converter import convert_elements
from .converter._005_line_converter import convert_lines
from .converter._006_solenoid_converter import convert_solenoids, solenoid_reference_shift_corrections
from .converter._007_harmonic_rf import convert_harmonic_rf
from .converter._008_reversals import reverse_line_bend_direction, reverse_line_element_order, reverse_line_charge
from .converter._009_offset_markers import convert_offset_markers
from .converter._010_write_lattice import write_lattice
from .converter._011_write_optics import write_optics

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
        reverse_bend_direction:         bool        = False,
        reverse_charge:                 bool        = False,
        **kwargs):
    
    ############################################################################
    # Load config
    ############################################################################
    config  = Config(**kwargs)

    ############################################################################
    # Introduction Printout
    ############################################################################
    if config._verbose:
        print(config.ASCII_LOGO)
        print(f"Processing SAD file: {sad_lattice_path}")

    ############################################################################
    # Parse Lattice
    ############################################################################
    if config._verbose:
        print_section_heading("Parsing SAD File", mode = 'section')

    parsed_lattice_data = parse_sad_file(
        sad_lattice_path    = sad_lattice_path,
        config              = config)

    ############################################################################
    # Remove Excluded elements
    ############################################################################
    if config._verbose:
        print_section_heading("Removing Excluded Elements", mode = 'section')

    parsed_lattice_data = exclude_elements(
        parsed_lattice_data = parsed_lattice_data,
        excluded_elements   = excluded_elements,
        config              = config)

    ############################################################################
    # Build Environment
    ############################################################################
    if config._verbose:
        print_section_heading("Building Environment", mode = 'section')

    env = xt.Environment()

    ############################################################################
    # Convert Expressions
    ############################################################################
    if config._verbose:
        print_section_heading("Converting Expressions", mode = 'section')

    convert_expressions(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env,
        config              = config)
    
    print(env.vars)

    ########################################
    # Add reference particle from globals
    ########################################
    env.particle_ref    = xt.Particles(
        p0c     = env['p0c'],
        q0      = env['q0'],
        mass0   = env['mass0'])

    ############################################################################
    # Convert Elements
    ############################################################################
    if config._verbose:
        print_section_heading("Converting Elements", mode = 'section')

    convert_elements(
        parsed_lattice_data         = parsed_lattice_data,
        environment                 = env,
        user_multipole_replacements = user_multipole_replacements,
        config                      = config)

    ############################################################################
    # Convert Lines
    ############################################################################
    if config._verbose:
        print_section_heading("Converting Lines", mode = 'section')

    convert_lines(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env)
    
    ########################################
    # Select the line
    ########################################
    if config._verbose:
        print_section_heading("Selecting Line", mode = 'subsection')
    
    if line_name is not None:
        line = env.lines[line_name.lower()]
        if config._verbose:
            print(f"Selected line: {line_name}")
    else:
        line_lengths    = {line: env.lines[line].get_length() for line in env.lines}
        
        # If several are the same length, check also number of elements (thin elements)
        if max(line_lengths.values()) != 0:
            longest_line    = max(line_lengths, key = lambda line: line_lengths[line])
        else:
            line_lengths    = {line: len(env.lines[line].element_names) for line in env.lines}
            longest_line    = max(line_lengths, key = lambda line: line_lengths[line])
        
        line            = env.lines[longest_line]

        if config._verbose:
            print(f"Selected line: {longest_line}")

    ############################################################################
    # Solenoid Corrections
    ############################################################################
    if config._verbose:
        print_section_heading("Performing Solenoid Corrections", mode = 'section')

    ########################################
    # Convert elements between solenoids
    ########################################
    if config._verbose:
        print_section_heading("Converting Elements between Solenoids", mode = 'subsection')
    convert_solenoids(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env,
        config              = config)
    
    ########################################
    # Correct solenoid reference shifts
    ########################################
    if config._verbose:
        print_section_heading("Correcting Solenoid Reference Shifts", mode = 'subsection')
    solenoid_reference_shift_corrections(
        line                    = line,
        parsed_lattice_data     = parsed_lattice_data,
        environment             = env,
        reverse_line            = reverse_element_order,
        config                  = config)
    
    ############################################################################
    # Harmonic Cavity Correction
    ############################################################################
    if config._verbose:
        print_section_heading("Converting Harmonic Cavities", mode = 'section')
    convert_harmonic_rf(
        line                = line,
        parsed_lattice_data = parsed_lattice_data,
        config              = config)

    ################################################################################
    # Configure Modelling Mode
    ################################################################################
    if config._verbose:
        print_section_heading("Configuring Element Modelling", mode = 'section')

    ########################################
    # Set integrators
    ########################################
    if config._verbose:
        print_section_heading("Configuring Integrators", mode = 'subsection')
    
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
    if config._verbose:
        print_section_heading("Configuring Bend Model", mode = 'subsection')

    line.configure_bend_model(edge = config.EDGE_MODEL_BEND)

    ############################################################################
    # Line reversals
    ############################################################################
    if reverse_element_order:
        if config._verbose:
            print_section_heading("Reversing Element order of Line", mode = 'section')
        line = reverse_line_element_order(line)

    if reverse_bend_direction:
        if config._verbose:
            print_section_heading("Reversing Bend Directions of Line", mode = 'section')
        line = reverse_line_bend_direction(line)

    if reverse_charge:
        if config._verbose:
            print_section_heading("Reversing Charge of Line", mode = 'section')
        # line = reverse_line_charge(line)
        line.particle_ref.q0    *= -1
        env.particle_ref.q0     *= -1

    ############################################################################
    # Handle Offset Markers
    ############################################################################
    if config._verbose:
        print_section_heading("Converting Offset Markers", mode = 'section')

    line, offset_marker_locations   = convert_offset_markers(
        line                = line,
        parsed_lattice_data = parsed_lattice_data)

    ############################################################################
    # Breakpoint for testing
    ############################################################################
    if config._test_mode:
        if config._verbose:
            print_section_heading("Converter Breakpoint: Test mode active", mode = 'section')
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
    if config._verbose:
        print_section_heading("Generating Lattice File", mode = 'section')

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
    if config._verbose:
        print_section_heading("Generating Optics File", mode = 'section')

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
    if config._verbose:
        print_section_heading("Conversion Complete", mode = 'section')

    ############################################################################
    # Return the line
    ############################################################################
    return line
