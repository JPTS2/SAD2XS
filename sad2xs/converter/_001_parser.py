"""
(Unofficial) SAD to XSuite Converter

SAD Lattice Text File Parser
"""

################################################################################
# Required Packages
################################################################################
import xtrack as xt
import numpy as np

from .._globals import print_section_heading, SAD_ALLOWED_ELEMENTS

################################################################################
# Electron Volt Conversion
################################################################################
def ev_text_to_float(value_in_ev: str):
    """
    Convert a string representation of energy in electron volts to a float
    """
    if 'kev' in value_in_ev:
        return float(value_in_ev.replace("kev", "")) * 1E3
    elif 'mev' in value_in_ev:
        return float(value_in_ev.replace("mev", "")) * 1E6
    elif 'gev' in value_in_ev:
        return float(value_in_ev.replace("gev", "")) * 1E9
    elif 'tev' in value_in_ev:
        return float(value_in_ev.replace("tev", "")) * 1E12
    elif 'ev' in value_in_ev:
        return float(value_in_ev.replace("ev", ""))
    else:
        try:
            return float(value_in_ev)
        except ValueError:
            return None

################################################################################
# Load and Clean Whitespace
################################################################################
def load_and_clean_whitespace(
        sad_lattice_path:       str):
    ############################################################################
    # Load SAD File to Python
    ############################################################################
    with open(sad_lattice_path, 'r', encoding = "utf-8") as sad_file:
        content = sad_file.read()

    ############################################################################
    # Convert Overall Formatting to Xsuite Style
    ############################################################################
    
    ########################################
    # Make naming lowercase
    ########################################
    content = content.lower()

    ########################################
    # Correct Formatting Issues
    ########################################
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
    content     = content.replace(' deg', 'deg')

    ########################################
    # Split the file into sections
    ########################################
    # Semicolons are used to separate element sections
    sections    = content.split(';')

    ########################################
    # Return the section information
    ########################################
    return sections

################################################################################
# Parsing Function
################################################################################
def parse_sad_file(
        sad_lattice_path:       str,
        ref_particle_mass0:     float | None        = None,
        ref_particle_q0:        float | None        = None,
        ref_particle_p0c:       float | None        = None,
        verbose:                bool                = False) -> dict:
    """
    Parse lattice definitions from SAD
    Convert a particle accelerator lattice defined in Stratgeic Accelerator 
    Design (SAD) to the Xtrack format (part of the Xsuite packages)

    Parameters:
    ----------
    sad_lattice_path: str
        Path to the SAD lattice file
        
    Outputs
    ----------
    parsed_lattice_data: dict
        Dictionary of markers and their locations
    """

    ############################################################################
    # Setup
    ############################################################################
    parsed_sections     = []
    
    cleaned_globals     = {}
    cleaned_elements    = {}
    cleaned_expressions = {}
    cleaned_lines       = {}

    ############################################################################
    # Load lattice and clean whitespace
    ############################################################################
    if verbose:
        print_section_heading('Loading and Cleaning SAD File', mode = 'subsection')
    
    sad_sections = load_and_clean_whitespace(sad_lattice_path)

    ############################################################################
    # Clean each different section of the file
    ############################################################################
    if verbose:
        print_section_heading('Cleaning Element Sections', mode = 'subsection')

    for section in sad_sections:
        current_section = section

        ########################################
        # Remove Commented Lines
        ########################################
        comment_removed_section = []
        for line in current_section.split('\n'):
            if not line.startswith('!'):
                # Lines that do contain content to pass
                if '!' in line:
                    # Trim lines that have comment part way through
                    line = line.split('!')[0]
                comment_removed_section.append(line)
            else:
                # Lines that are only comments
                continue
        current_section = '\n'.join(comment_removed_section)

        ########################################
        # Strip newlines and whitespace
        ########################################
        current_section = current_section.strip()

        ########################################
        # Remove Empty Sections
        ########################################
        if len(current_section) == 0:
            continue

        ########################################
        # Get the "Command" of the Section
        ########################################
        section_command = current_section.split()[0]

        ########################################
        # Output the cleaned section
        ########################################
        parsed_sections.append(current_section)
        
    ############################################################################
    # Remove SAD simulation commands
    ############################################################################
    # e.g. on rad, on cod...
    for section in parsed_sections[:]:
        section_command = section.split()[0]

        if section_command.startswith('on'):
            parsed_sections.remove(section)
            continue
        
        if section_command.startswith('off'):
            parsed_sections.remove(section)
            continue

    ############################################################################
    # Global Variables
    ############################################################################
    if verbose:
        print_section_heading('Parsing Global Variables', mode = 'subsection')

    for section in parsed_sections[:]:
        section_command = section.split()[0]

        ########################################
        # Momentum
        ########################################
        if section_command.startswith('momentum'):

            momentum    = section
            momentum    = momentum.replace("momentum", "")
            momentum    = momentum.replace("\n", "")
            momentum    = momentum.replace("\t", "")
            momentum    = momentum.replace(" ", "")
            momentum    = momentum.replace("=", "")

            momentum    = ev_text_to_float(momentum)

            cleaned_globals['momentum'] = momentum

            parsed_sections.remove(section)
            continue

        ########################################
        # Mass
        ########################################
        if section_command.startswith('mass'):

            mass    = section
            mass    = mass.replace("mass", "")
            mass    = mass.replace("\n", "")
            mass    = mass.replace("\t", "")
            mass    = mass.replace(" ", "")
            mass    = mass.replace("=", "")

            mass    = ev_text_to_float(mass)

            cleaned_globals['mass'] = mass

            parsed_sections.remove(section)
            continue

        ########################################
        # Charge
        ########################################
        if section_command.startswith('charge'):

            charge  = section
            charge  = charge.replace("charge", "")
            charge  = charge.replace("\n", "")
            charge  = charge.replace("\t", "")
            charge  = charge.replace(" ", "")
            charge  = charge.replace("=", "")

            charge  = ev_text_to_float(charge)

            cleaned_globals['charge'] = charge

            parsed_sections.remove(section)
            continue

        ########################################
        # Frequency Shift
        ########################################
        if section_command.startswith('fshift'):

            fshift  = section
            fshift  = fshift.replace("fshift", "")
            fshift  = fshift.replace("\n", "")
            fshift  = fshift.replace("\t", "")
            fshift  = fshift.replace(" ", "")
            fshift  = fshift.replace("=", "")

            fshift  = ev_text_to_float(fshift)

            cleaned_globals['fshift'] = fshift

            parsed_sections.remove(section)
            continue

    ############################################################################
    # Lines
    ############################################################################
    if verbose:
        print_section_heading('Parsing Lines', mode = 'subsection')

    for section in parsed_sections[:]:
        section_command = section.split()[0]

        if section_command.startswith('line'):

            line_section    = section
            line_section    = line_section.replace("line", "")
            line_section    = line_section.replace("\n", "")
            line_section    = line_section.replace("\t", "")

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

                line_name       = line_name.replace(' ', '')
                line_content    = line_content.replace('(', '')
                line_content    = line_content.replace('\n', ' ')
                line_content    = line_content.replace('\t', ' ')

                line_elements = []
                for element in line_content.split():
                    if len(element) > 0:
                        line_elements.append(element)

                cleaned_lines[line_name] = line_elements
            
            parsed_sections.remove(section)
            continue

    ############################################################################
    # Elements
    ############################################################################
    if verbose:
        print_section_heading('Parsing Elements', mode = 'subsection')

    for section in parsed_sections[:]:
        section_command = section.split()[0]

        if section_command in SAD_ALLOWED_ELEMENTS:
            section_dict    = {}

            ########################################
            # Convert to Dictionary Style
            ########################################
            element_section = section
            element_section = element_section.removeprefix(section_command)
            element_section = element_section.replace('\n ', ' ')
            element_section = element_section.replace(' \n', ' ')
            element_section = element_section.replace('\n', ' ')
            element_section = element_section.replace('\t', ' ')
            element_section = element_section.replace(')', '),')

            ########################################
            # Split the section into elements
            ########################################
            elements    = element_section.split(',')

            ########################################
            # Process each element
            ########################################
            for element in elements:
                ele_dict    = {}

                while element.startswith(' '):
                    element = element[1:]

                if len(element) == 0:
                    continue

                ########################################
                # Split the name and variables
                ########################################
                ele_name, ele_vars = element.split('(')

                ########################################
                # Handle the element name
                ########################################
                ele_name    = ele_name.replace(' ', '')
                ele_name    = ele_name.replace('=', '')

                ########################################
                # Handle the element variables
                ########################################
                ele_vars    = ele_vars.replace(')', '')
                ele_vars    = ele_vars.replace('\n', '')
                while '= ' in ele_vars:
                    ele_vars    = ele_vars.replace('= ', '=')

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

                    try:
                        var_name, var_value = token.split('=')
                    except ValueError:
                        raise ValueError(
                            f"Error parsing token: {token}. "
                            "Expected format 'name=value'.")

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

            parsed_sections.remove(section)
            continue

    ############################################################################
    # Deferred expressions
    ############################################################################
    if verbose:
        print_section_heading('Parsing Deferred Expressions', mode = 'subsection')

    for section in parsed_sections[:]:
        section_command = section.split()[0]

        ########################################
        # If no equals sign, skip the section
        ########################################
        if '=' not in section:
            if verbose:
                print('Unknown Section Includes the following information:')
                print(section)

            parsed_sections.remove(section)
            continue

        ########################################
        # Split information based on the equals sign
        ########################################
        try:
            variable, expression = section.split('=')
        except ValueError:
            raise ValueError(
                f"Error parsing section: {section}. "
                "Expected format 'name=expression'.")

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

    ############################################################################
    # Address missing momentum and mass and charge
    ############################################################################
    if 'mass' not in cleaned_globals and ref_particle_mass0 is None:
        cleaned_globals['mass'] = xt.ELECTRON_MASS_EV
        if verbose:
            print('Notice! No mass found in SAD file or function input: Using electron mass')
    if 'mass' not in cleaned_globals:
        cleaned_globals['mass'] = ref_particle_mass0
        if verbose:
            print('Notice! No mass found in SAD file: Using user provided value')
    elif 'mass' in cleaned_globals and ref_particle_mass0 is not None:
        cleaned_globals['mass'] = ref_particle_mass0
        if verbose:
            print('Warning! Mass found in SAD file and function input: Using user provided value')

    if 'momentum' not in cleaned_globals and ref_particle_p0c is None:
        # TODO: From SAD find what the nominal value is
        raise ValueError('Notice! No momentum found in SAD file or function input')
    if 'momentum' not in cleaned_globals:
        cleaned_globals['momentum'] = ref_particle_p0c
        if verbose:
            print('Notice! No momentum found in SAD file: Using user provided value')
    elif 'momentum' in cleaned_globals and ref_particle_p0c is not None:
        cleaned_globals['momentum'] = ref_particle_p0c
        if verbose:
            print('Warning! Momentum found in SAD file and function input: Using user provided value')

    if 'charge' not in cleaned_globals and ref_particle_q0 is None:
        cleaned_globals['charge']   = +1
        if verbose:
            print('Notice! No charge found in SAD file or function input: Using charge of +e')
    if 'charge' not in cleaned_globals:
        cleaned_globals['charge'] = ref_particle_q0
        if verbose:
            print('Notice! No charge found in SAD file: Using user provided value')
    elif 'charge' in cleaned_globals and ref_particle_q0 is not None:
        cleaned_globals['charge'] = ref_particle_q0
        if verbose:
            print('Warning! Charge found in SAD file and function input: Using user provided value')

    if 'fshift' not in cleaned_globals:
        cleaned_globals['fshift']   = 0.0
        if verbose:
            print('Notice! No fshift found in SAD file or function input: Using fshift of 0.0')

    ############################################################################
    # Return the Parsed Data
    ############################################################################
    parsed_lattice_data = {
        'globals':      cleaned_globals,
        'lines':        cleaned_lines,
        'elements':     cleaned_elements,
        'expressions':  cleaned_expressions}
    
    return parsed_lattice_data
