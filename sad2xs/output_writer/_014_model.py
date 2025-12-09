"""
(Unofficial) SAD to XSuite Converter: Output Writer - Modelling
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-12-2025
"""

################################################################################
# Import Packages
################################################################################
from ..types import ConfigLike

################################################################################
# Lattice File
################################################################################
def create_model_lattice_file_information(config: ConfigLike) -> str:
    """
    Docstring
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
tt_sol      = tt.rows[tt.element_type == "Solenoid"]
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
    num_multipole_kicks = {config.N_INTEGRATOR_KICKS_MULT})
line.set(
    tt_sol,
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
"""

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
