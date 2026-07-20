"""
================================================================================
User-Defined Element Exclusion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-20
================================================================================
"""

################################################################################
# Required Packages
################################################################################
import logging

logger  = logging.getLogger(__name__)

################################################################################
# Exclude particular elements
################################################################################
def exclude_elements(
        parsed_lattice_data:    dict,
        excluded_elements:      list[str] | None) -> dict:
    """
    Remove user-excluded elements from the parsed lattice data, in place.

    Matches both a name and its explicit reversal (a leading '-', SAD's
    own reversed-element marker) so an element excluded in one direction
    is also excluded in the other. Removed elements are dropped from
    every element-type dictionary and from every LINE's component list.

    Parameters
    ----------
    parsed_lattice_data : dict
        Parsed lattice data, as returned by `parse_sad_file`.
    excluded_elements : list of str or None
        Element names to exclude (case-insensitive). No-op if None or
        empty.

    Returns
    -------
    dict
        `parsed_lattice_data`, with excluded elements removed. The same
        object is returned and mutated in place.
    """

    ########################################
    # Check if there are excluded elements
    ########################################
    if excluded_elements is None or len(excluded_elements) == 0:
        logger.debug("No excluded elements found. Skipping exclusion.")
        return parsed_lattice_data

    ########################################
    # Parsed element/line names are lowercase; accept SAD's own (usually
    # uppercase) spelling too, rather than silently matching nothing.
    ########################################
    excluded_elements   = [elem.lower() for elem in excluded_elements]

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
    n_excluded  = 0
    for _, elems_dict in parsed_elements.items():
        # iterate over a snapshot of the keys
        for element in list(elems_dict.keys()):
            if element in excluded_elements:
                del elems_dict[element]
                n_excluded += 1
                logger.info(f"Element {element} excluded from conversion")

    ########################################
    # Delete the excluded elements from the lines dictionary
    ########################################
    for line, components in parsed_lines.items():
        parsed_lines[line] = [comp for comp in components if comp not in excluded_elements]

    logger.info(f"Excluded {n_excluded} element definitions")

    return parsed_lattice_data
