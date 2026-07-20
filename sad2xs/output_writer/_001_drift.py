"""
================================================================================
Output Writer: Drifts
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

from ._000_helpers import get_parentname
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_drift_lattice_file_information(
        line:       xt.Line,
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the lattice-file source for every unique DRIFT element.

    Writes one `env.new(...)` statement per distinct drift base name
    (see `get_parentname`), each with its own length.

    Parameters
    ----------
    line : xt.Line
        The converted line to generate drift source for.
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
        line has no drifts.
    """

    ########################################
    # Get unique drifts
    ########################################
    unique_drift_names      = []
    for drift in line_table.rows[line_table.element_type == 'Drift'].name:
        parentname  = get_parentname(drift)
        if parentname not in unique_drift_names:
            unique_drift_names.append(parentname)

    ########################################
    # Ensure there are drifts in the line
    ########################################
    if len(unique_drift_names) == 0:
        return ""

    ########################################
    # Create Output string
    ########################################
    output_string   = """
############################################################
# Drifts
############################################################"""

    ########################################
    # Create Drifts
    ########################################
    for drift in unique_drift_names:
        length          = line[drift].length
        output_string   += f"""
env.new(name = '{drift}', prototype = xt.Drift, length = {length})"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
