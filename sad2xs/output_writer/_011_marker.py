"""
(Unofficial) SAD to XSuite Converter

Output Writer: Markers
"""

################################################################################
# Import Packages
################################################################################
import textwrap
from ._000_helpers import *

################################################################################
# Lattice File
################################################################################
def create_marker_lattice_file_information(line, line_table, offset_marker_locations):

    ########################################
    # Get normal marker information
    ########################################
    unique_marker_names    = []

    for marker in line_table.rows[line_table.element_type == 'Marker'].name:
        parentname  = get_parentname(marker)
        if parentname not in unique_marker_names:
            unique_marker_names.append(parentname)

    ########################################
    # Get offset marker information
    ########################################
    unique_offset_marker_names    = []

    for marker in offset_marker_locations.keys():
        parentname  = get_parentname(marker)
        if parentname not in unique_offset_marker_names:
            unique_offset_marker_names.append(parentname)

    ########################################
    # All markers
    ########################################
    unique_marker_names = sorted(list(set(unique_marker_names + unique_offset_marker_names)))

    ########################################
    # Ensure there are markers in the line
    ########################################
    if len(unique_marker_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = f"""
############################################################
# Markers
############################################################"""
        
    ########################################
    # Create elements
    ########################################
    output_string   += f"""
ALL_MARKERS = [
{textwrap.fill(
        text                = str(unique_marker_names)[1:-1],
        width               = OUTPUT_STRING_LENGTH,
        initial_indent      = '    ',
        subsequent_indent   = '    ',
        break_on_hyphens    = False)}]
for marker in ALL_MARKERS:
    env.new(name = marker, parent = xt.Marker)"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
