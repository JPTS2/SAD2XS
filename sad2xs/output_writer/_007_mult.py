"""
(Unofficial) SAD to XSuite Converter

Output Writer: Multipoles
"""

################################################################################
# Import Packages
################################################################################
from ._000_helpers import *

################################################################################
# Lattice File
################################################################################
def create_multipole_lattice_file_information(line, line_table):

    ########################################
    # Get information
    ########################################
    mults, unique_mult_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Multipole")

    mult_lengths    = np.array(sorted(mults.keys()))
    mult_names      = generate_magnet_for_replication_names(mults, "mult")

    ########################################
    # Ensure there are multipoles in the line
    ########################################
    if len(unique_mult_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = f"""
############################################################
# Multipoles
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += f"""
########################################
# Base Elements
########################################"""
    
    for mult_name, mult_length in zip(mult_names, mult_lengths):
        output_string += f"""
env.new(
    name                = '{mult_name}',
    parent              = xt.Multipole,
    length              = {mult_length},
    _isthick            = True,
    order               = {MAX_KNL_ORDER},
    num_multipole_kicks = {N_MULTIPOLE_KICKS_SOL})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += f"""
########################################
# Cloned Elements
########################################"""

    for mult, mult_length in zip(mult_names, mult_lengths):
        for replica_name in mults[mult_length]:

            if check_is_simple_unpowered_multipole(line, replica_name):
                output_string += f"""
env.new(name = '{replica_name}', parent = '{mult}')"""
            
            else:
                # Get the replica information
                knl         = get_knl_string(line[replica_name].knl)
                ksl         = get_knl_string(line[replica_name].ksl)
                shift_x     = line[replica_name].shift_x
                shift_y     = line[replica_name].shift_y
                rot_s_rad   = line[replica_name].rot_s_rad

                # Basic information
                mult_generation = f"""
env.new(
    name        = '{replica_name}',
    parent      = '{mult}'"""
                
                # Strength information
                if knl != "[]":
                    mult_generation += f""",
    knl         = {knl}"""
                if ksl != "[]":
                    mult_generation += f""",
    ksl         = {ksl}"""

                # Misalignments
                if shift_x != 0:
                    mult_generation += f""",
    shift_x     = '{shift_x}'"""
                if shift_y != 0:
                    mult_generation += f""",
    shift_y     = '{shift_y}'"""
                if rot_s_rad != 0:
                    mult_generation += f""",
    rot_s_rad   = '{rot_s_rad}'"""

                # Close the element definition
                mult_generation += """)"""

                # Write to the file
                output_string += mult_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
