"""
(Unofficial) SAD to XSuite Converter: SAD File Parser
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-25
"""

################################################################################
# Required Packages
################################################################################
import re

import xtrack as xt
import numpy as np

from ..config import PROTECTED_ELEMENT_NAMES
from ..types import ConfigLike
from ..helpers import print_section_heading

################################################################################
# Element Body Splitting
################################################################################

def _split_element_bodies(element_section: str) -> list[str]:
    """
    Split a raw element section into individual element definition strings,
    correctly handling nested parentheses in parameter values.

    Each element definition has the form 'NAME=(param1 param2 ...)'. A naive
    split on ')' breaks when a parameter value itself contains parentheses —
    e.g. 'SQRT(L0)' or '(L0 + DL) / 2'. This function tracks parenthesis
    depth and only treats a ')' as a definition boundary when it closes the
    outermost wrapper, i.e. when depth returns to zero.

    Example:
        Input:  ' d1=(l=sqrt(l0)) d2=(l=1.0)'
        Output: ['d1=(l=sqrt(l0))', 'd2=(l=1.0)']
    """
    element_definitions = []
    current_definition  = []
    paren_depth         = 0

    for char in element_section:
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
            if paren_depth < 0:
                raise ValueError(
                    f"Malformed element definition — closing ')' has no matching "
                    f"'(': '{element_section.strip()}'")
            if paren_depth == 0:
                current_definition.append(char)
                element_definitions.append("".join(current_definition).strip())
                current_definition = []
                continue
        current_definition.append(char)

    return [defn for defn in element_definitions if defn.strip()]


################################################################################
# Element Parameter Parsing
################################################################################
ELEMENT_PARAMETER_PATTERN = re.compile(r"(?<!\S)([a-z][a-z0-9_]*)\s*=")

def split_element_parameters(ele_vars: str) -> list[tuple[str, str]]:
    """
    Split an element parameter string into complete name/value pairs.

    SAD element values can be arithmetic expressions with spaces. Splitting the
    whole parameter string on whitespace would break expressions such as
    `l=l0 + dl`. This function instead splits at parameter assignments.
    """
    parameters = []
    matches = list(ELEMENT_PARAMETER_PATTERN.finditer(ele_vars))

    if len(matches) == 0:
        if ele_vars.strip():
            raise ValueError(
                f"Error parsing element variables: {ele_vars}. "
                "Expected one or more 'name = value' assignments.")
        return parameters

    for index, match in enumerate(matches):
        var_name    = match.group(1)
        value_start = match.end()
        value_end   = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(ele_vars))

        var_value = ele_vars[value_start:value_end].strip()
        if len(var_value) == 0:
            raise ValueError(
                f"Error parsing element variable: {var_name}. "
                "Expected a value after '='.")

        parameters.append((var_name, var_value))

    return parameters

################################################################################
# Electron Volt Conversion
################################################################################
def ev_text_to_float(value_in_ev: str):
    """
    Convert a string representation of energy in electron volts to a float
    """
    if "kev" in value_in_ev:
        return float(value_in_ev.replace("kev", "")) * 1E3
    elif "mev" in value_in_ev:
        return float(value_in_ev.replace("mev", "")) * 1E6
    elif "gev" in value_in_ev:
        return float(value_in_ev.replace("gev", "")) * 1E9
    elif "tev" in value_in_ev:
        return float(value_in_ev.replace("tev", "")) * 1E12
    elif "ev" in value_in_ev:
        return float(value_in_ev.replace("ev", ""))
    else:
        try:
            return float(value_in_ev)
        except ValueError:
            return None

################################################################################
# Load and Clean Whitespace
################################################################################
def strip_sad_comments(content: str) -> str:
    """
    Remove full-line and inline SAD comments before section splitting.

    SAD comments begin with `!`. Removing comments before splitting sections is
    important because comment text can contain semicolons.
    """
    cleaned_lines = []
    for line in content.splitlines():
        cleaned_lines.append(line.split("!", 1)[0])

    return "\n".join(cleaned_lines)

def load_and_clean_whitespace(sad_lattice_path: str):
    """
    Docstring for load_and_clean_whitespace
    
    :param sad_lattice_path: Description
    :type sad_lattice_path: str
    """
    ############################################################################
    # Load SAD File to Python
    ############################################################################
    with open(sad_lattice_path, "r", encoding = "utf-8") as sad_file:
        content = sad_file.read()

    ############################################################################
    # Remove comments before section splitting
    ############################################################################
    content = strip_sad_comments(content)

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
    while " =" in content:
        content = content.replace(" =", "=")
    while "= " in content:
        content = content.replace("= ", "=")
    while "( " in content:
        content = content.replace("( ", "(")
    while " )" in content:
        content = content.replace(" )", ")")
    while "  " in content:
        content = content.replace("  ", " ")

    ########################################
    # Angle Handling
    ########################################
    # Ensure no spaces between the value and its unit
    content     = content.replace(" deg", "deg")
    content     = content.replace(" rad", "rad")

    ########################################
    # Split the file into sections
    ########################################
    # Semicolons are used to separate element sections
    sections    = content.split(";")

    ########################################
    # Return the section information
    ########################################
    return sections

################################################################################
# Parsing Function
################################################################################
def parse_sad_file(
        sad_lattice_path:               str,
        config:                         ConfigLike,
        install_apertures_as_markers:   bool = False) -> dict:
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
    if config._verbose:
        print_section_heading("Loading and Cleaning SAD File", mode = "subsection")

    sad_sections = load_and_clean_whitespace(sad_lattice_path)

    ############################################################################
    # Clean each different section of the file
    ############################################################################
    if config._verbose:
        print_section_heading("Cleaning Element Sections", mode = "subsection")

    for section in sad_sections:
        current_section = section

        ########################################
        # Remove Commented Lines
        ########################################
        comment_removed_section = []
        for line in current_section.split("\n"):
            if not line.startswith("!"):
                # Lines that do contain content to pass
                if "!" in line:
                    # Trim lines that have comment part way through
                    line = line.split("!")[0]
                comment_removed_section.append(line)
            else:
                # Lines that are only comments
                continue
        current_section = "\n".join(comment_removed_section)

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

        if section_command == "on":
            parsed_sections.remove(section)
            continue

        if section_command == "off":
            parsed_sections.remove(section)
            continue

    ############################################################################
    # Global Variables
    ############################################################################
    if config._verbose:
        print_section_heading("Parsing Global Variables", mode = "subsection")

    for section in parsed_sections[:]:
        section_command = section.split()[0]

        ########################################
        # Momentum
        ########################################
        if section_command.split("=")[0] == "momentum":

            momentum    = section
            momentum    = momentum.replace("momentum", "")
            momentum    = momentum.replace("\n", "")
            momentum    = momentum.replace("\t", "")
            momentum    = momentum.replace(" ", "")
            momentum    = momentum.replace("=", "")

            momentum    = ev_text_to_float(momentum)

            cleaned_globals["p0c"] = momentum

            parsed_sections.remove(section)
            continue

        ########################################
        # Mass
        ########################################
        if section_command.split("=")[0] == "mass":

            mass    = section
            mass    = mass.replace("mass", "")
            mass    = mass.replace("\n", "")
            mass    = mass.replace("\t", "")
            mass    = mass.replace(" ", "")
            mass    = mass.replace("=", "")

            mass    = ev_text_to_float(mass)

            cleaned_globals["mass0"] = mass

            parsed_sections.remove(section)
            continue

        ########################################
        # Charge
        ########################################
        if section_command.split("=")[0] == "charge":

            charge  = section
            charge  = charge.replace("charge", "")
            charge  = charge.replace("\n", "")
            charge  = charge.replace("\t", "")
            charge  = charge.replace(" ", "")
            charge  = charge.replace("=", "")

            charge  = float(charge)

            cleaned_globals["q0"] = charge

            parsed_sections.remove(section)
            continue

        ########################################
        # Frequency Shift
        ########################################
        if section_command.split("=")[0] == "fshift":

            fshift  = section
            fshift  = fshift.replace("fshift", "")
            fshift  = fshift.replace("\n", "")
            fshift  = fshift.replace("\t", "")
            fshift  = fshift.replace(" ", "")
            fshift  = fshift.replace("=", "")

            fshift  = float(fshift)

            cleaned_globals["fshift"] = fshift

            parsed_sections.remove(section)
            continue

    ############################################################################
    # Lines
    ############################################################################
    if config._verbose:
        print_section_heading("Parsing Lines", mode = "subsection")

    for section in parsed_sections[:]:
        section_command = section.split()[0]

        if section_command.startswith("line"):

            line_section    = section
            line_section    = line_section.replace("\n", " ")
            line_section    = line_section.replace("\t", " ")
            while "  " in line_section:
                line_section = line_section.replace("  ", " ")

            ########################################
            # Validate parenthesis balance
            ########################################
            open_count  = line_section.count("(")
            close_count = line_section.count(")")
            if open_count != close_count:
                raise ValueError(
                    f"Malformed LINE definition — unmatched parentheses "
                    f"({open_count} opening, {close_count} closing): "
                    f"'{line_section.strip()}'")

            ########################################
            # Split into lines by closing bracket
            ########################################
            lines   = line_section.split(")")

            ########################################
            # Process each line
            ########################################
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith("line "):
                    line = line[5:]

                if "=" in line:
                    line_name, line_content = line.split("=", 1)
                    if "=" in line_content:
                        raise ValueError(
                            f"Malformed LINE definition — multiple '=' found: "
                            f"'{line.strip()}'")
                elif "(" in line:
                    line_name, line_content = line.split("(", 1)
                else:
                    continue

                line_name       = line_name.replace(" ", "")
                line_content    = line_content.replace("(", "")
                line_content    = line_content.replace("\n", " ")
                line_content    = line_content.replace("\t", " ")
                line_content    = line_content.replace(",", " ")

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
    if config._verbose:
        print_section_heading("Parsing Elements", mode = "subsection")

    for section in parsed_sections[:]:
        section_command = section.split()[0]

        if section_command in config.SAD_ALLOWED_ELEMENTS:
            section_dict    = {}

            ########################################
            # Convert to Dictionary Style
            ########################################
            element_section = section
            element_section = element_section.removeprefix(section_command)
            element_section = element_section.replace("\n ", " ")
            element_section = element_section.replace(" \n", " ")
            element_section = element_section.replace("\n", " ")
            element_section = element_section.replace("\t", " ")
            ########################################
            # Split the section into elements
            ########################################
            elements    = _split_element_bodies(element_section)

            ########################################
            # Process each element
            ########################################
            for element in elements:
                ele_dict    = {}

                while element.startswith(" "):
                    element = element[1:]

                if len(element) == 0:
                    continue

                ########################################
                # Split the name and variables
                ########################################
                ele_name, ele_vars = element.split("(", 1)

                ########################################
                # Handle the element name
                ########################################
                ele_name    = ele_name.replace(" ", "")
                ele_name    = ele_name.replace("=", "")

                if ele_name in PROTECTED_ELEMENT_NAMES:
                    raise ValueError(
                        f"Element name '{ele_name}' collides with a protected "
                        f"SAD2XS reserved name. Choose a different element name.")

                ########################################
                # Handle the element variables
                # The depth-aware split guarantees the body ends with the outer
                # closing ')' — strip exactly that one character.
                ########################################
                ele_vars    = ele_vars[:-1]
                ele_vars    = ele_vars.replace("\n", "")
                while "= " in ele_vars:
                    ele_vars    = ele_vars.replace("= ", "=")

                ########################################
                # Process data in each element
                ########################################
                for var_name, var_value in split_element_parameters(ele_vars):

                    ########################################
                    # Angle handling
                    ########################################
                    if "deg" in var_value:
                        var_value = var_value.replace("deg", "")
                        var_value = np.deg2rad(float(var_value))
                    elif "rad" in var_value:
                        var_value = var_value.replace("rad", "")
                        var_value = float(var_value)

                    try:
                        var_value = float(var_value)
                        ele_dict[var_name] = var_value
                    except ValueError:
                        ele_dict[var_name] = var_value

                for other_type, other_dict in cleaned_elements.items():
                    if other_type != section_command and ele_name in other_dict:
                        # APERT+MARK sharing a name is valid when
                        # install_apertures_as_markers=True — the merge is
                        # handled downstream in main.py after parsing.
                        if (install_apertures_as_markers
                                and {other_type, section_command} == {"apert", "mark"}):
                            continue
                        raise ValueError(
                            f"Element name '{ele_name}' is already defined as a "
                            f"'{other_type}' element. SAD does not allow reusing "
                            f"element names across different element types.")

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
    if config._verbose:
        print_section_heading("Parsing Deferred Expressions", mode = "subsection")

    for section in parsed_sections[:]:
        section_command = section.split()[0]

        ########################################
        # If no equals sign, skip the section
        ########################################
        if "=" not in section:
            if config._verbose:
                print("Unknown Section Includes the following information:")
                print(section)

            parsed_sections.remove(section)
            continue

        ########################################
        # Split information based on the equals sign
        ########################################
        try:
            variable, expression = section.split("=")
            expression = " ".join(expression.split())
        except ValueError:
            raise ValueError(
                f"Error parsing section: {section}. "
                "Expected format 'name = expression'.")

        ########################################
        # Convert to Float if Possible
        ########################################
        if all(char in "0123456789-." for char in expression) \
                and expression.count(".") <= 1 \
                and expression.count("-") <= 1:

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
    if "mass0" not in cleaned_globals and config.ref_particle_mass0 is None:
        cleaned_globals["mass0"] = xt.ELECTRON_MASS_EV
        if config._verbose:
            print("Notice! No mass found in SAD file or function input: Using electron mass")
    if "mass0" not in cleaned_globals:
        cleaned_globals["mass0"] = config.ref_particle_mass0
        if config._verbose:
            print("Notice! No mass found in SAD file: Using user provided value")
    elif "mass0" in cleaned_globals and config.ref_particle_mass0 is not None:
        cleaned_globals["mass0"] = config.ref_particle_mass0
        if config._verbose:
            print("Warning! Mass found in SAD file and function input: Using user provided value")

    if "p0c" not in cleaned_globals and config.ref_particle_p0c is None:
        # TODO: From SAD find what the nominal value is
        raise ValueError("Notice! No momentum found in SAD file or function input")
    if "p0c" not in cleaned_globals:
        cleaned_globals["p0c"] = config.ref_particle_p0c
        if config._verbose:
            print("Notice! No momentum found in SAD file: Using user provided value")
    elif "p0c" in cleaned_globals and config.ref_particle_p0c is not None:
        cleaned_globals["p0c"] = config.ref_particle_p0c
        if config._verbose:
            print("Warning! Momentum found in SAD file and function input: Using user provided value")

    if "q0" not in cleaned_globals and config.ref_particle_q0 is None:
        cleaned_globals["q0"]   = +1
        if config._verbose:
            print("Notice! No charge found in SAD file or function input: Using charge of +e")
    if "q0" not in cleaned_globals:
        cleaned_globals["q0"] = config.ref_particle_q0
        if config._verbose:
            print("Notice! No charge found in SAD file: Using user provided value")
    elif "q0" in cleaned_globals and config.ref_particle_q0 is not None:
        cleaned_globals["q0"] = config.ref_particle_q0
        if config._verbose:
            print("Warning! Charge found in SAD file and function input: Using user provided value")

    if "fshift" not in cleaned_globals:
        cleaned_globals["fshift"]   = 0.0
        if config._verbose:
            print("Notice! No fshift found in SAD file or function input: Using fshift of 0.0")

    ############################################################################
    # Return the Parsed Data
    ############################################################################
    parsed_lattice_data = {
        "globals":      cleaned_globals,
        "lines":        cleaned_lines,
        "elements":     cleaned_elements,
        "expressions":  cleaned_expressions}

    return parsed_lattice_data
