"""
(Unofficial) SAD to XSuite Converter: Output Writer - Solenoids
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-12-2025
"""

################################################################################
# Import Packages
################################################################################
import textwrap
import xtrack as xt
import xdeps as xd
import numpy as np

from ._000_helpers import extract_multipole_information, \
    generate_magnet_for_replication_names, get_knl_string
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_solenoid_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Docstring for create_solenoid_lattice_file_information
    
    :param line: Description
    :type line: xt.Line
    :param line_table: Description
    :type line_table: xd.table.Table
    :param config: Description
    :type config: ConfigLike
    :return: Description
    :rtype: str
    """

    ########################################
    # Get information
    ########################################
    sols, unique_sol_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Solenoid")

    sol_lengths    = np.array(sorted(sols.keys()))
    sol_names      = generate_magnet_for_replication_names(sols, "sol")

    ########################################
    # Ensure there are solenoids in the line
    ########################################
    if len(unique_sol_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Solenoids
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += """
########################################
# Base Elements
########################################"""

    for sol_name, sol_length in zip(sol_names, sol_lengths):
        output_string += f"""
env.new(
    name                = '{sol_name}',
    parent              = xt.Solenoid,
    length              = {sol_length},
    order               = {config.MAX_KNL_ORDER})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += """
########################################
# Cloned Elements
########################################"""

    for sol, sol_length in zip(sol_names, sol_lengths):
        for replica_name in sols[sol_length]:

            # Get the replica information
            ks          = line[replica_name].ks
            knl         = get_knl_string(line[replica_name].knl)
            ksl         = get_knl_string(line[replica_name].ksl)
            shift_x     = line[replica_name].mult_shift_x
            shift_y     = line[replica_name].mult_shift_y
            rot_s_rad   = line[replica_name].rot_s_rad

            # Remove the minus sign if no non minus version exists
            if replica_name.startswith("-"):
                root_name   = replica_name[1:]
                if root_name not in sols[sol_length]:
                    replica_name        = root_name

            # Basic information
            sol_generation = f"""
env.new(
    name        = '{replica_name}',
    parent      = '{sol}'"""

            # Strength information
            if ks != 0:
                sol_generation += f""",
    ks          = {ks}"""
            if knl != "[]":
                sol_generation += f""",
{textwrap.fill(
    text                = f"knl         = {knl}",
    width               = config.OUTPUT_STRING_LENGTH,
    initial_indent      = '    ',
    subsequent_indent   = '        ',
    break_on_hyphens    = False)}"""
            if ksl != "[]":
                sol_generation += f""",
{textwrap.fill(
    text                = f"ksl         = {ksl}",
    width               = config.OUTPUT_STRING_LENGTH,
    initial_indent      = '    ',
    subsequent_indent   = '        ',
    break_on_hyphens    = False)}"""

            # Misalignments
            if shift_x != 0:
                sol_generation += f""",
    mult_shift_x     = '{shift_x}'"""
            if shift_y != 0:
                sol_generation += f""",
    mult_shift_y     = '{shift_y}'"""
            if rot_s_rad != 0:
                sol_generation += f""",
    rot_s_rad   = '{rot_s_rad}'"""

            # Close the element definition
            sol_generation += """)"""

            # Write to the file
            output_string += sol_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
