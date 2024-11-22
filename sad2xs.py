"""
UNOFFICIAL SAD to XSuite Converter
Designed for initial import of SuperKEKB Lattice
Tested (working) on import of FCC-ee (Z) Lattice (GHC 24.3)
=============================================
Author(s):      John P T Salvesen, Giovanni Iadarola
Email:          john.salvesen@cern.ch
Last Updated:   20-11-2024
"""
################################################################################
# Required Packages
################################################################################
import xtrack as xt
import numpy as np
import os

################################################################################
# Version Information
################################################################################
__version__ = '0.1.1'
__date__    = '20-11-2024'
__author__  = 'J. Salvesen, G. Iadarola'
__email__   = 'john.salvesen@cern.ch'

################################################################################
# Conversion Function
################################################################################
def sad2xsuite(
    sad_lattice_path,
    mult_replacements:  dict    = None,
    ref_particle_mass0: float   = xt.ELECTRON_MASS_EV,
    bend_edge_model:    str     = 'linear',
    install_markers:    bool    = True,
    ref_particle_p0c:   float   = None,
    allow_thick_mult:   bool    = False,
) -> tuple[xt.Line, dict]:
    """
    Convert SAD Lattice to XSuite Lattice
    
    ############################################################################
    Parameters:
    ############################################################################

    sad_lattice_path: str
        Path to the SAD lattice file

    mult_replacements: dict (optional)
        Dictionary of replacements for multipole elements
        Default is None
        Dictionary should be of the form:
        {'element_base_string': replacement_element_type}
        Where element_base_string is the base string of the element name
        and replacement_element_type is the element type to replace with
        Currently supported options for replacement_element_type are:
            'Bend', 'Quadrupole', 'Sextupole
        
    ref_particle_mass0: float (optional)
        Reference Particle Mass [eV]
        Default is the electron mass

    bend_edge_model: str (optional)
        Model for the bend elements. Options are 'full', 'linear', 'suppressed'
        Default is 'linear'
        
    install_markers: bool (optional)
        Install markers at the correct locations
        Default is True
        Requires slicing of thick elements
    
    ref_particle_p0c: float (optional)
        Reference Particle Momentum [eV/c]
        Default is None, will attempt to read from SAD file
    
    allow_thick_mult: bool (optional)
        Allows thick multipoles to be imported
        Default is False
        Default behaviour is to replace thick multipoles with drift kick drift
        NOT RECOMMENDED
        SUBJECT TO CHANGE WITH FUTURE XSUITE VERSIONS
    
        
    ############################################################################
    Outputs
    ############################################################################

    line: xtrack.Line
        XSuite Line object representing the lattice

    marker_locations: dict
        Dictionary of markers and their locations
    """

    ############################################################################
    # Print Version Information
    ############################################################################
    print(80 * '#' + '\n' + 'SAD to XSuite Converter' + '\n' + 80 * '#')
    print(f'Version: {__version__}')
    print(f'Dated: {__date__}')
    print(f'Author(s): {__author__}')
    print(f'Email: {__email__}')
    print(40 * '#' + 2*'\n')

    ############################################################################
    # Load Elements from SAD
    ############################################################################
    print('\n' + 40 * '*')
    print('Loading Elements from SAD Lattice')
    print(40 * '*')

    ########################################
    # Load and clean SAD File
    ########################################
    with open(sad_lattice_path, 'r', encoding="utf-8") as sad_file:
        content = sad_file.read()

    # Make Content Lowercase (Xsuite style)
    content = content.lower()

    # Correct Formatting Issues
    while ' =' in content:
        content = content.replace(' =', '=')
    while '= ' in content:
        content = content.replace('= ', '=')
    while '  ' in content:
        content = content.replace('  ', ' ')
    content = content.replace('deg', '')

    ########################################
    # Separate Elements By Kind
    ########################################
    # Remove commented out (parts of) lines in content
    content = os.linesep.join(line.split('!')[0] for line in content.splitlines())

    # Semicolons are used to separate element sections
    sad_sections = content.split(';')

    # Known Element Kinds
    sad_elements = (
        'drift', 'bend', 'quad', 'oct', 'mult', 'sol',
        'cavi', 'mark', 'moni', 'beambeam', 'apert')

    ########################################
    # Clean Each Section
    ########################################
    # Create a dictionary to store the cleaned content
    cleaned_content = {}

    for section in sad_sections:
        cleaned_section = section
        cleaned_section = cleaned_section.strip()

        # If the section is empty post strip, skip the section
        if len(cleaned_section) == 0:
            continue

        # Each section starts with a SAD command
        section_command = cleaned_section.split()[0]

        ########################################
        # Processing Elements
        ########################################
        # Check if this command is an element type
        if section_command in sad_elements:
            # Clean the section into dictionary style
            cleaned_section = cleaned_section.replace('(', 'dict(')
            cleaned_section = cleaned_section.replace(')', '),')
            cleaned_section = cleaned_section.replace(section_command, 'dict(')

            # Split the section into lines
            lines = cleaned_section.split('\n')

            for line_num, line in enumerate(lines):
                # Split the line into tokens
                tokens = line.split(' ')
                for token_num, token in enumerate(tokens):
                    # If the token is a parameter, add a comma
                    if '=' in token:
                        tokens[token_num] = token + ','
                # Rejoin the tokens into a line
                lines[line_num] = ' '.join(tokens)

            # Rejoin the lines into a section
            cleaned_section = '\n'.join(lines)

            # Format the section as a dictionary
            cleaned_section ='dict(\n' + cleaned_section + '\n)'

            # Remove any double commas
            while ',,' in cleaned_section:
                cleaned_section = cleaned_section.replace(',,', ',')

            # Add a closing bracket
            cleaned_section += ')'

            # Evaluate the section as a dictionary
            section_dict = eval(cleaned_section)

            # Add the section to the cleaned content
            # If command already in the cleaned content, append the section
            if section_command in cleaned_content:
                cleaned_content[section_command].update(section_dict)
            else:
                cleaned_content[section_command] = section_dict

        ########################################
        # Processing Line Description
        ########################################
        if section_command == 'line':

            # Parse the data to a dict to enable sublists
            line_dict = {}

            # Split the section into lines
            lines = section.splitlines()
            current_key = None
            current_values = []

            for line in lines:
                line = line.strip()

                if not line:
                    continue

                if '=' in line:
                    if current_key:
                        line_dict[current_key] = current_values
                    key, _ = line.split('=', 1)
                    current_key = key.strip()
                    current_values = []
                else:
                    current_values.extend(line.strip('()').split())

            if current_key:
                line_dict[current_key] = current_values

            # Step 2: Determine the master list by checking references
            all_keys = set(line_dict.keys())
            referenced_keys = set()

            for values in line_dict.values():
                for value in values:
                    if value in line_dict:
                        referenced_keys.add(value)

            # The master key is the one that is not referenced by any other key
            master_list_key = list(all_keys - referenced_keys)[0]
            master_list = line_dict[master_list_key]

            # Step 3: Replace references in the master list with actual values
            def expand_list(lst):
                expanded_list = []
                for item in lst:
                    if item in line_dict:
                        expanded_list.extend(expand_list(line_dict[item]))
                    else:
                        expanded_list.append(item)
                return expanded_list

            master_list_expanded = expand_list(master_list)

            cleaned_content['line'] = master_list_expanded

        ########################################
        # Misc Information
        ########################################
        # Can store important details e.g. energy, etc.
        if section_command not in (list(sad_elements) + ['line']):
            if 'momentum' in section:
                sad_p0c = section.replace("\n", "")
                sad_p0c = sad_p0c.replace(" ", "")
                sad_p0c = sad_p0c.replace("=", "")
                sad_p0c = sad_p0c.replace("momentum", "")

                if 'kev' in sad_p0c:
                    sad_p0c = sad_p0c.replace("kev", "")
                    sad_p0c = float(sad_p0c) * 1E3
                elif 'mev' in sad_p0c:
                    sad_p0c = sad_p0c.replace("mev", "")
                    sad_p0c = float(sad_p0c) * 1E6
                elif 'gev' in sad_p0c:
                    sad_p0c = sad_p0c.replace("gev", "")
                    sad_p0c = float(sad_p0c) * 1E9
                elif 'tev' in sad_p0c:
                    sad_p0c = sad_p0c.replace("tev", "")
                    sad_p0c = float(sad_p0c) * 1E12
                elif 'ev' in sad_p0c:
                    sad_p0c = sad_p0c.replace("ev", "")
                    sad_p0c = float(sad_p0c)
                else:
                    try:
                        sad_p0c = float(sad_p0c)
                    except TypeError:
                        sad_p0c = None
                        print('Error: Unable to parse momentum')

                if sad_p0c is None and ref_particle_p0c is None:
                    raise ValueError('Error: Unable to parse momentum \n' +\
                        'Please provide a reference momentum')
                elif ref_particle_p0c is None and sad_p0c is not None:
                    ref_particle_p0c = sad_p0c
                elif ref_particle_p0c is not None and sad_p0c is not None:
                    print('Warning: Multiple momenta detected')
                    print('Using the momentum provided in the function call')

            else:
                print('Unknown Section Includes the following information:')
                print(section)

    ############################################################################
    # Convert Elements to XSuite Elements
    ############################################################################
    print('\n' + 40 * '*')
    print('Converting Elements to Xsuite Objects')
    print(40 * '*')

    ########################################
    # Conversion Setup
    ########################################
    xsuite_elements     = {}
    excluded_elements   = []

    ########################################
    # Drift
    ########################################
    if 'drift' in cleaned_content:
        drifts  = cleaned_content['drift']

        for ele_name, ele_vars in drifts.items():
            # Drift must have a length
            if 'l' not in ele_vars:
                excluded_elements.append(ele_name)
                continue

            # Convert to XTrack Drift Element
            xsuite_elements[ele_name] = xt.Drift(length  = ele_vars['l'])

    ########################################
    # Bend
    ########################################
    if 'bend' in cleaned_content:
        bends   = cleaned_content['bend']

        for ele_name, ele_vars in bends.items():
            # Bend must have a length
            if 'l' not in ele_vars:
                excluded_elements.append(ele_name)
                continue

            length  = ele_vars['l']
            # SAD face angle parameters initialised to 0
            e1 = 0
            e2 = 0

            # Two types of bends: bends defining orbit and bends defining kicks
            # Parameters for bends
            if 'angle' in ele_vars:
                k0l     = ele_vars['angle']
                k0      = k0l / length
                h       = k0
                # We only import the edges if it is a real bend
                # This convention is employed by SAD at runtime
                if 'e1' in ele_vars:
                    e1 = ele_vars['e1']
                if 'e2' in ele_vars:
                    e2 = ele_vars['e2']
            # Parameters for kicks
            elif 'k0' in ele_vars:
                k0l     = ele_vars['k0'] # SAD k0 is k0l
                k0      = k0l / length
                h       = 0
            else:
                raise ValueError('Error: Bend must have an angle or k0')

            rotation = 0
            if 'rotate' in ele_vars:
                rotation = ele_vars['rotate'] * -1

            # Convert to XTrack Bend Element
            xsuite_elements[ele_name] = xt.elements.Bend(
                length              = length,
                k0                  = k0,
                h                   = h,
                edge_entry_angle    = e1 * k0l,
                edge_exit_angle     = e2 * k0l,
                rot_s_rad           = - np.deg2rad( rotation ))

    ########################################
    # Quadrupole
    ########################################
    if 'quad' in cleaned_content:
        quads   = cleaned_content['quad']

        for ele_name, ele_vars in quads.items():
            # Quadrupole must have a length
            if 'l' not in ele_vars:
                excluded_elements.append(ele_name)
                continue

            rotation = 0
            if 'rotate' in ele_vars:
                rotation = ele_vars['rotate'] * -1

            # Convert to XTrack Quadrupole Element
            xsuite_elements[ele_name] = xt.Quadrupole(
                length  = ele_vars['l'],
                k1      = ( ele_vars['k1'] / ele_vars['l'] ) *\
                    np.cos( np.deg2rad( rotation ) * 2),
                k1s     = ( ele_vars['k1'] / ele_vars['l'] ) *\
                    np.sin( np.deg2rad( rotation ) * 2))

    ########################################
    # Octupole
    ########################################
    if 'oct' in cleaned_content:
        octs    = cleaned_content['oct']

        for ele_name, ele_vars in octs.items():
            # Octupoles can be thin lenses
            length = 0
            if 'l' in ele_vars:
                length = ele_vars['l']

            k3l = 0
            if 'k3' in ele_vars:
                k3l = ele_vars['k3']
            knl_arr = np.array([0, 0, 0, k3l])

            rotation = 0
            if 'rotate' in ele_vars:
                rotation = ele_vars['rotate'] * -1

            xsuite_elements[ele_name] = xt.Multipole(
                length  = length,
                knl     = knl_arr * np.cos(np.deg2rad(rotation) * 4),
                ksl     = knl_arr * np.sin(np.deg2rad(rotation) * 4))

    ########################################
    # Multipole
    ########################################
    if 'mult' in cleaned_content:
        mults   = cleaned_content['mult']

        for ele_name, ele_vars in mults.items():
            # Multipole can be thin lenses
            length = 0
            if 'l' in ele_vars:
                length = ele_vars['l']

            knl_list = []
            for kn in range(0, 21):
                knl = 0
                if f'k{kn}' in ele_vars:
                    knl = ele_vars[f'k{kn}']
                knl_list.append(knl)
            knl_arr = np.array(knl_list)

            ksl_list = []
            for ks in range(0, 21):
                ksl = 0
                if f'sk{ks}' in ele_vars:
                    ksl = ele_vars[f'sk{ks}']
                ksl_list.append(ksl)
            ksl_arr = np.array(ksl_list)

            rotation = 0
            if 'rotate' in ele_vars:
                rotation = ele_vars['rotate'] * -1
            rotation_knl_scaling = np.array(
                [ np.cos(np.deg2rad(rotation) * (i +1)) for i in range(0, 21) ])
            rotation_ksl_scaling = np.array(
                [ np.sin(np.deg2rad(rotation) * (i +1)) for i in range(0, 21) ])

            ########################################
            # User Defined Multipole Replacements
            ########################################
            # Need mult_replacements to be a dictionary
            # Empty dict not function safe
            if mult_replacements is None:
                mult_replacements = {}

            # Check if the element name starts with any of the replacement keys
            if any(ele_name.startswith(test_key)
                    for test_key in mult_replacements):
                replace_key = None
                for test_key in mult_replacements:
                    if ele_name.startswith(test_key):
                        replace_key = test_key

                # Check what kind of replacement
                if mult_replacements[replace_key] == 'Bend':
                    k0l         = knl_arr[0] * np.cos(np.deg2rad(rotation)) +\
                        ksl_arr[0] * np.sin(np.deg2rad(rotation))
                    k0sl        = ksl_arr[0] * np.sin(np.deg2rad(rotation)) -\
                        knl_arr[0] * np.cos(np.deg2rad(rotation))
                    k0l         = np.sqrt(k0l**2 + k0sl**2)
                    rotation    = np.arctan2(k0sl, k0l)
                    k0          = k0l / length

                    # Convert to XTrack Bend Element
                    xsuite_elements[ele_name] = xt.elements.Bend(
                        length              = length,
                        k0                  = k0,
                        h                   = 0,
                        edge_entry_angle    = 0,
                        edge_exit_angle     = 0,
                        rot_s_rad           = np.deg2rad( rotation ))

                elif mult_replacements[replace_key] == 'Quadrupole':
                    k1l         = knl_arr[1] * np.cos(np.deg2rad(rotation * 2)) +\
                        ksl_arr[1] * np.sin(np.deg2rad(rotation * 2))
                    k1sl        = ksl_arr[1] * np.cos(np.deg2rad(rotation * 2)) -\
                        knl_arr[1] * np.sin(np.deg2rad(rotation * 2))

                    # Convert to XTrack Quadrupole Element
                    xsuite_elements[ele_name] = xt.Quadrupole(
                        length  = ele_vars['l'],
                        k1      = k1l / length,
                        k1s     = k1sl / length)

                elif mult_replacements[replace_key] == 'Sextupole':
                    k2l         = knl_arr[2] * np.cos(np.deg2rad(rotation * 3)) +\
                        ksl_arr[2] * np.sin(np.deg2rad(rotation * 3))
                    k2sl        = ksl_arr[2] * np.cos(np.deg2rad(rotation * 3)) -\
                        knl_arr[2] * np.sin(np.deg2rad(rotation * 3))

                    # Convert to XTrack Quadrupole Element
                    xsuite_elements[ele_name] = xt.Sextupole(
                        length  = ele_vars['l'],
                        k2      = k2l / length,
                        k2s     = k2sl / length)
                else:
                    raise ValueError('Error: Unknown element replacement')

            ########################################
            # Bends stored as Multipole
            ########################################
            elif (
                (
                    length != 0 and
                    knl_arr[1] == 0 and ksl_arr[1] == 0 and
                    knl_arr[2] == 0 and ksl_arr[2] == 0) and
                (knl_arr[0] != 0 or ksl_arr[0] != 0)
            ):
                k0l         = knl_arr[0] * np.cos(np.deg2rad(rotation)) +\
                    ksl_arr[0] * np.sin(np.deg2rad(rotation))
                k0sl        = ksl_arr[0] * np.sin(np.deg2rad(rotation)) -\
                    knl_arr[0] * np.cos(np.deg2rad(rotation))
                k0l         = np.sqrt(k0l**2 + k0sl**2)
                rotation    = np.arctan2(k0sl, k0l)
                k0          = k0l / length

                # Convert to XTrack Bend Element
                xsuite_elements[ele_name] = xt.elements.Bend(
                    length              = length,
                    k0                  = k0,
                    h                   = 0,
                    edge_entry_angle    = 0,
                    edge_exit_angle     = 0,
                    rot_s_rad           = np.deg2rad( rotation ))

            ########################################
            # Quadrupoles stored as Multipole
            ########################################
            elif (
                (
                    length != 0 and
                    knl_arr[0] == 0 and ksl_arr[0] == 0 and
                    knl_arr[2] == 0 and ksl_arr[2] == 0) and
                (knl_arr[1] != 0 or ksl_arr[1] != 0)
            ):
                k1l         = knl_arr[1] * np.cos(np.deg2rad(rotation * 2)) +\
                    ksl_arr[1] * np.sin(np.deg2rad(rotation * 2))
                k1sl        = ksl_arr[1] * np.cos(np.deg2rad(rotation * 2)) -\
                    knl_arr[1] * np.sin(np.deg2rad(rotation * 2))

                # Convert to XTrack Quadrupole Element
                xsuite_elements[ele_name] = xt.Quadrupole(
                    length  = ele_vars['l'],
                    k1      = k1l / length,
                    k1s     = k1sl / length)
            ########################################
            # Sextupoles stored as Multipole
            ########################################

            elif (
                (
                    length != 0 and
                    knl_arr[0] == 0 and ksl_arr[0] == 0 and
                    knl_arr[1] == 0 and ksl_arr[1] == 0) and
                (knl_arr[2] != 0 or ksl_arr[2] != 0)
            ):
                k2l         = knl_arr[2] * np.cos(np.deg2rad(rotation * 3)) +\
                    ksl_arr[2] * np.sin(np.deg2rad(rotation * 3))
                k2sl        = ksl_arr[2] * np.cos(np.deg2rad(rotation * 3)) -\
                    knl_arr[2] * np.sin(np.deg2rad(rotation * 3))

                # Convert to XTrack Quadrupole Element
                xsuite_elements[ele_name] = xt.Sextupole(
                    length  = ele_vars['l'],
                    k2      = k2l / length,
                    k2s     = k2sl / length)

            ########################################
            # Else is a true multipole
            ########################################
            else:
                xsuite_elements[ele_name] = xt.Multipole(
                        length  = length,
                        knl     = knl_arr * rotation_knl_scaling,
                        ksl     = knl_arr * rotation_ksl_scaling)

                mult_length = xsuite_elements[ele_name].length
                if mult_length != 0:
                    if allow_thick_mult:
                        xsuite_elements[ele_name].isthick = True
                    else:
                        # Convert to drift kick drift
                        xsuite_elements[ele_name].length = 0

                        # Create drifts either side of the multipole
                        xsuite_elements[ele_name + '.mult_drift..0'] = xt.Drift(
                            length = mult_length / 2)
                        xsuite_elements[ele_name + '.mult_drift..1'] = xt.Drift(
                            length = mult_length / 2)

                        # Add the drifts to the line
                        temp_line = []
                        for element_name in cleaned_content['line']:
                            if element_name == ele_name:
                                temp_line.extend([
                                    ele_name + '.mult_drift..0',
                                    ele_name,
                                    ele_name + '.mult_drift..1'])
                            else:
                                temp_line.append(element_name)
                        cleaned_content['line'] = temp_line

    ########################################
    # Cavities
    ########################################
    if 'cavi' in cleaned_content:
        cavs    = cleaned_content['cavi']

        for ele_name, ele_vars in cavs.items():

            phi = 0
            if 'phi' in ele_vars:
                phi = ele_vars['phi']

            xsuite_elements[ele_name] = xt.Cavity(
                voltage     = ele_vars['volt'],
                frequency   = ele_vars['freq'],
                lag         = phi)

    ########################################
    # Apertures
    ########################################
    if 'apert' in cleaned_content:
        aperts  = cleaned_content['apert']

        for ele_name, ele_vars in aperts.items():
            xsuite_elements[ele_name] = xt.LimitEllipse(
                a   = ele_vars['ax'],
                b   = ele_vars['ay'])

    ########################################
    # Solenoid (excluded except geometric effect)
    ########################################
    if 'sol' in cleaned_content:
        solenoids   = cleaned_content['sol']

        for ele_name, ele_vars in solenoids.items():
            if 'dz' in ele_vars:

                # Create a drift after the solenoid slice
                xsuite_elements[ele_name + '.geom_corr_drift'] = xt.Drift(
                    length = ele_vars['dz'])

                # Add the drift to the line
                temp_line = []
                for element_name in cleaned_content['line']:
                    if element_name == ele_name:
                        temp_line.extend([
                            ele_name,
                            ele_name + '.geom_corr_drift'])
                    elif element_name == '-' + ele_name:
                        temp_line.extend([
                            ele_name + '.geom_corr_drift',
                            ele_name])
                    else:
                        temp_line.append(element_name)

                cleaned_content['line'] = temp_line

            excluded_elements.append(ele_name)

    ########################################
    # Beam Beam (Marker)
    ########################################
    if 'beambeam' in cleaned_content:
        beam_beams   = cleaned_content['beambeam']

        for ele_name, ele_vars in beam_beams.items():
            xsuite_elements[ele_name] = xt.Marker()

    ########################################
    # Monitors (Marker)
    ########################################
    if 'moni' in cleaned_content:
        monis   = cleaned_content['moni']

        for ele_name, ele_vars in monis.items():
            # Monitor must be a thin element
            assert 'l' not in ele_vars
            xsuite_elements[ele_name] = xt.Marker()

    ########################################
    # Markers
    ########################################
    if 'mark' in cleaned_content:
        marks   = cleaned_content['mark']

        for ele_name, ele_vars in marks.items():
            # Markers must be a thin element
            assert 'l' not in ele_vars
            xsuite_elements[ele_name] = xt.Marker()

    ############################################################################
    # Create Line
    ############################################################################
    print('\n' + 40 * '*')
    print('Creating XSuite Line')
    print(40 * '*')

    ########################################
    # Element Name Corrections
    ########################################
    # First iterate through the elements to count the number of each element
    element_counts = {}
    for ele_name in cleaned_content['line']:

        # TODO: Decide naming convention for inverted elements
        if ele_name.startswith('-'):
            ele_name = ele_name[1:]

        if ele_name not in element_counts:
            element_counts[ele_name] = 1
        else:
            element_counts[ele_name] += 1

    element_names   = []
    elements        = []

    element_names_inc_markers = []
    marker_offsets = {}

    element_counts2 = {}
    # Second iterate through the elements to correct the names
    # Only adding numbers to elements that are repeated
    for ele_name in cleaned_content['line']:

        # Check for inversion
        inverted = False
        if ele_name.startswith('-'):
            inverted = True
            ele_name = ele_name[1:]

        if ele_name in excluded_elements:
            continue

        # Check if the element is repeated
        if ele_name not in element_counts2:
            element_counts2[ele_name] = 1
        else:
            element_counts2[ele_name] += 1

        # Correct the name if the element is repeated
        if element_counts[ele_name] == 1:
            xs_name = ele_name
        else:
            xs_name = ele_name + '.' + str(element_counts2[ele_name])

        # Get the element from the dictionary
        ele_to_insert = xsuite_elements[ele_name]

        # Invert the element longitudinally
        if inverted:
            if isinstance(ele_to_insert, xt.Bend):
                edge_entry_angle    = ele_to_insert.edge_entry_angle
                edge_exit_angle     = ele_to_insert.edge_exit_angle
                ele_to_insert.edge_entry_angle  = edge_exit_angle
                ele_to_insert.edge_exit_angle   = edge_entry_angle
            elif isinstance(ele_to_insert, xt.Cavity):
                ele_to_insert.voltage *= -1
            # TODO: Solenoid here

        element_names_inc_markers.append(xs_name)

        # if ele_name not in cleaned_content['mark']:
        # This way removes all markers, inclduing moni and beam beam

        if ele_name not in list(
            (list(cleaned_content['mark'].keys())
             if 'mark' in cleaned_content else []) +\
            (list(cleaned_content['moni'].keys())
             if 'moni' in cleaned_content else []) +\
            (list(cleaned_content['beambeam'].keys())
             if 'beambeam' in cleaned_content else [])
        ):
            element_names.append(xs_name)
            elements.append(ele_to_insert)
        else:
            offset = 0
            # Only mark can have offset, not moni or beambeam
            if ele_name in cleaned_content['mark']:
                if 'offset' in cleaned_content['mark'][ele_name]:
                    offset = cleaned_content['mark'][ele_name]['offset']

            if inverted:
                if offset < 0:
                    offset = 1 + offset * -1
                elif offset > 1:
                    offset = (offset -1) * -1
                elif 0 < offset < 1:
                    offset = 0

            marker_offsets[xs_name] = offset

    ########################################
    # Build Line
    ########################################
    line    = xt.Line(
        elements        = elements,
        element_names   = element_names)
    line.particle_ref = xt.Particles(
        p0c     = ref_particle_p0c,
        mass0   = ref_particle_mass0)

   ########################################
    # Add Markers at the correct position
    ########################################
    # Get the line table
    line.build_tracker()
    tt      = line.get_table(attr=True)
    buffer  = line._buffer
    line.discard_tracker()

    # Summary dict to output
    marker_locations = {}

    # Add a check for if the next element is a mult drift

    for marker_xs_name, offset in marker_offsets.items():

        # Cases based on offset
        if 0 <= offset <= 1:
            # Get the index of the next element
            marker_idx = element_names_inc_markers.index(marker_xs_name)
            try:
                insert_at_ele = element_names_inc_markers[marker_idx+1]
                s_to_insert = tt['s', insert_at_ele]
            except IndexError:
                # If index error, the next element is the end of the line
                s_to_insert = tt.s[-1]
            except KeyError:
                # If key error, the next element is a marker, so use the next
                relative_idx = 1
                while True:
                    relative_idx += 1
                    try:
                        insert_at_ele = element_names_inc_markers[
                            marker_idx + relative_idx]
                        s_to_insert = tt['s', insert_at_ele]
                        break
                    except KeyError:
                        pass
                    except IndexError:
                    # If index error, the next element is the end of the line
                        s_to_insert = tt.s[-1]
                        break

        else:
            # Get the index of the corresponding element
            relative_idx    = int(np.floor(offset))
            marker_idx      = element_names_inc_markers.index(marker_xs_name)
            insert_at_ele   = element_names_inc_markers[
                marker_idx + relative_idx
            ]
            # Get the length of the element to insert at
            insert_ele_length   = tt['length', insert_at_ele]
            # Add the fraction of element length
            # Check if the element is a multipole drift
            if 'mult_drift' in insert_at_ele:
                if offset > 0:
                    s_to_insert = tt['s', insert_at_ele] +\
                        (insert_ele_length * 2) * (offset % 1)
                else:
                    # If offset is negative, then need to step back the ele length
                    s_to_insert = tt['s', insert_at_ele] -\
                        insert_ele_length +\
                        (insert_ele_length * 2) * (offset % 1)
            else:
                s_to_insert     = tt['s', insert_at_ele] +\
                    insert_ele_length * (offset % 1)

        # Produce a dictionary of the s locations that markers are inserted at
        marker_locations[marker_xs_name] = s_to_insert

    if install_markers:
        for marker, insert_at_s in marker_locations.items():
            if insert_at_s < tt.s[-1]:
                try:
                    line.insert_element(
                        name    = marker,
                        element = xt.Marker(_buffer = buffer),
                        at_s    = insert_at_s,
                        s_tol   = 1e-6)
                except AttributeError:
                    print(f'Error: Unable to insert marker {marker}'
                        f' at {insert_at_s}')
                    print('Likely trying to slice a "thick" multipole')
                    print('Recommended to turn on "replace_thick_multipole')
            else:
                line.append_element(
                    name    = marker,
                    element = xt.Marker(_buffer = buffer))

    ########################################
    # Apply chosen bend model to the line
    ########################################
    line.configure_bend_model(edge = bend_edge_model)

    ############################################################################
    # Return Line
    ############################################################################
    print('\n' + 40 * '*')
    print('Conversion Complete')
    print(40 * '*')

    return line, marker_locations
