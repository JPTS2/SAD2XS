"""
(Unofficial) SAD to XSuite Converter

Output Writer: Reference Shifts
"""

################################################################################
# Import Packages
################################################################################
from ._000_helpers import *

################################################################################
# Lattice File
################################################################################
def create_refshift_lattice_file_information(line, line_table):

    ########################################
    # Get information
    ########################################
    unique_xyshift_names    = []
    unique_zetashift_names  = []
    unique_xrotation_names  = []
    unique_yrotation_names  = []
    unique_srotation_names  = []

    unique_xyshift_variable_names   = []
    unique_zetashift_variable_names = []
    unique_xrotation_variable_names = []
    unique_yrotation_variable_names = []
    unique_srotation_variable_names = []

    for xyshift in line_table.rows[line_table.element_type == 'XYShift'].name:
        parentname      = get_parentname(xyshift)
        variablename    = get_variablename(xyshift)
        if parentname not in unique_xyshift_names:
            unique_xyshift_names.append(parentname)
            unique_xyshift_variable_names.append(variablename)

    for zshift in line_table.rows[line_table.element_type == 'ZetaShift'].name:
        parentname      = get_parentname(zshift)
        variablename    = get_variablename(zshift)
        if parentname not in unique_zetashift_names:
            unique_zetashift_names.append(parentname)
            unique_zetashift_variable_names.append(variablename)

    for xrotation in line_table.rows[line_table.element_type == 'XRotation'].name:
        parentname      = get_parentname(xrotation)
        variablename    = get_variablename(xrotation)
        if parentname not in unique_xrotation_names:
            unique_xrotation_names.append(parentname)
            unique_xrotation_variable_names.append(variablename)

    for yrotation in line_table.rows[line_table.element_type == 'YRotation'].name:
        parentname      = get_parentname(yrotation)
        variablename    = get_variablename(yrotation)
        if parentname not in unique_yrotation_names:
            unique_yrotation_names.append(parentname)
            unique_yrotation_variable_names.append(variablename)

    for srotation in line_table.rows[line_table.element_type == 'SRotation'].name:
        parentname      = get_parentname(srotation)
        variablename    = get_variablename(srotation)
        if parentname not in unique_srotation_names:
            unique_srotation_names.append(parentname)
            unique_srotation_variable_names.append(variablename)

    ########################################
    # Ensure there are reference shifts in the line
    ########################################
    if len(unique_xyshift_names) == 0 and \
            len(unique_zetashift_names) == 0 and \
            len(unique_xrotation_names) == 0 and \
            len(unique_yrotation_names) == 0 and \
            len(unique_srotation_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = f"""
############################################################
# Reference Shifts
############################################################
"""

    ########################################
    # XYShifts
    ########################################
    if len(unique_xyshift_names) != 0:
        output_string += f"""
########################################
# XYShifts
########################################"""

        for xyshift_name, xyshift_variable_name in zip(unique_xyshift_names, unique_xyshift_variable_names):
            output_string += f"""
env.new(
    name        = '{xyshift_name}',
    parent      = xt.XYShift,
    dx          = 'dx_{xyshift_variable_name}',
    dy          = 'dy_{xyshift_variable_name}')"""

        output_string += "\n"

    ########################################
    # ZetaShifts
    ########################################
    if len(unique_zetashift_names) != 0:
        output_string += f"""
########################################
# ZetaShifts
########################################"""

        for zetashift_name, zetashift_variable_name in zip(unique_zetashift_names, unique_zetashift_variable_names):
            output_string += f"""
env.new(
    name        = '{zetashift_name}',
    parent      = xt.ZetaShift,
    dzeta       = 'dz_{zetashift_variable_name}')"""

        output_string += "\n"

    ########################################
    # YRotations
    ########################################
    if len(unique_yrotation_names) != 0:
        output_string += f"""
########################################
# YRotations (CHI1)
########################################"""

        for yrotation_name, yrotation_variable_name in zip(unique_yrotation_names, unique_yrotation_variable_names):
            output_string += f"""
env.new(
    name        = '{yrotation_name}',
    parent      = xt.YRotation,
    angle       = 'chi1_{yrotation_variable_name}')"""

        output_string += "\n"

    ########################################
    # XRotations
    ########################################
    if len(unique_xrotation_names) != 0:
        output_string += f"""
########################################
# XRotations (CHI2)
########################################"""

        for xrotation_name, xrotation_variable_name in zip(unique_xrotation_names, unique_xrotation_variable_names):
            output_string += f"""
env.new(
    name        = '{xrotation_name}',
    parent      = xt.XRotation,
    angle       = 'chi2_{xrotation_variable_name}')"""

        output_string += "\n"

    ########################################
    # SRotations
    ########################################
    if len(unique_srotation_names) != 0:
        output_string += f"""
########################################
# SRotations (CHI3)
########################################"""

        for srotation_name, srotation_variable_name in zip(unique_srotation_names, unique_srotation_variable_names):
            output_string += f"""
env.new(
    name        = '{srotation_name}',
    parent      = xt.SRotation,
    angle       = 'chi3_{srotation_variable_name}')"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string

################################################################################
# Optics File
################################################################################
def create_refshift_optics_file_information(line, line_table):

    ########################################
    # Get information
    ########################################
    unique_xyshift_names    = []
    unique_zetashift_names  = []
    unique_xrotation_names  = []
    unique_yrotation_names  = []
    unique_srotation_names  = []

    unique_xyshift_variable_names   = []
    unique_zetashift_variable_names = []
    unique_xrotation_variable_names = []
    unique_yrotation_variable_names = []
    unique_srotation_variable_names = []

    for xyshift in line_table.rows[line_table.element_type == 'XYShift'].name:
        parentname      = get_parentname(xyshift)
        variablename    = get_variablename(xyshift)
        if parentname not in unique_xyshift_names:
            unique_xyshift_names.append(parentname)
            unique_xyshift_variable_names.append(variablename)

    for zshift in line_table.rows[line_table.element_type == 'ZetaShift'].name:
        parentname      = get_parentname(zshift)
        variablename    = get_variablename(zshift)
        if parentname not in unique_zetashift_names:
            unique_zetashift_names.append(parentname)
            unique_zetashift_variable_names.append(variablename)

    for xrotation in line_table.rows[line_table.element_type == 'XRotation'].name:
        parentname      = get_parentname(xrotation)
        variablename    = get_variablename(xrotation)
        if parentname not in unique_xrotation_names:
            unique_xrotation_names.append(parentname)
            unique_xrotation_variable_names.append(variablename)

    for yrotation in line_table.rows[line_table.element_type == 'YRotation'].name:
        parentname      = get_parentname(yrotation)
        variablename    = get_variablename(yrotation)
        if parentname not in unique_yrotation_names:
            unique_yrotation_names.append(parentname)
            unique_yrotation_variable_names.append(variablename)

    for srotation in line_table.rows[line_table.element_type == 'SRotation'].name:
        parentname      = get_parentname(srotation)
        variablename    = get_variablename(srotation)
        if parentname not in unique_srotation_names:
            unique_srotation_names.append(parentname)
            unique_srotation_variable_names.append(variablename)

    ########################################
    # Ensure there are reference shifts in the line
    ########################################
    if len(unique_xyshift_names) == 0 and \
            len(unique_zetashift_names) == 0 and \
            len(unique_xrotation_names) == 0 and \
            len(unique_yrotation_names) == 0 and \
            len(unique_srotation_names) == 0:
        return ""

    ########################################
    # Sort the lists
    ########################################
    unique_xyshift_variable_names, unique_xyshift_names = map(
        list, zip(*sorted(zip(unique_xyshift_variable_names, unique_xyshift_names))))
    unique_zetashift_variable_names, unique_zetashift_names = map(
        list, zip(*sorted(zip(unique_zetashift_variable_names, unique_zetashift_names))))
    unique_xrotation_variable_names, unique_xrotation_names = map(
        list, zip(*sorted(zip(unique_xrotation_variable_names, unique_xrotation_names))))
    unique_yrotation_variable_names, unique_yrotation_names = map(
        list, zip(*sorted(zip(unique_yrotation_variable_names, unique_yrotation_names))))
    unique_srotation_variable_names, unique_srotation_names = map(
        list, zip(*sorted(zip(unique_srotation_variable_names, unique_srotation_names))))

    ########################################
    # Create Output string
    ########################################
    output_string = f"""
    ############################################################
    # Reference Shifts
    ############################################################
"""

    ########################################
    # XYShifts
    ########################################
    if len(unique_xyshift_names) != 0:
        output_string += f"""
    ########################################
    # XYShifts
    ########################################"""

        for xyshift_name, xyshift_variable_name in zip(unique_xyshift_names, unique_xyshift_variable_names):

            dx  = line[xyshift_name].dx
            dy  = line[xyshift_name].dy
            
            if dx != 0:
                output_string += f"""
    {f'dx_{xyshift_variable_name}'}{' ' * (OUTPUT_STRING_SEP - len(f'dx_{xyshift_variable_name}') + 4)}{'= '}{dx:.12f},"""
            if dy != 0:
                output_string += f"""
    {f'dy_{xyshift_variable_name}'}{' ' * (OUTPUT_STRING_SEP - len(f'dy_{xyshift_variable_name}') + 4)}{'= '}{dy:.12f},"""

        output_string += "\n"

    ########################################
    # ZetaShifts
    ########################################
    if len(unique_zetashift_names) != 0:
        output_string += f"""
    ########################################
    # ZetaShifts
    ########################################"""

        for zetashift_name, zetashift_variable_name in zip(unique_zetashift_names, unique_zetashift_variable_names):

            dz  = line[zetashift_name].dzeta
            
            if dz != 0:
                output_string += f"""
    {f'dz_{zetashift_variable_name}'}{' ' * (OUTPUT_STRING_SEP - len(f'dz_{zetashift_variable_name}') + 4)}{'= '}{dz:.12f},"""

        output_string += "\n"

    ########################################
    # YRotations
    ########################################
    if len(unique_yrotation_names) != 0:
        output_string += f"""
    ########################################
    # YRotations (CHI1)
    ########################################"""

        for yrotation_name, yrotation_variable_name in zip(unique_yrotation_names, unique_yrotation_variable_names):

            chi1    = line[yrotation_name].angle

            if chi1 != 0:
                output_string += f"""
    {f'chi1_{yrotation_variable_name}'}{' ' * (OUTPUT_STRING_SEP - len(f'chi1_{yrotation_variable_name}') + 4)}{'= '}{chi1:.12f},"""

        output_string += "\n"

    ########################################
    # XRotations
    ########################################
    if len(unique_xrotation_names) != 0:
        output_string += f"""
    ########################################
    # XRotations (CHI2)
    ########################################"""

        for xrotation_name, xrotation_variable_name in zip(unique_xrotation_names, unique_xrotation_variable_names):

            chi2    = line[xrotation_name].angle

            if chi2 != 0:
                output_string += f"""
    {f'chi2_{xrotation_variable_name}'}{' ' * (OUTPUT_STRING_SEP - len(f'chi2_{xrotation_variable_name}') + 4)}{'= '}{chi2:.12f},"""

        output_string += "\n"

    ########################################
    # XRotations
    ########################################
    if len(unique_srotation_names) != 0:
        output_string += f"""
    ########################################
    # SRotations (CHI3)
    ########################################"""

        for srotation_name, srotation_variable_name in zip(unique_srotation_names, unique_srotation_variable_names):

            chi3    = line[srotation_name].angle

            if chi3 != 0:
                output_string += f"""
    {f'chi3_{srotation_variable_name}'}{' ' * (OUTPUT_STRING_SEP - len(f'chi3_{srotation_variable_name}') + 4)}{'= '}{chi3:.12f},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
