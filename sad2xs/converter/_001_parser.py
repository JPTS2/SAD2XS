"""
(Unofficial) SAD to XSuite Converter: SAD File Parser
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-27
"""

################################################################################
# Required Packages
################################################################################
import logging
import re

import xtrack as xt
import numpy as np

from ..config import PROTECTED_ELEMENT_NAMES
from ..types import ConfigLike
from ..helpers import log_section_heading

logger  = logging.getLogger(__name__)

################################################################################
# Element Body Splitting
################################################################################

def _split_element_bodies(element_section: str, line_no: int | None = None) -> list[str]:
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
    line_prefix         = f"line {line_no}: " if line_no is not None else ""

    for char in element_section:
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
            if paren_depth < 0:
                raise ValueError(
                    f"{line_prefix}Malformed element definition — closing ')' has "
                    f"no matching '(': '{element_section.strip()}'")
            if paren_depth == 0:
                current_definition.append(char)
                element_definitions.append("".join(current_definition).strip())
                current_definition = []
                continue
        current_definition.append(char)

    return [defn for defn in element_definitions if defn.strip()]


################################################################################
# Deferred Expression Numeric Literal Detection
################################################################################
# Matches plain decimal/exponential numeric literals only (e.g. '1.0', '-.5',
# '1.0e9'), never bare words like 'inf'/'nan' that Python's float() would
# otherwise silently accept as floating-point special values.
NUMERIC_LITERAL_PATTERN = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")

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
# Scalar Global Extraction
################################################################################
def _extract_scalar_global(section: str, keyword: str) -> str:
    """
    Strip a scalar global's keyword and all whitespace/assignment characters
    from its section, leaving the bare value text (e.g. 'momentum = 1.0 gev'
    with keyword 'momentum' -> '1.0gev').
    """
    value = section
    value = value.replace(keyword, "")
    value = value.replace("\n", "")
    value = value.replace("\t", "")
    value = value.replace(" ", "")
    value = value.replace("=", "")
    return value

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

def _split_sections_with_line_numbers(content: str) -> list[tuple[int, str]]:
    """
    Split semicolon-separated SAD content into sections, pairing each with the
    source line number it starts on so later parse errors can cite it.
    """
    def _append_section(text, first_line_no):
        # 'text' may begin with newlines carried over from the previous
        # section's terminator — count them so the reported line matches
        # where the section's own text actually begins, not one line early.
        leading_newlines = len(text) - len(text.lstrip("\n"))
        sections.append((first_line_no + leading_newlines, text))

    sections    = []
    line_no     = 1
    start_line  = 1
    chunk       = []

    for char in content:
        if char == ";":
            _append_section("".join(chunk), start_line)
            chunk       = []
            start_line  = line_no
            continue
        chunk.append(char)
        if char == "\n":
            line_no += 1

    _append_section("".join(chunk), start_line)

    return sections

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
    # Collapse " deg" / " rad" only when they are unit suffixes on a number,
    # not when "deg" or "rad" begins a parameter name (e.g. "radius", "degree").
    # The negative lookahead (?![a-z]) ensures we only match " rad" / " deg"
    # when the next character is NOT a letter — i.e. only at end-of-token.
    # A plain str.replace(" rad", "rad") would corrupt "3 radius" → "3radius",
    # which the element splitter then fails to parse correctly.
    content     = re.sub(r' deg(?![a-z])', 'deg', content)
    content     = re.sub(r' rad(?![a-z])', 'rad', content)

    ########################################
    # Split the file into sections
    ########################################
    # Semicolons are used to separate element sections. Track the original
    # source line each section starts on so parse errors can cite it.
    sections    = _split_sections_with_line_numbers(content)

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
    parsed_sections                 = []

    cleaned_globals                 = {}
    cleaned_elements                = {}
    cleaned_expressions             = {}
    cleaned_expression_line_numbers = {}
    cleaned_lines                   = {}

    ############################################################################
    # Load lattice and clean whitespace
    ############################################################################
    log_section_heading("Loading and Cleaning SAD File", mode = "section")

    sad_sections = load_and_clean_whitespace(sad_lattice_path)

    ############################################################################
    # Clean each different section of the file
    ############################################################################
    log_section_heading("Cleaning Element Sections", mode = "section")

    for line_no, section in sad_sections:
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
        # Output the cleaned section
        ########################################
        parsed_sections.append((line_no, current_section))

    ############################################################################
    # Remove SAD simulation commands
    ############################################################################
    # e.g. on rad, on cod, ffs use = ring, ffs[calc; go;]...
    for line_no, section in parsed_sections[:]:
        section_command = section.split()[0]

        if section_command == "on":
            parsed_sections.remove((line_no, section))
            continue

        if section_command == "off":
            parsed_sections.remove((line_no, section))
            continue

        # FFS is SAD's own interactive command interpreter (USE, CALCULATE,
        # GO, etc.) — sad2xs already knows which line to convert from its own
        # explicit line_name argument, so any FFS command is simulation-only
        # and safe to drop. Matches bare 'ffs;', 'ffs use = ring', and the
        # bracketed 'ffs[...]' command-string form.
        if section_command == "ffs" or section_command.startswith("ffs["):
            parsed_sections.remove((line_no, section))
            continue

    ############################################################################
    # Global Variables
    ############################################################################
    log_section_heading("Parsing Global Variables", mode = "section")

    for line_no, section in parsed_sections[:]:
        section_command = section.split()[0]

        ########################################
        # Momentum
        ########################################
        if section_command.split("=")[0] == "momentum":
            cleaned_globals["p0c"] = ev_text_to_float(
                _extract_scalar_global(section, "momentum"))
            parsed_sections.remove((line_no, section))
            continue

        ########################################
        # Mass
        ########################################
        if section_command.split("=")[0] == "mass":
            cleaned_globals["mass0"] = ev_text_to_float(
                _extract_scalar_global(section, "mass"))
            parsed_sections.remove((line_no, section))
            continue

        ########################################
        # Charge
        ########################################
        if section_command.split("=")[0] == "charge":
            cleaned_globals["q0"] = float(_extract_scalar_global(section, "charge"))
            parsed_sections.remove((line_no, section))
            continue

        ########################################
        # Frequency Shift
        ########################################
        if section_command.split("=")[0] == "fshift":
            cleaned_globals["fshift"] = float(_extract_scalar_global(section, "fshift"))
            parsed_sections.remove((line_no, section))
            continue

    ############################################################################
    # Lines
    ############################################################################
    log_section_heading("Parsing Lines", mode = "section")

    for line_no, section in parsed_sections[:]:
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
                    f"line {line_no}: Malformed LINE definition — unmatched "
                    f"parentheses ({open_count} opening, {close_count} closing): "
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
                            f"line {line_no}: Malformed LINE definition — "
                            f"multiple '=' found: '{line.strip()}'")
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

            parsed_sections.remove((line_no, section))
            continue

    ############################################################################
    # Elements
    ############################################################################
    log_section_heading("Parsing Elements", mode = "section")

    for line_no, section in parsed_sections[:]:
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
            elements    = _split_element_bodies(element_section, line_no)

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
                        f"line {line_no}: Element name '{ele_name}' collides with "
                        f"a protected SAD2XS reserved name. Choose a different "
                        f"element name.")

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
                try:
                    element_parameters = split_element_parameters(ele_vars)
                except ValueError as exc:
                    raise ValueError(f"line {line_no}: {exc}") from exc

                for var_name, var_value in element_parameters:

                    ########################################
                    # Angle handling
                    ########################################
                    # Use endswith to avoid matching "deg"/"rad" embedded in
                    # parameter names (e.g. "degree", "radius", "gradient").
                    if var_value.endswith("deg"):
                        var_value = np.deg2rad(float(var_value[:-3]))
                    elif var_value.endswith("rad"):
                        var_value = float(var_value[:-3])

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
                            f"line {line_no}: Element name '{ele_name}' is "
                            f"already defined as a '{other_type}' element. SAD "
                            f"does not allow reusing element names across "
                            f"different element types.")

                # Same-type redefinition follows SAD semantics: later wins
                if (ele_name in section_dict
                        or ele_name in cleaned_elements.get(section_command, {})):
                    logger.debug(
                        f"line {line_no}: Element {ele_name} redefined: "
                        "using the later definition")

                section_dict[ele_name] = ele_dict

            ########################################
            # Add elements
            ########################################
            if section_command in cleaned_elements:
                cleaned_elements[section_command].update(section_dict)
            else:
                cleaned_elements[section_command] = section_dict

            parsed_sections.remove((line_no, section))
            continue

    ############################################################################
    # Deferred expressions
    ############################################################################
    log_section_heading("Parsing Deferred Expressions", mode = "section")

    for line_no, section in parsed_sections[:]:
        section_command = section.split()[0]

        ########################################
        # If no equals sign, skip the section
        ########################################
        if "=" not in section:
            logger.warning(
                f"line {line_no}: Unknown section skipped during parsing: "
                f"{section.strip()!r}")

            parsed_sections.remove((line_no, section))
            continue

        ########################################
        # Reject SAD function definitions explicitly (':=') instead of
        # silently misparsing them as a garbage deferred expression.
        ########################################
        if ":=" in section:
            raise ValueError(
                f"line {line_no}: SAD function definitions ('name[args] := "
                f"expression') are not supported: '{section.strip()}'.")

        ########################################
        # Split information based on the equals sign
        ########################################
        try:
            variable, expression = section.split("=")
            expression = " ".join(expression.split())
        except ValueError:
            raise ValueError(
                f"line {line_no}: Error parsing section: {section}. "
                "Expected format 'name = expression'.")

        ########################################
        # Convert to Float if Possible
        ########################################
        # A strict numeric-literal regex (not bare float()) so that variable
        # references such as 'INF' or 'NAN' are never mistaken for the
        # floating-point special values Python's float() would parse them as.
        if NUMERIC_LITERAL_PATTERN.fullmatch(expression):
            cleaned_expressions[variable] = float(expression)
            cleaned_expression_line_numbers[variable] = line_no
            continue

        ########################################
        # Check if the expression is duplicated
        ########################################
        if variable not in cleaned_expressions:
            cleaned_expressions[variable] = expression
            cleaned_expression_line_numbers[variable] = line_no
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
            cleaned_expression_line_numbers[variable] = line_no
            continue

    ############################################################################
    # Address missing momentum and mass and charge
    ############################################################################
    if "mass0" not in cleaned_globals and config.ref_particle_mass0 is None:
        cleaned_globals["mass0"] = xt.ELECTRON_MASS_EV
        logger.warning(
            "No mass found in SAD file or function input: using electron mass")
    if "mass0" not in cleaned_globals:
        cleaned_globals["mass0"] = config.ref_particle_mass0
        logger.info("No mass found in SAD file: using user provided value")
    elif "mass0" in cleaned_globals and config.ref_particle_mass0 is not None:
        cleaned_globals["mass0"] = config.ref_particle_mass0
        logger.warning(
            "Mass found in both SAD file and function input: "
            "using user provided value")

    if "p0c" not in cleaned_globals and config.ref_particle_p0c is None:
        raise ValueError("No momentum found in SAD file or function input")
    if "p0c" not in cleaned_globals:
        cleaned_globals["p0c"] = config.ref_particle_p0c
        logger.info("No momentum found in SAD file: using user provided value")
    elif "p0c" in cleaned_globals and config.ref_particle_p0c is not None:
        cleaned_globals["p0c"] = config.ref_particle_p0c
        logger.warning(
            "Momentum found in both SAD file and function input: "
            "using user provided value")

    if "q0" not in cleaned_globals and config.ref_particle_q0 is None:
        cleaned_globals["q0"]   = +1
        logger.warning(
            "No charge found in SAD file or function input: using charge of +e")
    if "q0" not in cleaned_globals:
        cleaned_globals["q0"] = config.ref_particle_q0
        logger.info("No charge found in SAD file: using user provided value")
    elif "q0" in cleaned_globals and config.ref_particle_q0 is not None:
        cleaned_globals["q0"] = config.ref_particle_q0
        logger.warning(
            "Charge found in both SAD file and function input: "
            "using user provided value")

    if cleaned_globals["q0"] == 0:
        raise ValueError(
            "Reference particle charge (q0) is 0. A neutral reference "
            "particle is not physically meaningful for SAD2XS conversion.")

    if "fshift" not in cleaned_globals:
        cleaned_globals["fshift"]   = 0.0
        logger.info(
            "No fshift found in SAD file or function input: using fshift of 0.0")

    ############################################################################
    # Return the Parsed Data
    ############################################################################
    parsed_lattice_data = {
        "globals":                     cleaned_globals,
        "lines":                       cleaned_lines,
        "elements":                    cleaned_elements,
        "expressions":                 cleaned_expressions,
        "expression_line_numbers":     cleaned_expression_line_numbers}

    n_element_definitions = sum(
        len(family) for family in cleaned_elements.values())
    logger.info(
        f"Parsed {n_element_definitions} element definitions across "
        f"{len(cleaned_elements)} families, {len(cleaned_lines)} lines, "
        f"{len(cleaned_expressions)} deferred expressions")

    return parsed_lattice_data
