"""
================================================================================
Output Writer: Offset Markers
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
# Import Packages
################################################################################
import textwrap

from ._000_helpers import get_parentname
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_offset_marker_lattice_file_information(
        offset_marker_locations:    dict,
        config:                     ConfigLike) -> str:
    """
    Generate the lattice-file source re-inserting resolved offset
    markers at their computed s-positions.

    Writes a `MARKER_POSITIONS` dict (marker name -> list of
    s-positions), then, if `config._install_offset_markers` is set,
    installs each marker via `env.place`/`line.insert` -- or, if a
    marker's position is within `config.MARKER_INSERTION_TOLERANCE` of
    the line's end, via `line.append` instead, since
    `line.insert` cannot place an element exactly at the end. Any
    marker `line.insert` still fails to place is
    reported with a `print()` at runtime, naming exactly which markers
    were lost, rather than failing the whole reload silently.

    Parameters
    ----------
    offset_marker_locations : dict
        Resolved offset-marker insertion points, as returned by
        `sad2xs.converter._008_offset_markers.convert_offset_markers`.
    config : ConfigLike
        Converter configuration (`_install_offset_markers`,
        `MARKER_INSERTION_TOLERANCE`, `_replace_repeated_elements`,
        `OUTPUT_STRING_SEP`, `OUTPUT_STRING_LENGTH`).

    Returns
    -------
    str
        The generated Python source for this section, or "" if
        `offset_marker_locations` is empty.
    """

    ########################################
    # Ensure there are offset markers in the line
    ########################################
    if len(list(offset_marker_locations.keys())) == 0:
        return ""

    ########################################
    # Set up output string
    ########################################
    output_string = """
################################################################################
# Offset markers
################################################################################

############################################################
# Get length of the line
############################################################
length   = line.get_length()

############################################################
# Offset marker locations
############################################################
"""

    ########################################
    # Write offset marker locations
    ########################################
    # Open the dictionary
    output_string += """MARKER_POSITIONS = {"""

    for i, (offset_marker, insert_at_s_values) in enumerate(offset_marker_locations.items()):

        offset_marker           = get_parentname(offset_marker)
        insert_s_values_string  = "[" + ", ".join([f"{s:.12f}" for s in insert_at_s_values]) + "]"
        insertion_string        = f""""{offset_marker}":{" " * (config.OUTPUT_STRING_SEP - len(offset_marker) + 4)}{insert_s_values_string}"""

        if i == 0:
            output_string += f"""
{textwrap.fill(
    text                = insertion_string,
    width               = config.OUTPUT_STRING_LENGTH,
    initial_indent      = "    ",
    subsequent_indent   = "        ",
    break_on_hyphens    = False)}"""
        else:
            output_string += f""",
{textwrap.fill(
    text                = insertion_string,
    width               = config.OUTPUT_STRING_LENGTH,
    initial_indent      = "    ",
    subsequent_indent   = "        ",
    break_on_hyphens    = False)}"""

    # Close the dictionary
    output_string += """}"""
    output_string += "\n"

    ########################################
    # Write installation section
    ########################################
    if config._install_offset_markers:
        output_string += f"""
############################################################
# Install Markers
############################################################
marker_insertions   = []
attempted_markers   = []
for marker, insert_at_s_values in MARKER_POSITIONS.items():
    for insert_at_s in insert_at_s_values:
        if (length - insert_at_s) > {config.MARKER_INSERTION_TOLERANCE:.2E}:
            marker_insertions.append(
                env.place(name = marker, at = insert_at_s))
            attempted_markers.append(marker)
        else:
            line.append(marker)
try:
    line.insert(marker_insertions, s_tol = {config.MARKER_INSERTION_TOLERANCE:.2E})
except AssertionError as err:
"""
        # The generated file is a standalone script: report the data loss
        # unconditionally when it is run, naming the specific markers lost
        # so it's clear which comparisons downstream are missing them.
        output_string += """\
    missing_markers = sorted(set(attempted_markers) - set(line.element_names))
    print(
        f"Couldn't insert {len(missing_markers)} offset marker(s). Positions "
        "are checked for multiply-defined s before being written here, so "
        f"this is unexpected: {missing_markers}")
    print(err)
"""

        ########################################
        # Replace repeated elements
        ########################################
        if config._replace_repeated_elements:
            output_string += """
########################################
# Replace repeated elements
########################################
line.replace_all_repeated_elements()"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
