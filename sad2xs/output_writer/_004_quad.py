"""
(Unofficial) SAD to XSuite Converter

Output Writer: Quadrupoles
"""

################################################################################
# Import Packages
################################################################################
from ._000_helpers import *

################################################################################
# Lattice File
################################################################################
def create_quadrupole_lattice_file_information(line, line_table):

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
    output_string   = f"""
############################################################
# Quadrupoles
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += f"""
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
    output_string += f"""
########################################
# Cloned Elements
########################################"""

    for quad, quad_length in zip(quad_names, quad_lengths):
        for replica_name in quads[quad_length]:

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
def create_quadrupole_optics_file_information(line, line_table):

    ########################################
    # Get information
    ########################################
    quads, unique_quad_names = extract_multipole_information(
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
    output_string = f"""
    ############################################################
    # Quadrupoles
    ############################################################"""

    for quad in unique_quad_names:
        k1          = None
        k1s         = None

        if line[quad].k1 != 0:
            k1			= line[quad].k1
        if line[quad].k1s != 0:
            k1s			= line[quad].k1s

        if k1 is not None:
            output_string += f"""
    {f'k1_{quad}'}{' ' * (OUTPUT_STRING_SEP - len(f'k1_{quad}') + 4)}{'= '}{k1:.12f},"""
        if k1s is not None:
            output_string += f"""
    {f'k1s_{quad}'}{' ' * (OUTPUT_STRING_SEP - len(f'k1s_{quad}') + 4)}{'= '}{k1s:.12f},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
