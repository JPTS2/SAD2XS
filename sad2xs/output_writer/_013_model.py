"""
(Unofficial) SAD to XSuite Converter

Output Writer: Model
"""

################################################################################
# Import Packages
################################################################################
from ._000_helpers import *

################################################################################
# Lattice File
################################################################################
def create_model_lattice_file_information():

    output_string = f'''
################################################################################
# Configure Modelling
################################################################################

########################################
# Set bend model
########################################
line.configure_bend_model(edge = 'full')

########################################
# Set Integrators
########################################
tt          = line.get_table()
tt_drift    = tt.rows[tt.element_type == 'Drift']
tt_bend     = tt.rows[tt.element_type == 'Bend']
tt_quad     = tt.rows[tt.element_type == 'Quadrupole']
tt_sext     = tt.rows[tt.element_type == 'Sextupole']
tt_oct      = tt.rows[tt.element_type == 'Octupole']

line.set(tt_drift, model = 'exact')
line.set(tt_bend,   integrator = 'uniform',     num_multipole_kicks = {N_INTEGRATOR_KICKS},
    model = 'mat-kick-mat')
line.set(tt_quad,   integrator = 'uniform',     num_multipole_kicks = {N_INTEGRATOR_KICKS},
    model = 'mat-kick-mat')
line.set(tt_sext,   integrator = 'yoshida4',    num_multipole_kicks = {N_INTEGRATOR_KICKS})
line.set(tt_oct,    integrator = 'yoshida4',    num_multipole_kicks = {N_INTEGRATOR_KICKS})

########################################
# Replace repeated elements
########################################
line.replace_all_repeated_elements()'''

    ########################################
    # Return
    ########################################
    output_string += "\n"
    return output_string
