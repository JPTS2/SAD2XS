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

from ._000_helpers import get_parentname
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_aperture_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Docstring for create_aperture_lattice_file_information
    
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
    unique_limitellipse_names   = []
    unique_limitrect_names      = []

    for limitellipse in line_table.rows[line_table.element_type == 'LimitEllipse'].name:
        parentname      = get_parentname(limitellipse)
        if parentname not in unique_limitellipse_names:
            unique_limitellipse_names.append(parentname)

    for limitrect in line_table.rows[line_table.element_type == 'LimitRect'].name:
        parentname      = get_parentname(limitrect)
        if parentname not in unique_limitrect_names:
            unique_limitrect_names.append(parentname)

    ########################################
    # Ensure there are reference shifts in the line
    ########################################
    if len(unique_limitellipse_names) == 0 and \
            len(unique_limitrect_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Apertures
############################################################
"""

    ########################################
    # Limit Ellipses
    ########################################
    if len(unique_limitellipse_names) != 0:
        output_string += """
########################################
# Limit Ellipses
########################################"""

        for limitellipse_name in unique_limitellipse_names:

            # Get the replica information
            a           = line[limitellipse_name].a
            b           = line[limitellipse_name].b
            shift_x     = line[limitellipse_name].shift_x
            shift_y     = line[limitellipse_name].shift_y

            # Remove the minus sign if no non minus version exists
            if limitellipse_name.startswith("-"):
                root_name   = limitellipse_name[1:]
                if root_name not in unique_limitellipse_names:
                    limitellipse_name        = root_name

            output_string += f"""
env.new(
    name        = '{limitellipse_name}',
    parent      = xt.LimitEllipse,
    a           = {a},
    b           = {b},
    shift_x     = {shift_x},
    shift_y     = {shift_y})"""

        output_string += "\n"

    ########################################
    # Limit Rects
    ########################################
    if len(unique_limitrect_names) != 0:
        output_string += """
########################################
# Limit Rects
########################################"""

        for limitrect_name in unique_limitrect_names:

            # Get the replica information
            min_x       = line[limitrect_name].min_x
            max_x       = line[limitrect_name].max_x
            min_y       = line[limitrect_name].min_y
            max_y       = line[limitrect_name].max_y
            shift_x     = line[limitrect_name].shift_x
            shift_y     = line[limitrect_name].shift_y

            # Remove the minus sign if no non minus version exists
            if limitrect_name.startswith("-"):
                root_name   = limitrect_name[1:]
                if root_name not in unique_limitrect_names:
                    limitrect_name        = root_name

            output_string += f"""
env.new(
    name        = '{limitrect_name}',
    parent      = xt.LimitRect,
    min_x       = {min_x},
    max_x       = {max_x},
    min_y       = {min_y},
    max_y       = {max_y},
    shift_x     = {shift_x},
    shift_y     = {shift_y})"""

        output_string += "\n"

    return output_string
