"""
Unofficial SAD to XSuite Lattice Converter
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       30-09-2025
"""

################################################################################
# Required Packages
################################################################################
import xtrack as xt

from ._globals import print_section_heading, ASCII_LOGO, N_INTEGRATOR_KICKS

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
        sad_lattice_path,
        output_directory,
        output_filename             = None,
        line_name                   = None,
        output_header               = "SAD to XSuite Lattice Conversion",
        excluded_elements           = None,
        user_multipole_replacements = None,
        reverse_element_order       = False,
        reverse_bend_direction      = False,
        reverse_charge              = False,
        _verbose                    = True,
        _test_mode                  = False):

    ############################################################################
    # Introduction Printout
    ############################################################################
    if _verbose:
        print(ASCII_LOGO)
        print(f"Processing SAD file: {sad_lattice_path}")

    ############################################################################
    # Parse Lattice
    ############################################################################
    if _verbose:
        print_section_heading("Parsing SAD File", mode = 'section')

    parsed_lattice_data = parse_sad_file(
        sad_lattice_path    = sad_lattice_path,
        ref_particle_mass0  = None,
        ref_particle_q0     = None,
        ref_particle_p0c    = None,
        verbose             = _verbose)

    ############################################################################
    # Remove Excluded elements
    ############################################################################
    if _verbose:
        print_section_heading("Removing Excluded Elements", mode = 'section')

    parsed_lattice_data = exclude_elements(
        parsed_lattice_data = parsed_lattice_data,
        excluded_elements   = excluded_elements,
        verbose             = _verbose)

    ############################################################################
    # Build Environment
    ############################################################################
    if _verbose:
        print_section_heading("Building Environment", mode = 'section')

    env = xt.Environment()

    ############################################################################
    # Convert Expressions
    ############################################################################
    if _verbose:
        print_section_heading("Converting Expressions", mode = 'section')

    convert_expressions(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env,
        verbose             = _verbose)

    ########################################
    # Add reference particle from globals
    ########################################
    env.particle_ref    = xt.Particles(
        p0c     = parsed_lattice_data['globals']['momentum'],
        q0      = parsed_lattice_data['globals']['charge'],
        mass0   = parsed_lattice_data['globals']['mass'])

    ############################################################################
    # Convert Elements
    ############################################################################
    if _verbose:
        print_section_heading("Converting Elements", mode = 'section')

    convert_elements(
        parsed_lattice_data         = parsed_lattice_data,
        environment                 = env,
        user_multipole_replacements = user_multipole_replacements,
        verbose                     = _verbose)

    ############################################################################
    # Convert Lines
    ############################################################################
    if _verbose:
        print_section_heading("Converting Lines", mode = 'section')

    convert_lines(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env)
    
    ########################################
    # Select the line
    ########################################
    if _verbose:
        print_section_heading("Selecting Line", mode = 'subsection')
    
    if line_name is not None:
        line = env.lines[line_name.lower()]
        if _verbose:
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

        if _verbose:
            print(f"Selected line: {longest_line}")

    ############################################################################
    # Solenoid Corrections
    ############################################################################
    if _verbose:
        print_section_heading("Performing Solenoid Corrections", mode = 'section')

    ########################################
    # Convert elements between solenoids
    ########################################
    if _verbose:
        print_section_heading("Converting Elements between Solenoids", mode = 'subsection')
    convert_solenoids(
        parsed_lattice_data = parsed_lattice_data,
        environment         = env,
        verbose             = _verbose)
    
    ########################################
    # Correct solenoid reference shifts
    ########################################
    if _verbose:
        print_section_heading("Correcting Solenoid Reference Shifts", mode = 'subsection')
    solenoid_reference_shift_corrections(
        line                    = line,
        parsed_lattice_data     = parsed_lattice_data,
        environment             = env,
        reverse_line            = reverse_element_order,
        verbose                 = _verbose)
    
    ############################################################################
    # Harmonic Cavity Correction
    ############################################################################
    if _verbose:
        print_section_heading("Converting Harmonic Cavities", mode = 'section')
    convert_harmonic_rf(
        line                = line,
        parsed_lattice_data = parsed_lattice_data,
        verbose             = _verbose)

    ################################################################################
    # Configure Modelling Mode
    ################################################################################
    if _verbose:
        print_section_heading("Configuring Modelling Mode", mode = 'section')

    ########################################
    # Use exact drifts
    ########################################
    # Needed for large angles inside drifts
    line.config.XTRACK_USE_EXACT_DRIFTS = True                  # type: ignore

    ########################################
    # Set bend model
    ########################################
    if _verbose:
        print_section_heading("Configuring Bend Model", mode = 'subsection')
    
    line.configure_bend_model(edge = 'full')

    ########################################
    # Set integrators
    ########################################
    if _verbose:
        print_section_heading("Configuring Integrators", mode = 'subsection')
    
    tt          = line.get_table()
    tt_drift    = tt.rows[tt.element_type == 'Drift']
    tt_bend     = tt.rows[tt.element_type == 'Bend']
    tt_quad     = tt.rows[tt.element_type == 'Quadrupole']
    tt_sext     = tt.rows[tt.element_type == 'Sextupole']
    tt_oct      = tt.rows[tt.element_type == 'Octupole']

    line.set(
        tt_drift,
        model               = 'exact')
    line.set(
        tt_bend,
        integrator          = 'uniform',
        num_multipole_kicks = N_INTEGRATOR_KICKS,
        model               = 'mat-kick-mat')
    line.set(
        tt_quad,
        integrator          = 'uniform',
        num_multipole_kicks = N_INTEGRATOR_KICKS,
        model               = 'mat-kick-mat')
    line.set(
        tt_sext,
        integrator          = 'yoshida4',
        num_multipole_kicks = N_INTEGRATOR_KICKS)
    line.set(
        tt_oct,
        integrator          = 'yoshida4',
        num_multipole_kicks = N_INTEGRATOR_KICKS)

    ############################################################################
    # Line reversals
    ############################################################################
    if reverse_element_order:
        if _verbose:
            print_section_heading("Reversing Element order of Line", mode = 'section')
        line = reverse_line_element_order(line)

    if reverse_bend_direction:
        if _verbose:
            print_section_heading("Reversing Bend Directions of Line", mode = 'section')
        line = reverse_line_bend_direction(line)

    if reverse_charge:
        if _verbose:
            print_section_heading("Reversing Charge of Line", mode = 'section')
        line = reverse_line_charge(line)

    ############################################################################
    # Handle Offset Markers
    ############################################################################
    if _verbose:
        print_section_heading("Converting Offset Markers", mode = 'subsection')

    line, offset_marker_locations   = convert_offset_markers(
        line                = line,
        parsed_lattice_data = parsed_lattice_data)

    ############################################################################
    # Breakpoint for testing
    ############################################################################
    if _test_mode:
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
    if _verbose:
        print_section_heading("Generating Lattice File", mode = 'subsection')

    write_lattice(
        line                        = line,
        offset_marker_locations     = offset_marker_locations,
        output_filename             = output_filename,
        output_directory            = output_directory,
        output_header               = output_header)
    
    ########################################
    # Import optics
    ########################################
    if _verbose:
        print_section_heading("Generating Optics File", mode = 'subsection')

    write_optics(
        line                        = line,
        output_filename             = output_filename,
        output_directory            = output_directory,
        output_header               = output_header)

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
    if _verbose:
        print_section_heading("Conversion Complete", mode = 'section')

    ############################################################################
    # Return the line
    ############################################################################
    return line
