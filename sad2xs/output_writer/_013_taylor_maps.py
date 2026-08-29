"""
================================================================================
Output Writer: Taylor Maps
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-08-29
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


_SAD_K1_FRINGE_WRITER_HELPER = r'''
def _new_sad_k1_fringe_map(env, *, name, a, b, frame_rotation_rad):
    """Rebuild a zero-BZ SAD K1 soft-edge map without literal tensors."""
    ea, eam = np.exp(a), np.exp(-a)
    k = np.zeros(6)
    R = np.zeros((6, 6))
    T = np.zeros((6, 6, 6))

    R[0, 0], R[0, 1], R[1, 1] = ea, b, eam
    R[2, 2], R[2, 3], R[3, 3] = eam, -b, ea
    R[4, 4] = R[5, 5] = 1.0

    T[0, 0, 5] = T[0, 5, 0] = -a * ea / 2.0
    T[0, 1, 5] = T[0, 5, 1] = -b
    T[1, 1, 5] = T[1, 5, 1] = a * eam / 2.0
    T[2, 2, 5] = T[2, 5, 2] = a * eam / 2.0
    T[2, 3, 5] = T[2, 5, 3] = b
    T[3, 3, 5] = T[3, 5, 3] = -a * ea / 2.0
    T[4, 1, 1] = -b * eam * (1.0 + a / 2.0)
    T[4, 3, 3] = b * ea * (1.0 - a / 2.0)
    T[4, 0, 1] = T[4, 1, 0] = -a / 2.0
    T[4, 2, 3] = T[4, 3, 2] = a / 2.0

    c, s = np.cos(frame_rotation_rad), np.sin(frame_rotation_rad)
    rotate_in = np.eye(6)
    rotate_in[0, 0], rotate_in[0, 2] = c, -s
    rotate_in[1, 1], rotate_in[1, 3] = c, -s
    rotate_in[2, 0], rotate_in[2, 2] = s, c
    rotate_in[3, 1], rotate_in[3, 3] = s, c
    rotate_out = rotate_in.T

    env.new(
        name        = name,
        prototype   = xt.SecondOrderTaylorMap,
        length      = 0.0,
        k           = rotate_out @ k,
        R           = rotate_out @ R @ rotate_in,
        T           = np.einsum(
            "ia,abc,bj,ck->ijk", rotate_out, T, rotate_in, rotate_in),
        _sad_k1_fringe_a              = a,
        _sad_k1_fringe_b              = b,
        _sad_k1_fringe_frame_rotation = frame_rotation_rad)
'''

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

    Generic maps are not grouped/cloned: two Taylor maps
    sharing every coefficient by coincidence would still gain nothing
    from cloning, and in practice every map's (k, R, T) or (m0, m1)
    is a distinct, per-element derived result (e.g. one SAD QUAD's own
    linear fringe, entrance and exit built separately -- see
    `_004_element_converter._new_quad_fringe_element`), so each is
    written individually with the full coefficient arrays as literals.

    SAD K1 fringe maps are the exception. Their three scalar parameters
    reconstruct the tensors exactly, so one generated helper and one compact
    call per map avoid embedding hundreds of mostly-zero coefficients. The
    scalar metadata is passed through `env.new`, keeping the generated file
    self-contained and preserving reversal support. Pre-0.4 QUAD metadata is
    still serialized by the legacy literal path for compatibility.

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

    if any(hasattr(line[name], "_sad_k1_fringe_a")
           for name in unique_second_order_names):
        output_string += "\n" + _SAD_K1_FRINGE_WRITER_HELPER

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

        if hasattr(element, "_sad_k1_fringe_a"):
            output_string += f'''
_new_sad_k1_fringe_map(
    env,
    name = "{name}",
    a = {element._sad_k1_fringe_a:.24e},
    b = {element._sad_k1_fringe_b:.24e},
    frame_rotation_rad = {element._sad_k1_fringe_frame_rotation:.24e})'''
            continue

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
