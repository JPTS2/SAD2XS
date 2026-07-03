"""
(Unofficial) SAD to XSuite Converter: User Defined Element Exclusion
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-12-2025
"""

################################################################################
# Required Packages
################################################################################
import logging

from ..helpers import log_section_heading

logger  = logging.getLogger(__name__)

################################################################################
# Exclude particular elements
################################################################################
def exclude_elements(
        parsed_lattice_data:    dict,
        excluded_elements:      list[str] | None) -> dict:
    """
    Docstring for exclude_elements

    :param parsed_lattice_data: Description
    :type parsed_lattice_data: dict
    :param excluded_elements: Description
    :type excluded_elements: list[str] | None
    :return: Description
    :rtype: dict[Any, Any]
    """

    ########################################
    # Check if there are excluded elements
    ########################################
    log_section_heading("Checking for Excluded Elements", mode = "subsection")
    if excluded_elements is None or len(excluded_elements) == 0:
        logger.debug("No excluded elements found. Skipping exclusion.")
        return parsed_lattice_data

    ########################################
    # When we exclude elements, need to exclude the reverse also
    ########################################
    excluded_elements   += [
        elem[1:] for elem in excluded_elements if elem.startswith("-")]
    excluded_elements   += [
        "-" + elem for elem in excluded_elements if not elem.startswith("-")]

    ########################################
    # Get the required data
    ########################################
    parsed_elements     = parsed_lattice_data["elements"]
    parsed_lines        = parsed_lattice_data["lines"]

    ########################################
    # Delete the excluded elements from the elements dictionary
    ########################################
    for _, elems_dict in parsed_elements.items():
        # iterate over a snapshot of the keys
        for element in list(elems_dict.keys()):
            if element in excluded_elements:
                del elems_dict[element]
                logger.info(f"Element {element} excluded from conversion")

    ########################################
    # Delete the excluded elements from the lines dictionary
    ########################################
    for line, components in parsed_lines.items():
        parsed_lines[line] = [comp for comp in components if comp not in excluded_elements]

    return parsed_lattice_data
