"""
(Unofficial) SAD to XSuite Converter

Reversal
"""

################################################################################
# Required Packages
################################################################################
import numpy as np

################################################################################
# Line Element Order Reversal
################################################################################
def reverse_line_element_order(line):
    """ Reverse the order of elements in a line and adjust their parameters
    accordingly to maintain the same physics but in the opposite direction.

    Parameters
    ----------
    line : xt.Line
        The original line to be reversed.

    Returns
    -------
    xt.Line
        A new line with elements in reverse order and adjusted parameters.
    """

    ########################################
    # Copy the line for changes
    ########################################
    env             = line.env
    env_elements    = list(set(env.elements.keys()))

    ########################################
    # Reverse Element Order
    ########################################
    line.mirror()

    ########################################
    # Get tables
    ########################################
    tt      = line.get_table(attr = True)
    tt_bend = tt.rows[
        (tt.element_type == 'Bend') | (tt.element_type == 'RBend')]
    tt_sol  = tt.rows[tt.element_type == 'Solenoid']
    tt_dxy  = tt.rows[tt.element_type == 'XYShift']

    ########################################
    # Get unique elements
    ########################################
    unique_bends    = list(set([name.split('::')[0] for name in tt_bend.name]))
    unique_sols     = list(set([name.split('::')[0] for name in tt_sol.name]))
    unique_dxys     = list(set([name.split('::')[0] for name in tt_dxy.name]))

    ########################################
    # Get only the non-reversed and handle reverse later
    ########################################
    # This only applies to the elements that can keep the minus sign
    unique_bends    = list(set(
        [name[1:] if name.startswith('-') else name for name in unique_bends]))
    unique_sols     = list(set(
        [name[1:] if name.startswith('-') else name for name in unique_sols]))
    unique_dxys     = list(set(
        [name[1:] if name.startswith('-') else name for name in unique_dxys]))

    ########################################
    # Bend Adjustments
    ########################################
    for bend in unique_bends:

        # Handling trying forward and reverse
        for bend in [bend, '-' + bend]:

            if bend not in env_elements:
                continue

            # Reverse entry/exit angles of bends
            entry_angle                 = env[bend].edge_entry_angle
            exit_angle                  = env[bend].edge_exit_angle
            env[bend].edge_entry_angle  = exit_angle
            env[bend].edge_exit_angle   = entry_angle

    ########################################
    # Solenoid Adjustments
    ########################################
    for sol in unique_sols:

        # Handling trying forward and reverse
        for sol in [sol, '-' + sol]:

            if sol not in env_elements:
                continue

            # Solenoid strength
            env[sol].ks *= -1

    ########################################
    # Reference Shifts
    ########################################
    for dxy in unique_dxys:

        # Handling trying forward and reverse
        for dxy in [dxy, '-' + dxy]:

            if dxy not in env_elements:
                continue
            env[dxy].dx *= -1
            env[dxy].dy *= -1

    return line

################################################################################
# Line Bend Direction Reversal
################################################################################
def reverse_line_bend_direction(line):
    """ Reverse the order of elements in a line and adjust their parameters
    accordingly to maintain the same physics but in the opposite direction.

    Parameters
    ----------
    line : xt.Line
        The original line to be reversed.

    Returns
    -------
    xt.Line
        A new line with elements in reverse order and adjusted parameters.
    """

    ########################################
    # Copy the line for changes
    ########################################
    env             = line.env
    env_elements    = list(set(env.elements.keys()))

    ########################################
    # Get tables
    ########################################
    tt      = line.get_table(attr = True)
    tt_bend = tt.rows[
        (tt.element_type == 'Bend') | (tt.element_type == 'RBend')]
    tt_quad = tt.rows[tt.element_type == 'Quadrupole']
    tt_sext = tt.rows[tt.element_type == 'Sextupole']
    tt_oct  = tt.rows[tt.element_type == 'Octupole']
    tt_mult = tt.rows[tt.element_type == 'Multipole']
    tt_sol  = tt.rows[tt.element_type == 'Solenoid']
    tt_dxy  = tt.rows[tt.element_type == 'XYShift']
    tt_chi1 = tt.rows[tt.element_type == 'YRotation']
    tt_chi2 = tt.rows[tt.element_type == 'XRotation']
    tt_chi3 = tt.rows[tt.element_type == 'SRotation']

    ########################################
    # Get unique elements
    ########################################
    unique_bends    = list(set([name.split('::')[0] for name in tt_bend.name]))
    unique_quads    = list(set([name.split('::')[0] for name in tt_quad.name]))
    unique_sexts    = list(set([name.split('::')[0] for name in tt_sext.name]))
    unique_octs     = list(set([name.split('::')[0] for name in tt_oct.name]))
    unique_mults    = list(set([name.split('::')[0] for name in tt_mult.name]))
    unique_sols     = list(set([name.split('::')[0] for name in tt_sol.name]))
    unique_dxys     = list(set([name.split('::')[0] for name in tt_dxy.name]))
    unique_chi1s    = list(set([name.split('::')[0] for name in tt_chi1.name]))
    unique_chi2s    = list(set([name.split('::')[0] for name in tt_chi2.name]))
    unique_chi3s    = list(set([name.split('::')[0] for name in tt_chi3.name]))

    ########################################
    # Get only the non-reversed and handle reverse later
    ########################################
    # This only applies to the elements that can keep the minus sign
    unique_bends    = list(set(
        [name[1:] if name.startswith('-') else name for name in unique_bends]))
    unique_sols     = list(set(
        [name[1:] if name.startswith('-') else name for name in unique_sols]))
    unique_dxys     = list(set(
        [name[1:] if name.startswith('-') else name for name in unique_dxys]))
    unique_chi1s    = list(set(
        [name[1:] if name.startswith('-') else name for name in unique_chi1s]))
    unique_chi2s    = list(set(
        [name[1:] if name.startswith('-') else name for name in unique_chi2s]))
    unique_chi3s    = list(set(
        [name[1:] if name.startswith('-') else name for name in unique_chi3s]))

    ########################################
    # Bend Adjustments
    ########################################
    for bend in unique_bends:

        # Handling trying forward and reverse
        for bend in [bend, '-' + bend]:

            if bend not in env_elements:
                continue
            
            env[bend].k0  *= -1
            env[bend].k1  *= +1
            env[bend].h   *= -1

            # Reverse entry/exit angles of bends
            env[bend].edge_entry_angle  *= -1
            env[bend].edge_exit_angle   *= -1

            # knl ksl Adjustments
            order   = env[bend]._order
            for even_order in np.arange(0, order + 1, 2):
                env[bend].knl[even_order] *= -1
                env[bend].ksl[even_order] *= +1
            for odd_order in np.arange(1, order + 1, 2):
                env[bend].knl[odd_order]  *= +1
                env[bend].ksl[odd_order]  *= -1

            # Offset adjustments
            env[bend].shift_x   *= -1
            env[bend].shift_y   *= +1
            env[bend].rot_s_rad *= -1

    ########################################
    # Quadrupole Adjustments
    ########################################
    for quad in unique_quads:

        env[quad].k1  *= +1
        env[quad].k1s *= -1

        # knl ksl Adjustments
        order   = env[quad]._order
        for even_order in np.arange(0, order + 1, 2):
            env[quad].knl[even_order] *= -1
            env[quad].ksl[even_order] *= +1
        for odd_order in np.arange(1, order + 1, 2):
            env[quad].knl[odd_order]  *= +1
            env[quad].ksl[odd_order]  *= -1

        # Offset adjustments
        env[quad].shift_x   *= -1
        env[quad].shift_y   *= +1
        env[quad].rot_s_rad *= -1

    ########################################
    # Sextupole Adjustments
    ########################################
    for sext in unique_sexts:

        env[sext].k2  *= -1
        env[sext].k2s *= +1

        # knl ksl Adjustments
        order   = env[sext]._order
        for even_order in np.arange(0, order + 1, 2):
            env[sext].knl[even_order] *= -1
            env[sext].ksl[even_order] *= +1
        for odd_order in np.arange(1, order + 1, 2):
            env[sext].knl[odd_order]  *= +1
            env[sext].ksl[odd_order]  *= -1

        # Offset adjustments
        env[sext].shift_x   *= -1
        env[sext].shift_y   *= +1
        env[sext].rot_s_rad *= -1

    ########################################
    # Octupole Adjustments
    ########################################
    for oct in unique_octs:

        env[oct].k3     *= +1
        env[oct].k3s    *= -1

        # knl ksl Adjustments
        order   = env[oct]._order
        for even_order in np.arange(0, order + 1, 2):
            env[oct].knl[even_order]  *= -1
            env[oct].ksl[even_order]  *= +1
        for odd_order in np.arange(1, order + 1, 2):
            env[oct].knl[odd_order]   *= +1
            env[oct].ksl[odd_order]   *= -1

        # Offset adjustments
        env[oct].shift_x    *= -1
        env[oct].shift_y    *= +1
        env[oct].rot_s_rad  *= -1

    ########################################
    # Multipole Adjustments
    ########################################
    for mult in unique_mults:

        # knl ksl Adjustments
        order   = env[mult]._order
        for even_order in np.arange(0, order + 1, 2):
            env[mult].knl[even_order] *= -1
            env[mult].ksl[even_order] *= +1
        for odd_order in np.arange(1, order + 1, 2):
            env[mult].knl[odd_order]  *= +1
            env[mult].ksl[odd_order]  *= -1

        # Offset adjustments
        env[mult].shift_x   *= -1
        env[mult].shift_y   *= +1
        env[mult].rot_s_rad *= -1

    ########################################
    # Solenoid Adjustments
    ########################################
    for sol in unique_sols:

        # Handling trying forward and reverse
        for sol in [sol, '-' + sol]:

            if sol not in env_elements:
                continue

            # Solenoid strength
            env[sol].ks *= -1

            # knl ksl Adjustments
            order   = env[sol]._order
            for even_order in np.arange(0, order + 1, 2):
                env[sol].knl[even_order]  *= -1
                env[sol].ksl[even_order]  *= +1
            for odd_order in np.arange(1, order + 1, 2):
                env[sol].knl[odd_order]   *= +1
                env[sol].ksl[odd_order]   *= -1

            # Offset adjustments
            env[sol].mult_shift_x   *= -1
            env[sol].mult_shift_y   *= +1
            env[sol].rot_s_rad      *= -1

    ########################################
    # Reference Shifts
    ########################################
    for dxy in unique_dxys:

        # Handling trying forward and reverse
        for dxy in [dxy, '-' + dxy]:

            if dxy not in env_elements:
                continue
            env[dxy].dx *= -1
            env[dxy].dy *= +1

    for chi1 in unique_chi1s:

        # Handling trying forward and reverse
        for chi1 in [chi1, '-' + chi1]:
            
            if chi1 not in env_elements:
                continue
            env[chi1].angle *= -1

    for chi2 in unique_chi2s:

        # Handling trying forward and reverse
        for chi2 in [chi2, '-' + chi2]:
            
            if chi2 not in env_elements:
                continue
            env[chi2].angle *= +1

    for chi3 in unique_chi3s:

        # Handling trying forward and reverse
        for chi3 in [chi3, '-' + chi3]:
            
            if chi3 not in env_elements:
                continue
            env[chi3].angle *= -1

    return line

################################################################################
# Charge Reversal
################################################################################
def reverse_line_charge(line):
    """ Reverse the order of elements in a line and adjust their parameters
    accordingly to maintain the same physics but in the opposite direction.

    Parameters
    ----------
    line : xt.Line
        The original line to be reversed.

    Returns
    -------
    xt.Line
        A new line with elements in reverse order and adjusted parameters.
    """

    ########################################
    # Flip the charge
    ########################################
    line.particle_ref.q0  *= -1

    return line