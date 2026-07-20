"""
================================================================================
Output Writer: Apertures
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-20
================================================================================
"""

################################################################################
# Import Packages
################################################################################
import xtrack as xt
import xdeps as xd

from ._000_helpers import get_parentname
from ..types import ConfigLike

################################################################################
# Helpers
################################################################################
def _get_unique_aperture_names(line_table: xd.table.Table) -> tuple:
    """
    Collect the unique prototype names of each aperture type in the line.

    :param line_table: Table describing the line elements.
    :return: (unique_limitellipse_names, unique_limitrect_names,
        unique_limitrectellipse_names)
    """
    unique_limitellipse_names       = []
    unique_limitrect_names          = []
    unique_limitrectellipse_names   = []

    for limitellipse in line_table.rows[line_table.element_type == 'LimitEllipse'].name:
        parentname      = get_parentname(limitellipse)
        if parentname not in unique_limitellipse_names:
            unique_limitellipse_names.append(parentname)

    for limitrect in line_table.rows[line_table.element_type == 'LimitRect'].name:
        parentname      = get_parentname(limitrect)
        if parentname not in unique_limitrect_names:
            unique_limitrect_names.append(parentname)

    for limitrectellipse in line_table.rows[line_table.element_type == 'LimitRectEllipse'].name:
        parentname      = get_parentname(limitrectellipse)
        if parentname not in unique_limitrectellipse_names:
            unique_limitrectellipse_names.append(parentname)

    return (
        unique_limitellipse_names,
        unique_limitrect_names,
        unique_limitrectellipse_names)


def _resolve_aperture_name(aperture_name: str, unique_names: list) -> str:
    """
    Strip a leading minus sign when no non-minus version of the name exists.

    This mirrors the naming used elsewhere in the writers so that the lattice
    file element name and the optics file variable name always agree.
    """
    if aperture_name.startswith("-"):
        root_name   = aperture_name[1:]
        if root_name not in unique_names:
            return root_name
    return aperture_name


def _optics_variable_line(variable_name: str, value: float, config: ConfigLike) -> str:
    """
    Format a single `name = value` optics variable line.
    """
    padding = ' ' * (config.OUTPUT_STRING_SEP - len(variable_name) + 4)
    return f"""
    {variable_name}{padding}{'= '}{value:.24f},"""

################################################################################
# Lattice File
################################################################################
def create_aperture_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Write env.new() calls for all aperture elements in the line.
    Dimensions are referenced as named variables; bootstrapped to safe
    placeholders so LimitEllipse can be constructed before the optics file.
    """

    ########################################
    # Get information
    ########################################
    unique_limitellipse_names, unique_limitrect_names, \
        unique_limitrectellipse_names = _get_unique_aperture_names(line_table)

    ########################################
    # Ensure there are apertures in the line
    ########################################
    if len(unique_limitellipse_names) == 0 and \
            len(unique_limitrect_names) == 0 and \
            len(unique_limitrectellipse_names) == 0:
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

            shift_x     = line[limitellipse_name].shift_x
            shift_y     = line[limitellipse_name].shift_y
            rot_s_rad   = line[limitellipse_name].rot_s_rad

            limitellipse_name   = _resolve_aperture_name(
                limitellipse_name, unique_limitellipse_names)

            # LimitEllipse rejects a/b=0; bootstrap to 1.0 until optics file sets values.
            ellipse_generation = f"""
env['a_{limitellipse_name}'] = 1.0
env['b_{limitellipse_name}'] = 1.0
env.new(
    name        = '{limitellipse_name}',
    prototype   = xt.LimitEllipse,
    a           = 'a_{limitellipse_name}',
    b           = 'b_{limitellipse_name}',
    shift_x     = {shift_x},
    shift_y     = {shift_y}"""
            if rot_s_rad != 0:
                ellipse_generation += f""",
    rot_s_rad   = {rot_s_rad}"""
            ellipse_generation += ")"

            output_string += ellipse_generation

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

            shift_x     = line[limitrect_name].shift_x
            shift_y     = line[limitrect_name].shift_y
            rot_s_rad   = line[limitrect_name].rot_s_rad

            limitrect_name      = _resolve_aperture_name(
                limitrect_name, unique_limitrect_names)

            rect_generation = f"""
env['min_x_{limitrect_name}'] = -1.0
env['max_x_{limitrect_name}'] = 1.0
env['min_y_{limitrect_name}'] = -1.0
env['max_y_{limitrect_name}'] = 1.0
env.new(
    name        = '{limitrect_name}',
    prototype   = xt.LimitRect,
    min_x       = 'min_x_{limitrect_name}',
    max_x       = 'max_x_{limitrect_name}',
    min_y       = 'min_y_{limitrect_name}',
    max_y       = 'max_y_{limitrect_name}',
    shift_x     = {shift_x},
    shift_y     = {shift_y}"""
            if rot_s_rad != 0:
                rect_generation += f""",
    rot_s_rad   = {rot_s_rad}"""
            rect_generation += ")"

            output_string += rect_generation

        output_string += "\n"

    ########################################
    # Limit RectEllipses
    ########################################
    if len(unique_limitrectellipse_names) != 0:
        output_string += """
########################################
# Limit RectEllipses
########################################"""

        for limitrectellipse_name in unique_limitrectellipse_names:

            shift_x     = line[limitrectellipse_name].shift_x
            shift_y     = line[limitrectellipse_name].shift_y
            rot_s_rad   = line[limitrectellipse_name].rot_s_rad

            limitrectellipse_name   = _resolve_aperture_name(
                limitrectellipse_name, unique_limitrectellipse_names)

            rectellipse_generation = f"""
env['max_x_{limitrectellipse_name}'] = 1.0
env['max_y_{limitrectellipse_name}'] = 1.0
env['a_{limitrectellipse_name}'] = 1.0
env['b_{limitrectellipse_name}'] = 1.0
env.new(
    name        = '{limitrectellipse_name}',
    prototype   = xt.LimitRectEllipse,
    max_x       = 'max_x_{limitrectellipse_name}',
    max_y       = 'max_y_{limitrectellipse_name}',
    a           = 'a_{limitrectellipse_name}',
    b           = 'b_{limitrectellipse_name}',
    shift_x     = {shift_x},
    shift_y     = {shift_y}"""
            if rot_s_rad != 0:
                rectellipse_generation += f""",
    rot_s_rad   = {rot_s_rad}"""
            rectellipse_generation += ")"

            output_string += rectellipse_generation

        output_string += "\n"

    return output_string

################################################################################
# Optics File
################################################################################
def create_aperture_optics_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Write aperture dimensions as live optics variables so that they can be
    inspected and tuned via the optics file after reload.

    Each aperture dimension becomes a named variable of the form
    `<dim>_<aperture_name>` (e.g. a_ap1, b_ap1, min_x_ap1, max_x_ap1).

    :param line: The xtrack line object.
    :param line_table: Table describing the line elements.
    :param config: The conversion configuration.
    :return: The optics file fragment for apertures.
    """

    ########################################
    # Get information
    ########################################
    unique_limitellipse_names, unique_limitrect_names, \
        unique_limitrectellipse_names = _get_unique_aperture_names(line_table)

    ########################################
    # Ensure there are apertures in the line
    ########################################
    if len(unique_limitellipse_names) == 0 and \
            len(unique_limitrect_names) == 0 and \
            len(unique_limitrectellipse_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string = """
    ############################################################
    # Apertures
    ############################################################"""

    ########################################
    # Limit Ellipses
    ########################################
    for limitellipse_name in unique_limitellipse_names:
        a       = line[limitellipse_name].a
        b       = line[limitellipse_name].b
        name    = _resolve_aperture_name(limitellipse_name, unique_limitellipse_names)
        output_string += _optics_variable_line(f"a_{name}", a, config)
        output_string += _optics_variable_line(f"b_{name}", b, config)

    ########################################
    # Limit Rects
    ########################################
    for limitrect_name in unique_limitrect_names:
        min_x   = line[limitrect_name].min_x
        max_x   = line[limitrect_name].max_x
        min_y   = line[limitrect_name].min_y
        max_y   = line[limitrect_name].max_y
        name    = _resolve_aperture_name(limitrect_name, unique_limitrect_names)
        output_string += _optics_variable_line(f"min_x_{name}", min_x, config)
        output_string += _optics_variable_line(f"max_x_{name}", max_x, config)
        output_string += _optics_variable_line(f"min_y_{name}", min_y, config)
        output_string += _optics_variable_line(f"max_y_{name}", max_y, config)

    ########################################
    # Limit RectEllipses
    ########################################
    for limitrectellipse_name in unique_limitrectellipse_names:
        max_x   = line[limitrectellipse_name].max_x
        max_y   = line[limitrectellipse_name].max_y
        a       = line[limitrectellipse_name].a
        b       = line[limitrectellipse_name].b
        name    = _resolve_aperture_name(
            limitrectellipse_name, unique_limitrectellipse_names)
        output_string += _optics_variable_line(f"max_x_{name}", max_x, config)
        output_string += _optics_variable_line(f"max_y_{name}", max_y, config)
        output_string += _optics_variable_line(f"a_{name}", a, config)
        output_string += _optics_variable_line(f"b_{name}", b, config)

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
