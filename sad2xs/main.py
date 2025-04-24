"""
(Unofficial) SAD to XSuite Converter
Designed for initial import of SuperKEKB Lattice
Tested (working) on import of FCC-ee (Z) Lattice (GHC 24.3)
"""
################################################################################
# Required Packages
################################################################################
import xtrack as xt
import numpy as np

from scipy.constants import c as clight
from scipy.constants import e as qe

################################################################################
# Conversion Function
################################################################################
def sad2xsuite(
        sad_lattice_path:       str,
        multipole_replacements: dict        = None,
        ref_particle_mass0:     float       = None,
        ref_particle_q0:        float       = +1,
        ref_particle_p0c:       float       = None,
        bend_edge_model:        str         = 'linear',
        install_markers:        bool        = True) -> tuple[xt.Line, dict]:
    """
    Convert a particle accelerator lattice defined in Stratgeic Accelerator 
    Design (SAD) to the Xtrack format (part of the Xsuite packages)

    Parameters:
    ----------
    sad_lattice_path: str
        Path to the SAD lattice file

    multipole_replacements: dict, optional
        Dictionary of replacements for multipole elements, default is None\n 
        formatted in the form:\n
        {'element_base_string': replacement_element_type}\n
        Currently supported options for replacement_element_type are:
            'Bend', 'Quadrupole', 'Sextupole
        
    ref_particle_mass0: float, optional
        Reference Particle Mass [eV], default is the None\n
        If provided, will override any mass found in the SAD file

    ref_particle_q0: float (optional)
        Reference Particle Charge [e]
        Default is +1 (positron)

    ref_particle_p0c: float, optional
        Reference particle momentum [eV/c], default is None\n
        If provided, will override any momentum found in the SAD file

    bend_edge_model: str, optional
        Model for the bend elements, default is 'linear'\n
        Options are 'full', 'linear', 'suppressed'
        
    install_markers: bool, optional
        Install markers at the correct locations, default is True\n
        Requires slicing of thick elements
        
    Outputs
    ----------
    line: xtrack.Line
        XSuite Line object representing the lattice

    marker_locations: dict
        Dictionary of markers and their locations
    """

    ############################################################################
    # Setup
    ############################################################################

    ########################################
    # Known Element Types
    ########################################
    sad_elements = (
        'drift',
        'bend', 'quad', 'sext', 'oct', 'mult',
        'sol', 'cavi', 'apert',
        'mark', 'moni', 'beambeam')

    ########################################
    # Marker Replacements
    ########################################
    # Dangerous default value {} as argument
    if multipole_replacements is None:
        multipole_replacements  = {}

    ############################################################################
    # Parsing Raw SAD File
    ############################################################################

    ########################################
    # Load SAD File to Python
    ########################################
    with open(sad_lattice_path, 'r', encoding="utf-8") as sad_file:
        content = sad_file.read()

    ########################################
    # Convert Formatting to XSuite Style
    ########################################
    # Make Content Lowercase (Xsuite style)
    content = content.lower()

    # Correct Formatting Issues
    while ' =' in content:
        content = content.replace(' =', '=')
    while '= ' in content:
        content = content.replace('= ', '=')
    while '( ' in content:
        content = content.replace('( ', '(')
    while ' )' in content:
        content = content.replace(' )', ')')
    while '  ' in content:
        content = content.replace('  ', ' ')

    ########################################
    # Angle Handling
    ########################################
    # Ensure no spaces between the value and it's unit
    content = content.replace(' deg', 'deg')

    ########################################
    # Split the file into sections
    ########################################
    # Semicolons are used to separate element sections
    sad_sections    = content.split(';')

    ############################################################################
    # SAD File Section Cleaning
    ############################################################################
    cleaned_sections = []

    ########################################
    # Iterate through the sections
    ########################################
    for section in sad_sections:
        cleaned_section = section

        ########################################
        # Remove Commented Lines
        ########################################
        # Remove lines that start with '!'
        comment_removed_section = []
        for line in cleaned_section.split('\n'):
            if not line.startswith('!'):
                comment_removed_section.append(line)
        cleaned_section = '\n'.join(comment_removed_section)

        ########################################
        # Strip newlines and whitespace
        ########################################
        cleaned_section = cleaned_section.strip()

        ########################################
        # Remove Empty Sections
        ########################################
        if len(cleaned_section) == 0:
            continue

        cleaned_sections.append(cleaned_section)

    ############################################################################
    # Separation by Element Type
    ############################################################################
    cleaned_elements    = {}
    cleaned_expressions = {}
    cleaned_lines       = {}

    ########################################
    # Iterate through the sections
    ########################################
    for section in cleaned_sections:

        ########################################
        # Get the "Command" of the Section
        ########################################
        section_command = section.split()[0]

        ########################################
        # SAD Feature Commands
        ########################################
        if section_command.startswith('on') or section_command.startswith('off'):
            continue

        ########################################
        # Momentum Command
        ########################################
        if section_command.startswith('momentum'):

            momentum    = section
            momentum    = momentum.replace("momentum", "")
            momentum    = momentum.replace("\n", "")
            momentum    = momentum.replace(" ", "")
            momentum    = momentum.replace("=", "")

            if 'kev' in momentum:
                momentum    = float(momentum.replace("kev", "")) * 1E3
            elif 'mev' in momentum:
                momentum    = float(momentum.replace("mev", "")) * 1E6
            elif 'gev' in momentum:
                momentum    = float(momentum.replace("gev", "")) * 1E9
            elif 'tev' in momentum:
                momentum    = float(momentum.replace("tev", "")) * 1E12
            elif 'ev' in momentum:
                momentum    = float(momentum.replace("ev", ""))
            else:
                try:
                    momentum    = float(momentum)
                except TypeError:
                    continue

            cleaned_expressions['momentum'] = momentum
            continue

        ########################################
        # Mass Command
        ########################################
        if section_command.startswith('mass'):

            mass    = section
            mass    = mass.replace("mass", "")
            mass    = mass.replace("\n", "")
            mass    = mass.replace(" ", "")
            mass    = mass.replace("=", "")

            if 'kev' in mass:
                mass    = float(mass.replace("kev", "")) * 1E3
            elif 'mev' in mass:
                mass    = float(mass.replace("mev", "")) * 1E6
            elif 'gev' in mass:
                mass    = float(mass.replace("gev", "")) * 1E9
            elif 'tev' in mass:
                mass    = float(mass.replace("tev", "")) * 1E12
            elif 'ev' in mass:
                mass    = float(mass.replace("ev", ""))
            else:
                try:
                    mass    = float(mass)
                except TypeError:
                    continue

            cleaned_expressions['mass'] = mass
            continue

        ########################################
        # Deferred Expressions
        ########################################
        if section_command not in sad_elements and section_command != 'line':

            ########################################
            # If no equals sign, skip the section
            ########################################
            if '=' not in section:
                print('Unknown Section Includes the following information:')
                print(section)
                continue

            ########################################
            # Split information based on the equals sign
            ########################################
            variable, expression = section.split('=')

            ########################################
            # Convert to Float if Possible
            ########################################
            if all(char in "0123456789-." for char in expression) \
                    and expression.count('.') <= 1 \
                    and expression.count('-') <= 1:

                cleaned_expressions[variable] = float(expression)
                continue
            else:

                ########################################
                # Check if the expression is duplicated
                ########################################
                if variable not in cleaned_expressions:
                    cleaned_expressions[variable] = expression
                    continue
                else:
                    ########################################
                    # If duplicate, create new with all dependencies
                    ########################################
                    previous_expression = cleaned_expressions[variable]

                    if isinstance(previous_expression, float):
                        previous_expression = str(previous_expression)

                    new_expression      = expression.replace(
                        variable, previous_expression)

                    cleaned_expressions[variable] = new_expression
                    continue

        ########################################
        # Lines
        ########################################
        if section_command.startswith('line'):

            line_section    = section
            line_section    = line_section.replace("line", "")
            line_section    = line_section.replace("\n", "")

            ########################################
            # Split into lines by closing bracket
            ########################################
            lines   = line_section.split(')')

            ########################################
            # Process each line
            ########################################
            for line in lines:
                if len(line) == 0:
                    continue

                line_name, line_content = line.split('=')

                line_name   = line_name.replace(' ', '')

                line_content    = line_content.replace('(', '')
                line_content    = line_content.replace('\n', ' ')

                line_elements = []
                for element in line_content.split():
                    if len(element) > 0:
                        line_elements.append(element)

                cleaned_lines[line_name] = line_elements

        ########################################
        # Elements
        ########################################
        if section_command in sad_elements:
            section_dict    = {}

            ########################################
            # Convert to Dictionary Style
            ########################################
            element_section = section
            element_section = element_section.replace(section_command, "")
            element_section = element_section.replace('\n ', ' ')
            element_section = element_section.replace(' \n', ' ')
            element_section = element_section.replace('\n', ' ')
            element_section = element_section.replace(')', '),')

            ########################################
            # Split the section into elements
            ########################################
            elements    = element_section.split(',')

            ########################################
            # Process each element
            ########################################
            for element in elements:
                if len(element) == 0:
                    continue

                ele_dict    = {}

                while element.startswith(' '):
                    element = element[1:]

                ele_name, ele_vars = element.split('(')

                ele_name    = ele_name.replace(' ', '')
                ele_name    = ele_name.replace('=', '')
                ele_vars    = ele_vars.replace(')', '')

                ########################################
                # Process data in each element
                ########################################
                tokens  = ele_vars.split(' ')
                for token in tokens:

                    if len(token) == 0:
                        continue

                    ########################################
                    # Angle handling
                    ########################################
                    if 'deg' in token:
                        token_name, token_value = token.split('=')

                        token_value = token_value.replace('deg', '')
                        token_value = float(token_value)
                        token_value = np.deg2rad(token_value)
                        token = token_name + '=' + str(token_value)

                    var_name, var_value = token.split('=')

                    try:
                        var_value = float(var_value)
                        ele_dict[var_name] = var_value
                    except ValueError:
                        ele_dict[var_name] = var_value

                section_dict[ele_name] = ele_dict

            ########################################
            # Add elements
            ########################################
            if section_command in cleaned_elements:
                cleaned_elements[section_command].update(section_dict)
            else:
                cleaned_elements[section_command] = section_dict

    ############################################################################
    # Address missing momentum and mass
    ############################################################################
    if 'mass' not in cleaned_expressions and ref_particle_mass0 is None:
        raise ValueError('No mass found in SAD file or function input')
    if 'mass' not in cleaned_expressions:
        print('Warning: No mass found in SAD file')
        print('Using user provided value')
        cleaned_expressions['mass'] = ref_particle_mass0
    elif 'mass' in cleaned_expressions and ref_particle_mass0 is not None:
        print('Warning: Mass found in SAD file and function input')
        print('Using user provided value')
        cleaned_expressions['mass'] = ref_particle_mass0

    if 'momentum' not in cleaned_expressions and ref_particle_p0c is None:
        raise ValueError('No momentum found in SAD file or function input')
    if 'momentum' not in cleaned_expressions:
        print('Warning: No momentum found in SAD file')
        print('Using user provided value')
        cleaned_expressions['momentum'] = ref_particle_p0c
    elif 'momentum' in cleaned_expressions and ref_particle_p0c is not None:
        print('Warning: Momentum found in SAD file and function input')
        print('Using user provided value')
        cleaned_expressions['momentum'] = ref_particle_p0c

    ############################################################################
    # Beam rigidity for solenoids
    ############################################################################
    P0_J    = cleaned_expressions['momentum'] * qe / clight
    BRHO    = P0_J / qe / ref_particle_q0
    # TODO: Actually get the variable for this

    ############################################################################
    # Create Xsuite Environment
    ############################################################################
    env = xt.Environment()

    ############################################################################
    # Pass deferred expressions to the environment
    ############################################################################

    ########################################
    # Floats first
    ########################################
    for expression_name, expression in cleaned_expressions.items():
        if isinstance(expression, float):
            env[expression_name] = expression

    ########################################
    # Strings may depend on floats
    ########################################
    for expression_name, expression in cleaned_expressions.items():
        if isinstance(expression, str):
            env[expression_name] = expression

    ############################################################################
    # Create Xsuite Elements
    ############################################################################

    ########################################
    # Drift
    ########################################
    if 'drift' in cleaned_elements:
        drifts  = cleaned_elements['drift']

        for ele_name, ele_vars in drifts.items():

            ########################################
            # Assert Length
            ########################################
            if 'l' not in ele_vars:
                raise ValueError(f'Error: Drift {ele_name} missing length')

            ########################################
            # Create Element
            ########################################
            env.new(
                name    = ele_name,
                parent  = xt.Drift,
                length  = ele_vars['l'])
            continue

    ########################################
    # Bend
    ########################################
    if 'bend' in cleaned_elements:
        bends   = cleaned_elements['bend']

        for ele_name, ele_vars in bends.items():

            ########################################
            # Assert Length
            ########################################
            if 'l' not in ele_vars:
                print(f'Warning: Bend {ele_name} missing length ')
                print('Installing unpowered 0 length bend')
                env.new(
                    name                = ele_name,
                    parent              = xt.Bend,
                    length              = 0,
                    k0                  = 0,
                    h                   = 0,
                    edge_entry_angle    = 0,
                    edge_exit_angle     = 0,
                    rot_s_rad           = 0)
                continue

            ########################################
            # Initialise parameters that may not be present
            ########################################
            rotation    = 0
            if 'rotate' in ele_vars:
                rotation = ele_vars['rotate']

            e1          = 0
            e2          = 0
            h           = 0

            ########################################
            # Separate Bends and Kicks
            ########################################
            # Bends have angle, and allowed to have edge angles
            if 'angle' in ele_vars:
                k0l     = ele_vars['angle']
                k0      = f"{k0l} / {ele_vars['l']}"
                h       = k0
                if 'e1' in ele_vars:
                    e1 = ele_vars['e1']
                if 'e2' in ele_vars:
                    e2 = ele_vars['e2']
            # Kicks have k0, and are not allowed to have edge angles
            elif 'k0' in ele_vars:
                k0l     = ele_vars['k0']
                k0      = f"{k0l} / {ele_vars['l']}"

            ########################################
            # Create Element
            ########################################
            env.new(
                name    = ele_name,
                parent  = xt.Bend,
                length  = ele_vars['l'],
                k0      = k0,
                h       = h,
                edge_entry_angle    = f"{e1} * {k0l}",
                edge_exit_angle     = f"{e2} * {k0l}",
                rot_s_rad           = rotation)
            continue

    ########################################
    # Quadrupole
    ########################################
    if 'quad' in cleaned_elements:
        quads   = cleaned_elements['quad']

        for ele_name, ele_vars in quads.items():

            ########################################
            # Assert Length
            ########################################
            if 'l' not in ele_vars:
                print(f'Error: Quadrupole {ele_name} missing length and excluded')
                continue

            ########################################
            # Initialise parameters that may not be present
            ########################################
            rotation    = 0
            if 'rotate' in ele_vars:
                rotation = ele_vars['rotate']

            ########################################
            # Create Element
            ########################################
            # TODO: Better to do k1 and k1s native + rotation?
            env.new(
                name    = ele_name,
                parent  = xt.Quadrupole,
                length  = ele_vars['l'],
                k1      = f"{ele_vars['k1']} / {ele_vars['l']} *\
                    {np.cos(rotation * 2)}",
                k1s     = f"{ele_vars['k1']} / {ele_vars['l']} *\
                    {np.sin(rotation * 2)}")
            continue

    ########################################
    # Sextupole
    ########################################
    if 'sext' in cleaned_elements:
        sexts   = cleaned_elements['sext']

        for ele_name, ele_vars in sexts.items():

            ########################################
            # Assert Length
            ########################################
            if 'l' not in ele_vars:
                print(f'Error: Sextupole {ele_name} missing length and excluded')
                continue

            ########################################
            # Initialise parameters that may not be present
            ########################################
            rotation    = 0
            if 'rotate' in ele_vars:
                rotation = ele_vars['rotate']

            ########################################
            # Create Element
            ########################################
            # TODO: Better to do k1 and k1s native + rotation?
            env.new(
                name    = ele_name,
                parent  = xt.Sextupole,
                length  = ele_vars['l'],
                k2      = f"{ele_vars['k2']} / {ele_vars['l']} *\
                    {np.cos(rotation * 3)}",
                k2s     = f"{ele_vars['k2']} / {ele_vars['l']} *\
                    {np.sin(rotation * 3)}")
            continue

    ########################################
    # Octupole
    ########################################
    if 'oct' in cleaned_elements:
        octs    = cleaned_elements['oct']

        for ele_name, ele_vars in octs.items():

            ########################################
            # Initialise parameters that may not be present
            ########################################
            rotation    = 0
            if 'rotate' in ele_vars:
                rotation = ele_vars['rotate']

            k0l = 0
            if 'k0' in ele_vars:
                k0l = ele_vars['k0']
            k1l = 0
            if 'k1' in ele_vars:
                k1l = ele_vars['k1']
            k2l = 0
            if 'k2' in ele_vars:
                k2l = ele_vars['k2']
            k3l = 0
            if 'k3' in ele_vars:
                k3l = ele_vars['k3']

            knl = [
                f"{k0l} * {np.cos(rotation)}"       if k0l != 0 else 0,
                f"{k1l} * {np.cos(rotation * 2)}"   if k1l != 0 else 0,
                f"{k2l} * {np.cos(rotation * 3)}"   if k2l != 0 else 0,
                f"{k3l} * {np.cos(rotation * 4)}"   if k3l != 0 else 0]
            ksl = [
                f"{k0l} * {np.sin(rotation)}"       if k0l != 0 else 0,
                f"{k1l} * {np.sin(rotation * 2)}"   if k1l != 0 else 0,
                f"{k2l} * {np.sin(rotation * 3)}"   if k2l != 0 else 0,
                f"{k3l} * {np.sin(rotation * 4)}"   if k3l != 0 else 0]

            ########################################
            # Thin lens, or drift kick drift
            ########################################
            if 'l' in ele_vars:
                if ele_vars['l'] != 0:

                    env.new(
                        f'{ele_name}_drift_i', xt.Drift,
                        length = f"{ele_vars['l']} / 2")
                    env.new(
                        f'{ele_name}_drift_o', xt.Drift,
                        length = f"{ele_vars['l']} / 2")

                    env.new(
                        f'{ele_name}_kick', xt.Multipole,
                        knl = knl, ksl = ksl)

                    env.new_line(
                        name        = ele_name,
                        components  = [
                            f'{ele_name}_drift_i',
                            f'{ele_name}_kick',
                            f'{ele_name}_drift_o'])
                    continue

            else:
                env.new(f'{ele_name}', xt.Multipole, knl = knl, ksl = ksl)
                continue

    ########################################
    # Multipole
    ########################################
    if 'mult' in cleaned_elements:
        mults   = cleaned_elements['mult']

        for ele_name, ele_vars in mults.items():

            ########################################
            # Initialise parameters that may not be present
            ########################################
            length  = 0
            if 'l' in ele_vars:
                length = ele_vars['l']

            rotation    = 0
            if 'rotate' in ele_vars:
                rotation = ele_vars['rotate']

            knl = []
            for kn in range(0, 21):
                knl.append(0)
                if f'k{kn}' in ele_vars:
                    knl[kn] = ele_vars[f'k{kn}']

            ksl = []
            for ks in range(0, 21):
                ksl.append(0)
                if f'sk{ks}' in ele_vars:
                    ksl[ks] = ele_vars[f'sk{ks}']

            offset_x    = 0
            offset_y    = 0
            if 'dx' in ele_vars:
                offset_x    = ele_vars['dx']
            if 'dy' in ele_vars:
                offset_y    = ele_vars['dy']

            ########################################
            # User Defined Multipole Replacements
            ########################################
            if any(ele_name.startswith(test_key) for test_key in multipole_replacements):
                replace_type    = None

                if not 'l' in ele_vars:
                    print('Warning: Multipole replacement not supported for thin lens')
                    print(f'Installing element {ele_name} as normal multipole')
                    env.new(
                        f'{ele_name}', xt.Multipole,
                        knl = knl, ksl = ksl, rot_s_rad = rotation)
                    continue

                # Search the multipole replacements dict for the type of element
                for replacement in multipole_replacements:
                    if ele_name.startswith(replacement):
                        replace_type    = multipole_replacements[replacement]

                ########################################
                # Bend Replacement (kick)
                ########################################
                k0  = 0
                if 'k0' in ele_vars:
                    k0  = f"{ele_vars['k0']} / {ele_vars['l']}"

                if replace_type == 'Bend':
                    env.new(
                        name                = ele_name,
                        parent              = xt.Bend,
                        length              = ele_vars['l'],
                        k0                  = k0,
                        h                   = 0,
                        edge_entry_angle    = 0,
                        edge_exit_angle     = 0,
                        rot_s_rad           = rotation)
                    continue

                ########################################
                # Quadrupole Replacement
                ########################################
                k1  = 0
                k1s = 0
                if 'k1' in ele_vars:
                    k1  = f"{ele_vars['k1']} / {ele_vars['l']} * {np.cos(rotation * 2)}"
                    k1s = f"{ele_vars['k1']} / {ele_vars['l']} * {np.sin(rotation * 2)}"

                elif replace_type == 'Quadrupole':
                    # TODO: Better to do k1 and k1s native + rotation?
                    env.new(
                        name    = ele_name,
                        parent  = xt.Quadrupole,
                        length  = ele_vars['l'],
                        k1      = k1,
                        k1s     = k1s,
                        shift_x = offset_x,
                        shift_y = offset_y)
                    continue

                ########################################
                # Sextupole Replacement
                ########################################
                k2  = 0
                k2s = 0
                if 'k2' in ele_vars:
                    k2  = f"{ele_vars['k2']} / {ele_vars['l']} * {np.cos(rotation * 3)}"
                    k2s = f"{ele_vars['k2']} / {ele_vars['l']} * {np.sin(rotation * 3)}"

                elif replace_type == 'Sextupole':
                    env.new(
                        name    = ele_name,
                        parent  = xt.Sextupole,
                        length  = ele_vars['l'],
                        k2      = k2,
                        k2s     = k2s,
                        shift_x = offset_x,
                        shift_y = offset_y)
                    continue

                else:
                    raise ValueError('Error: Unknown element replacement')

            ########################################
            # Elements stored as multipole, but really something simpler
            ########################################
            if (length != 0 and knl[1] == 0 and ksl[1] == 0 \
                and knl[2] == 0 and ksl[2] == 0) \
                and (knl[0] != 0 or ksl[0] != 0):

                # Then it's a bend
                env.new(
                    name                = ele_name,
                    parent              = xt.Bend,
                    length              = ele_vars['l'],
                    k0                  = f"sqrt({knl[0]}**2 + {ksl[0]}**2) / {ele_vars['l']}",
                    h                   = 0,
                    edge_entry_angle    = 0,
                    edge_exit_angle     = 0,
                    shift_x = offset_x,
                    shift_y = offset_y,
                    rot_s_rad           = rotation)
                continue

            elif (length != 0 and knl[0] == 0 and ksl[0] == 0 \
                  and knl[2] == 0 and ksl[2] == 0) \
                  and (knl[1] != 0 or ksl[1] != 0):

                # Then it's a quadrupole
                env.new(
                    name    = ele_name,
                    parent  = xt.Quadrupole,
                    length  = ele_vars['l'],
                    k1      = f"{knl[1]} / {ele_vars['l']}",
                    k1s     = f"{ksl[1]} / {ele_vars['l']}",
                    shift_x = offset_x,
                    shift_y = offset_y)
                continue

            elif (length != 0 and knl[0] == 0 and ksl[0] == 0 \
                  and knl[1] == 0 and ksl[1] == 0) \
                  and (knl[2] != 0 or ksl[2] != 0):

                # Then it's a sextupole
                env.new(
                    name    = ele_name,
                    parent  = xt.Sextupole,
                    length  = ele_vars['l'],
                    k2      = f"{knl[2]} / {ele_vars['l']}",
                    k2s     = f"{ksl[2]} / {ele_vars['l']}",
                    shift_x = offset_x,
                    shift_y = offset_y)
                continue

            ########################################
            # Else True multipole
            ########################################
            if 'l' in ele_vars:
                if ele_vars['l'] != 0:

                    env.new(f'{ele_name}_drift_i', xt.Drift,
                        length = f"{ele_vars['l']} / 2")
                    env.new(f'{ele_name}_drift_o', xt.Drift,
                        length = f"{ele_vars['l']} / 2")

                    env.new(f'{ele_name}_kick', xt.Multipole,
                            knl         = knl,
                            ksl         = ksl,
                            shift_x     = offset_x,
                            shift_y     = offset_y,
                            rot_s_rad   = rotation)

                    env.new_line(
                        name        = ele_name,
                        components  = [
                            f'{ele_name}_drift_i',
                            f'{ele_name}_kick',
                            f'{ele_name}_drift_o'])
                    continue

            else:
                env.new(f'{ele_name}', xt.Multipole,
                    knl         = knl,
                    ksl         = ksl,
                    shift_x     = offset_x,
                    shift_y     = offset_y,
                    rot_s_rad   = rotation)
                continue

    ########################################
    # Cavities
    ########################################
    if 'cavi' in cleaned_elements:
        cavis   = cleaned_elements['cavi']

        for ele_name, ele_vars in cavis.items():

            ########################################
            # Initialise parameters that may not be present
            ########################################
            phi     = 0
            if 'phi' in ele_vars:
                phi = ele_vars['phi']

            freq    = 0
            if 'freq' in ele_vars:
                freq = ele_vars['freq']

            if 'harm' in ele_vars:
                print('Warning: Harmonic numbers not implemented')

            ########################################
            # Create Element
            ########################################
            env.new(
                name        = ele_name,
                parent      = xt.Cavity,
                voltage     = ele_vars['volt'],
                frequency   = freq,
                lag         = phi)
            continue

    ########################################
    # Apertures
    ########################################
    if 'apert' in cleaned_elements:
        aperts  = cleaned_elements['apert']

        for ele_name, ele_vars in aperts.items():

            ########################################
            # Create Element
            ########################################
            env.new(
                name    = ele_name,
                parent  = xt.LimitEllipse,
                a       = ele_vars['ax'],
                b       = ele_vars['ay'])
            continue

    ########################################
    # Solenoid
    ########################################
    if 'sol' in cleaned_elements:
        solenoids   = cleaned_elements['sol']

        for ele_name, ele_vars in solenoids.items():
            # TODO: Continue to update the solenoid

            if 'dz' in ele_vars:
                env.new(
                    name    = ele_name,
                    parent  = xt.Solenoid,
                    length  = ele_vars['dz'],
                    ks      = ele_vars['bz'] / BRHO)
                continue

            else:
                env.new(
                    name    = ele_name,
                    parent  = xt.Solenoid,
                    ks      = ele_vars['bz'] / BRHO)
                continue

    ########################################
    # Markers (all types)
    ########################################
    if 'mark' in cleaned_elements:
        marks   = cleaned_elements['mark']

        for ele_name, ele_vars in marks.items():
            env.new(
                name    = ele_name,
                parent  = xt.Marker)
            continue

    if 'moni' in cleaned_elements:
        monis   = cleaned_elements['moni']

        for ele_name, ele_vars in monis.items():
            env.new(
                name    = ele_name,
                parent  = xt.Marker)
            continue

    if 'beambeam' in cleaned_elements:
        beam_beams   = cleaned_elements['beambeam']

        for ele_name, ele_vars in beam_beams.items():
            env.new(
                name    = ele_name,
                parent  = xt.Marker)
            continue

    ############################################################################
    # Create Lines
    ############################################################################

    ########################################
    # Create all lines
    ########################################
    for line, components in cleaned_lines.items():

        ########################################
        # Handle reversed components
        ########################################
        reverse_handled_components  = []

        for component in components:
            if '-' in component:
                # If the component is already in the element dictionary
                # We must remove this, not overwrite it
                if component in env.element_dict:
                    env.element_dict.pop(component)

                if isinstance(env.element_dict[component[1:]], xt.Bend):
                    env.new(
                        name    = component,
                        parent  = component[1:],
                        mode    = 'clone')
                    env[component].edge_entry_angle  =\
                        env[component[1:]].edge_exit_angle
                    env[component].edge_exit_angle   =\
                        env[component[1:]].edge_entry_angle

                elif isinstance(env.element_dict[component[1:]], xt.Cavity):
                    env.new(
                        name    = component,
                        parent  = component[1:],
                        mode    = 'clone')
                    env[component].voltage  *= -1
                else:
                    component = component[1:]
            reverse_handled_components.append(component)

        env.new_line(
            name        = line,
            components  = reverse_handled_components)

    ########################################
    # Select the top line
    ########################################
    line = env[list(cleaned_lines.keys())[-1]]

    ########################################
    # Add reference particle
    ########################################
    line.particle_ref = xt.Particles(
        p0c     = cleaned_expressions['momentum'],
        mass0   = cleaned_expressions['mass'])

    ########################################
    # Apply chosen bend model to the line
    ########################################
    line.configure_bend_model(edge = bend_edge_model)

    ############################################################################
    # Reposition markers
    ############################################################################
    # Markers in SAD have an offset parameter that is not replicated in Xsuite
    marker_offsets = {}

    ########################################
    # Get line table
    ########################################
    print('Getting line table')
    line.build_tracker()
    tt      = line.get_table(attr = True)
    buffer  = line._buffer # Buffer for inserting elements
    line.discard_tracker()
    print('Got line table')

    ########################################
    # Check for the offset of each marker
    ########################################
    print('Calculating marker positions')
    for marker_type in ['mark', 'moni', 'beambeam']:
        if marker_type in cleaned_elements:
            for marker_name, marker in cleaned_elements[marker_type].items():
                if 'offset' in marker:
                    marker_offsets[marker_name] = marker['offset']
                else:
                    marker_offsets[marker_name] = 0

    ########################################
    # Get the names of inserted markers (check for reversed)
    ########################################
    inserted_markers    = list(tt.rows[tt.element_type == 'Marker'].name)
    element_names       = list(tt.name)

    ########################################
    # Calculate intended marker locations
    ########################################
    marker_locations = {}

    for marker in inserted_markers:

        base_marker     = marker.split('::')[0]

        if base_marker.startswith('-'):
            base_marker = base_marker[1:]
            offset      = marker_offsets[base_marker]
        else:
            offset      = marker_offsets[base_marker]

        ########################################
        # Case 1: Marker remains in the same element
        ########################################
        if 0 <= offset <= 1:
            marker_idx = element_names.index(marker)
            try:
                insert_at_ele   = element_names[marker_idx + 1]
                s_to_insert     = tt['s', insert_at_ele]
            except IndexError:  # Next element is the end of the line
                s_to_insert = tt.s[-1]
            except KeyError:    # Next element is a marker
                relative_idx = 1
                while True:
                    relative_idx += 1
                    try:
                        insert_at_ele   = element_names[marker_idx + relative_idx]
                        s_to_insert     = tt['s', insert_at_ele]
                        break
                    except KeyError:   # Next element is a marker
                        pass
                    except IndexError: # Next element is the end of the line
                        s_to_insert = tt.s[-1]
                        break
        ########################################
        # Case 2: Marker is offset to within another element
        ########################################
        else:
            # Get the index of the corresponding element
            relative_idx    = int(np.floor(offset))
            marker_idx      = element_names.index(marker)
            insert_at_ele   = element_names[marker_idx + relative_idx]

            # Get the length of the element to insert at
            insert_ele_length   = tt['length', insert_at_ele]

            # Add the fraction of element length
            s_to_insert     = tt['s', insert_at_ele] +\
                insert_ele_length * (offset % 1)

        # Produce a dictionary of the s locations that markers are inserted at
        marker_locations[marker] = s_to_insert

    ########################################
    # Remove previous markers
    ########################################
    line.remove_markers()

    ########################################
    # Replace repeated elements
    ########################################
    line.replace_all_repeated_elements()

    ########################################
    # Slice and install markers
    ########################################
    if install_markers:
        for marker, insert_at_s in marker_locations.items():
            if insert_at_s < tt.s[-1]:
                line.insert_element(
                    name    = marker,
                    element = xt.Marker(_buffer = buffer),
                    at_s    = insert_at_s,
                    s_tol   = 1E-6)
            else:
                line.append_element(
                    name    = marker,
                    element = xt.Marker(_buffer = buffer))

    ############################################################################
    # Return Line
    ############################################################################å
    return line, marker_locations
