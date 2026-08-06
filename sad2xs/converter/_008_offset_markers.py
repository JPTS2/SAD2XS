"""
================================================================================
Offset Marker Converter
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-29
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
# SAD-native line flattening
#
# "floor(OFFSET) positions forward" must be counted on SAD's own element
# sequence, not the post-conversion Xsuite table: one SAD element can
# become several Xsuite ones (quad fringe, RF-carrying MULT slices),
# which would silently count sub-pieces instead of real SAD elements.
################################################################################
def _flatten_sad_line_elements(
        line_name:      str,
        parsed_lines:   dict[str, list[str]]) -> list[str]:
    """
    Expand a parsed SAD LINE into its flat, ordered leaf-element
    sequence -- SAD's own element numbering.

    Resolves nested LINE-of-LINEs recursively; "-SUBLINE" reverses both
    the order and the sign of every leaf in its expansion. A leaf's own
    "-" sign is otherwise kept, not dropped: `create_reversed_component`
    names a reversed clone "-name" (not a "::N" replica), so the sign
    must survive to tell a forward and reversed reference apart.

    Assumes `parsed_lines` is unmutated by `convert_lines`
    (`_005_line_converter.py` works on a local copy) -- so this never
    sees the generated quad-fringe/solenoid sub-lines it builds.

    Parameters
    ----------
    line_name : str
        The (lowercase) name of the line to expand.
    parsed_lines : dict
        `parsed_lattice_data["lines"]`: line name -> ordered component
        list, as returned by `parse_sad_file`.

    Returns
    -------
    list of str
        The flat, ordered sequence of leaf element names, each
        optionally "-"-prefixed.
    """
    flat_names = []
    for token in parsed_lines[line_name]:
        is_reversed_ref = token.startswith("-")
        base_name       = token[1:] if is_reversed_ref else token

        if base_name in parsed_lines:
            sub_names = _flatten_sad_line_elements(base_name, parsed_lines)
            if is_reversed_ref:
                sub_names = [
                    name[1:] if name.startswith("-") else f"-{name}"
                    for name in reversed(sub_names)]
            flat_names.extend(sub_names)
        else:
            flat_names.append(token)

    return flat_names

def _element_length(name: str, parsed_elements: dict, line: xt.Line) -> float:
    """
    Look up a SAD element's own declared length ("L"), resolved the
    same way OFFSET is resolved elsewhere in this file. Elements with
    no "l" parameter (markers, thin correctors, ...) are zero-length.

    Parameters
    ----------
    name : str
        The (lowercase) SAD element name, optionally "-"-prefixed
        (from `_flatten_sad_line_elements`) -- a reversed clone has
        the same length as the element it was cloned from.
    parsed_elements : dict
        `parsed_lattice_data["elements"]`.
    line : xt.Line
        Only used to resolve a length given as a SAD variable
        expression, via `line.env.eval(...)`.

    Returns
    -------
    float
        The element's length, in metres.
    """
    name = name[1:] if name.startswith("-") else name
    for elements_of_type in parsed_elements.values():
        if name in elements_of_type:
            ele_vars = elements_of_type[name]
            if "l" not in ele_vars:
                return 0.0
            length = parse_expression(ele_vars["l"])
            if isinstance(length, str):
                length = line.env.eval(length)
            return length
    return 0.0

def _regions_of_multiply_defined_s(
        cumulative_s: np.ndarray) -> list[tuple[float, float]]:
    """
    Regions of s that more than one element occupies.

    A negative-length element makes the s table non-monotonic. The elements
    after it then cover s that an earlier element already covered. Each such
    region is found by comparing every element's start against the largest s
    reached so far. The lengths come from SAD's own sequence, not from the
    converted line.

    Parameters
    ----------
    cumulative_s : np.ndarray
        Cumulative s at each element boundary, length `n_elements + 1`.

    Returns
    -------
    list of tuple
        `(start, end)` of each region, in s order.
    """
    regions         = []
    furthest_s      = cumulative_s[0]

    for index in range(len(cumulative_s) - 1):
        start, end  = cumulative_s[index], cumulative_s[index + 1]
        if start < furthest_s:
            regions.append((float(start), float(min(end, furthest_s))))
        furthest_s  = max(furthest_s, end)

    return regions


################################################################################
# Conversion Function
################################################################################
def convert_offset_markers(
        line:                   xt.Line,
        parsed_lattice_data:    dict,
        line_name:              str,
        reverse_element_order:  bool            = False) -> tuple[xt.Line, dict[str, list[float]]]:
    """
    Resolve SAD MARK/MONI/BEAMBEAM OFFSET positions into insertion
    points.

    SAD's OFFSET places a marker at a fractional position relative to
    its own nominal location: 0 <= OFFSET <= 1 is a no-op (confirmed
    against real SAD); otherwise it moves floor(OFFSET) positions
    forward (SAD's own declared sequence, from `_flatten_sad_line_elements`,
    not the post-conversion Xsuite table -- one SAD element can become
    several Xsuite ones) and lands at (OFFSET mod 1) through that
    element. A reversed reference (`-NAME`) walks OFFSET in the
    opposite direction (1 - OFFSET).

    `reverse_element_order=True` mirrors `line` before this function
    runs (`reverse_line_element_order`) but never touches
    `parsed_lattice_data`, so the target is still found by walking
    SAD's forward-declared sequence (OFFSET's "N positions forward" is
    physical adjacency in the declared lattice, not travel direction);
    the resulting s is then mirrored the same way `line.mirror()`
    mirrors everything else: s -> (total length) - s. Cross-checked
    against SAD's native `-LINE` reversal, which gives an identical
    offset-marker s.

    No element type is excluded as a target. A marker is skipped for
    one reason only: a negative-length element makes two elements cover
    its s, so the position does not name a unique insertion point.
    These regions come from SAD's own cumulative lengths. Finding them
    here keeps an unplaceable marker out of the generated file's single
    batched insertion, where one failure would cost every other marker.

    Every moved marker (skipped or not) is removed from `line` here; a
    surviving one is only re-inserted later, when the lattice file is
    generated (`sad2xs.output_writer._016_offset_markers`) -- `line`
    itself never gets it back.

    Parameters
    ----------
    line : xt.Line
        The converted line to resolve and remove offset markers from.
    parsed_lattice_data : dict
        Parsed lattice data, as returned by `parse_sad_file`.
    line_name : str
        The (lowercase) name of the line being converted, as selected
        in `main.py` (explicit `line_name` or the auto-selected
        longest line) -- the line `_flatten_sad_line_elements` expands.
    reverse_element_order : bool, optional
        Whether `line`'s element order has already been mirrored (see
        `reverse_line_element_order`). Defaults to False.

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
    # SAD's own flat element sequence, and cumulative length along it
    # -- the ground truth for "floor(OFFSET) positions forward", fully
    # independent of how any element is represented in Xsuite.
    ########################################
    sad_sequence    = _flatten_sad_line_elements(line_name, parsed_lattice_data["lines"])
    sad_lengths     = [_element_length(name, parsed_elements, line) for name in sad_sequence]
    cumulative_s    = np.concatenate(([0.0], np.cumsum(sad_lengths)))

    ########################################
    # Get line table -- for the literal Xsuite marker names (with any
    # "::N" replica or "-" reversal sign) so the right ones get removed
    # from `line` at the end; not used for the position calculation.
    ########################################
    logger.debug("Getting line table")

    line.build_tracker()
    tt      = line.get_table(attr = True)
    line.discard_tracker()

    ########################################
    # Get the names of the inserted markers in the line
    ########################################
    inserted_markers    = list(tt.rows[tt.element_type == "Marker"].name)

    ########################################
    # Calculate intended marker locations
    ########################################
    offset_marker_locations = {}
    unmoved_markers         = set()
    skipped_markers         = []

    # Found once from SAD's own lengths, before any insertion is attempted.
    ambiguous_regions       = _regions_of_multiply_defined_s(cumulative_s)
    if ambiguous_regions:
        logger.debug(
            f"{len(ambiguous_regions)} region(s) of multiply-defined s, from "
            f"negative-length elements: {ambiguous_regions}")

    for marker in inserted_markers:

        marker_parts    = marker.split("::")
        # Keeps any "-" sign -- a per-element-reversed clone (e.g. "-m")
        # is `sad_sequence`'s own lookup key, distinct from the "::N"
        # replica suffix Xsuite gives a same-sign repeated element.
        signed_marker   = marker_parts[0]
        replica_index   = int(marker_parts[1]) if len(marker_parts) > 1 else 0

        reversed_marker = signed_marker.startswith("-")
        base_marker     = signed_marker[1:] if reversed_marker else signed_marker

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
            relative_idx    = int(np.floor(offset))

            # `signed_marker` (not `base_marker`) is the lookup key: a
            # per-element-reversed clone is a distinct "-"-prefixed
            # entry in `sad_sequence`, not a numbered replica of the
            # forward one -- `base_marker` would find the wrong
            # occurrence for a reversed reference.
            occurrences     = [
                i for i, name in enumerate(sad_sequence) if name == signed_marker]
            marker_idx      = occurrences[replica_index]
            target_idx      = marker_idx + relative_idx
            target_name     = sad_sequence[target_idx]
            target_length   = sad_lengths[target_idx]

            # Add the fraction of element length
            s_to_insert     = cumulative_s[target_idx] +\
                target_length * (offset % 1)

            # `line` was already mirrored (reverse_line_element_order,
            # _007_reversals.py) before this function runs -- carry the
            # target across the same s -> (total length) - s transform.
            if reverse_element_order:
                s_to_insert = cumulative_s[-1] - s_to_insert

            ########################################
            # Skip markers landing where s is defined twice
            ########################################
            region = next(
                ((start, end) for start, end in ambiguous_regions
                 if start <= s_to_insert <= end), None)
            if region is not None:
                skipped_markers.append(base_marker)
                logger.debug(
                    f"Offset marker {base_marker} resolves to s = "
                    f"{s_to_insert} in target {target_name}. Two elements "
                    f"cover s from {region[0]} to {region[1]}, so this "
                    "position does not name a unique insertion point.")
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

    # A relocated marker belongs only in the generated lattice file, so this is
    # progress information, not a warning. The names go to DEBUG because on a
    # real lattice the list runs to dozens.
    if offset_marker_locations:
        logger.info(
            f"{len(offset_marker_locations)} relocated offset marker(s) are "
            "present only in the generated lattice file, not the returned line")
        logger.debug(
            f"Relocated offset markers: {sorted(offset_marker_locations)}")

    # Skipping a requested marker loses data, so it warns. The count goes here,
    # the names to DEBUG, and each marker's own reason is logged above.
    if skipped_markers:
        logger.warning(
            f"{len(skipped_markers)} offset marker(s) were not placed: their "
            "positions fall where a negative-length element makes s "
            "multiply-defined")
        logger.debug(f"Skipped offset markers: {sorted(set(skipped_markers))}")

    return line, offset_marker_locations
