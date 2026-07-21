"""
================================================================================
Output Writer: Solenoids
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-21
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
    generate_magnet_for_replication_names, get_knl_string
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_solenoid_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the lattice-file source for every UniformSolenoid
    element.

    Groups solenoids by quantized length (from
    `extract_multipole_information`), writes one base
    `xt.UniformSolenoid` per length (with `config.MAX_KNL_ORDER`
    slots), then clones every individual solenoid from its length's
    base element with its ks, any combined knl/ksl field (from
    elements absorbed into the solenoid region by
    `convert_solenoids`), and any non-zero offset/rotation/x0/y0.
    Unlike bend/quad/sext/oct, no separate optics file is written for
    solenoids -- ks and any combined field are baked in as literals.

    Parameters
    ----------
    line : xt.Line
        The converted line to generate solenoid source for.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration (`MAGNET_LENGTH_PRECISION`,
        `MAX_KNL_ORDER`, `OUTPUT_STRING_LENGTH`).

    Returns
    -------
    str
        The generated Python source for this section, or "" if the
        line has no solenoids.
    """

    ########################################
    # Get information
    ########################################
    sols, unique_sol_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "UniformSolenoid",
        config      = config)

    sol_lengths    = np.array(sorted(sols.keys()))
    sol_names      = generate_magnet_for_replication_names(sols, "sol", config.MAGNET_LENGTH_PRECISION)

    ########################################
    # Ensure there are solenoids in the line
    ########################################
    if len(unique_sol_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Solenoids
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += """
########################################
# Base Elements
########################################"""

    for sol_name, sol_length in zip(sol_names, sol_lengths):
        output_string += f"""
env.new(
    name                = "{sol_name}",
    prototype           = xt.UniformSolenoid,
    length              = {sol_length},
    order               = {config.MAX_KNL_ORDER})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += """
########################################
# Cloned Elements
########################################"""

    for sol, sol_length in zip(sol_names, sol_lengths):
        for replica_name in sols[sol_length]:

            # Get the replica information
            ks          = line[replica_name].ks
            knl         = get_knl_string(line[replica_name].knl)
            ksl         = get_knl_string(line[replica_name].ksl)
            shift_x     = line[replica_name].shift_x
            shift_y     = line[replica_name].shift_y
            rot_s_rad   = line[replica_name].rot_s_rad
            x0          = line[replica_name].x0
            y0          = line[replica_name].y0

            # Remove the minus sign if no non minus version exists
            if replica_name.startswith("-"):
                root_name   = replica_name[1:]
                if root_name not in sols[sol_length]:
                    replica_name        = root_name
            elif "-" in replica_name:
                assert len(replica_name.split("-")) == 2
                suffix_name = replica_name.split("-")[-1]
                if suffix_name not in sols[sol_length]:
                    replica_name        = replica_name.split("-")[0] + \
                        replica_name.split("-")[-1]

            # Basic information
            sol_generation = f"""
env.new(
    name        = "{replica_name}",
    prototype   = "{sol}\""""

            # Strength information
            if ks != 0:
                sol_generation += f""",
    ks          = {ks}"""
            if knl != "[]":
                sol_generation += f""",
{textwrap.fill(
    text                = f"knl         = {knl}",
    width               = config.OUTPUT_STRING_LENGTH,
    initial_indent      = "    ",
    subsequent_indent   = "        ",
    break_on_hyphens    = False)}"""
            if ksl != "[]":
                sol_generation += f""",
{textwrap.fill(
    text                = f"ksl         = {ksl}",
    width               = config.OUTPUT_STRING_LENGTH,
    initial_indent      = "    ",
    subsequent_indent   = "        ",
    break_on_hyphens    = False)}"""

            # Misalignments
            if shift_x != 0:
                sol_generation += f""",
    shift_x     = "{shift_x}\""""
            if shift_y != 0:
                sol_generation += f""",
    shift_y     = "{shift_y}\""""
            if rot_s_rad != 0:
                sol_generation += f""",
    rot_s_rad   = "{rot_s_rad}\""""
            if x0 != 0:
                sol_generation += f""",
    x0          = "{x0}\""""
            if y0 != 0:
                sol_generation += f""",
    y0          = "{y0}\""""

            # Close the element definition
            sol_generation += """)"""

            # Write to the file
            output_string += sol_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
