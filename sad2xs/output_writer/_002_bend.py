"""
================================================================================
Output Writer: Bends
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

from ._000_helpers import extract_bend_information, get_value_string, \
    generate_magnet_for_replication_names, check_is_simple_bend_corr, get_knl_string
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_bend_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the lattice-file source for every BEND element.

    Groups bends by orientation (horizontal, vertical, or skew, from
    `extract_bend_information`) and quantized length, writes one base
    `xt.Bend` per group, then clones every individual bend from its
    group's base element. A "simple" bend (see
    `check_is_simple_bend_corr`) is written as a single-line clone
    with just angle/k0; any other bend is written with every non-zero
    edge/offset/combined-multipole parameter listed explicitly.
    k0/k1 are referenced as live optics variables
    ("k0_<name>"/"k1_<name>"), not baked-in literals.

    Parameters
    ----------
    line : xt.Line
        The converted line to generate bend source for.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration; only `MAGNET_LENGTH_PRECISION` is
        used.

    Returns
    -------
    str
        The generated Python source for this section, or "" if the
        line has no bends.
    """

    ########################################
    # Get information
    ########################################
    hbends, vbends, sbends, _, bend_name_dict = \
        extract_bend_information(line, line_table, config)

    hbend_lengths       = np.array(sorted(hbends.keys()))
    hbend_names         = generate_magnet_for_replication_names(hbends, "hbend", config.MAGNET_LENGTH_PRECISION)
    vbend_lengths       = np.array(sorted(vbends.keys()))
    vbend_names         = generate_magnet_for_replication_names(vbends, "vbend", config.MAGNET_LENGTH_PRECISION)
    sbend_lengths       = np.array(sorted(sbends.keys()))
    sbend_names         = generate_magnet_for_replication_names(sbends, "sbend", config.MAGNET_LENGTH_PRECISION)

    ########################################
    # Ensure there are bends in the line
    ########################################
    if len(hbend_names) == 0 and len(vbend_names) == 0 and len(sbend_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Bends
############################################################
"""

    ########################################
    # Create base elements
    ########################################
    output_string += """
########################################
# Base Elements
########################################"""

    for hbend_name, hbend_length in zip(hbend_names, hbend_lengths):
        output_string += f"""
env.new(name = "{hbend_name}", prototype = xt.Bend, length = {hbend_length})"""

    for vbend_name, vbend_length in zip(vbend_names, vbend_lengths):
        output_string += f"""
env.new(name = "{vbend_name}", prototype = xt.Bend, length = {vbend_length}, rot_s_rad = +np.pi/2)"""

    for sbend_name, sbend_length in zip(sbend_names, sbend_lengths):
        output_string += f"""
env.new(name = "{sbend_name}", prototype = xt.Bend, length = {sbend_length})"""

    output_string += "\n"

    ########################################
    # Clone Elements
    ########################################
    output_string += """
########################################
# Cloned Elements
########################################"""

    for hbend, hbend_length in zip(hbend_names, hbend_lengths):
        for replica_name in hbends[hbend_length]:
            source_name         = replica_name
            replica_variable    = bend_name_dict[source_name]
            bend                = line[source_name]
            angle               = bend.angle
            edge_entry_angle    = bend.edge_entry_angle
            edge_exit_angle     = bend.edge_exit_angle

            # Remove the minus sign if no non minus version exists
            if replica_name.startswith("-"):
                root_name    = replica_name[1:]
                source_names = hbends[hbend_length]
                if root_name not in source_names:
                    replica_name = root_name

            # If simple try to make it more compact
            if check_is_simple_bend_corr(line, source_name):
                bend_generation = f"""
env.new(name = "{replica_name}", prototype = "{hbend}", angle = {get_value_string(angle)}, k0 = "k0_{replica_variable}")"""

            # Otherwise do the full version
            else:
                bend_generation = f"""
env.new(
    name                    = "{replica_name}",
    prototype               = "{hbend}",
    angle                   = {get_value_string(angle)},
    k0                      = "k0_{replica_variable}\""""
                if bend.k1 != 0:
                    bend_generation += f""",
    k1                      = "k1_{replica_variable}\""""
            # Append edge entry angles
                if bend.edge_entry_angle != 0:
                    bend_generation += f""",
    edge_entry_angle        = {edge_entry_angle}"""
                if bend.edge_exit_angle != 0:
                    bend_generation += f""",
    edge_exit_angle         = {edge_exit_angle}"""
                if bend.edge_entry_angle_fdown != 0:
                    bend_generation += f""",
    edge_entry_angle_fdown  = {bend.edge_entry_angle_fdown}"""
                if bend.edge_exit_angle_fdown != 0:
                    bend_generation += f""",
    edge_exit_angle_fdown   = {bend.edge_exit_angle_fdown}"""
                if bend.edge_entry_fint != 0:
                    bend_generation += f""",
    edge_entry_fint         = {get_value_string(bend.edge_entry_fint)}"""
                if bend.edge_entry_hgap != 0:
                    bend_generation += f""",
    edge_entry_hgap         = {get_value_string(bend.edge_entry_hgap)}"""
                if bend.edge_exit_fint != 0:
                    bend_generation += f""",
    edge_exit_fint          = {get_value_string(bend.edge_exit_fint)}"""
                if bend.edge_exit_hgap != 0:
                    bend_generation += f""",
    edge_exit_hgap          = {get_value_string(bend.edge_exit_hgap)}"""
                # Append shifts if they exist
                if bend.shift_x != 0:
                    bend_generation += f""",
    shift_x                 = "{bend.shift_x}\""""
                if bend.shift_y != 0:
                    bend_generation += f""",
    shift_y                 = "{bend.shift_y}\""""
                # Combined multipole components
                knl_str = get_knl_string(np.asarray(bend.knl))
                ksl_str = get_knl_string(np.asarray(bend.ksl))
                if knl_str != "[]":
                    bend_generation += f""",
    knl                     = {knl_str}"""
                if ksl_str != "[]":
                    bend_generation += f""",
    ksl                     = {ksl_str}"""
                # Append the missing parenthesis
                bend_generation += """)"""

            # Write to the file
            output_string += bend_generation


    for vbend, vbend_length in zip(vbend_names, vbend_lengths):
        for replica_name in vbends[vbend_length]:
            source_name         = replica_name
            replica_variable    = bend_name_dict[source_name]
            bend                = line[source_name]
            angle               = bend.angle
            edge_entry_angle    = bend.edge_entry_angle
            edge_exit_angle     = bend.edge_exit_angle

            # Remove the minus sign if no non minus version exists
            if replica_name.startswith("-"):
                root_name    = replica_name[1:]
                source_names = vbends[vbend_length]
                if root_name not in source_names:
                    replica_name = root_name

            # If simple try to make it more compact
            if check_is_simple_bend_corr(line, source_name):
                bend_generation = f"""
env.new(name = "{replica_name}", prototype = "{vbend}", angle = {get_value_string(angle)}, k0 = "k0_{replica_variable}")"""

            # Otherwise do the full version
            else:
                bend_generation = f"""
env.new(
    name                    = "{replica_name}",
    prototype               = "{vbend}",
    angle                   = {get_value_string(angle)},
    k0                      = "k0_{replica_variable}\""""
                if bend.k1 != 0:
                    bend_generation += f""",
    k1                      = "k1_{replica_variable}\""""
            # Append edge entry angles
                if bend.edge_entry_angle != 0:
                    bend_generation += f""",
    edge_entry_angle        = {edge_entry_angle}"""
                if bend.edge_exit_angle != 0:
                    bend_generation += f""",
    edge_exit_angle         = {edge_exit_angle}"""
                if bend.edge_entry_angle_fdown != 0:
                    bend_generation += f""",
    edge_entry_angle_fdown  = {bend.edge_entry_angle_fdown}"""
                if bend.edge_exit_angle_fdown != 0:
                    bend_generation += f""",
    edge_exit_angle_fdown   = {bend.edge_exit_angle_fdown}"""
                if bend.edge_entry_fint != 0:
                    bend_generation += f""",
    edge_entry_fint         = {get_value_string(bend.edge_entry_fint)}"""
                if bend.edge_entry_hgap != 0:
                    bend_generation += f""",
    edge_entry_hgap         = {get_value_string(bend.edge_entry_hgap)}"""
                if bend.edge_exit_fint != 0:
                    bend_generation += f""",
    edge_exit_fint          = {get_value_string(bend.edge_exit_fint)}"""
                if bend.edge_exit_hgap != 0:
                    bend_generation += f""",
    edge_exit_hgap          = {get_value_string(bend.edge_exit_hgap)}"""
                # Append shifts if they exist
                if bend.shift_x != 0:
                    bend_generation += f""",
    shift_x                 = "{bend.shift_x}\""""
                if bend.shift_y != 0:
                    bend_generation += f""",
    shift_y                 = "{bend.shift_y}\""""
                # Combined multipole components
                knl_str = get_knl_string(np.asarray(bend.knl))
                ksl_str = get_knl_string(np.asarray(bend.ksl))
                if knl_str != "[]":
                    bend_generation += f""",
    knl                     = {knl_str}"""
                if ksl_str != "[]":
                    bend_generation += f""",
    ksl                     = {ksl_str}"""
                # Append the missing parenthesis
                bend_generation += """)"""

            # Write to the file
            output_string += bend_generation

    for sbend, sbend_length in zip(sbend_names, sbend_lengths):
        for replica_name in sbends[sbend_length]:
            source_name         = replica_name
            replica_variable    = bend_name_dict[source_name]
            bend                = line[source_name]
            angle               = bend.angle
            edge_entry_angle    = bend.edge_entry_angle
            edge_exit_angle     = bend.edge_exit_angle
            rot_s_rad           = bend.rot_s_rad

            # Remove the minus sign if no non minus version exists
            if replica_name.startswith("-"):
                root_name    = replica_name[1:]
                source_names = sbends[sbend_length]
                if root_name not in source_names:
                    replica_name = root_name

            # If simple try to make it more compact
            if check_is_simple_bend_corr(line, source_name):
                bend_generation = f"""
env.new(name = "{replica_name}", prototype = "{sbend}", angle = {get_value_string(angle)}, k0 = "k0_{replica_variable}", rot_s_rad = "{rot_s_rad}")"""

            # Otherwise do the full version
            else:
                bend_generation = f"""
env.new(
    name                    = "{replica_name}",
    prototype               = "{sbend}",
    angle                   = {get_value_string(angle)},
    k0                      = "k0_{replica_variable}\""""
                if bend.k1 != 0:
                    bend_generation += f""",
    k1                      = "k1_{replica_variable}\""""
            # Append edge entry angles
                if bend.edge_entry_angle != 0:
                    bend_generation += f""",
    edge_entry_angle        = {edge_entry_angle}"""
                if bend.edge_exit_angle != 0:
                    bend_generation += f""",
    edge_exit_angle         = {edge_exit_angle}"""
                if bend.edge_entry_angle_fdown != 0:
                    bend_generation += f""",
    edge_entry_angle_fdown  = {bend.edge_entry_angle_fdown}"""
                if bend.edge_exit_angle_fdown != 0:
                    bend_generation += f""",
    edge_exit_angle_fdown   = {bend.edge_exit_angle_fdown}"""
                if bend.edge_entry_fint != 0:
                    bend_generation += f""",
    edge_entry_fint         = {get_value_string(bend.edge_entry_fint)}"""
                if bend.edge_entry_hgap != 0:
                    bend_generation += f""",
    edge_entry_hgap         = {get_value_string(bend.edge_entry_hgap)}"""
                if bend.edge_exit_fint != 0:
                    bend_generation += f""",
    edge_exit_fint          = {get_value_string(bend.edge_exit_fint)}"""
                if bend.edge_exit_hgap != 0:
                    bend_generation += f""",
    edge_exit_hgap          = {get_value_string(bend.edge_exit_hgap)}"""
                # Append shifts if they exist
                if bend.shift_x != 0:
                    bend_generation += f""",
    shift_x                 = "{bend.shift_x}\""""
                if bend.shift_y != 0:
                    bend_generation += f""",
    shift_y                 = "{bend.shift_y}\""""
            # In the case of a skew bend, we need to add a rotation
                bend_generation += f""",
    rot_s_rad               = "{rot_s_rad}\""""
                # Combined multipole components
                knl_str = get_knl_string(np.asarray(bend.knl))
                ksl_str = get_knl_string(np.asarray(bend.ksl))
                if knl_str != "[]":
                    bend_generation += f""",
    knl                     = {knl_str}"""
                if ksl_str != "[]":
                    bend_generation += f""",
    ksl                     = {ksl_str}"""
                # Append the missing parenthesis
                bend_generation += """)"""

            # Write to the file
            output_string += bend_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string

################################################################################
# Optics File
################################################################################
def create_bend_optics_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the optics-file source assigning every bend's k0/k1.

    Writes one `k0_<name>`/`k1_<name> = <value>,` line per distinct
    bend optics-variable name, aligned to `config.OUTPUT_STRING_SEP`,
    for use inside the generated `env.vars.update(...)` call. Zero
    values are omitted (the writer's `default_to_zero` setting covers
    them). `k0` is read from `bend.angle / bend.length` when the
    element's `k0_from_h` flag is set, otherwise directly from
    `bend.k0`.

    Parameters
    ----------
    line : xt.Line
        The converted line to generate bend optics source for.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration (`MAGNET_LENGTH_PRECISION`,
        `OUTPUT_STRING_SEP`).

    Returns
    -------
    str
        The generated Python source for this section, or "" if the
        line has no bends.

    Raises
    ------
    KeyError
        If neither `bend_variable` nor its reversed form is found in
        `line`.
    """

    ########################################
    # Get information
    ########################################
    hbends, vbends, sbends, unique_bend_variables, _ = extract_bend_information(line, line_table, config)

    hbend_names         = generate_magnet_for_replication_names(hbends, "hbend", config.MAGNET_LENGTH_PRECISION)
    vbend_names         = generate_magnet_for_replication_names(vbends, "vbend", config.MAGNET_LENGTH_PRECISION)
    sbend_names         = generate_magnet_for_replication_names(sbends, "sbend", config.MAGNET_LENGTH_PRECISION)

    ########################################
    # Ensure there are bends in the line
    ########################################
    if len(hbend_names) == 0 and len(vbend_names) == 0 and len(sbend_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
    ############################################################
    # Bends
    ############################################################"""

    for bend_variable in unique_bend_variables:
        k0 = None
        k1 = None

        try:
            bend = line[bend_variable]
        except KeyError:
            try:
                bend = line[f"-{bend_variable}"]
            except KeyError as exc:
                raise KeyError(
                    f"Could not find bend variable {bend_variable} or "
                    f"-{bend_variable} in line.") from exc

        if bend.k0_from_h is True:
            k0 = bend.angle / bend.length
        else:
            k0 = bend.k0
        k1 = bend.k1

        if k0 == 0:
            k0 = None
        if k1 == 0:
            k1 = None

        if k0 is not None:
            output_string += f"""
    {f"k0_{bend_variable}"}{" " * (config.OUTPUT_STRING_SEP - len(f"k0_{bend_variable}") + 4)}{"= "}{get_value_string(k0)},"""
        if k1 is not None:
            output_string += f"""
    {f"k1_{bend_variable}"}{" " * (config.OUTPUT_STRING_SEP - len(f"k1_{bend_variable}") + 4)}{"= "}{get_value_string(k1)},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
