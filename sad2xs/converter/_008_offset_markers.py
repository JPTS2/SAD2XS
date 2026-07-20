"""
================================================================================
Offset Marker Converter
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
    Resolve SAD MARK/MONI/BEAMBEAM OFFSET positions into insertion
    points.

    SAD's OFFSET parameter places a marker at a fractional position
    relative to its own nominal location: 0 <= OFFSET <= 1 leaves it
    in place (a no-op, confirmed against real SAD); any other value
    moves it into a neighbouring element, at
    s = (that element's start) + (that element's length) *
    (OFFSET mod 1), where the neighbouring element is floor(OFFSET)
    positions away. A reversed reference walks OFFSET in the opposite
    direction (1 - OFFSET). Offset markers whose target element is a
    UniformSolenoid are left in place with a warning, since slicing a
    solenoid is not supported. Every offset marker that does move is
    removed from `line` here -- the moved positions are only
    re-inserted later, when the lattice file is generated (see
    `sad2xs.output_writer._015_offset_markers`); `line` itself never
    gets them back.

    Parameters
    ----------
    line : xt.Line
        The converted line to resolve and remove offset markers from.
    parsed_lattice_data : dict
        Parsed lattice data, as returned by `parse_sad_file`.

    Returns
    -------
    tuple of (xt.Line, dict)
        `(line, offset_marker_locations)`, where
        `offset_marker_locations` maps each moved marker's base name
        to a list of s-positions it should be re-inserted at.
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
    unmoved_markers         = set()

    for marker in inserted_markers:

        base_marker     = marker.split("::")[0]

        reversed_marker = base_marker.startswith("-")
        if reversed_marker:
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

        # A reversed reference walks OFFSET in the opposite direction: the
        # marker's own "forward" is global-backward.
        if reversed_marker:
            offset = 1 - offset

        ########################################
        # Case 1: Marker stays at its own nominal position (confirmed
        # against real SAD: 0 <= OFFSET <= 1 never moves or splits anything)
        ########################################
        if 0 <= offset <= 1:
            unmoved_markers.add(base_marker)
            continue

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
        lookup_marker   = base_marker[1:] if base_marker.startswith("-") else base_marker
        if lookup_marker not in offset_marker_offsets or lookup_marker in unmoved_markers:
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

    # `line` never gets these markers back -- only the generated lattice
    # file's "Install Markers" step re-adds them.
    if offset_marker_locations:
        logger.warning(
            f"{len(offset_marker_locations)} relocated offset marker(s) are "
            "absent from the returned line (present only in the generated "
            f"lattice file): {sorted(offset_marker_locations)}")

    return line, offset_marker_locations
