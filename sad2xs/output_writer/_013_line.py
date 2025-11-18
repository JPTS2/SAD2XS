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
    # Account for the removal of unnecessary minus signs in other scripts
    ########################################
    minus_names = [name for name in parent_names if name.startswith('-')]
    for minus_name in minus_names:
        non_minus_name = minus_name[1:]
        if non_minus_name not in parent_names:
            # Correct all instances in the parent names list
            parent_names = [
                name if name != minus_name else non_minus_name
                for name in parent_names]

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
