"""
(Unofficial) SAD to XSuite Converter

Output Writer: Bends
"""

################################################################################
# Import Packages
################################################################################
from ._000_helpers import *

################################################################################
# Lattice File
################################################################################
def create_bend_lattice_file_information(line, line_table):

    ########################################
    # Get information
    ########################################
    hbends, vbends, sbends, unique_bend_variables, bend_name_dict = extract_bend_information(line, line_table)
    
    hbend_lengths       = np.array(sorted(hbends.keys()))
    hbend_names         = generate_magnet_for_replication_names(hbends, "hbend")
    vbend_lengths       = np.array(sorted(vbends.keys()))
    vbend_names         = generate_magnet_for_replication_names(vbends, "vbend")
    sbend_lengths       = np.array(sorted(sbends.keys()))
    sbend_names         = generate_magnet_for_replication_names(sbends, "sbend")

    ########################################
    # Ensure there are bends in the line
    ########################################
    if len(hbend_names) == 0 and len(vbend_names) == 0 and len(sbend_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = f"""
############################################################
# Bends
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += f"""
########################################
# Base Elements
########################################"""

    for hbend_name, hbend_length in zip(hbend_names, hbend_lengths):
        output_string += f"""
env.new(name = '{hbend_name}', parent = xt.Bend, length = {hbend_length})"""

    for vbend_name, vbend_length in zip(vbend_names, vbend_lengths):
        output_string += f"""
env.new(name = '{vbend_name}', parent = xt.Bend, length = {vbend_length}, rot_s_rad = +np.pi/2)"""

    for sbend_name, sbend_length in zip(sbend_names, sbend_lengths):
        output_string += f"""
env.new(name = '{sbend_name}', parent = xt.Bend, length = {sbend_length})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += f"""
########################################
# Cloned Elements
########################################"""

    for hbend, hbend_length in zip(hbend_names, hbend_lengths):
        for replica_name in hbends[hbend_length]:
            replica_variable    = bend_name_dict[replica_name]

            # If simple try to make it more compact
            if check_is_simple_bend_corr(line, replica_name):
                bend_generation = f"""
env.new(name = '{replica_name}', parent = '{hbend}', k0 = 'k0_{replica_variable}', h = {line[replica_name].h})"""

            # Otherwise do the full version
            else:
                bend_generation = f"""
env.new(
    name                    = '{replica_name}',
    parent                  = '{hbend}',
    k0                      = 'k0_{replica_variable}',
    h                       = {line[replica_name].h}"""
            # Append edge entry angles
                if line[replica_name].edge_entry_angle != 0:
                    bend_generation += f""",
    edge_entry_angle        = {line[replica_name].edge_entry_angle}"""
                if line[replica_name].edge_exit_angle != 0:
                    bend_generation += f""",
    edge_exit_angle         = {line[replica_name].edge_exit_angle}"""
                if line[replica_name].edge_entry_angle_fdown != 0:
                    bend_generation += f""",
    edge_entry_angle_fdown  = {line[replica_name].edge_entry_angle_fdown}"""
                if line[replica_name].edge_exit_angle_fdown != 0:
                    bend_generation += f""",
    edge_exit_angle_fdown   = {line[replica_name].edge_exit_angle_fdown}"""
                # Append shifts if they exist
                if line[replica_name].shift_x != 0:
                    bend_generation += f""",
    shift_x                 = '{line[replica_name].shift_x}'"""
                if line[replica_name].shift_y != 0:
                    bend_generation += f""",
    shift_y                 = '{line[replica_name].shift_y}'"""
                # Append the missing parenthesis
                bend_generation += """)"""
            
            # Write to the file
            output_string += bend_generation


    for vbend, vbend_length in zip(vbend_names, vbend_lengths):
        for replica_name in vbends[vbend_length]:
            replica_variable    = bend_name_dict[replica_name]

            # If simple try to make it more compact
            if check_is_simple_bend_corr(line, replica_name):
                bend_generation = f"""
env.new(name = '{replica_name}', parent = '{vbend}', k0 = 'k0_{replica_variable}', h = {line[replica_name].h})"""

            # Otherwise do the full version
            else:
                bend_generation = f"""
env.new(
    name                    = '{replica_name}',
    parent                  = '{vbend}',
    k0                      = 'k0_{replica_variable}',
    h                       = {line[replica_name].h}"""
            # Append edge entry angles
                if line[replica_name].edge_entry_angle != 0:
                    bend_generation += f""",
    edge_entry_angle        = {line[replica_name].edge_entry_angle}"""
                if line[replica_name].edge_exit_angle != 0:
                    bend_generation += f""",
    edge_exit_angle         = {line[replica_name].edge_exit_angle}"""
                if line[replica_name].edge_entry_angle_fdown != 0:
                    bend_generation += f""",
    edge_entry_angle_fdown  = {line[replica_name].edge_entry_angle_fdown}"""
                if line[replica_name].edge_exit_angle_fdown != 0:
                    bend_generation += f""",
    edge_exit_angle_fdown   = {line[replica_name].edge_exit_angle_fdown}"""
                # Append shifts if they exist
                if line[replica_name].shift_x != 0:
                    bend_generation += f""",
    shift_x                 = '{line[replica_name].shift_x}'"""
                if line[replica_name].shift_y != 0:
                    bend_generation += f""",
    shift_y                 = '{line[replica_name].shift_y}'"""
                # Append the missing parenthesis
                bend_generation += """)"""
            
            # Write to the file
            output_string += bend_generation

    for sbend, sbend_length in zip(sbend_names, sbend_lengths):
        for replica_name in sbends[sbend_length]:
            replica_variable    = bend_name_dict[replica_name]

            # If simple try to make it more compact
            if check_is_simple_bend_corr(line, replica_name):
                bend_generation = f"""
env.new(name = '{replica_name}', parent = '{sbend}', k0 = 'k0_{replica_variable}', h = {line[replica_name].h}, rot_s_rad = '{line[replica_name].rot_s_rad}')"""

            # Otherwise do the full version
            else:
                bend_generation = f"""
env.new(
    name                    = '{replica_name}',
    parent                  = '{sbend}',
    k0                      = 'k0_{replica_variable}',
    h                       = {line[replica_name].h}"""
            # Append edge entry angles
                if line[replica_name].edge_entry_angle != 0:
                    bend_generation += f""",
    edge_entry_angle        = {line[replica_name].edge_entry_angle}"""
                if line[replica_name].edge_exit_angle != 0:
                    bend_generation += f""",
    edge_exit_angle         = {line[replica_name].edge_exit_angle}"""
                if line[replica_name].edge_entry_angle_fdown != 0:
                    bend_generation += f""",
    edge_entry_angle_fdown  = {line[replica_name].edge_entry_angle_fdown}"""
                if line[replica_name].edge_exit_angle_fdown != 0:
                    bend_generation += f""",
    edge_exit_angle_fdown   = {line[replica_name].edge_exit_angle_fdown}"""
                # Append shifts if they exist
                if line[replica_name].shift_x != 0:
                    bend_generation += f""",
    shift_x                 = '{line[replica_name].shift_x}'"""
                if line[replica_name].shift_y != 0:
                    bend_generation += f""",
    shift_y                 = '{line[replica_name].shift_y}'"""
            # In the case of a skew corrector, we need to add a rotation
                bend_generation += f""",
    rot_s_rad               = '{line[replica_name].rot_s_rad}'"""
                # Append the missing parenthesis
                bend_generation += """)"""
            
            # Write to the file
            output_string += bend_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string


################################################################################
# Optics File
################################################################################
def create_bend_optics_file_information(line, line_table):

    ########################################
    # Get information
    ########################################
    hbends, vbends, sbends, unique_bend_variables, bend_name_dict = extract_bend_information(line, line_table)

    hbend_names         = generate_magnet_for_replication_names(hbends, "hbend")
    vbend_names         = generate_magnet_for_replication_names(vbends, "vbend")
    sbend_names         = generate_magnet_for_replication_names(sbends, "sbend")

    ########################################
    # Ensure there are bends in the line
    ########################################
    if len(hbend_names) == 0 and len(vbend_names) == 0 and len(sbend_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = f"""
    ############################################################
    # Bends
    ############################################################"""

    for bend_variable in unique_bend_variables:
        k0 = None

        k0  = line[bend_variable].k0
        if k0 == 0:
            k0 = None

        if k0 is not None:
            output_string += f"""
    {f'k0_{bend_variable}'}{' ' * (OUTPUT_STRING_SEP - len(f'k0_{bend_variable}') + 4)}{'= '}{k0:.12f},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string