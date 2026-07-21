"""
================================================================================
Output Writer: Markers
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
# Import Packages
################################################################################
import textwrap
import xdeps as xd

from ._000_helpers import get_parentname
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_marker_lattice_file_information(
        line_table:                 xd.table.Table,
        offset_marker_locations:    dict | None,
        config:                     ConfigLike) -> str:
    """
    Generate the lattice-file source for every Marker element (MARK,
    MONI, BEAMBEAM, and any relocated offset markers).

    All marker names are collected into a single `ALL_MARKERS` list
    and installed in one loop, rather than one `env.new(...)` call
    per marker, since markers carry no parameters to differentiate
    them. Offset markers (whose target insertion points were resolved
    by `convert_offset_markers`) are included here even though they
    were removed from the in-memory line -- they get their real
    positions from
    `sad2xs.output_writer._015_offset_markers.create_offset_marker_lattice_file_information`
    later in the file; this section only needs to declare them to
    exist.

    Parameters
    ----------
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    offset_marker_locations : dict or None
        Resolved offset-marker insertion points, as returned by
        `sad2xs.converter._008_offset_markers.convert_offset_markers`.
    config : ConfigLike
        Converter configuration; only `OUTPUT_STRING_LENGTH` is used.

    Returns
    -------
    str
        The generated Python source for this section, or "" if the
        line has no markers (including offset markers).
    """

    ########################################
    # Get normal marker information
    ########################################
    unique_marker_names    = []

    for marker in line_table.rows[line_table.element_type == "Marker"].name:
        parentname  = get_parentname(marker)
        if parentname not in unique_marker_names:
            unique_marker_names.append(parentname)

    ########################################
    # Get offset marker information
    ########################################
    if offset_marker_locations is not None:
        unique_offset_marker_names    = []

        for marker in offset_marker_locations.keys():
            parentname  = get_parentname(marker)
            if parentname not in unique_offset_marker_names:
                unique_offset_marker_names.append(parentname)

        unique_marker_names = sorted(list(set(
            unique_marker_names + unique_offset_marker_names)))

    ########################################
    # Ensure there are markers in the line
    ########################################
    if len(unique_marker_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Markers
############################################################"""

    ########################################
    # Create elements
    ########################################
    output_string   += f"""
ALL_MARKERS = [
{textwrap.fill(
        text                = ", ".join(f"\"{name}\"" for name in unique_marker_names),
        width               = config.OUTPUT_STRING_LENGTH,
        initial_indent      = "    ",
        subsequent_indent   = "    ",
        break_on_hyphens    = False)}]
for marker in ALL_MARKERS:
    env.new(name = marker, prototype = xt.Marker)"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
