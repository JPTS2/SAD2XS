"""
================================================================================
Output Writer: Taylor Maps
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-03
================================================================================
"""

################################################################################
# Required Packages
################################################################################
import numpy as np
import xtrack as xt

from ._000_helpers import get_parentname, get_value_string
from ..types import ConfigLike

################################################################################
# Array Formatting
################################################################################
def _format_taylor_map_array(values) -> str:
    """
    Format a Taylor-map coefficient array as a nested Python list
    literal, one float per entry.

    Recurses over `values`'s dimensions (1D for `k`/`m0`, 2D for `R`/
    `m1`, 3D for `T`), so the same helper covers every array shape
    these elements carry. Every float is written to full round-trip
    precision (`.24e`), matching the KNL/KSL convention
    (`get_knl_string`) rather than the `.24f` used for single physical
    scalars elsewhere in this package -- these coefficients can span
    many orders of magnitude and are not individually meaningful
    physical quantities on their own.

    Parameters
    ----------
    values : array_like
        The coefficient array (or a scalar, at the base of the
        recursion).

    Returns
    -------
    str
        A Python list literal (or float literal, for a scalar).
    """
    array = np.asarray(values)
    if array.ndim == 0:
        return f"{float(array):.24e}"
    return "[" + ", ".join(
        _format_taylor_map_array(sub_array) for sub_array in array) + "]"

########################################
# Generated SAD Fringe Helper
########################################
def _sad_soft_quadrupolar_fringe_helper_source() -> str:
    """
    Return the self-contained SAD fringe helper for generated lattice files.

    Returns
    -------
    str
        Python source defining `_create_sad_soft_quadrupolar_fringe`. The helper
        uses only NumPy and Xtrack objects already imported by the generated
        lattice, so reloading does not depend on SAD2XS being installed.
    """
    return '''
def _create_sad_soft_quadrupolar_fringe(
        environment,
        name,
        a,
        b,
        field_rotation,
        shift_x = 0.0,
        shift_y = 0.0):
    """
    Add one SAD K1/SK1 soft-edge map to an Xsuite environment.

    The physical map is stored in the element's canonical k, R, and T
    coefficients. Its five defining quantities are recorded once in
    Environment.metadata, so a reloaded lattice carries the same fringe
    information as a freshly converted one.

    Parameters
    ----------
    environment : xtrack.Environment
        Environment receiving the new element.
    name : str
        Name of the new SecondOrderTaylorMap element.
    a : float or str
        Dimensionless signed F1 coefficient for this face.
    b : float or str
        F2 coefficient in metres for this face.
    field_rotation : float or str
        SAD transverse field-frame rotation in radians.
    shift_x : float or str, optional
        Horizontal displacement of the magnet axis in metres. Defaults to
        zero.
    shift_y : float or str, optional
        Vertical displacement of the magnet axis in metres. Defaults to zero.

    Returns
    -------
    None
    """
    def resolve(value):
        return environment.vars.new_expr(value) if isinstance(value, str) else value

    def exponential(value):
        if isinstance(value, (int, float, np.number)):
            return np.exp(value)
        return environment.functions.exp(value)

    a_value = resolve(a)
    b_value = resolve(b)
    exp_a   = exponential(a_value)
    exp_ma  = exponential(-a_value)

    k = np.zeros(6, dtype = object)
    R = np.zeros((6, 6), dtype = object)
    T = np.zeros((6, 6, 6), dtype = object)
    R[0, 0], R[0, 1], R[1, 1] = exp_a, b_value, exp_ma
    R[2, 2], R[2, 3], R[3, 3] = exp_ma, -b_value, exp_a
    R[4, 4] = R[5, 5] = 1.0
    T[0, 0, 5] = T[0, 5, 0] = -a_value * exp_a / 2.0
    T[0, 1, 5] = T[0, 5, 1] = -b_value
    T[1, 1, 5] = T[1, 5, 1] = a_value * exp_ma / 2.0
    T[2, 2, 5] = T[2, 5, 2] = a_value * exp_ma / 2.0
    T[2, 3, 5] = T[2, 5, 3] = b_value
    T[3, 3, 5] = T[3, 5, 3] = -a_value * exp_a / 2.0
    T[4, 1, 1] = -b_value * exp_ma * (1.0 + a_value / 2.0)
    T[4, 3, 3] = b_value * exp_a * (1.0 - a_value / 2.0)
    T[4, 0, 1] = T[4, 1, 0] = -a_value / 2.0
    T[4, 2, 3] = T[4, 3, 2] = a_value / 2.0

    rot_s_rad = -resolve(field_rotation)
    environment.new(
        name        = name,
        prototype   = xt.SecondOrderTaylorMap,
        length      = 0.0,
        k           = k,
        R           = R,
        T           = T,
        shift_x     = shift_x,
        shift_y     = shift_y,
        rot_s_rad   = rot_s_rad)
    sad2xs  = environment.metadata.setdefault("sad2xs", {})
    fringes = sad2xs.setdefault("soft_quadrupolar_fringes", {})
    fringes[name] = {
        "a":              a,
        "b":              b,
        "field_rotation": field_rotation,
        "shift_x":        shift_x,
        "shift_y":        shift_y}
'''

################################################################################
# Lattice File
################################################################################
def create_taylor_map_lattice_file_information(
        line:       xt.Line,
        line_table: xt.Table,
        config:     ConfigLike) -> str:
    """
    Generate the lattice-file source for every FirstOrderTaylorMap and
    SecondOrderTaylorMap element.

    Generic maps are not grouped/cloned: two Taylor maps
    sharing every coefficient by coincidence would still gain nothing
    from cloning, and in practice every generic map's (k, R, T) or
    (m0, m1) is a distinct, per-element derived result. Each generic map is
    therefore written with the full coefficient arrays as literals.

    SAD soft quadrupolar fringe maps are emitted as compact calls containing
    their physical ``a``, ``b``, field rotation, and offsets. A short local
    helper reconstructs the canonical Taylor coefficients and preserves live
    QUAD-strength expressions without making the generated file import
    SAD2XS. Generic maps retain literal tensor serialization.

    Parameters
    ----------
    line : xt.Line
        The converted line to generate Taylor-map source for.
    line_table : xt.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Accepted for interface consistency with the other
        `create_*_lattice_file_information` functions; not used
        directly by this function.

    Returns
    -------
    str
        The generated Python source for this section, or "" if the
        line has no Taylor-map elements.
    """

    ########################################
    # Get information
    ########################################
    unique_first_order_names   = []
    for taylor_map in line_table.rows[line_table.element_type == "FirstOrderTaylorMap"].name:
        parentname = get_parentname(taylor_map)
        if parentname not in unique_first_order_names:
            unique_first_order_names.append(parentname)

    unique_second_order_names  = []
    for taylor_map in line_table.rows[line_table.element_type == "SecondOrderTaylorMap"].name:
        parentname = get_parentname(taylor_map)
        if parentname not in unique_second_order_names:
            unique_second_order_names.append(parentname)

    ########################################
    # Ensure there are Taylor maps in the line
    ########################################
    if len(unique_first_order_names) == 0 and len(unique_second_order_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Taylor Maps
############################################################"""

    fringe_parameters = line.env.metadata.get(
        "sad2xs", {}).get("soft_quadrupolar_fringes", {})
    written_fringe_names = {
        name for name in unique_second_order_names
        if name in fringe_parameters}
    if written_fringe_names:
        output_string += _sad_soft_quadrupolar_fringe_helper_source()

    ########################################
    # First order Taylor maps
    ########################################
    for name in unique_first_order_names:

        element = line[name]

        # Remove the minus sign if no non minus version exists
        if name.startswith("-"):
            root_name   = name[1:]
            if root_name not in unique_first_order_names:
                name    = root_name

        output_string   += f"""
env.new(
    name        = "{name}",
    prototype   = xt.FirstOrderTaylorMap,
    length      = {element.length:.24f},
    m0          = {_format_taylor_map_array(element.m0)},
    m1          = {_format_taylor_map_array(element.m1)})"""

    ########################################
    # Second order Taylor maps
    ########################################
    for source_name in unique_second_order_names:

        element = line[source_name]
        name    = source_name

        # Remove the minus sign if no non minus version exists
        if name.startswith("-"):
            root_name   = name[1:]
            if root_name not in unique_second_order_names:
                name    = root_name

        if source_name in fringe_parameters:
            parameters = fringe_parameters[source_name]
            output_string += f"""
_create_sad_soft_quadrupolar_fringe(
    environment     = env,
    name            = "{name}",
    a               = {get_value_string(parameters["a"])},
    b               = {get_value_string(parameters["b"])},
    field_rotation  = {get_value_string(parameters["field_rotation"])}"""

            # Offsets are zero for most fringes, and default to zero in the helper
            for offset in ("shift_x", "shift_y"):
                value = parameters[offset]
                if isinstance(value, str) or value != 0.0:
                    output_string += f""",
    {offset:<15} = {get_value_string(value)}"""

            output_string += ")"
            continue

        output_string   += f"""
env.new(
    name        = "{name}",
    prototype   = xt.SecondOrderTaylorMap,
    length      = {element.length:.24f},
    k           = {_format_taylor_map_array(element.k)},
    R           = {_format_taylor_map_array(element.R)},
    T           = {_format_taylor_map_array(element.T)},
    shift_x     = {element.shift_x:.24e},
    shift_y     = {element.shift_y:.24e},
    rot_s_rad   = {element.rot_s_rad:.24e})"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
