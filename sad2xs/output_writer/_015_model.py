"""
================================================================================
Output Writer: Model and Integrator Settings
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-01
================================================================================
"""

################################################################################
# Import Packages
################################################################################
import xtrack as xt

from ._000_helpers import get_parentname
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_model_lattice_file_information(
        line:       xt.Line,
        config:     ConfigLike) -> str:
    """
    Generate the lattice-file source configuring per-element-type
    models and integrators.

    Writes the same `line.set(...)`/`configure_bend_model`/
    `configure_quadrupole_model` calls
    `sad2xs.main.convert_sad_to_xsuite` itself applies during
    conversion, baking `config`'s model/integrator/kick-count settings
    into the generated file as literal values, so a reloaded line
    reproduces the exact same modelling choices without needing the
    original `Config` object. Also emits
    `line.replace_all_repeated_elements()` if
    `config._replace_repeated_elements` is set.

    Parameters
    ----------
    line : xtrack.Line
        Converted line whose per-element MULT edge settings must survive
        global model configuration and writer reload.
    config : ConfigLike
        Converter configuration supplying every model/integrator/
        kick-count setting and `_replace_repeated_elements`.

    Returns
    -------
    str
        The generated Python source configuring the reloaded line's
        modelling.
    """

    output_string = f"""
################################################################################
# Configure Modelling
################################################################################

########################################
# Set integrators
########################################
tt          = line.get_table()
tt_drift    = tt.rows[tt.element_type == "Drift"]
tt_bend     = tt.rows[tt.element_type == "Bend"]
tt_quad     = tt.rows[tt.element_type == "Quadrupole"]
tt_sext     = tt.rows[tt.element_type == "Sextupole"]
tt_oct      = tt.rows[tt.element_type == "Octupole"]
tt_mult     = tt.rows[tt.element_type == "Multipole"]
tt_sol      = tt.rows[tt.element_type == "UniformSolenoid"]
tt_cavi     = tt.rows[tt.element_type == "Cavity"]

line.set(
    tt_drift,
    model               = "{config.MODEL_DRIFT}")
line.set(
    tt_bend,
    model               = "{config.MODEL_BEND}",
    integrator          = "{config.INTEGRATOR_BEND}",
    num_multipole_kicks = {config.N_INTEGRATOR_KICKS_BEND})
line.set(
    tt_quad,
    model               = "{config.MODEL_QUAD}",
    integrator          = "{config.INTEGRATOR_QUAD}",
    num_multipole_kicks = {config.N_INTEGRATOR_KICKS_QUAD})
line.set(
    tt_sext,
    model               = "{config.MODEL_SEXT}",
    integrator          = "{config.INTEGRATOR_SEXT}",
    num_multipole_kicks = {config.N_INTEGRATOR_KICKS_SEXT})
line.set(
    tt_oct,
    model               = "{config.MODEL_OCT}",
    integrator          = "{config.INTEGRATOR_OCT}",
    num_multipole_kicks = {config.N_INTEGRATOR_KICKS_OCT})
line.set(
    tt_mult,
    model               = "{config.MODEL_MULT}",
    integrator          = "{config.INTEGRATOR_MULT}",
    num_multipole_kicks = {config.N_INTEGRATOR_KICKS_MULT})
line.set(
    tt_sol,
    integrator          = "{config.INTEGRATOR_SOL}",
    num_multipole_kicks = {config.N_INTEGRATOR_KICKS_SOL})
line.set(
    tt_cavi,
    model               = "{config.MODEL_CAVI}",
    integrator          = "{config.INTEGRATOR_CAVI}",
    absolute_time       = {config.ABSOLUTE_TIME_CAVI})

########################################
# Set bend edges
########################################
line.configure_bend_model(edge = "{config.EDGE_MODEL_BEND}")

########################################
# Set quad edges
########################################
line.configure_quadrupole_model(edge = "{config.EDGE_MODEL_QUAD}")
"""

    ########################################
    # Restore SAD MULT Native Edge Settings
    ########################################
    native_edges = line.env.metadata.get(
        "sad2xs", {}).get("mult_native_fringe_faces", {})
    line_names = [
        get_parentname(name) for name in line.get_table().name
        if name != "_end_point"]
    written_edges = {}
    for source_name, faces in native_edges.items():
        if source_name not in line_names:
            continue
        name = source_name
        if name.startswith("-") and name[1:] not in line_names:
            name = name[1:]
        written_edges[name] = faces

    if written_edges:
        output_string += """
########################################
# Restore SAD MULT Native Edge Settings
########################################"""
    for name, faces in written_edges.items():
        edge_entry_active = bool(faces["edge_entry_active"])
        edge_exit_active  = bool(faces["edge_exit_active"])
        output_string += f"""
line["{name}"].edge_entry_active = {edge_entry_active}
line["{name}"].edge_exit_active  = {edge_exit_active}
env.metadata.setdefault("sad2xs", {{}}).setdefault(
    "mult_native_fringe_faces", {{}})["{name}"] = {{
        "edge_entry_active": {edge_entry_active},
        "edge_exit_active":  {edge_exit_active}}}"""

    ########################################
    # Replace repeated elements
    ########################################
    if config._replace_repeated_elements:
        output_string += """
########################################
# Replace repeated elements
########################################
line.replace_all_repeated_elements()"""

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
