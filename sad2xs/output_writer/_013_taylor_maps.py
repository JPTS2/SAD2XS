"""
================================================================================
Output Writer: Taylor Maps
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-24
================================================================================
"""

################################################################################
# Import Packages
################################################################################
import numpy as np
import xtrack as xt
import xdeps as xd

from ._000_helpers import get_parentname
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

################################################################################
# Lattice File
################################################################################
def create_taylor_map_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the lattice-file source for every FirstOrderTaylorMap and
    SecondOrderTaylorMap element.

    Like cavities, these are not grouped/cloned: two Taylor maps
    sharing every coefficient by coincidence would still gain nothing
    from cloning, and in practice every map's (k, R, T) or (m0, m1)
    is a distinct, per-element derived result (e.g. one SAD QUAD's own
    linear fringe, entrance and exit built separately -- see
    `_004_element_converter._new_quad_fringe_element`), so each is
    written individually with the full coefficient arrays as literals.

    A SecondOrderTaylorMap built by `_new_quad_fringe_element` also
    carries three plain (non-xofield) Python attributes --
    `_sad_quad_fringe_a`/`_sad_quad_fringe_b`/`_sad_quad_fringe_theta`
    -- that `_007_reversals.py`'s reversal fix-up needs to rebuild the
    map correctly under `-LINE`/`reverse_element_order`. Where present,
    these are written as three follow-up assignment lines after the
    element is created, so a written-and-reloaded line still supports
    that fix-up.

    Parameters
    ----------
    line : xt.Line
        The converted line to generate Taylor-map source for.
    line_table : xd.table.Table
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
    for name in unique_second_order_names:

        element = line[name]

        # Remove the minus sign if no non minus version exists
        if name.startswith("-"):
            root_name   = name[1:]
            if root_name not in unique_second_order_names:
                name    = root_name

        output_string   += f"""
env.new(
    name        = "{name}",
    prototype   = xt.SecondOrderTaylorMap,
    length      = {element.length:.24f},
    k           = {_format_taylor_map_array(element.k)},
    R           = {_format_taylor_map_array(element.R)},
    T           = {_format_taylor_map_array(element.T)})"""

        # Preserve the SAD quad-fringe reversal metadata, if present
        if hasattr(element, "_sad_quad_fringe_a"):
            output_string   += f"""
env.elements["{name}"]._sad_quad_fringe_a      = {element._sad_quad_fringe_a:.24e}
env.elements["{name}"]._sad_quad_fringe_b      = {element._sad_quad_fringe_b:.24e}
env.elements["{name}"]._sad_quad_fringe_theta  = {element._sad_quad_fringe_theta:.24e}"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
