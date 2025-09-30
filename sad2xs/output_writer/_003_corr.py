"""
(Unofficial) SAD to XSuite Converter

Output Writer: Correctors
"""

################################################################################
# Import Packages
################################################################################
from ._000_helpers import *

################################################################################
# Lattice File
################################################################################
def create_corrector_lattice_file_information(line, line_table):

    ########################################
    # Get information
    ########################################
    hcorrs, vcorrs, scorrs, unique_corr_variables, corr_name_dict = extract_corrector_information(line, line_table)
    
    hcorr_lengths       = np.array(sorted(hcorrs.keys()))
    hcorr_names         = generate_magnet_for_replication_names(hcorrs, "hcorr")
    vcorr_lengths       = np.array(sorted(vcorrs.keys()))
    vcorr_names         = generate_magnet_for_replication_names(vcorrs, "vcorr")
    scorr_lengths       = np.array(sorted(scorrs.keys()))
    scorr_names         = generate_magnet_for_replication_names(scorrs, "scorr")

    ########################################
    # Ensure there are correctors in the line
    ########################################
    if len(hcorr_names) == 0 and len(vcorr_names) == 0 and len(scorr_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = f"""
############################################################
# Correctors
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += f"""
########################################
# Base Elements
########################################"""

    for hcorr_name, hcorr_length in zip(hcorr_names, hcorr_lengths):
        output_string += f"""
env.new(name = '{hcorr_name}', parent = xt.Bend, length = {hcorr_length})"""

    for vcorr_name, vcorr_length in zip(vcorr_names, vcorr_lengths):
        output_string += f"""
env.new(name = '{vcorr_name}', parent = xt.Bend, length = {vcorr_length}, rot_s_rad = +np.pi/2)"""

    for scorr_name, scorr_length in zip(scorr_names, scorr_lengths):
        output_string += f"""
env.new(name = '{scorr_name}', parent = xt.Bend, length = {scorr_length})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += f"""
########################################
# Cloned Elements
########################################"""

    for hcorr, hcorr_length in zip(hcorr_names, hcorr_lengths):
        for replica_name in hcorrs[hcorr_length]:
            replica_variable    = corr_name_dict[replica_name]

            # If simple try to make it more compact
            if check_is_simple_bend_corr(line, replica_name):
                corr_generation = f"""
env.new(name = '{replica_name}', parent = '{hcorr}', k0 = 'k0_{replica_variable}')"""
            
            # Otherwise do the full version
            else:
                corr_generation = f"""
env.new(
    name                    = '{replica_name}',
    parent                  = '{hcorr}',
    k0                      = 'k0_{replica_variable}'"""
            # Append edge entry angles
                if line[replica_name].edge_entry_angle != 0:
                    corr_generation += f""",
    edge_entry_angle        = {line[replica_name].edge_entry_angle}"""
                if line[replica_name].edge_exit_angle != 0:
                    corr_generation += f""",
    edge_exit_angle         = {line[replica_name].edge_exit_angle}"""
                if line[replica_name].edge_entry_angle_fdown != 0:
                    corr_generation += f""",
    edge_entry_angle_fdown  = {line[replica_name].edge_entry_angle_fdown}"""
                if line[replica_name].edge_exit_angle_fdown != 0:
                    corr_generation += f""",
    edge_exit_angle_fdown   = {line[replica_name].edge_exit_angle_fdown}"""
                # Append shifts if they exist
                if line[replica_name].shift_x != 0:
                    corr_generation += f""",
    shift_x                 = '{line[replica_name].shift_x}'"""
                if line[replica_name].shift_y != 0:
                    corr_generation += f""",
    shift_y                 = '{line[replica_name].shift_y}'"""
            # Append the missing parenthesis
                corr_generation += """)"""
            
            # Write to the file
            output_string += corr_generation


    for vcorr, vcorr_length in zip(vcorr_names, vcorr_lengths):
        for replica_name in vcorrs[vcorr_length]:
            replica_variable    = corr_name_dict[replica_name]

            # If simple try to make it more compact
            if check_is_simple_bend_corr(line, replica_name):
                corr_generation = f"""
env.new(name = '{replica_name}', parent = '{vcorr}', k0 = 'k0_{replica_variable}')"""
            
            # Otherwise do the full version
            else:
                corr_generation = f"""
env.new(
    name                    = '{replica_name}',
    parent                  = '{vcorr}',
    k0                      = 'k0_{replica_variable}'"""
            # Append edge entry angles
                if line[replica_name].edge_entry_angle != 0:
                    corr_generation += f""",
    edge_entry_angle        = {line[replica_name].edge_entry_angle}"""
                if line[replica_name].edge_exit_angle != 0:
                    corr_generation += f""",
    edge_exit_angle         = {line[replica_name].edge_exit_angle}"""
                if line[replica_name].edge_entry_angle_fdown != 0:
                    corr_generation += f""",
    edge_entry_angle_fdown  = {line[replica_name].edge_entry_angle_fdown}"""
                if line[replica_name].edge_exit_angle_fdown != 0:
                    corr_generation += f""",
    edge_exit_angle_fdown   = {line[replica_name].edge_exit_angle_fdown}"""
                # Append shifts if they exist
                if line[replica_name].shift_x != 0:
                    corr_generation += f""",
    shift_x                 = '{line[replica_name].shift_x}'"""
                if line[replica_name].shift_y != 0:
                    corr_generation += f""",
    shift_y                 = '{line[replica_name].shift_y}'"""
            # Append the missing parenthesis
                corr_generation += """)"""
            
            # Write to the file
            output_string += corr_generation

    for scorr, scorr_length in zip(scorr_names, scorr_lengths):
        for replica_name in scorrs[scorr_length]:
            replica_variable    = corr_name_dict[replica_name]

            # If simple try to make it more compact
            if check_is_simple_bend_corr(line, replica_name):
                corr_generation = f"""
env.new(name = '{replica_name}', parent = '{scorr}', k0 = 'k0_{replica_variable}', rot_s_rad = '{line[replica_name].rot_s_rad}')"""
            
            # Otherwise do the full version
            else:
                corr_generation = f"""
env.new(
    name                    = '{replica_name}',
    parent                  = '{scorr}',
    k0                      = 'k0_{replica_variable}'"""
            # Append edge entry angles
                if line[replica_name].edge_entry_angle != 0:
                    corr_generation += f""",
    edge_entry_angle        = {line[replica_name].edge_entry_angle}"""
                if line[replica_name].edge_exit_angle != 0:
                    corr_generation += f""",
    edge_exit_angle         = {line[replica_name].edge_exit_angle}"""
                if line[replica_name].edge_entry_angle_fdown != 0:
                    corr_generation += f""",
    edge_entry_angle_fdown  = {line[replica_name].edge_entry_angle_fdown}"""
                if line[replica_name].edge_exit_angle_fdown != 0:
                    corr_generation += f""",
    edge_exit_angle_fdown   = {line[replica_name].edge_exit_angle_fdown}"""
                # Append shifts if they exist
                if line[replica_name].shift_x != 0:
                    corr_generation += f""",
    shift_x                 = '{line[replica_name].shift_x}'"""
                if line[replica_name].shift_y != 0:
                    corr_generation += f""",
    shift_y                 = '{line[replica_name].shift_y}'"""
            # In the case of a skew corrector, we need to add a rotation
                corr_generation += f""",
    rot_s_rad               = '{line[replica_name].rot_s_rad}'"""
            # Append the missing parenthesis
                corr_generation += """)"""
            
            # Write to the file
            output_string += corr_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string


################################################################################
# Optics File
################################################################################
def create_corrector_optics_file_information(line, line_table):

    ########################################
    # Get information
    ########################################
    hcorrs, vcorrs, scorrs, unique_corr_variables, corr_name_dict = extract_corrector_information(line, line_table)

    hcorr_names         = generate_magnet_for_replication_names(hcorrs, "hcorr")
    vcorr_names         = generate_magnet_for_replication_names(vcorrs, "vcorr")
    scorr_names         = generate_magnet_for_replication_names(scorrs, "scorr")

    ########################################
    # Ensure there are correctors in the line
    ########################################
    if len(hcorr_names) == 0 and len(vcorr_names) == 0 and len(scorr_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    # TODO: This still gives an empty section is they are all set to 0
    output_string   = f"""
    ############################################################
    # Correctors
    ############################################################"""

    for corr_variable in unique_corr_variables:
        k0 = None

        k0  = line[corr_variable].k0
        if k0 == 0:
            k0 = None

        if k0 is not None:
            output_string += f"""
    {f'k0_{corr_variable}'}{' ' * (OUTPUT_STRING_SEP - len(f'k0_{corr_variable}') + 4)}{'= '}{k0:.12f},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string