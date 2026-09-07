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
    these elements carry. Every float is written by `get_value_string`,
    like every other scalar in this package.

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
        return get_value_string(float(array))
    return "[" + ", ".join(
        _format_taylor_map_array(sub_array) for sub_array in array) + "]"

########################################
# Generated SAD Fringe Helper
########################################
def _sad_fringe_taylor_map_helper_source() -> str:
    """
    Return the self-contained SAD fringe helper for generated lattice files.

    Returns
    -------
    str
        Python source defining `_create_sad_fringe_taylor_map`. The helper
        uses only NumPy and Xtrack objects already imported by the generated
        lattice, so reloading does not depend on SAD2XS being installed.
    """
    return '''
def _create_sad_fringe_taylor_map(
        environment,
        name,
        soft_quadrupole = None,
        hard_dipole = None,
        alignment = None,
        is_exit = False):
    """
    Add one supported SAD fringe Taylor map to an Xsuite environment.

    The physical map is stored in the element's canonical k, R, and T
    coefficients. Its physical inputs are recorded in Environment.metadata,
    so reversal can reconstruct the opposite face after reloading.

    Parameters
    ----------
    environment : xtrack.Environment
        Environment receiving the new element.
    name : str
        Name of the new SecondOrderTaylorMap element.
    soft_quadrupole : dict or None, optional
        Soft F1/F2 component in its quadrupolar field frame.
    hard_dipole : dict or None, optional
        Hard K0/SK0 component in the parent magnet frame.
    alignment : dict or None, optional
        Parent magnet shift_x, shift_y, and rot_s_rad.
    is_exit : bool, optional
        Whether this is the exit face.

    Returns
    -------
    None
    """
    ########################################
    # Value Helpers
    ########################################
    def resolve(value):
        if isinstance(value, str):
            return environment.vars.new_expr(value)
        return value

    def exponential(value):
        if isinstance(value, (int, float, np.number)):
            return np.exp(value)
        return environment.functions.exp(value)

    def negate(value):
        if isinstance(value, (int, float, np.number)):
            return -value
        return f"-({value})"

    ########################################
    # Taylor Operations
    ########################################
    def rotate(coefficients, rotation):
        k_local, R_local, T_local = coefficients
        cosine = np.cos(rotation)
        sine   = np.sin(rotation)
        coordinates = np.eye(6)
        coordinates[0, 0] = coordinates[1, 1] = cosine
        coordinates[0, 2] = coordinates[1, 3] = sine
        coordinates[2, 0] = coordinates[3, 1] = -sine
        coordinates[2, 2] = coordinates[3, 3] = cosine
        return (
            coordinates.T @ k_local,
            coordinates.T @ R_local @ coordinates,
            np.einsum(
                "ia,abc,bj,ck->ijk", coordinates.T, T_local,
                coordinates, coordinates))

    def compose(first, second):
        k_first, R_first, T_first    = first
        k_second, R_second, T_second = second
        k_result = k_second + R_second @ k_first + np.einsum(
            "imn,m,n->i", T_second, k_first, k_first)
        R_result = R_second @ R_first
        R_result += np.einsum(
            "imn,m,nj->ij", T_second, k_first, R_first)
        R_result += np.einsum(
            "imn,mj,n->ij", T_second, R_first, k_first)
        T_result = np.einsum("im,mjk->ijk", R_second, T_first)
        T_result += np.einsum(
            "imn,mj,nk->ijk", T_second, R_first, R_first)
        T_result += np.einsum(
            "imn,m,njk->ijk", T_second, k_first, T_first)
        T_result += np.einsum(
            "imn,mjk,n->ijk", T_second, T_first, k_first)
        return k_result, R_result, T_result

    ########################################
    # Parent Alignment
    ########################################
    alignment = {} if alignment is None else alignment.copy()
    alignment.setdefault("shift_x",   0.0)
    alignment.setdefault("shift_y",   0.0)
    alignment.setdefault("rot_s_rad", 0.0)

    ########################################
    # Soft Quadrupolar Map
    ########################################
    if soft_quadrupole is None:
        soft = np.zeros(6), np.eye(6), np.zeros((6, 6, 6))
    else:
        a_value = resolve(soft_quadrupole["a"])
        b_value = resolve(soft_quadrupole["b"])
        exp_a   = exponential(a_value)
        exp_ma  = exponential(-a_value)
        k_soft  = np.zeros(6, dtype = object)
        R_soft  = np.zeros((6, 6), dtype = object)
        T_soft  = np.zeros((6, 6, 6), dtype = object)
        R_soft[0, 0], R_soft[0, 1], R_soft[1, 1] = exp_a, b_value, exp_ma
        R_soft[2, 2], R_soft[2, 3], R_soft[3, 3] = exp_ma, -b_value, exp_a
        R_soft[4, 4] = R_soft[5, 5] = 1.0
        T_soft[0, 0, 5] = T_soft[0, 5, 0] = -a_value * exp_a / 2.0
        T_soft[0, 1, 5] = T_soft[0, 5, 1] = -b_value
        T_soft[1, 1, 5] = T_soft[1, 5, 1] = a_value * exp_ma / 2.0
        T_soft[2, 2, 5] = T_soft[2, 5, 2] = a_value * exp_ma / 2.0
        T_soft[2, 3, 5] = T_soft[2, 5, 3] = b_value
        T_soft[3, 3, 5] = T_soft[3, 5, 3] = -a_value * exp_a / 2.0
        T_soft[4, 1, 1] = -b_value * exp_ma * (1.0 + a_value / 2.0)
        T_soft[4, 3, 3] = b_value * exp_a * (1.0 - a_value / 2.0)
        T_soft[4, 0, 1] = T_soft[4, 1, 0] = -a_value / 2.0
        T_soft[4, 2, 3] = T_soft[4, 3, 2] = a_value / 2.0
        soft = k_soft, R_soft, T_soft
        relative_rotation = soft_quadrupole.get("relative_rotation", 0.0)
        if relative_rotation != 0.0:
            soft = rotate(soft, relative_rotation)

    ########################################
    # Hard Dipolar Map
    ########################################
    coefficients = soft
    if hard_dipole is not None:
        magnitude = np.hypot(hard_dipole["k0"], hard_dipole["sk0"])
        k_hard    = np.zeros(6)
        R_hard    = np.eye(6)
        T_hard    = np.zeros((6, 6, 6))
        if magnitude != 0.0:
            face_sign = -1.0 if is_exit else 1.0
            scale     = face_sign * magnitude / hard_dipole["length"]
            T_hard[0, 2, 2] = 0.5 * scale
            T_hard[3, 1, 2] = T_hard[3, 2, 1] = -0.5 * scale
            angle = np.arctan2(hard_dipole["sk0"], hard_dipole["k0"])
            # Field conjugation is opposite to a map-to-parent frame rotation.
            hard = rotate((k_hard, R_hard, T_hard), -angle)
        else:
            hard = k_hard, R_hard, T_hard
        if is_exit:
            coefficients = compose(soft, hard)
        else:
            coefficients = compose(hard, soft)

    ########################################
    # Create Fringe Element
    ########################################
    k, R, T = coefficients
    environment.new(
        name        = name,
        prototype   = xt.SecondOrderTaylorMap,
        length      = 0.0,
        k           = k,
        R           = R,
        T           = T,
        **alignment)

    ########################################
    # Store Physical Metadata
    ########################################
    sad2xs  = environment.metadata.setdefault("sad2xs", {})
    fringes = sad2xs.setdefault("fringe_taylor_maps", {})
    if soft_quadrupole is None:
        metadata = {
            "a": 0.0, "b": 0.0,
            "field_rotation": negate(alignment["rot_s_rad"])}
    else:
        relative_rotation = soft_quadrupole.get("relative_rotation", 0.0)
        field_rotation = negate(alignment["rot_s_rad"])
        if relative_rotation != 0.0:
            field_rotation = -relative_rotation - alignment["rot_s_rad"]
        metadata = {
            "a": soft_quadrupole["a"], "b": soft_quadrupole["b"],
            "field_rotation": field_rotation}
        if relative_rotation != 0.0:
            metadata["relative_rotation"] = relative_rotation
    metadata["shift_x"] = alignment["shift_x"]
    metadata["shift_y"] = alignment["shift_y"]
    if hard_dipole is not None or "relative_rotation" in metadata:
        metadata["parent_rotation"] = alignment["rot_s_rad"]
        metadata["is_exit"]         = is_exit
    if hard_dipole is not None:
        metadata["hard_dipole"] = hard_dipole
    fringes[name] = metadata
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

    Registered SAD fringe maps are emitted as compact calls containing their
    physical soft-quadrupolar and hard-dipolar components plus the parent
    alignment. A local helper reconstructs the canonical Taylor coefficients
    and preserves live QUAD-strength expressions without making the generated
    file import SAD2XS. Generic maps retain literal tensor serialization.

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
        "sad2xs", {}).get("fringe_taylor_maps", {})
    written_fringe_names = {
        name for name in unique_second_order_names
        if name in fringe_parameters}
    if written_fringe_names:
        output_string += _sad_fringe_taylor_map_helper_source()

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
    length      = {get_value_string(element.length)},
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
            soft_quadrupole = "None"
            if parameters["a"] != 0.0 or parameters["b"] != 0.0:
                soft_quadrupole = f'''{{
        "a": {get_value_string(parameters["a"])},
        "b": {get_value_string(parameters["b"])}'''
                if "relative_rotation" in parameters:
                    soft_quadrupole += f''',
        "relative_rotation": {get_value_string(parameters["relative_rotation"])}'''
                soft_quadrupole += "}"

            hard_dipole = "None"
            if "hard_dipole" in parameters:
                hard = parameters["hard_dipole"]
                hard_dipole = f'''{{
        "k0": {get_value_string(hard["k0"])},
        "sk0": {get_value_string(hard["sk0"])},
        "length": {get_value_string(hard["length"])}}}'''

            parent_rotation = parameters.get("parent_rotation")
            if parent_rotation is None:
                field_rotation = parameters["field_rotation"]
                parent_rotation = (
                    f"-({field_rotation})" if isinstance(field_rotation, str)
                    else -field_rotation)

            alignment_values = {
                "shift_x":   parameters["shift_x"],
                "shift_y":   parameters["shift_y"],
                "rot_s_rad": parent_rotation}
            active_alignment = {
                key: value for key, value in alignment_values.items()
                if isinstance(value, str) or value != 0.0}
            alignment = "None"
            if active_alignment:
                alignment = "{\n" + ",\n".join(
                    f'        "{key}": {get_value_string(value)}'
                    for key, value in active_alignment.items()) + "}"
            arguments = [
                "    environment         = env",
                f'    name                = "{name}"']
            if soft_quadrupole != "None":
                arguments.append(
                    f"    soft_quadrupole     = {soft_quadrupole}")
            if hard_dipole != "None":
                arguments.append(
                    f"    hard_dipole         = {hard_dipole}")
            if alignment != "None":
                arguments.append(f"    alignment           = {alignment}")
            if parameters.get("is_exit", False):
                arguments.append("    is_exit             = True")
            output_string += "\n_create_sad_fringe_taylor_map(\n"
            output_string += ",\n".join(arguments) + ")"
            continue

        output_string   += f"""
env.new(
    name        = "{name}",
    prototype   = xt.SecondOrderTaylorMap,
    length      = {get_value_string(element.length)},
    k           = {_format_taylor_map_array(element.k)},
    R           = {_format_taylor_map_array(element.R)},
    T           = {_format_taylor_map_array(element.T)},
    shift_x     = {get_value_string(element.shift_x)},
    shift_y     = {get_value_string(element.shift_y)},
    rot_s_rad   = {get_value_string(element.rot_s_rad)})"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
