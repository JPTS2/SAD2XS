"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Import Packages
################################################################################
import numpy as np
from .._globals import *

################################################################################
# Naming
################################################################################

########################################
# Parent/Variable Name Extraction
########################################
def get_parentname(element_name):
    """
    Elements may be repeated or inverted
    Repeated elements are suffixed with ::0, ::1 etc
    """
    # Assume to start that the parent name is the element name excluding replica
    parent_name    = element_name.split('::')[0]
    
    return parent_name

def get_variablename(element_name):
    """
    Elements may be repeated or inverted
    Repeated elements are suffixed with ::0, ::1 etc
    Inverted elements are prefixed with a '-' but take the same variable as the non-inverted element
    """

    # Get the parent name
    parent_name     = get_parentname(element_name)

    # If the element is inverted, the variable name needs the '-' removed
    if parent_name.startswith('-'):
        variable_name   = parent_name[1:]
    else:
        variable_name   = parent_name
    
    return variable_name

################################################################################
# Elements for replication naming
################################################################################
def generate_magnet_for_replication_names(length_dict, base_string):
    """
    To simplify the output, we create base magnets for replication
    This function generates the names for these base magnets
    Convention based on magnet type and length in microns

    N.B. Two assumptions:
    1. Lengths are rounded to the nearest micron
    2. Lengths are less than 10m
    3. Lengths are non-negative
    """
    names           = []
    length_values	= np.array(list(length_dict.keys()))
    length_values	= length_values * 1E9
    length_values	= length_values.astype(int)
    
    for length in length_values:
        name = f"{base_string}{length:011d}"
        names.append(name)
    names = sorted(names)
    
    return names

################################################################################
# KNL/KSL arrays to strings
################################################################################
def get_knl_string(knl_array):
    """
    Returns a string with the knl values
    """
    # If all zero, just give an empty array
    if np.all(knl_array == 0):
        return "[]"
    
    # Otherwise, iterate through
    knl_string = "["
    for i, knl in enumerate(knl_array):

        # If there are no more knl values, close:
        if np.all(knl_array[i:] == 0):
            break

        # Fromat the knl value
        if knl == 0:
            knl_substring   = f"0"
        else:
            knl_substring   = f"{knl:.10e}"
        
        # Append to the string
        if i == 0:
            knl_string += knl_substring
        else:
            knl_string += f', {knl_substring}'
    
    # Close the string
    knl_string += "]"
    return knl_string

################################################################################
# Extract Magnet Information
################################################################################

########################################
# Bends
########################################
def extract_bend_information(line, line_table):

    ########################################
    # Get Bend Element information
    ########################################
    unique_bend_names           = []
    unique_bend_variables       = []

    for bend in line_table.rows[line_table.element_type == 'Bend'].name:
        parentname      = get_parentname(bend)
        variablename    = get_variablename(bend)
        
        # Ensure the element is a bend not a corrector
        if line[parentname].h != 0:
            if parentname not in unique_bend_names:
                unique_bend_names.append(parentname)
                unique_bend_variables.append(variablename)

    bend_name_dict      = {}
    for bend_name, bend_variable in zip(unique_bend_names, unique_bend_variables):
        bend_name_dict[bend_name] = bend_variable

    unique_bend_variables       = sorted(list(set(unique_bend_variables)))

    ########################################
    # Bend Base Element information
    ########################################
    # Get the base elements to replicate: pure horizontal, vertical and skew
    hbends	= {}
    vbends  = {}
    sbends  = {}

    for bend in unique_bend_names:

        # Get the length and rotation of the bend
        length		= line[bend].length
        rot_s_rad	= line[bend].rot_s_rad

        ########################################
        # Categorise H and V based on the rotation
        ########################################
        # Mapping from rotation → (target‑dict, need_flip)
        angle_map = {
            0:               (hbends, False),
            np.pi:           (hbends, True),
            -np.pi / 2:      (vbends, True),
            np.pi / 2:       (vbends, False)}

        # Try to match one of the valid angles
        angle_matched   = False
        for angle, (bend_dict, flip) in angle_map.items():
            if np.isclose(rot_s_rad, angle):
                angle_matched   = True
                
                # Handle horizontal and vertical bends rotated by 180 degrees
                if flip:
                    line[bend].k0               *= -1
                    line[bend].h                *= -1
                    line[bend].edge_entry_angle *= -1
                    line[bend].edge_exit_angle  *= -1
                    line[bend].rot_s_rad        *= -1

                # insert without duplicates
                lst = bend_dict.setdefault(length, [])
                if bend not in lst:
                    lst.append(bend)
                # else: already there → skip silently
                break

        if not angle_matched:
            # → skew bend
            lst = sbends.setdefault(length, [])
            if bend not in lst:
                lst.append(bend)

    return hbends, vbends, sbends, unique_bend_variables, bend_name_dict

########################################
# Correctors
########################################
def extract_corrector_information(line, line_table):

    ########################################
    # Get Corrector Element information
    ########################################
    unique_corr_names           = []
    unique_corr_variables       = []

    for corr in line_table.rows[line_table.element_type == 'Bend'].name:
        parentname      = get_parentname(corr)
        variablename    = get_variablename(corr)
        
        # Ensure the element is a corr not a corrector
        if line[parentname].h == 0:
            if parentname not in unique_corr_names:
                unique_corr_names.append(parentname)
                unique_corr_variables.append(variablename)

    corr_name_dict      = {}
    for corr_name, corr_variable in zip(unique_corr_names, unique_corr_variables):
        corr_name_dict[corr_name] = corr_variable

    unique_corr_variables       = sorted(list(set(unique_corr_variables)))

    ########################################
    # corr Base Element information
    ########################################
    # Get the base elements to replicate: pure horizontal, vertical and skew
    hcorrs	= {}
    vcorrs  = {}
    scorrs  = {}

    for corr in unique_corr_names:

        # Get the length and rotation of the corr
        length		= line[corr].length
        rot_s_rad	= line[corr].rot_s_rad

        ########################################
        # Categorise H and V based on the rotation
        ########################################
        # Mapping from rotation → (target‑dict, need_flip)
        angle_map = {
            0:               (hcorrs, False),
            np.pi:           (hcorrs, True),
            -np.pi / 2:      (vcorrs, True),
            np.pi / 2:       (vcorrs, False)}

        # Try to match one of the valid angles
        angle_matched   = False
        for angle, (corr_dict, flip) in angle_map.items():
            if np.isclose(rot_s_rad, angle):
                angle_matched   = True

                # Handle horizontal and vertical corrs rotated by 180 degrees
                if flip:
                    line[corr].k0               *= -1
                    line[corr].h                *= -1
                    line[corr].edge_entry_angle *= -1
                    line[corr].edge_exit_angle  *= -1
                    line[corr].rot_s_rad        *= -1

                # insert without duplicates
                lst = corr_dict.setdefault(length, [])
                if corr not in lst:
                    lst.append(corr)
                # else: already there → skip silently
                break

        if not angle_matched:
            # → skew corr
            lst = scorrs.setdefault(length, [])
            if corr not in lst:
                lst.append(corr)

    return hcorrs, vcorrs, scorrs, unique_corr_variables, corr_name_dict

########################################
# Quadrupole/Sextupole/Octupole information
########################################
def extract_multipole_information(line, line_table, mode):

    ########################################
    # Get Magnet Element information
    ########################################
    unique_names       = []
    for magnet in line_table.rows[line_table.element_type == mode].name:
        parentname      = get_parentname(magnet)
        if parentname not in unique_names:
            unique_names.append(parentname)

    ########################################
    # Magnets based on length
    ########################################
    magnets   = {}
    for magnet in unique_names:
        length		= line[magnet].length
        if length not in magnets:
            magnets[length] = [magnet]
        else:
            if magnet not in magnets[length]:
                magnets[length].append(magnet)
            else:
                continue

    return magnets, unique_names

################################################################################
# Element is simple to clone
################################################################################
def check_is_simple_bend_corr(line, replica_name):
    is_simple = False
    
    if line[replica_name].edge_entry_angle == 0 and \
            line[replica_name].edge_exit_angle == 0 and \
            line[replica_name].edge_entry_angle_fdown == 0 and \
            line[replica_name].edge_exit_angle_fdown == 0 and \
            line[replica_name].shift_x == 0 and \
            line[replica_name].shift_y == 0:
        is_simple = True
    
    return is_simple

def check_is_simple_quad_sext_oct(line, replica_name, mode):
    is_simple   = False
    is_skew     = False

    if mode == "Quadrupole":
        # Simple assumes only one of k1 or k1s is non-zero
        if (line[replica_name].k1 * line[replica_name].k1s) == 0 and \
                line[replica_name].shift_x == 0 and \
                line[replica_name].shift_y == 0 and \
                line[replica_name].rot_s_rad == 0:
            is_simple = True

    if mode == "Sextupole":
        # Simple assumes only one of k2 or k2s is non-zero
        if (line[replica_name].k2 * line[replica_name].k2s) == 0 and \
                line[replica_name].shift_x == 0 and \
                line[replica_name].shift_y == 0 and \
                line[replica_name].rot_s_rad == 0:
            is_simple = True

    if mode == "Octupole":
        # Simple assumes only one of k3 or k3s is non-zero
        if (line[replica_name].k3 * line[replica_name].k3s) == 0 and \
                line[replica_name].shift_x == 0 and \
                line[replica_name].shift_y == 0 and \
                line[replica_name].rot_s_rad == 0:
            is_simple = True

    return is_simple

def check_is_skew_quad_sext_oct(line, replica_name, mode):
    is_skew     = False

    if mode == "Quadrupole":
        if line[replica_name].k1s != 0:
            is_skew = True

    if mode == "Sextupole":
        if line[replica_name].k2s != 0:
            is_skew = True

    if mode == "Octupole":
        if line[replica_name].k3s != 0:
            is_skew = True

    return is_skew

def check_is_simple_unpowered_multipole(line, replica_name):
    is_simple_unpowered = False

    if np.all(line[replica_name].knl == 0) and \
            np.all(line[replica_name].ksl == 0) and \
            line[replica_name].shift_x == 0 and \
            line[replica_name].shift_y == 0 and \
            line[replica_name].rot_s_rad == 0:
        is_simple_unpowered = True

    return is_simple_unpowered

def check_is_simple_solenoid(line, replica_name):
    is_simple_unpowered = False

    if np.all(line[replica_name].knl == 0) and \
            np.all(line[replica_name].ksl == 0) and \
            line[replica_name].mult_shift_x == 0 and \
            line[replica_name].mult_shift_y == 0 and \
            line[replica_name].rot_s_rad == 0:
        is_simple_unpowered = True

    return is_simple_unpowered
