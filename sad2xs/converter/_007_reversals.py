"""
================================================================================
Line Reversals
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
# Required Packages
################################################################################
import numpy as np

################################################################################
# Line Element Order Reversal
################################################################################
def reverse_line_element_order(line):
    """
    Reverse a line's element order (SAD's '-LINE' operator).

    Mirrors the line (via `xt.Line.mirror`) and then fixes up the
    physics quantities that a plain element-order reversal gets wrong:
    bend edge angles/fringe fint/hgap are swapped (the old exit edge
    becomes the new entry edge and vice versa), solenoid ks is
    negated, and solenoid GEO reference-shift Translations (name
    suffix "_dxy") are negated since the former exit boundary is now
    the entrance. Standalone COORD-derived Translations (no "_dxy"
    suffix) are left unchanged, since a COORD offset is a fixed
    geometric property of the beampipe and does not flip sign under
    reversal (verified against SAD's own `-LINE` output for both
    cases).

    Parameters
    ----------
    line : xt.Line
        The original line to be reversed.

    Returns
    -------
    xt.Line
        The same line object, mirrored and with reversal-sensitive
        parameters corrected in place.
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
        (tt.element_type == "Bend") | (tt.element_type == "RBend")]
    tt_sol  = tt.rows[tt.element_type == "UniformSolenoid"]
    tt_dxy  = tt.rows[tt.element_type == "Translation"]

    ########################################
    # Get unique elements
    ########################################
    unique_bends    = list(set([name.split("::")[0] for name in tt_bend.name]))
    unique_sols     = list(set([name.split("::")[0] for name in tt_sol.name]))
    unique_dxys     = list(set([name.split("::")[0] for name in tt_dxy.name]))

    ########################################
    # Get only the non-reversed and handle reverse later
    ########################################
    # This only applies to the elements that can keep the minus sign
    unique_bends    = list(set(
        [name[1:] if name.startswith("-") else name for name in unique_bends]))
    unique_sols     = list(set(
        [name[1:] if name.startswith("-") else name for name in unique_sols]))
    unique_dxys     = list(set(
        [name[1:] if name.startswith("-") else name for name in unique_dxys]))

    ########################################
    # Bend Adjustments
    ########################################
    for bend in unique_bends:

        # Handling trying forward and reverse
        for bend in [bend, "-" + bend]:

            if bend not in env_elements:
                continue

            # Reverse entry/exit angles of bends
            entry_angle                 = env[bend].edge_entry_angle
            exit_angle                  = env[bend].edge_exit_angle
            env[bend].edge_entry_angle  = exit_angle
            env[bend].edge_exit_angle   = entry_angle

            # Reverse entry/exit fringe fields (SAD F1/FB1/FB2 -> fint/hgap)
            entry_fint                  = env[bend].edge_entry_fint
            exit_fint                   = env[bend].edge_exit_fint
            env[bend].edge_entry_fint   = exit_fint
            env[bend].edge_exit_fint    = entry_fint

            entry_hgap                  = env[bend].edge_entry_hgap
            exit_hgap                   = env[bend].edge_exit_hgap
            env[bend].edge_entry_hgap   = exit_hgap
            env[bend].edge_exit_hgap    = entry_hgap

    ########################################
    # Solenoid Adjustments
    ########################################
    for sol in unique_sols:

        # Handling trying forward and reverse
        for sol in [sol, "-" + sol]:

            if sol not in env_elements:
                continue

            # Solenoid strength
            env[sol].ks *= -1

    ########################################
    # Reference Shifts
    ########################################
    # Two categories of Translation element require different treatment:
    #
    # 1. Solenoid GEO translations (suffix "_dxy", e.g. sol_in_dxy / sol_out_dxy)
    #    These are created by the solenoid converter to express the GEO-computed
    #    reference-frame entry/exit offsets.  When the element order is reversed,
    #    SOL_OUT becomes the new entry and SOL_IN becomes the new exit, so both
    #    shifts must be negated to keep the beam on-axis through the solenoid.
    #    Empirically verified against SAD's LINE TESTREV = (-TEST) with BZ > 0
    #    and DX != 0 after rebuild_sad_lattice bakes in the GEO values.
    #
    # 2. Standalone COORD translations (any name without the "_dxy" suffix)
    #    A COORD offset is a geometric property of the beampipe at that point —
    #    it does not change sign when the beam direction is reversed.  SAD's own
    #    LINE TESTREV = (-TEST) gives identical x displacement to the forward
    #    line for a COORD(DX=d) element, confirming that no negation is applied.
    #    Negating here would produce the wrong orbit.
    for dxy in unique_dxys:

        # Handling trying forward and reverse
        for dxy in [dxy, "-" + dxy]:

            if dxy not in env_elements:
                continue

            if dxy.lstrip("-").endswith("_dxy"):
                env[dxy].shift_x *= -1
                env[dxy].shift_y *= -1

    return line

################################################################################
# Line Bend Direction Reversal
################################################################################
def reverse_line_survey_horizontal(line):
    """
    Flip a line's horizontal bend direction (mirror the survey through
    the horizontal plane), without reversing element order.

    Every element keeps its position in the line, but each bending/
    field-carrying element has its horizontal-plane quantities
    negated and vertical-plane quantities left alone (or vice versa,
    following each element's own reflection parity): bend angle/k0
    and even knl/odd ksl orders negate, quadrupole/sextupole/
    octupole/multipole field orders negate by the same even/odd
    parity rule, and every element's shift_x/rot_s_rad negate while
    shift_y stays unchanged (a reflection through the horizontal
    plane). Solenoids additionally get their x0/y0 recomputed from
    the new shift/rotation. Standalone Translation/Rotation
    reference-shift elements follow the same pattern: Translation's
    shift_x negates and shift_y is unchanged; Rotation's rot_y_rad and
    rot_s_rad negate and rot_x_rad is unchanged.

    Parameters
    ----------
    line : xt.Line
        The original line whose bend direction should be flipped.

    Returns
    -------
    xt.Line
        The same line object, with reflection-sensitive parameters
        corrected in place.
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
        (tt.element_type == "Bend") | (tt.element_type == "RBend")]
    tt_quad = tt.rows[tt.element_type == "Quadrupole"]
    tt_sext = tt.rows[tt.element_type == "Sextupole"]
    tt_oct  = tt.rows[tt.element_type == "Octupole"]
    tt_mult = tt.rows[tt.element_type == "Multipole"]
    tt_sol  = tt.rows[tt.element_type == "UniformSolenoid"]
    tt_dxy  = tt.rows[tt.element_type == "Translation"]
    tt_rot  = tt.rows[tt.element_type == "Rotation"]

    ########################################
    # Get unique elements
    ########################################
    unique_bends    = list(set([name.split("::")[0] for name in tt_bend.name]))
    unique_quads    = list(set([name.split("::")[0] for name in tt_quad.name]))
    unique_sexts    = list(set([name.split("::")[0] for name in tt_sext.name]))
    unique_octs     = list(set([name.split("::")[0] for name in tt_oct.name]))
    unique_mults    = list(set([name.split("::")[0] for name in tt_mult.name]))
    unique_sols     = list(set([name.split("::")[0] for name in tt_sol.name]))
    unique_dxys     = list(set([name.split("::")[0] for name in tt_dxy.name]))
    unique_rots     = list(set([name.split("::")[0] for name in tt_rot.name]))

    ########################################
    # Get only the non-reversed and handle reverse later
    ########################################
    # This only applies to the elements that can keep the minus sign
    unique_bends    = list(set(
        [name[1:] if name.startswith("-") else name for name in unique_bends]))
    unique_sols     = list(set(
        [name[1:] if name.startswith("-") else name for name in unique_sols]))
    unique_dxys     = list(set(
        [name[1:] if name.startswith("-") else name for name in unique_dxys]))
    unique_rots     = list(set(
        [name[1:] if name.startswith("-") else name for name in unique_rots]))

    ########################################
    # Bend Adjustments
    ########################################
    for bend in unique_bends:

        # Handling trying forward and reverse
        for bend in [bend, "-" + bend]:

            if bend not in env_elements:
                continue

            env[bend].angle *= -1
            env[bend].k0    *= -1
            env[bend].k1    *= +1

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
        for sol in [sol, "-" + sol]:

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
            env[sol].shift_x    *= -1
            env[sol].shift_y    *= +1
            env[sol].rot_s_rad  *= -1

            x0          = -1 * (env[sol].shift_x * np.cos(env[sol].rot_s_rad) + \
                env[sol].shift_y * np.sin(env[sol].rot_s_rad))
            y0          = -1 * (env[sol].shift_y * np.cos(env[sol].rot_s_rad) - \
                env[sol].shift_x * np.sin(env[sol].rot_s_rad))
            env[sol].x0         = x0
            env[sol].y0         = y0

    ########################################
    # Reference Shifts
    ########################################
    for dxy in unique_dxys:

        # Handling trying forward and reverse
        for dxy in [dxy, "-" + dxy]:

            if dxy not in env_elements:
                continue
            env[dxy].shift_x *= -1
            env[dxy].shift_y *= +1

    for rot in unique_rots:

        # Handling trying forward and reverse
        for rot in [rot, "-" + rot]:

            if rot not in env_elements:
                continue
            env[rot].rot_y_rad *= -1
            env[rot].rot_x_rad *= +1
            env[rot].rot_s_rad *= -1

    return line
