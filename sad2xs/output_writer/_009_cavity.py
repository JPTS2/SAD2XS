"""
================================================================================
Output Writer: Cavities
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
import numpy as np
import xtrack as xt
import xdeps as xd


from ._000_helpers import get_parentname, get_variablename
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_cavity_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the lattice-file source for every CAVI element.

    Unlike the other magnet families, cavities are not grouped/cloned
    by length -- each is written individually, since RF parameters
    rarely repeat exactly. voltage/phase are always referenced as
    live optics variables; frequency is written as
    "freq_<name> * (1 + fshift)" (SAD's FSHIFT convention) unless the
    element has a non-zero harmonic number, in which case harmonic is
    referenced instead and Xsuite derives frequency from it.

    Parameters
    ----------
    line : xt.Line
        The converted line to generate cavity source for.
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
        line has no cavities.
    """

    ########################################
    # Get information
    ########################################
    unique_cavi_names       = []
    unique_cavi_variables   = []
    for cavi in line_table.rows[line_table.element_type == 'Cavity'].name:
        parentname      = get_parentname(cavi)
        variablename    = get_variablename(cavi)
        if parentname not in unique_cavi_names:
            unique_cavi_names.append(parentname)
            unique_cavi_variables.append(variablename)

    ########################################
    # Ensure there are cavities in the line
    ########################################
    if len(unique_cavi_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Cavities
############################################################"""

    ########################################
    # Create elements
    ########################################
    for cavi_name, cavi_variable_name in zip(unique_cavi_names, unique_cavi_variables):

        # Get the information
        length          = line[cavi_name].length
        harmonic_value  = line[cavi_name].harmonic

        # Remove the minus sign if no non minus version exists
        if cavi_name.startswith("-"):
            root_name   = cavi_name[1:]
            if root_name not in unique_cavi_names:
                cavi_name        = root_name

        cavity_generation   = f"""
env.new(
    name        = '{cavi_name}',
    prototype   = xt.Cavity"""
        if length != 0:
            cavity_generation += f""",
    length      = {length}"""
        if harmonic_value != 0:
            cavity_generation += f""",
    harmonic    = 'harm_{cavi_variable_name}'"""
        else:
            cavity_generation += f""",
    frequency   = 'freq_{cavi_variable_name} * (1 + fshift)'"""
        cavity_generation += f""",
    voltage     = 'volt_{cavi_variable_name}'"""
        cavity_generation += f""",
    phase       = 'phase_{cavi_variable_name}'"""

        # Close the element definition
        cavity_generation += """)"""

        # Write to the file
        output_string += cavity_generation

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string

################################################################################
# Optics File
################################################################################
def create_cavity_optics_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the optics-file source assigning every cavity's RF
    parameters.

    Writes `volt_<name>`, `phase_<name>`, and either `harm_<name>` (if
    the cavity has a non-zero harmonic number) or `freq_<name>`
    (otherwise) per distinct cavity, aligned to
    `config.OUTPUT_STRING_SEP`, for use inside the generated
    `env.vars.update(...)` call. Reversed ('-'-prefixed) cavities are
    skipped, since they share the same optics variables as their
    non-reversed counterpart.

    Parameters
    ----------
    line : xt.Line
        The converted line to generate cavity optics source for.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration; only `OUTPUT_STRING_SEP` is used.

    Returns
    -------
    str
        The generated Python source for this section, or "" if the
        line has no cavities.

    Raises
    ------
    KeyError
        If neither a cavity name nor its reversed form is found in
        `line`.
    """

    ########################################
    # Get information
    ########################################
    unique_cavi_names       = []
    unique_cavi_variables   = []
    for cavi in line_table.rows[line_table.element_type == 'Cavity'].name:
        parentname      = get_parentname(cavi)
        variablename    = get_variablename(cavi)
        if parentname not in unique_cavi_names:
            unique_cavi_names.append(parentname)
            unique_cavi_variables.append(variablename)

    ########################################
    # Ensure there are cavities in the line
    ########################################
    if len(unique_cavi_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string = """
    ############################################################
    # Cavities
    ############################################################"""

    for cavi, variable_name in zip(unique_cavi_names, unique_cavi_variables):

        if cavi.startswith('-'):
            continue

        freq    = 0
        volt    = 0
        phase   = np.pi

        try:
            freq  = line[cavi].frequency
        except KeyError:
            try:
                freq  = line[f"-{cavi}"].frequency
            except KeyError as exc:
                raise KeyError(
                    f"Could not find cavity variable {cavi} or -{cavi} in line.") from exc

        try:
            volt  = line[cavi].voltage
        except KeyError:
            try:
                volt  = line[f"-{cavi}"].voltage
            except KeyError as exc:
                raise KeyError(
                    f"Could not find cavity variable {cavi} or -{cavi} in line.") from exc

        try:
            phase = line[cavi].phase
        except KeyError:
            try:
                phase = line[f"-{cavi}"].phase
            except KeyError as exc:
                raise KeyError(
                    f"Could not find cavity variable {cavi} or -{cavi} in line.") from exc

        harmonic = 0
        try:
            harmonic = line[cavi].harmonic
        except KeyError:
            try:
                harmonic = line[f"-{cavi}"].harmonic
            except KeyError as exc:
                raise KeyError(
                    f"Could not find cavity variable {cavi} or -{cavi} in line.") from exc

        if harmonic != 0:
            output_string += f"""
    {f'harm_{variable_name}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'harm_{variable_name}') + 4)}{'= '}{harmonic:.24f},"""
        else:
            output_string += f"""
    {f'freq_{variable_name}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'freq_{variable_name}') + 4)}{'= '}{freq:.24f},"""
        output_string += f"""
    {f'volt_{variable_name}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'volt_{variable_name}') + 4)}{'= '}{volt:.24f},"""
        output_string += f"""
    {f'phase_{variable_name}'}{' ' * (config.OUTPUT_STRING_SEP - len(f'phase_{variable_name}') + 4)}{'= '}{phase:.24f},"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
