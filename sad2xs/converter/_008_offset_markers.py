"""
(Unofficial) SAD to XSuite Converter: Offset Marker Converter
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-12-2025
"""

################################################################################
# Required Packages
################################################################################
import logging

import numpy as np
import xtrack as xt

from ._000_helpers import parse_expression

logger  = logging.getLogger(__name__)

################################################################################
# Conversion Function
################################################################################
def convert_offset_markers(
        line,
        parsed_lattice_data:    dict):
    """
    Markers in SAD have an offset parameter that is not replicated in Xsuite
    """

    ########################################
    # Get the required data
    ########################################
    parsed_elements = parsed_lattice_data["elements"]

    ########################################
    # Create output dictionary for the markers
    ########################################
    offset_marker_offsets   = {}

    ########################################
    # Get the offsets for each marker
    ########################################
    logger.debug("Calculating offset marker positions")

    # Markers in Xsuite can come from mark, moni or beam-beam elements
    for marker_type in ["mark", "moni", "beambeam"]:
        if marker_type in parsed_elements:
            for marker_name, marker in parsed_elements[marker_type].items():
                if "offset" in marker:
                    offset_marker_offsets[marker_name] = marker["offset"]

    ########################################
    # Return if there are no offset markers
    ########################################
    if len(offset_marker_offsets) == 0:
        logger.debug("No offset markers found")
        return line, {}

    ########################################
    # Get line table
    ########################################
    logger.debug("Getting line table")

    line.build_tracker()
    tt      = line.get_table(attr = True)
    line.discard_tracker()

    ########################################
    # Get the names of the inserted markers in the line
    ########################################
    inserted_markers    = list(tt.rows[tt.element_type == "Marker"].name)
    element_names       = list(tt.name)

    ########################################
    # Calculate intended marker locations
    ########################################
    offset_marker_locations = {}

    for marker in inserted_markers:

        base_marker     = marker.split("::")[0]

        if base_marker.startswith("-"):
            base_marker = base_marker[1:]

        ########################################
        # Only consider the offset markers
        ########################################
        if base_marker not in offset_marker_offsets:
            continue

        ########################################
        # Get the offset as a float
        ########################################
        offset  = offset_marker_offsets[base_marker]
        if isinstance(offset, str):
            # Resolve through the SAD variable scope in the line's environment
            # rather than bare eval(), which has no access to SAD variables
            # and executes arbitrary Python on lattice-file-derived input.
            offset = parse_expression(offset)
            if isinstance(offset, str):
                offset = line.env.eval(offset)

        ########################################
        # Case 1: Marker remains in the same element
        ########################################
        if 0 <= offset <= 1:
            marker_idx = element_names.index(marker)
            try:
                insert_at_ele   = element_names[marker_idx + 1]
                s_to_insert     = tt["s", insert_at_ele]
            except IndexError:  # Next element is the end of the line
                s_to_insert = tt.s[-1]
            except KeyError:    # Next element is a marker
                relative_idx = 1
                while True:
                    relative_idx += 1
                    try:
                        insert_at_ele   = element_names[marker_idx + relative_idx]
                        s_to_insert     = tt["s", insert_at_ele]
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
            insert_ele_length   = tt["length", insert_at_ele]

            # Add the fraction of element length
            s_to_insert     = tt["s", insert_at_ele] +\
                insert_ele_length * (offset % 1)

            ########################################
            # Exclude slicing solenoids
            ########################################
            if isinstance(line[insert_at_ele], xt.UniformSolenoid):
                logger.warning(
                    f"Offset marker {base_marker} not installed at "
                    f"s = {s_to_insert}: slicing solenoid elements "
                    "is not supported")
                continue

        # Produce a dictionary of the s locations that markers are inserted at
        if base_marker in offset_marker_locations:
            offset_marker_locations[base_marker].append(s_to_insert)
        else:
            offset_marker_locations[base_marker] = [s_to_insert]

    ############################################################################
    # Remove the offset markers
    ############################################################################
    removed_markers = []
    for marker in inserted_markers:
        base_marker     = marker.split("::")[0]
        if base_marker.startswith("-"):
            base_marker = base_marker[1:]
        if base_marker not in offset_marker_offsets:
            continue

        if base_marker not in removed_markers:
            line.remove(base_marker)
            removed_markers.append(base_marker)

    ############################################################################
    # Return line
    ############################################################################
    n_locations = sum(len(s_values) for s_values in offset_marker_locations.values())
    logger.info(
        f"Converted {len(offset_marker_locations)} offset markers "
        f"({n_locations} insertion points)")

    return line, offset_marker_locations
