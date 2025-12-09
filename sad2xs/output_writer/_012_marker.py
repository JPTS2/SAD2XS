"""
(Unofficial) SAD to XSuite Converter: Output Writer - Markers
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-12-2025
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
    Docstring for create_marker_lattice_file_information
    
    :param line_table: Description
    :type line_table: xd.table.Table
    :param offset_marker_locations: Description
    :type offset_marker_locations: dict | None
    :param config: Description
    :type config: ConfigLike
    :return: Description
    :rtype: str
    """

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
        text                = str(unique_marker_names)[1:-1],
        width               = config.OUTPUT_STRING_LENGTH,
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
