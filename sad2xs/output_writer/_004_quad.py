"""
(Unofficial) SAD to XSuite Converter: Output Writer - Quadrupoles
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-12-2025
"""

################################################################################
# Import Packages
################################################################################
import xtrack as xt
import xdeps as xd
import numpy as np

from ._000_helpers import extract_multipole_information, \
    generate_magnet_for_replication_names, check_is_simple_quad_sext_oct, \
    check_is_skew_quad_sext_oct
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_quadrupole_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Docstring for create_quadrupole_lattice_file_information
    
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
    quads, unique_quad_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Quadrupole")

    quad_lengths    = np.array(sorted(quads.keys()))
    quad_names      = generate_magnet_for_replication_names(quads, "quad")

    ########################################
    # Ensure there are quadrupoles in the line
    ########################################
    if len(unique_quad_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Quadrupoles
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += """
########################################
# Base Elements
########################################"""

    for quad_name, quad_length in zip(quad_names, quad_lengths):
        output_string += f"""
env.new(name = '{quad_name}', parent = xt.Quadrupole, length = {quad_length})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += """
########################################
# Cloned Elements
########################################"""

    for quad, quad_length in zip(quad_names, quad_lengths):
        for replica_name in quads[quad_length]:

            # Remove the minus sign if no non minus version exists
            if replica_name.startswith("-"):
                root_name   = replica_name[1:]
                if root_name not in quads[quad_length]:
                    replica_name        = root_name

            if check_is_simple_quad_sext_oct(line, replica_name, "Quadrupole"):

                if not check_is_skew_quad_sext_oct(line, replica_name, "Quadrupole"):
                    output_string += f"""
env.new(name = '{replica_name}', parent = '{quad}', k1 = 'k1_{replica_name}')"""
                else:
                    output_string += f"""
env.new(name = '{replica_name}', parent = '{quad}', k1s = 'k1s_{replica_name}')"""

            else:
                # Get the replica information
                k1          = line[replica_name].k1
                k1s         = line[replica_name].k1s
                shift_x     = line[replica_name].shift_x
                shift_y     = line[replica_name].shift_y
                rot_s_rad   = line[replica_name].rot_s_rad

                # Basic information
                quad_generation = f"""
env.new(
    name        = '{replica_name}',
    parent      = '{quad}'"""

                # Strength information
                if k1 != 0:
                    quad_generation += f""",
    k1          = 'k1_{replica_name}'"""
                if k1s != 0:
                    quad_generation += f""",
    k1s         = 'k1s_{replica_name}'"""

                # Misalignments
                if shift_x != 0:
                    quad_generation += f""",
    shift_x     = '{shift_x}'"""
                if shift_y != 0:
                    quad_generation += f""",
    shift_y     = '{shift_y}'"""
                if rot_s_rad != 0:
                    quad_generation += f""",
    rot_s_rad   = '{rot_s_rad}'"""

                # Close the element definition
                quad_generation += """)"""

                # Write to the file
                output_string += quad_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string

################################################################################
# Optics File
################################################################################
def create_quadrupole_optics_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Docstring for create_quadrupole_optics_file_information
    
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
    _, unique_quad_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Quadrupole")

    ########################################
    # Ensure there are quadrupoles in the line
    ########################################
    if len(unique_quad_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string = """
    ############################################################
    # Quadrupoles
    ############################################################"""

    for quad in unique_quad_names:
        k1          = None
        k1s         = None

        try:
            k1  = line[quad].k1
        except KeyError:
            try:
                k1  = line[f"-{quad}"].k1
            except KeyError:
                raise KeyError(f"Could not find quad variable {quad} or -{quad} in line.")

        try:
            k1s     = line[quad].k1s
        except KeyError:
            try:
                k1s = line[f"-{quad}"].k1s
            except KeyError:
                raise KeyError(f"Could not find quad variable {quad} or -{quad} in line.")

        if k1 == 0:
            k1 = None
        if k1s == 0:
            k1s = None

        if k1 is not None:
            output_string += f"""
    {f'k1_{quad}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'k1_{quad}') + 4)}{'= '}{k1:.24f},"""
        if k1s is not None:
            output_string += f"""
    {f'k1s_{quad}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'k1s_{quad}') + 4)}{'= '}{k1s:.24f},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
