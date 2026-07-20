"""
================================================================================
Output Writer: Line Assembly
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
import logging
import textwrap

import xdeps as xd
import numpy as np

from ._000_helpers import get_parentname
from ..types import ConfigLike

logger  = logging.getLogger(__name__)

################################################################################
# Lattice File
################################################################################
def create_line_lattice_file_information(
        line_table: xd.table.Table,
        config:     ConfigLike) -> str:
    """
    Generate the lattice-file source assembling the written line
    ("line = env.lines['line']") from its base-element names.

    Drops any element type not in `config.ALLOWED_ELEMENTS` (warning
    once for the whole lattice about what was omitted and why), then
    resolves each remaining element to the base-element name actually
    written by the other `create_*_lattice_file_information`
    functions (stripping a leading '-' or an embedded '-' suffix
    wherever the corresponding non-reversed base element is the one
    that exists, matching the same minus-sign cleanup applied to the
    written elements themselves).

    Parameters
    ----------
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration (`ALLOWED_ELEMENTS`,
        `OUTPUT_STRING_LENGTH`).

    Returns
    -------
    str
        The generated Python source assembling and naming the line.
    """

    ########################################
    # Get allowed elements
    ########################################
    is_allowed      = np.isin(line_table.element_type, list(config.ALLOWED_ELEMENTS))
    valid_elements  = line_table.rows[is_allowed]

    ########################################
    # Warn about elements the writer cannot represent
    ########################################
    dropped_mask    = ~is_allowed & (line_table.name != "_end_point")
    dropped_names   = line_table.name[dropped_mask]
    if len(dropped_names) > 0:
        dropped_types   = sorted(set(line_table.element_type[dropped_mask]))
        logger.warning(
            f"{len(dropped_names)} element(s) omitted from the written "
            f"lattice: unsupported element type(s) {', '.join(dropped_types)}")
        logger.debug(
            f"Omitted elements: {sorted(set(dropped_names))}")

    ########################################
    # Get parent names
    ########################################
    parent_names    = []
    for element_name in valid_elements.name:
        parentname = get_parentname(element_name)
        parent_names.append(parentname)

    ########################################
    # Account for the removal of unnecessary minus signs in other scripts
    ########################################
    minus_names = [name for name in parent_names if name.startswith('-')]
    for minus_name in minus_names:
        non_minus_name = minus_name[1:]
        if non_minus_name not in parent_names:
            # Correct all instances in the parent names list
            parent_names = [
                name if name != minus_name else non_minus_name
                for name in parent_names]

    # Ones that start with - are handled above
    minus_names = [name for name in parent_names if "-" in name and not name.startswith("-")]
    for minus_name in minus_names:
        assert len(minus_name.split("-")) == 2
        suffix_name = "-" + minus_name.split("-")[-1]
        if suffix_name not in parent_names:
            non_minus_name = minus_name.split("-")[0] + \
                minus_name.split("-")[-1]
            # Correct all instances in the parent names list
            parent_names = [
                name if name != minus_name else non_minus_name
                for name in parent_names]

    ########################################
    # Convert to single string
    ########################################
    line_string = parent_names
    line_string = str(line_string)[1:-1]

    ########################################
    # Write output
    ########################################
    output_string   = f"""
############################################################
# Create Line
############################################################
env.new_line(
    name        = 'line',
    components  = [
{textwrap.fill(
    text                = line_string,
    width               = config.OUTPUT_STRING_LENGTH,
    initial_indent      = '        ',
    subsequent_indent   = '        ',
    break_on_hyphens    = False)}])"""

    ########################################
    # Set line attributes
    ########################################
    output_string   += """
line = env.lines['line']
line.particle_ref = env.particle_ref.copy()"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
