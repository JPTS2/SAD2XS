"""
Creation of expresions for imported lattice
"""
################################################################################
# Required Packages
################################################################################
import numpy as np

################################################################################
# Helper Functions
################################################################################
def get_element_class(element_name):
    """
    Get the element class from the element name. Used to define powering groups.

    e.g. 'Bend.1' -> 'Bend'

    Parameters:
    ----------
    element_name: str
        The name of the element
        
    Outputs
    ----------
    element_class: string
        The name of the element class
    """
    # Default to the element name
    element_class   = element_name
    # Split the element name by the last period
    substrings      = element_name.rsplit('.', 1)
    # If the element name has a period, the base string is the first substring
    if len(substrings) == 2 and substrings[1].isdigit():
        element_class   = substrings[0]

    return element_class

################################################################################
# Conversion Function
################################################################################

def generate_expressions(line):
    """
    Generate Xsuite line variables for an Xtrack lattice 
    according to the naming of the elements

    Parameters:
    ----------
    line: xtrack.Line
        Xsuite Line object representing the lattice    

    Outputs
    ----------
    line: xtrack.Line
        Xsuite Line object representing the lattice
    """

    ############################################################################
    # Build Line Table
    ############################################################################
    line.build_tracker()
    line_table  = line.get_table(attr = True)
    line.discard_tracker()

    ############################################################################
    # Bend Knobs
    ############################################################################
    bend_names  = line_table.rows[line_table['element_type'] == 'Bend'].name

    for bend_name in bend_names:
        # Get the root name ignoring any numbering
        bend_class = get_element_class(bend_name)

        # If the bend has a k0, create a variable
        if line[bend_name].k0 != 0:
            line.vars[f'k0_{bend_class}']       = line[bend_name].k0
            # Assign the variable to the bend
            line.element_refs[bend_name].k0     = line.vars[f'k0_{bend_class}']

        # If the bend has a h value, and it's close to k0
        # Assign to the same variable
        if line[bend_name].h != 0:
            if np.isclose(line[bend_name].h, line[bend_name].k0, rtol=1E-3):
                line.element_refs[bend_name].h  = line.vars[f'k0_{bend_class}']

        # No such thing as k0s in xtrack, it is controlled by s_rotation

        # If the bend has a k1, create a variable
        if line[bend_name].k1 != 0:
            line.vars[f'k1_{bend_class}']       = line[bend_name].k1
            # Assign the variable to the bend
            line.element_refs[bend_name].k1     = line.vars[f'k1_{bend_class}']

    ############################################################################
    # Quadrupole Knobs
    ############################################################################
    quad_names  = line_table.rows[line_table['element_type'] == 'Quadrupole'].name

    for quad_name in quad_names:
        # Get the root name ignoring any numbering
        quad_class = get_element_class(quad_name)

        # If the quad has a k1, create a variable
        if line[quad_name].k1 != 0:
            line.vars[f'k1_{quad_class}']       = line[quad_name].k1
            # Assign the variable to the bend
            line.element_refs[quad_name].k1     = line.vars[f'k1_{quad_class}']

        # If the quad has a k1s, create a variable
        if line[quad_name].k1s != 0:
            line.vars[f'k1s_{quad_class}']      = line[quad_name].k1s
            # Assign the variable to the bend
            line.element_refs[quad_name].k1s    = line.vars[f'k1s_{quad_class}']

    ############################################################################
    # Sextupole Knobs
    ############################################################################
    sext_names  = line_table.rows[line_table['element_type'] == 'Sextupole'].name

    for sext_name in sext_names:
        # Get the root name ignoring any numbering
        sext_class = get_element_class(sext_name)

        # If the quad has a k1, create a variable
        if line[sext_name].k2 != 0:
            line.vars[f'k2_{sext_class}']       = line[sext_name].k2
            # Assign the variable to the bend
            line.element_refs[sext_name].k2     = line.vars[f'k2_{sext_class}']

        # If the quad has a k2s, create a variable
        if line[sext_name].k2s != 0:
            line.vars[f'k2s_{sext_class}']      = line[sext_name].k2s
            # Assign the variable to the bend
            line.element_refs[sext_name].k2s    = line.vars[f'k2s_{sext_class}']

    ############################################################################
    # RF Cavities
    ############################################################################
    cavi_names  = line_table.rows[line_table['element_type'] == 'Cavity'].name

    for cavi_name in cavi_names:
        # Get the root name ignoring any numbering
        cavi_class = get_element_class(cavi_name)

        # Create cavity variables
        line.vars[f'volt_{cavi_class}']    = line[cavi_name].voltage
        line.vars[f'freq_{cavi_class}']    = line[cavi_name].frequency
        line.vars[f'lag_{cavi_class}']     = line[cavi_name].lag

        # Assign the variables to the cavity
        line.element_refs[cavi_name].voltage   = line.vars[f'volt_{cavi_class}']
        line.element_refs[cavi_name].frequency = line.vars[f'freq_{cavi_class}']
        line.element_refs[cavi_name].lag       = line.vars[f'lag_{cavi_class}']

    ############################################################################
    # Return Line
    ############################################################################
    return line
