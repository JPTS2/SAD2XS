"""
(Unofficial) SAD to XSuite Converter

Output Writer: Drifts
"""

################################################################################
# Import Packages
################################################################################
from ._000_helpers import *

################################################################################
# Lattice File
################################################################################
def create_drift_lattice_file_information(line, line_table):

    ########################################
    # Get unique drifts
    ########################################
    unique_drift_names      = []
    for drift in line_table.rows[line_table.element_type == 'Drift'].name:
        parentname  = get_parentname(drift)
        if parentname not in unique_drift_names:
            unique_drift_names.append(parentname)

    ########################################
    # Ensure there are drifts in the line
    ########################################
    if len(unique_drift_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = f"""
############################################################
# Drifts
############################################################"""

    ########################################
    # Create Drifts
    ########################################
    for drift in unique_drift_names:
        length          = line[drift].length
        output_string   += f"""
env.new(name = '{drift}', parent = xt.Drift, length = {length})"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
