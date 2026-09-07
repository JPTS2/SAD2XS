"""
================================================================================
Output Writer: Multipoles
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-07
================================================================================
"""

################################################################################
# Import Packages
################################################################################
import textwrap
import xtrack as xt
import xdeps as xd
import numpy as np

from ._000_helpers import extract_multipole_information, \
    generate_magnet_for_replication_names, check_is_simple_unpowered_multipole, \
    get_knl_string, get_parentname, get_value_string
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_multipole_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the lattice-file source for every Xsuite Multipole and
    MultipoleEdge element.

    Groups multipoles by quantized length (from
    `extract_multipole_information`), writes one base `xt.Multipole`
    per length (thick, with `config.MAX_KNL_ORDER` slots), then
    clones every individual multipole from its length's base element.
    A "simple" (unpowered, unshifted, unrotated) multipole (see
    `check_is_simple_unpowered_multipole`) is written as a bare clone;
    any other multipole is written with its full knl/ksl arrays and
    any non-zero offset/rotation. Unlike the typed magnets (bend,
    quad, sext, oct), multipole strengths are baked into the file as
    literal knl/ksl values, not referenced as live optics variables --
    there is no corresponding `create_multipole_optics_file_information`.
    MultipoleEdge elements are written directly with their normal/skew
    strengths, face flag and parent-magnet alignment. Registered SAD edges
    retain their metadata so lattice reversal remains available after reload.

    Parameters
    ----------
    line : xt.Line
        The converted line to generate multipole source for.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration (`MAGNET_LENGTH_PRECISION`,
        `MAX_KNL_ORDER`, `OUTPUT_STRING_LENGTH`).

    Returns
    -------
    str
        The generated Python source for this section, or "" if the
        line has no multipoles.
    """

    ########################################
    # Get information
    ########################################
    mults, unique_mult_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Multipole",
        config      = config)

    mult_lengths      = np.array(sorted(mults.keys()))
    mult_names        = generate_magnet_for_replication_names(mults, "mult", config.MAGNET_LENGTH_PRECISION)
    sad_fringe_edges  = line.env.metadata.get(
        "sad2xs", {}).get("mult_hard_quadrupolar_edges", {})

    unique_edge_names = []
    for edge in line_table.rows[
            line_table.element_type == "MultipoleEdge"].name:
        parentname = get_parentname(edge)
        if parentname not in unique_edge_names:
            unique_edge_names.append(parentname)

    ########################################
    # Ensure there are multipole elements in the line
    ########################################
    if len(unique_mult_names) == 0 and len(unique_edge_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Multipoles
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += """
########################################
# Base Elements
########################################"""

    for mult_name, mult_length in zip(mult_names, mult_lengths):
        output_string += f"""
env.new(
    name                = "{mult_name}",
    prototype           = xt.Multipole,
    length              = {mult_length},
    _isthick            = True,
    order               = {config.MAX_KNL_ORDER})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += """
########################################
# Cloned Elements
########################################"""

    for mult, mult_length in zip(mult_names, mult_lengths):
        for replica_name in mults[mult_length]:

            # Remove the minus sign if no non minus version exists
            if replica_name.startswith("-"):
                root_name   = replica_name[1:]
                if root_name not in mults[mult_length]:
                    replica_name        = root_name

            if check_is_simple_unpowered_multipole(line, replica_name):
                output_string += f"""
env.new(name = "{replica_name}", prototype = "{mult}")"""

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
    name        = "{replica_name}",
    prototype   = "{mult}\""""

                # Strength information                    
                if knl != "[]":
                    mult_generation += f""",
    {textwrap.fill(
        text                = f"knl         = {knl}",
        width               = config.OUTPUT_STRING_LENGTH,
        initial_indent      = "    ",
        subsequent_indent   = "        ",
        break_on_hyphens    = False)}"""
                if ksl != "[]":
                    mult_generation += f""",
    {textwrap.fill(
        text                = f"ksl         = {ksl}",
        width               = config.OUTPUT_STRING_LENGTH,
        initial_indent      = "    ",
        subsequent_indent   = "        ",
        break_on_hyphens    = False)}"""

                # Misalignments
                if shift_x != 0:
                    mult_generation += f""",
    shift_x     = "{shift_x}\""""
                if shift_y != 0:
                    mult_generation += f""",
    shift_y     = "{shift_y}\""""
                if rot_s_rad != 0:
                    mult_generation += f""",
    rot_s_rad   = "{rot_s_rad}\""""

                # Close the element definition
                mult_generation += """)"""

                # Write to the file
                output_string += mult_generation

    ########################################
    # Multipole Edges
    ########################################
    if unique_edge_names:
        output_string += """
########################################
# Multipole Edges
########################################"""

    for source_name in unique_edge_names:
        element = line[source_name]
        name    = source_name

        # Remove the minus sign if no non-minus version exists
        if name.startswith("-"):
            root_name = name[1:]
            if root_name not in unique_edge_names:
                name = root_name

        output_string += f"""
env.elements["{name}"] = xt.MultipoleEdge(
    kn          = {get_knl_string(element.kn)},
    ks          = {get_knl_string(element.ks)},
    order       = {int(element.order)},
    is_exit     = {bool(element.is_exit)},
    shift_x     = {get_value_string(element.shift_x)},
    shift_y     = {get_value_string(element.shift_y)},
    rot_s_rad   = {get_value_string(element.rot_s_rad)})"""
        if source_name in sad_fringe_edges:
            output_string += f"""
env.metadata.setdefault("sad2xs", {{}}).setdefault(
    "mult_hard_quadrupolar_edges", {{}})["{name}"] = {{}}"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
