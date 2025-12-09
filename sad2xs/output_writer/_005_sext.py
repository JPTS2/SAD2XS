"""
(Unofficial) SAD to XSuite Converter: Output Writer - Sextupoles
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
import numpy as np

from ._000_helpers import extract_multipole_information, \
    generate_magnet_for_replication_names, check_is_simple_quad_sext_oct, \
    check_is_skew_quad_sext_oct
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_sextupole_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Docstring for create_sextupole_lattice_file_information
    
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
    sexts, unique_sext_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Sextupole")

    sext_lengths    = np.array(sorted(sexts.keys()))
    sext_names      = generate_magnet_for_replication_names(sexts, "sext")

    ########################################
    # Ensure there are sextupoles in the line
    ########################################
    if len(unique_sext_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Sextupoles
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += """
########################################
# Base Elements
########################################"""

    for sext_name, sext_length in zip(sext_names, sext_lengths):
        output_string += f"""
env.new(name = '{sext_name}', parent = xt.Sextupole, length = {sext_length})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += """
########################################
# Cloned Elements
########################################"""

    for sext, sext_length in zip(sext_names, sext_lengths):
        for replica_name in sexts[sext_length]:

            # Remove the minus sign if no non minus version exists
            if replica_name.startswith("-"):
                root_name   = replica_name[1:]
                if root_name not in sexts[sext_length]:
                    replica_name        = root_name

            if check_is_simple_quad_sext_oct(line, replica_name, "Sextupole"):

                if not check_is_skew_quad_sext_oct(line, replica_name, "Sextupole"):
                    output_string += f"""
env.new(name = '{replica_name}', parent = '{sext}', k2 = 'k2_{replica_name}')"""
                else:
                    output_string += f"""
env.new(name = '{replica_name}', parent = '{sext}', k2s = 'k2s_{replica_name}')"""

            else:
                # Get the replica information
                k2          = line[replica_name].k2
                k2s         = line[replica_name].k2s
                shift_x     = line[replica_name].shift_x
                shift_y     = line[replica_name].shift_y
                rot_s_rad   = line[replica_name].rot_s_rad

                # Basic information
                sext_generation = f"""
env.new(
    name        = '{replica_name}',
    parent      = '{sext}'"""

                # Strength information
                if k2 != 0:
                    sext_generation += f""",
    k2          = 'k2_{replica_name}'"""
                if k2s != 0:
                    sext_generation += f""",
    k2s         = 'k2s_{replica_name}'"""

                # Misalignments
                if shift_x != 0:
                    sext_generation += f""",
    shift_x     = '{shift_x}'"""
                if shift_y != 0:
                    sext_generation += f""",
    shift_y     = '{shift_y}'"""
                if rot_s_rad != 0:
                    sext_generation += f""",
    rot_s_rad   = '{rot_s_rad}'"""

                # Close the element definition
                sext_generation += """)"""

                # Write to the file
                output_string += sext_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string

################################################################################
# Optics File
################################################################################
def create_sextupole_optics_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Docstring for create_sextupole_optics_file_information
    
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
    _, unique_sext_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Sextupole")

    ########################################
    # Ensure there are sextupoles in the line
    ########################################
    if len(unique_sext_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string = """
    ############################################################
    # Sextupoles
    ############################################################"""

    for sext in unique_sext_names:
        k2          = None
        k2s         = None

        try:
            k2  = line[sext].k2
        except KeyError:
            try:
                k2  = line[f"-{sext}"].k2
            except KeyError:
                raise KeyError(f"Could not find sext variable {sext} or -{sext} in line.")

        try:
            k2s     = line[sext].k2s
        except KeyError:
            try:
                k2s = line[f"-{sext}"].k2s
            except KeyError:
                raise KeyError(f"Could not find sext variable {sext} or -{sext} in line.")

        if k2 == 0:
            k2 = None
        if k2s == 0:
            k2s = None

        if k2 is not None:
            output_string += f"""
    {f'k2_{sext}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'k2_{sext}') + 4)}{'= '}{k2:.24f},"""
        if k2s is not None:
            output_string += f"""
    {f'k2s_{sext}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'k2s_{sext}') + 4)}{'= '}{k2s:.24f},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
