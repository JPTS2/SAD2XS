"""
(Unofficial) SAD to XSuite Converter: Output Writer - Offset Markers
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-16
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

    ########################################
    # Ensure there are offset markers in the line
    ########################################
    if len(list(offset_marker_locations.keys())) == 0:
        return ""

    ########################################
    # Set up output string
    ########################################
    output_string = '''
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
'''

    ########################################
    # Write offset marker locations
    ########################################
    # Open the dictionary
    output_string += """MARKER_POSITIONS = {"""

    for i, (offset_marker, insert_at_s_values) in enumerate(offset_marker_locations.items()):

        offset_marker           = get_parentname(offset_marker)
        insert_s_values_string  = "[" + ", ".join([f"{s:.12f}" for s in insert_at_s_values]) + "]"
        insertion_string        = f"""'{offset_marker}':{' ' * (config.OUTPUT_STRING_SEP - len(offset_marker) + 4)}{insert_s_values_string}"""

        if i == 0:
            output_string += f"""
{textwrap.fill(
    text                = insertion_string,
    width               = config.OUTPUT_STRING_LENGTH,
    initial_indent      = '    ',
    subsequent_indent   = '        ',
    break_on_hyphens    = False)}"""
        else:
            output_string += f""",
{textwrap.fill(
    text                = insertion_string,
    width               = config.OUTPUT_STRING_LENGTH,
    initial_indent      = '    ',
    subsequent_indent   = '        ',
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
            line.append_element(name = marker)
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
        f"Couldn't insert {len(missing_markers)} offset marker(s), usually "
        f"because of negative drifts: {missing_markers}")
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
