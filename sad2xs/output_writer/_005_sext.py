"""
================================================================================
Output Writer: Sextupoles
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
import numpy as np

from ._000_helpers import extract_multipole_information, \
    generate_magnet_for_replication_names, check_is_simple_quad_sext_oct, \
    check_is_skew_quad_sext_oct, get_knl_string
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_sextupole_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the lattice-file source for every SEXT element.

    Groups sextupoles by quantized length (from
    `extract_multipole_information`), writes one base `xt.Sextupole`
    per length, then clones every individual sextupole from its
    length's base element. A "simple" sextupole (see
    `check_is_simple_quad_sext_oct`) is written as a single-line clone
    with just k2 or k2s (whichever is active); any other sextupole is
    written with every non-zero strength/offset/combined-multipole
    parameter listed explicitly. Strengths are referenced as live
    optics variables ("k2_<name>"/"k2s_<name>"), not baked-in
    literals.

    Parameters
    ----------
    line : xt.Line
        The converted line to generate sextupole source for.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration; only `MAGNET_LENGTH_PRECISION` is
        used.

    Returns
    -------
    str
        The generated Python source for this section, or "" if the
        line has no sextupoles.
    """

    ########################################
    # Get information
    ########################################
    sexts, unique_sext_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Sextupole",
        config      = config)

    sext_lengths    = np.array(sorted(sexts.keys()))
    sext_names      = generate_magnet_for_replication_names(sexts, "sext", config.MAGNET_LENGTH_PRECISION)

    ########################################
    # Ensure there are sextupoles in the line
    ########################################
    if len(unique_sext_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Sextupoles
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += """
########################################
# Base Elements
########################################"""

    for sext_name, sext_length in zip(sext_names, sext_lengths):
        output_string += f"""
env.new(name = '{sext_name}', prototype = xt.Sextupole, length = {sext_length})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += """
########################################
# Cloned Elements
########################################"""

    for sext, sext_length in zip(sext_names, sext_lengths):
        for replica_name in sexts[sext_length]:

            # Remove the minus sign if no non minus version exists
            if replica_name.startswith("-"):
                root_name   = replica_name[1:]
                if root_name not in sexts[sext_length]:
                    replica_name        = root_name

            if check_is_simple_quad_sext_oct(line, replica_name, "Sextupole"):

                if not check_is_skew_quad_sext_oct(line, replica_name, "Sextupole"):
                    output_string += f"""
env.new(name = '{replica_name}', prototype = '{sext}', k2 = 'k2_{replica_name}')"""
                else:
                    output_string += f"""
env.new(name = '{replica_name}', prototype = '{sext}', k2s = 'k2s_{replica_name}')"""

            else:
                # Get the replica information
                k2          = line[replica_name].k2
                k2s         = line[replica_name].k2s
                shift_x     = line[replica_name].shift_x
                shift_y     = line[replica_name].shift_y
                rot_s_rad   = line[replica_name].rot_s_rad
                knl         = np.asarray(line[replica_name].knl)
                ksl         = np.asarray(line[replica_name].ksl)

                # Basic information
                sext_generation = f"""
env.new(
    name        = '{replica_name}',
    prototype   = '{sext}'"""

                # Strength information
                if k2 != 0:
                    sext_generation += f""",
    k2          = 'k2_{replica_name}'"""
                if k2s != 0:
                    sext_generation += f""",
    k2s         = 'k2s_{replica_name}'"""

                # Misalignments
                if shift_x != 0:
                    sext_generation += f""",
    shift_x     = '{shift_x}'"""
                if shift_y != 0:
                    sext_generation += f""",
    shift_y     = '{shift_y}'"""
                if rot_s_rad != 0:
                    sext_generation += f""",
    rot_s_rad   = '{rot_s_rad}'"""

                # Combined multipole components
                knl_str = get_knl_string(knl)
                ksl_str = get_knl_string(ksl)
                if knl_str != "[]":
                    sext_generation += f""",
    knl         = {knl_str}"""
                if ksl_str != "[]":
                    sext_generation += f""",
    ksl         = {ksl_str}"""

                # Close the element definition
                sext_generation += """)"""

                # Write to the file
                output_string += sext_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string

################################################################################
# Optics File
################################################################################
def create_sextupole_optics_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the optics-file source assigning every sextupole's
    k2/k2s.

    Writes one `k2_<name>`/`k2s_<name> = <value>,` line per distinct
    sextupole optics-variable name, aligned to
    `config.OUTPUT_STRING_SEP`, for use inside the generated
    `env.vars.update(...)` call. Zero values are omitted (the writer's
    `default_to_zero` setting covers them).

    Parameters
    ----------
    line : xt.Line
        The converted line to generate sextupole optics source for.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration (`MAGNET_LENGTH_PRECISION`,
        `OUTPUT_STRING_SEP`).

    Returns
    -------
    str
        The generated Python source for this section, or "" if the
        line has no sextupoles.

    Raises
    ------
    KeyError
        If neither the sextupole variable nor its reversed form is
        found in `line`.
    """

    ########################################
    # Get information
    ########################################
    _, unique_sext_names = extract_multipole_information(
        line        = line,
        line_table  = line_table,
        mode        = "Sextupole",
        config      = config)

    ########################################
    # Ensure there are sextupoles in the line
    ########################################
    if len(unique_sext_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string = """
    ############################################################
    # Sextupoles
    ############################################################"""

    for sext in unique_sext_names:
        k2          = None
        k2s         = None

        try:
            k2  = line[sext].k2
        except KeyError:
            try:
                k2  = line[f"-{sext}"].k2
            except KeyError:
                raise KeyError(f"Could not find sext variable {sext} or -{sext} in line.")

        try:
            k2s     = line[sext].k2s
        except KeyError:
            try:
                k2s = line[f"-{sext}"].k2s
            except KeyError:
                raise KeyError(f"Could not find sext variable {sext} or -{sext} in line.")

        if k2 == 0:
            k2 = None
        if k2s == 0:
            k2s = None

        if k2 is not None:
            output_string += f"""
    {f'k2_{sext}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'k2_{sext}') + 4)}{'= '}{k2:.24f},"""
        if k2s is not None:
            output_string += f"""
    {f'k2s_{sext}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'k2s_{sext}') + 4)}{'= '}{k2s:.24f},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
