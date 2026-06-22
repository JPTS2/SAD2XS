"""
(Unofficial) SAD to XSuite Converter: Output Writer - Reference Shifts
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

from ._000_helpers import get_parentname, get_variablename
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_refshift_lattice_file_information(
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Docstring for create_refshift_lattice_file_information

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
    unique_translation_names  = []
    unique_timedelay_names    = []
    unique_rotation_names     = []

    unique_translation_variable_names  = []
    unique_timedelay_variable_names    = []
    unique_rotation_variable_names     = []

    for translation in line_table.rows[line_table.element_type == 'Translation'].name:
        parentname      = get_parentname(translation)
        variablename    = get_variablename(translation)
        if parentname not in unique_translation_names:
            unique_translation_names.append(parentname)
            unique_translation_variable_names.append(variablename)

    for timedelay in line_table.rows[line_table.element_type == 'TimeDelay'].name:
        parentname      = get_parentname(timedelay)
        variablename    = get_variablename(timedelay)
        if parentname not in unique_timedelay_names:
            unique_timedelay_names.append(parentname)
            unique_timedelay_variable_names.append(variablename)

    for rotation in line_table.rows[line_table.element_type == 'Rotation'].name:
        parentname      = get_parentname(rotation)
        variablename    = get_variablename(rotation)
        if parentname not in unique_rotation_names:
            unique_rotation_names.append(parentname)
            unique_rotation_variable_names.append(variablename)

    ########################################
    # Ensure there are reference shifts in the line
    ########################################
    if len(unique_translation_names) == 0 and \
            len(unique_timedelay_names) == 0 and \
            len(unique_rotation_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Reference Shifts
############################################################
"""

    ########################################
    # Translations
    ########################################
    if len(unique_translation_names) != 0:
        output_string += """
########################################
# Translations
########################################"""

        for translation_name, translation_variable_name in zip(
                unique_translation_names, unique_translation_variable_names):

            # Remove the minus sign if no non minus version exists
            if translation_name.startswith("-"):
                root_name   = translation_name[1:]
                if root_name not in unique_translation_names:
                    translation_name        = root_name

            output_string += f"""
env.new(
    name        = '{translation_name}',
    parent      = xt.Translation,
    shift_x     = 'dx_{translation_variable_name}',
    shift_y     = 'dy_{translation_variable_name}')"""

        output_string += "\n"

    ########################################
    # TimeDelays
    ########################################
    if len(unique_timedelay_names) != 0:
        output_string += """
########################################
# TimeDelays
########################################"""

        for timedelay_name, timedelay_variable_name in zip(
                unique_timedelay_names, unique_timedelay_variable_names):

            # Remove the minus sign if no non minus version exists
            if timedelay_name.startswith("-"):
                root_name   = timedelay_name[1:]
                if root_name not in unique_timedelay_names:
                    timedelay_name        = root_name

            output_string += f"""
env.new(
    name        = '{timedelay_name}',
    parent      = xt.TimeDelay,
    shift_zeta  = 'dz_{timedelay_variable_name}')"""

        output_string += "\n"

    ########################################
    # Rotations (CHI1/CHI2/CHI3)
    ########################################
    if len(unique_rotation_names) != 0:
        output_string += """
########################################
# Rotations (CHI1/CHI2/CHI3)
########################################"""

        for rotation_name, rotation_variable_name in zip(
                unique_rotation_names, unique_rotation_variable_names):

            # Remove the minus sign if no non minus version exists
            if rotation_name.startswith("-"):
                root_name   = rotation_name[1:]
                if root_name not in unique_rotation_names:
                    rotation_name        = root_name

            output_string += f"""
env.new(
    name        = '{rotation_name}',
    parent      = xt.Rotation,
    rot_y_rad   = 'chi1_{rotation_variable_name}',
    rot_x_rad   = 'chi2_{rotation_variable_name}',
    rot_s_rad   = 'chi3_{rotation_variable_name}')"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string

################################################################################
# Optics File
################################################################################
def create_refshift_optics_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Docstring for create_refshift_optics_file_information

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
    unique_translation_names  = []
    unique_timedelay_names    = []
    unique_rotation_names     = []

    unique_translation_variable_names  = []
    unique_timedelay_variable_names    = []
    unique_rotation_variable_names     = []

    for translation in line_table.rows[line_table.element_type == 'Translation'].name:
        parentname      = get_parentname(translation)
        variablename    = get_variablename(translation)
        if parentname not in unique_translation_names:
            unique_translation_names.append(parentname)
            unique_translation_variable_names.append(variablename)

    for timedelay in line_table.rows[line_table.element_type == 'TimeDelay'].name:
        parentname      = get_parentname(timedelay)
        variablename    = get_variablename(timedelay)
        if parentname not in unique_timedelay_names:
            unique_timedelay_names.append(parentname)
            unique_timedelay_variable_names.append(variablename)

    for rotation in line_table.rows[line_table.element_type == 'Rotation'].name:
        parentname      = get_parentname(rotation)
        variablename    = get_variablename(rotation)
        if parentname not in unique_rotation_names:
            unique_rotation_names.append(parentname)
            unique_rotation_variable_names.append(variablename)

    ########################################
    # Ensure there are reference shifts in the line
    ########################################
    if len(unique_translation_names) == 0 and \
            len(unique_timedelay_names) == 0 and \
            len(unique_rotation_names) == 0:
        return ""

    ########################################
    # Sort the lists
    ########################################
    if len(unique_translation_names) != 0:
        unique_translation_variable_names, unique_translation_names = map(
            list, zip(*sorted(zip(
                unique_translation_variable_names, unique_translation_names))))
    if len(unique_timedelay_names) != 0:
        unique_timedelay_variable_names, unique_timedelay_names = map(
            list, zip(*sorted(zip(
                unique_timedelay_variable_names, unique_timedelay_names))))
    if len(unique_rotation_names) != 0:
        unique_rotation_variable_names, unique_rotation_names = map(
            list, zip(*sorted(zip(
                unique_rotation_variable_names, unique_rotation_names))))

    ########################################
    # Create Output string
    ########################################
    output_string = """
    ############################################################
    # Reference Shifts
    ############################################################
"""

    ########################################
    # Translations
    ########################################
    if len(unique_translation_names) != 0:
        output_string += """
    ########################################
    # Translations
    ########################################"""

        for translation_name, translation_variable_name in zip(
                unique_translation_names, unique_translation_variable_names):

            dx  = line[translation_name].shift_x
            dy  = line[translation_name].shift_y

            if dx != 0:
                output_string += f"""
    {f'dx_{translation_variable_name}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'dx_{translation_variable_name}') + 4)}{'= '}{dx:.24f},"""
            if dy != 0:
                output_string += f"""
    {f'dy_{translation_variable_name}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'dy_{translation_variable_name}') + 4)}{'= '}{dy:.24f},"""

        output_string += "\n"

    ########################################
    # TimeDelays
    ########################################
    if len(unique_timedelay_names) != 0:
        output_string += """
    ########################################
    # TimeDelays
    ########################################"""

        for timedelay_name, timedelay_variable_name in zip(
                unique_timedelay_names, unique_timedelay_variable_names):

            dz  = line[timedelay_name].shift_zeta

            if dz != 0:
                output_string += f"""
    {f'dz_{timedelay_variable_name}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'dz_{timedelay_variable_name}') + 4)}{'= '}{dz:.24f},"""

        output_string += "\n"

    ########################################
    # Rotations (CHI1/CHI2/CHI3)
    ########################################
    if len(unique_rotation_names) != 0:
        output_string += """
    ########################################
    # Rotations (CHI1/CHI2/CHI3)
    ########################################"""

        for rotation_name, rotation_variable_name in zip(
                unique_rotation_names, unique_rotation_variable_names):

            chi1 = line[rotation_name].rot_y_rad
            chi2 = line[rotation_name].rot_x_rad
            chi3 = line[rotation_name].rot_s_rad

            if chi1 != 0:
                output_string += f"""
    {f'chi1_{rotation_variable_name}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'chi1_{rotation_variable_name}') + 4)}{'= '}{chi1:.24f},"""
            if chi2 != 0:
                output_string += f"""
    {f'chi2_{rotation_variable_name}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'chi2_{rotation_variable_name}') + 4)}{'= '}{chi2:.24f},"""
            if chi3 != 0:
                output_string += f"""
    {f'chi3_{rotation_variable_name}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'chi3_{rotation_variable_name}') + 4)}{'= '}{chi3:.24f},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
