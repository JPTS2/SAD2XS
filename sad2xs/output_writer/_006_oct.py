"""
(Unofficial) SAD to XSuite Converter

Output Writer: Octupoles
"""

################################################################################
# Import Packages
################################################################################
from ._000_helpers import *

################################################################################
# Lattice File
################################################################################
def create_octupole_lattice_file_information(line, line_table):

    ########################################
    # Get information
    ########################################
    octs, unique_oct_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Octupole")

    oct_lengths    = np.array(sorted(octs.keys()))
    oct_names      = generate_magnet_for_replication_names(octs, "oct")

    ########################################
    # Ensure there are octupoles in the line
    ########################################
    if len(unique_oct_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = f"""
############################################################
# Octupoles
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += f"""
########################################
# Base Elements
########################################"""
    
    for oct_name, oct_length in zip(oct_names, oct_lengths):
        output_string += f"""
env.new(name = '{oct_name}', parent = xt.Octupole, length = {oct_length})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += f"""
########################################
# Cloned Elements
########################################"""

    for oct, oct_length in zip(oct_names, oct_lengths):
        for replica_name in octs[oct_length]:

            if check_is_simple_quad_sext_oct(line, replica_name, "Octupole"):

                if not check_is_skew_quad_sext_oct(line, replica_name, "Octupole"):
                    output_string += f"""
env.new(name = '{replica_name}', parent = '{oct}', k3 = 'k3_{replica_name}')"""
                else:
                    output_string += f"""
env.new(name = '{replica_name}', parent = '{oct}', k3s = 'k3s_{replica_name}')"""

            else:
                # Get the replica information
                k3          = line[replica_name].k3
                k3s         = line[replica_name].k3s
                shift_x     = line[replica_name].shift_x
                shift_y     = line[replica_name].shift_y
                rot_s_rad   = line[replica_name].rot_s_rad

                # Basic information
                oct_generation = f"""
env.new(
    name        = '{replica_name}',
    parent      = '{oct}'"""

                # Strength information
                if k3 != 0:
                    oct_generation += f""",
    k3          = 'k3_{replica_name}'"""
                if k3s != 0:
                    oct_generation += f""",
    k3s         = 'k3s_{replica_name}'"""

                # Misalignments
                if shift_x != 0:
                    oct_generation += f""",
    shift_x     = '{shift_x}'"""
                if shift_y != 0:
                    oct_generation += f""",
    shift_y     = '{shift_y}'"""
                if rot_s_rad != 0:
                    oct_generation += f""",
    rot_s_rad   = '{rot_s_rad}'"""

                # Close the element definition
                oct_generation += """)"""

                # Write to the file
                output_string += oct_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string

################################################################################
# Optics File
################################################################################
def create_octupole_optics_file_information(line, line_table):

    ########################################
    # Get information
    ########################################
    octs, unique_oct_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Octupole")
    
    ########################################
    # Ensure there are octupoles in the line
    ########################################
    if len(unique_oct_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string = f"""
    ############################################################
    # Octupoles
    ############################################################"""

    for oct in unique_oct_names:
        k3          = None
        k3s         = None

        if line[oct].k3 != 0:
            k3			= line[oct].k3
        if line[oct].k3s != 0:
            k3s			= line[oct].k3s

        if k3 is not None:
            output_string += f"""
    {f'k3_{oct}'}{' ' * (OUTPUT_STRING_SEP - len(f'k3_{oct}') + 4)}{'= '}{k3:.12f},"""
        if k3s is not None:
            output_string += f"""
    {f'k3s_{oct}'}{' ' * (OUTPUT_STRING_SEP - len(f'k3s_{oct}') + 4)}{'= '}{k3s:.12f},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
