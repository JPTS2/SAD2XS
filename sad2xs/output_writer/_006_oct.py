"""
================================================================================
Output Writer: Octupoles
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
# Import Packages
################################################################################
import xtrack as xt
import xdeps as xd
import numpy as np

from ._000_helpers import extract_multipole_information, get_value_string, \
    generate_magnet_for_replication_names, check_is_simple_quad_sext_oct, \
    check_is_skew_quad_sext_oct, get_knl_string
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_octupole_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the lattice-file source for every OCT element.

    Groups octupoles by quantized length (from
    `extract_multipole_information`), writes one base `xt.Octupole`
    per length, then clones every individual octupole from its
    length's base element. A "simple" octupole (see
    `check_is_simple_quad_sext_oct`) is written as a single-line clone
    with just k3 or k3s (whichever is active); any other octupole is
    written with every non-zero strength/offset/combined-multipole
    parameter listed explicitly. Strengths are referenced as live
    optics variables ("k3_<name>"/"k3s_<name>"), not baked-in
    literals.

    Parameters
    ----------
    line : xt.Line
        The converted line to generate octupole source for.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration; only `MAGNET_LENGTH_PRECISION` is
        used.

    Returns
    -------
    str
        The generated Python source for this section, or "" if the
        line has no octupoles.
    """

    ########################################
    # Get information
    ########################################
    octs, unique_oct_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Octupole",
        config      = config)

    oct_lengths    = np.array(sorted(octs.keys()))
    oct_names      = generate_magnet_for_replication_names(octs, "oct", config.MAGNET_LENGTH_PRECISION)

    ########################################
    # Ensure there are octupoles in the line
    ########################################
    if len(unique_oct_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Octupoles
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += """
########################################
# Base Elements
########################################"""

    for oct_name, oct_length in zip(oct_names, oct_lengths):
        output_string += f"""
env.new(name = "{oct_name}", prototype = xt.Octupole, length = {oct_length})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += """
########################################
# Cloned Elements
########################################"""

    for oct, oct_length in zip(oct_names, oct_lengths):
        for replica_name in octs[oct_length]:

            # Remove the minus sign if no non minus version exists
            if replica_name.startswith("-"):
                root_name   = replica_name[1:]
                if root_name not in octs[oct_length]:
                    replica_name        = root_name

            if check_is_simple_quad_sext_oct(line, replica_name, "Octupole"):

                if not check_is_skew_quad_sext_oct(line, replica_name, "Octupole"):
                    output_string += f"""
env.new(name = "{replica_name}", prototype = "{oct}", k3 = "k3_{replica_name}")"""
                else:
                    output_string += f"""
env.new(name = "{replica_name}", prototype = "{oct}", k3s = "k3s_{replica_name}")"""

            else:
                # Get the replica information
                k3          = line[replica_name].k3
                k3s         = line[replica_name].k3s
                shift_x     = line[replica_name].shift_x
                shift_y     = line[replica_name].shift_y
                rot_s_rad   = line[replica_name].rot_s_rad
                knl         = np.asarray(line[replica_name].knl)
                ksl         = np.asarray(line[replica_name].ksl)

                # Basic information
                oct_generation = f"""
env.new(
    name        = "{replica_name}",
    prototype   = "{oct}\""""

                # Strength information
                if k3 != 0:
                    oct_generation += f""",
    k3          = "k3_{replica_name}\""""
                if k3s != 0:
                    oct_generation += f""",
    k3s         = "k3s_{replica_name}\""""

                # Misalignments
                if shift_x != 0:
                    oct_generation += f""",
    shift_x     = "{shift_x}\""""
                if shift_y != 0:
                    oct_generation += f""",
    shift_y     = "{shift_y}\""""
                if rot_s_rad != 0:
                    oct_generation += f""",
    rot_s_rad   = "{rot_s_rad}\""""

                # Combined multipole components
                knl_str = get_knl_string(knl)
                ksl_str = get_knl_string(ksl)
                if knl_str != "[]":
                    oct_generation += f""",
    knl         = {knl_str}"""
                if ksl_str != "[]":
                    oct_generation += f""",
    ksl         = {ksl_str}"""

                # Close the element definition
                oct_generation += """)"""

                # Write to the file
                output_string += oct_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string

################################################################################
# Optics File
################################################################################
def create_octupole_optics_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the optics-file source assigning every octupole's
    k3/k3s.

    Writes one `k3_<name>`/`k3s_<name> = <value>,` line per distinct
    octupole optics-variable name, aligned to
    `config.OUTPUT_STRING_SEP`, for use inside the generated
    `env.vars.update(...)` call. Zero values are omitted (the writer's
    `default_to_zero` setting covers them).

    Parameters
    ----------
    line : xt.Line
        The converted line to generate octupole optics source for.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration (`MAGNET_LENGTH_PRECISION`,
        `OUTPUT_STRING_SEP`).

    Returns
    -------
    str
        The generated Python source for this section, or "" if the
        line has no octupoles.

    Raises
    ------
    KeyError
        If neither the octupole variable nor its reversed form is
        found in `line`.
    """

    ########################################
    # Get information
    ########################################
    _, unique_oct_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Octupole",
        config      = config)

    ########################################
    # Ensure there are octupoles in the line
    ########################################
    if len(unique_oct_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string = """
    ############################################################
    # Octupoles
    ############################################################"""

    for oct in unique_oct_names:
        k3          = None
        k3s         = None

        try:
            k3  = line[oct].k3
        except KeyError:
            try:
                k3  = line[f"-{oct}"].k3
            except KeyError:
                raise KeyError(f"Could not find oct variable {oct} or -{oct} in line.")

        try:
            k3s = line[oct].k3s
        except KeyError:
            try:
                k3s = line[f"-{oct}"].k3s
            except KeyError:
                raise KeyError(f"Could not find oct variable {oct} or -{oct} in line.")

        if k3 == 0:
            k3 = None
        if k3s == 0:
            k3s = None

        if k3 is not None:
            output_string += f"""
    {f"k3_{oct}"}{" " * (config.OUTPUT_STRING_SEP - len(f"k3_{oct}") + 4)}{"= "}{get_value_string(k3)},"""
        if k3s is not None:
            output_string += f"""
    {f"k3s_{oct}"}{" " * (config.OUTPUT_STRING_SEP - len(f"k3s_{oct}") + 4)}{"= "}{get_value_string(k3s)},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
