"""
(Unofficial) SAD to XSuite Converter: Output Writer - Line
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-10-2025
"""

################################################################################
# Import Packages
################################################################################
import xtrack as xt
import xdeps as xd
import textwrap

from ._000_helpers import *
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_line_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:

    ########################################
    # Get allowed elements
    ########################################
    valid_elements  = line_table.rows[
        np.isin(line_table.element_type, list(config.ALLOWED_ELEMENTS))]

    ########################################
    # Get parent names
    ########################################
    parent_names    = []
    for element_name in valid_elements.name:
        parentname = get_parentname(element_name)
        parent_names.append(parentname)

    ########################################
    # Convert to single string
    ########################################
    line_string = parent_names
    line_string = str(line_string)[1:-1]

    ########################################
    # Write output
    ########################################
    output_string   = f"""
############################################################
# Create Line
############################################################
env.new_line(
    name        = 'line',
    components  = [
{textwrap.fill(
    text                = line_string,
    width               = config.OUTPUT_STRING_LENGTH,
    initial_indent      = '        ',
    subsequent_indent   = '        ',
    break_on_hyphens    = False)}])"""

    ########################################
    # Set line attributes
    ########################################
    output_string   += f"""
line = env.lines['line']
line.particle_ref = env.particle_ref.copy()"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
