"""
================================================================================
Solenoid Converter
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
# Required Packages
################################################################################
import logging

import numpy as np
import xtrack as xt

from ..types import ConfigLike
from ._000_helpers import is_effectively_zero

logger  = logging.getLogger(__name__)

################################################################################
# Conversion Function
################################################################################
def convert_solenoids(
        parsed_lattice_data:    dict,
        environment:            xt.Environment,
        config:                 ConfigLike) -> None:
    """
    Convert non-solenoid elements inside bound solenoid regions into
    equivalent UniformSolenoid elements carrying the local ks.

    Between each pair of BOUND solenoid markers, every element picks
    up the solenoidal field active at that point in the lattice (the
    ks of the nearest preceding, or if reversed, nearest following,
    boundary solenoid): Drifts convert directly; Bend/Quadrupole/
    Sextupole/Octupole/Multipole elements convert to a UniformSolenoid
    carrying both their own field (as knl/ksl) and ks, with x0/y0 set
    to keep the transverse offset consistent under the field rotation.
    Thin, field-free elements (Translation, TimeDelay, Rotation,
    Marker, aperture limits, zero-length Cavity) are left alone; any
    other thick element found inside a solenoid region is warned
    about, not converted.

    Parameters
    ----------
    parsed_lattice_data : dict
        Parsed lattice data, as returned by `parse_sad_file`.
    environment : xt.Environment
        The Xsuite environment containing the lines and elements to
        convert. Must already have every element and every line
        created (including reversed lines).
    config : ConfigLike
        Converter configuration; only `MAX_KNL_ORDER` is used.

    Raises
    ------
    ValueError
        If BOUND solenoids in a line are not paired (an odd number in
        entrance/exit order).
    """

    ########################################
    # Get the required data
    ########################################
    parsed_elements = parsed_lattice_data["elements"]

    ########################################
    # Check if there are any solenoids
    ########################################
    if "sol" not in parsed_elements:
        logger.info("No solenoids in lattice: skipping solenoid corrections")
        return
    solenoids: dict                      = parsed_elements["sol"]
    n_converted: int                     = 0
    powered_dipole_elements: set[str]    = set()
    powered_offset_fringes: set[str]     = set()

    ########################################
    # Get bound and geo solenoids
    ########################################
    bound_solenoids = []
    geo_solenoids   = []
    for ele_name, ele_vars in solenoids.items():

        if "bound" in ele_vars:
            bound_solenoids.append(ele_name)
        if "geo" in ele_vars:
            geo_solenoids.append(ele_name)

    ############################################################################
    # Iterate through lines
    ############################################################################
    for line_name in environment.lines:

        # The line may be a compound solenoid element
        # e.g. dx, chi1, sol
        if line_name in bound_solenoids:
            continue
        if line_name.endswith("_reversed") and line_name[:-9] in bound_solenoids:
            continue

        line    = environment.lines[line_name]

        bound_sols_in_line      = []
        bound_solenoid_indicies = []
        for idx, element in enumerate(line.element_names):

            # Element must actually be a solenoid
            if not isinstance(environment.element_dict[element], xt.UniformSolenoid):  # type: ignore
                continue

            # Case where the element is a bound solenoid with the right name
            if element in bound_solenoids:
                bound_sols_in_line.append(element)
                bound_solenoid_indicies.append(idx)
            # Case where the bound solenoid has the _bound suffix
            elif element.endswith("_bound") and element[:-6] in bound_solenoids:
                bound_sols_in_line.append(element)
                bound_solenoid_indicies.append(idx)
            # Same cases, but for reversed elements
            # Case where the element is a bound solenoid with the right name
            elif element[1:] in bound_solenoids:
                bound_sols_in_line.append(element)
                bound_solenoid_indicies.append(idx)
            # Case where the bound solenoid has the _bound suffix
            elif element.endswith("_bound") and element[1:-6] in bound_solenoids:
                bound_sols_in_line.append(element)
                bound_solenoid_indicies.append(idx)

        # If no bound solenoids are found in the line, skip to the next line
        if len(bound_sols_in_line) == 0:
            continue

        ########################################
        # Ensure an even number of boundary solenoids
        ########################################
        bound_solenoid_pairs            = []
        bound_solenoid_pair_indicies    = []
        for i in range(0, len(bound_sols_in_line), 2):
            if i + 1 < len(bound_sols_in_line):
                bound_solenoid_pairs.append(
                    (bound_sols_in_line[i], bound_sols_in_line[i + 1]))
                bound_solenoid_pair_indicies.append(
                    (bound_solenoid_indicies[i], bound_solenoid_indicies[i + 1]))
            else:
                raise ValueError(
                    f"Unmatched boundary solenoid {bound_sols_in_line[i]} in "
                    f"line {line_name}: BOUND solenoids must come in "
                    "entrance/exit pairs.")

        ########################################
        # Get the elements between bound solenoids
        ########################################
        reversed_solenoid   = False
        previous_solenoid   = None
        ahead_solenoid      = None
        ks_previous         = 0
        ks_ahead            = 0
        segment_length      = 0
        ele_length          = 0

        ########################################
        # Get the elements between bound solenoids
        ########################################
        for (sol_start, sol_end), (start_idx, end_idx) in zip(
                bound_solenoid_pairs, bound_solenoid_pair_indicies):

            if start_idx > end_idx:
                raise ValueError(
                    f"Start solenoid {sol_start} is after " +\
                    f"end solenoid {sol_end} in line {line_name}.")

            ########################################
            # Loop through the elements between
            ########################################
            # Here, iterate through all the elements in the line
            # Enumerate also for the index
            # If the element index < start_index, it is before the solenoid
            # If the element index > end_index, it is after the solenoid
            # If the element index is between start_index and end_index, it is between the solenoids
            # Makes it easier to do the replacement
            for idx, element in enumerate(line.element_names):

                if idx < start_idx or idx >= end_idx:
                    # If the element is before or after the solenoid, skip it
                    continue

                # Do the swaps if the element is reversed
                if reversed_solenoid:
                    solenoid_suffix = ahead_solenoid
                    ks              = ks_ahead
                else:
                    solenoid_suffix = previous_solenoid
                    ks              = ks_previous

                # If the element is a solenoid, update the current solenoidal field
                if isinstance(environment.element_dict[element], xt.UniformSolenoid):  # type: ignore

                    # Start calculating new segment length
                    segment_length = ele_length

                    # If the solenoid is reversed, we need to swap to that case
                    if element.startswith("-"):
                        reversed_solenoid    = True
                    else:
                        reversed_solenoid    = False

                    if element.endswith("_bound"):
                        # If the element is a bound solenoid clip this bit
                        previous_solenoid    = element[:-6]
                    else:
                        previous_solenoid    = element
                    ks_previous         = line[element].ks

                    # Get the information about the ahead solenoid
                    for ahead_element in line.element_names[idx + 1:]:
                        # If the element is a solenoid, update the solenoidal field
                        if isinstance(environment.element_dict[ahead_element], xt.UniformSolenoid):    # type: ignore
                            if ahead_element.endswith("_bound"):
                                # If the element is a bound solenoid clip this bit
                                ahead_solenoid      = ahead_element[:-6]
                            else:
                                ahead_solenoid      = ahead_element
                            ks_ahead            = line[ahead_element].ks
                            break
                        else:
                            try:
                                segment_length += line[ahead_element].length
                            except AttributeError:
                                # Some elements (like markers) have no length
                                pass

                    continue

                # Drift conversion
                elif isinstance(environment.element_dict[element], xt.Drift):   # type: ignore

                    length              = line[element].length
                    new_element_name    = f"{element}_{solenoid_suffix}"

                    if new_element_name not in environment.element_dict:        # type: ignore
                        environment.new(
                            name      = new_element_name,
                            prototype = xt.UniformSolenoid,
                            length    = length,
                            ks        = ks)
                    line.element_names[idx] = new_element_name

                    n_converted += 1
                    logger.debug(
                        f"Converted drift {element} to solenoid "
                        f"{new_element_name} with ks = {ks}")
                    continue

                # Bend conversion
                elif isinstance(environment.element_dict[element], xt.Bend):        # type: ignore

                    assert line[element].h == 0, \
                        f"Bend {element} with non-zero angle found between solenoids."

                    length      = line[element].length
                    k0          = line[element].k0
                    k1          = line[element].k1
                    shift_x     = line[element].shift_x
                    shift_y     = line[element].shift_y
                    rotation    = line[element].rot_s_rad
                    knl         = [f"{k0} * {length}", f"{k1} * {length}"]

                    if not is_effectively_zero(ks, tol = 0.0) \
                            and not is_effectively_zero(k0, tol = 0.0):
                        powered_dipole_elements.add(element.lstrip("-"))

                    x0          = -1 * (shift_x * np.cos(rotation) + \
                        shift_y * np.sin(rotation))
                    y0          = -1 * (shift_y * np.cos(rotation) - \
                        shift_x * np.sin(rotation))

                    new_element_name    = f"{element}_{solenoid_suffix}"

                    if new_element_name not in environment.element_dict:        # type: ignore
                        environment.new(
                            name        = new_element_name,
                            prototype   = xt.UniformSolenoid,
                            length      = length,
                            ks          = ks,
                            knl         = knl,
                            order       = config.MAX_KNL_ORDER,
                            shift_x     = shift_x,
                            shift_y     = shift_y,
                            rot_s_rad   = rotation,
                            x0          = x0,
                            y0          = y0)

                    line.element_names[idx] = new_element_name

                    n_converted += 1
                    logger.debug(
                        f"Converted Bend {element} to solenoid "
                        f"{new_element_name} with ks = {ks}")
                    continue

                # Quadrupole conversion
                elif isinstance(environment.element_dict[element], xt.Quadrupole):   # type: ignore

                    length      = line[element].length
                    k1          = line[element].k1
                    k1s         = line[element].k1s
                    shift_x     = line[element].shift_x
                    shift_y     = line[element].shift_y
                    rotation    = line[element].rot_s_rad
                    knl         = [0, f"{k1} * {length}"]
                    ksl         = [0, f"{k1s} * {length}"]

                    x0          = -1 * (shift_x * np.cos(rotation) + \
                        shift_y * np.sin(rotation))
                    y0          = -1 * (shift_y * np.cos(rotation) - \
                        shift_x * np.sin(rotation))

                    new_element_name    = f"{element}_{solenoid_suffix}"

                    if new_element_name not in environment.element_dict:        # type: ignore
                        environment.new(
                            name				= new_element_name,
                            prototype			= xt.UniformSolenoid,
                            length				= length,
                            ks					= ks,
                            knl					= knl,
                            ksl					= ksl,
                            order				= config.MAX_KNL_ORDER,
                            shift_x		        = shift_x,
                            shift_y		        = shift_y,
                            rot_s_rad           = rotation,
                            x0                  = x0,
                            y0                  = y0)
                    line.element_names[idx] = new_element_name

                    n_converted += 1
                    logger.debug(
                        f"Converted Quadrupole {element} to solenoid "
                        f"{new_element_name} with ks = {ks}")
                    continue

                # Sextupole conversion
                elif isinstance(environment.element_dict[element], xt.Sextupole):   # type: ignore

                    length      = line[element].length
                    k2          = line[element].k2
                    k2s         = line[element].k2s
                    shift_x     = line[element].shift_x
                    shift_y     = line[element].shift_y
                    rotation    = line[element].rot_s_rad
                    knl         = [0, 0, f"{k2} * {length}"]
                    ksl         = [0, 0, f"{k2s} * {length}"]

                    x0          = -1 * (shift_x * np.cos(rotation) + \
                        shift_y * np.sin(rotation))
                    y0          = -1 * (shift_y * np.cos(rotation) - \
                        shift_x * np.sin(rotation))

                    new_element_name    = f"{element}_{solenoid_suffix}"

                    if new_element_name not in environment.element_dict:     # type: ignore
                        environment.new(
                            name				= new_element_name,
                            prototype			= xt.UniformSolenoid,
                            length				= length,
                            ks					= ks,
                            knl					= knl,
                            ksl					= ksl,
                            order				= config.MAX_KNL_ORDER,
                            shift_x		        = shift_x,
                            shift_y		        = shift_y,
                            rot_s_rad           = rotation,
                            x0                  = x0,
                            y0                  = y0)
                    line.element_names[idx] = new_element_name

                    n_converted += 1
                    logger.debug(
                        f"Converted Sextupole {element} to solenoid "
                        f"{new_element_name} with ks = {ks}")
                    continue

                # Octupole conversion
                elif isinstance(environment.element_dict[element], xt.Octupole):    # type: ignore

                    length      = line[element].length
                    k3          = line[element].k3
                    k3s         = line[element].k3s
                    shift_x     = line[element].shift_x
                    shift_y     = line[element].shift_y
                    rotation    = line[element].rot_s_rad
                    knl         = [0, 0, 0, f"{k3} * {length}"]
                    ksl         = [0, 0, 0, f"{k3s} * {length}"]

                    x0          = -1 * (shift_x * np.cos(rotation) + \
                        shift_y * np.sin(rotation))
                    y0          = -1 * (shift_y * np.cos(rotation) - \
                        shift_x * np.sin(rotation))

                    new_element_name    = f"{element}_{solenoid_suffix}"

                    if new_element_name not in environment.element_dict:    # type: ignore
                        environment.new(
                            name				= new_element_name,
                            prototype			= xt.UniformSolenoid,
                            length				= length,
                            ks					= ks,
                            knl					= knl,
                            ksl					= ksl,
                            order				= config.MAX_KNL_ORDER,
                            shift_x		        = shift_x,
                            shift_y		        = shift_y,
                            rot_s_rad           = rotation,
                            x0                  = x0,
                            y0                  = y0)
                    line.element_names[idx] = new_element_name

                    n_converted += 1
                    logger.debug(
                        f"Converted Octupole {element} to solenoid "
                        f"{new_element_name} with ks = {ks}")
                    continue

                # Multipole conversion
                elif isinstance(environment.element_dict[element], xt.Multipole):   # type: ignore

                    length      = line[element].length
                    knl         = line[element].knl
                    ksl         = line[element].ksl
                    shift_x     = line[element].shift_x
                    shift_y     = line[element].shift_y
                    rotation    = line[element].rot_s_rad

                    if not is_effectively_zero(ks, tol = 0.0) and (
                            not is_effectively_zero(knl[0], tol = 0.0)
                            or not is_effectively_zero(ksl[0], tol = 0.0)):
                        powered_dipole_elements.add(element.lstrip("-"))

                    x0          = -1 * (shift_x * np.cos(rotation) + \
                        shift_y * np.sin(rotation))
                    y0          = -1 * (shift_y * np.cos(rotation) - \
                        shift_x * np.sin(rotation))

                    new_element_name = f"{element}_{solenoid_suffix}"
                    if new_element_name not in environment.element_dict:  # type: ignore
                        environment.new(
                            name        = new_element_name,
                            prototype   = xt.UniformSolenoid,
                            length      = length,
                            ks          = ks,
                            knl         = knl,
                            ksl         = ksl,
                            order       = config.MAX_KNL_ORDER,
                            shift_x     = shift_x,
                            shift_y     = shift_y,
                            rot_s_rad   = rotation,
                            x0          = x0,
                            y0          = y0)
                    line.element_names[idx] = new_element_name

                    n_converted += 1
                    logger.debug(
                        f"Converted Multipole {element} to solenoid "
                        f"{new_element_name} with ks = {ks}")
                    continue

                # Solenoid segment edges supply the local canonical transform,
                # so the centred source fringe map remains unchanged.
                elif isinstance(
                        environment.element_dict[element],
                        xt.SecondOrderTaylorMap):
                    source_map = line[element]
                    if element not in environment.metadata.get(
                            "sad2xs", {}).get(
                                "soft_quadrupolar_fringes", {}):
                        logger.warning(
                            f"Element {element} in line {line_name} has not "
                            "been converted")
                        continue
                    if is_effectively_zero(ks, tol = 0.0):
                        continue
                    if float(source_map.shift_x) != 0.0 \
                            or float(source_map.shift_y) != 0.0:
                        source_name = element.lstrip("-")
                        for suffix in ("_fringe_in", "_fringe_out"):
                            if source_name.endswith(suffix):
                                source_name = source_name[:-len(suffix)]
                                break
                        powered_offset_fringes.add(source_name)
                    continue

                # Known thin elements that don't need conversion
                elif isinstance(
                    environment.element_dict[element],      # type: ignore
                    (
                        xt.Translation,
                        xt.TimeDelay,
                        xt.Rotation,
                        xt.Marker,
                        xt.LimitEllipse,
                        xt.LimitRect,
                        xt.LimitRectEllipse)):
                    continue
                # Thin RF doesn't need conversion
                elif isinstance(environment.element_dict[element], xt.Cavity) \
                        and line[element].length == 0:
                    continue
                # Other potentially thick elements to warn on
                else:
                    logger.warning(
                        f"Element {element} in line {line_name} has not been converted")

    if powered_dipole_elements:
        logger.warning(
            f"{len(powered_dipole_elements)} element(s) have "
            "K0/SK0 body components inside powered bound-solenoid "
            "regions. Xtrack's split solenoid/multipole map differs from "
            "SAD's combined paraxial body map and can accumulate orbit and "
            "coupled-optics differences.")
        logger.debug(
            "Elements affected by the powered-solenoid K0/SK0 body "
            "limitation: " + ", ".join(sorted(powered_dipole_elements)))

    if powered_offset_fringes:
        logger.warning(
            f"{len(powered_offset_fringes)} offset element(s) "
            "with SAD K1 soft-edge fringes occur inside powered bound-solenoid "
            "regions. SAD's combined DX/DY and local-BZ convention is not "
            "reproduced exactly.")
        logger.debug(
            "Offset elements with K1 fringes affected by the powered-solenoid "
            "limitation: "
            + ", ".join(sorted(powered_offset_fringes)))

    logger.info(f"Converted {n_converted} elements inside solenoid regions")

###############################################################################
# Reference shift corrections
###############################################################################
def solenoid_reference_shift_corrections(
        line:                   xt.Line,
        parsed_lattice_data:    dict,
        environment:            xt.Environment,
        reverse_line:           bool,
        config:                 ConfigLike) -> None:
    """
    Correct and reorder the reference-frame shift elements installed
    by `convert_solenoids` for each bound solenoid boundary.

    Each BOUND solenoid was converted (in
    `_004_element_converter.convert_solenoids`) to a sub-line of
    [UniformSolenoid, Translation, TimeDelay, Rotation] components in a
    fixed generic order; this function fixes that
    order and the sign of the Translation/Rotation parameters per
    boundary, based on whether it is an inbound (entrance) or outbound
    (exit) boundary, whether it is the GEO boundary of its pair, and
    whether the inbound/outbound solenoids of the pair were
    individually reversed (by line reversal). The correct sign
    combinations were verified empirically against real SAD Twiss
    output (see test_sol_reference_transform_orbit_matches_sad_twiss
    and test_sol_reference_transform_restores_design_orbit_at_end).

    Parameters
    ----------
    line : xt.Line
        The line whose bound solenoid boundaries should be corrected.
    parsed_lattice_data : dict
        Parsed lattice data, as returned by `parse_sad_file`.
    environment : xt.Environment
        The Xsuite environment containing `line`'s elements.
    reverse_line : bool
        Not used directly by this function -- reversal is instead
        detected per solenoid from its own name (a leading `-`).
        Accepted for interface consistency with the conversion
        pipeline's other line-level correction calls.
    config : ConfigLike
        Not used directly by this function. Accepted for interface
        consistency with the conversion pipeline's other line-level
        correction calls.

    Raises
    ------
    ValueError
        If BOUND solenoids in `line` are not paired, or if neither
        solenoid in a pair is the GEO boundary.
    """

    ########################################
    # Get the required data
    ########################################
    parsed_elements = parsed_lattice_data["elements"]

    ########################################
    # Check if there are any solenoids
    ########################################
    if "sol" not in parsed_elements:
        logger.debug(
            "No solenoids in lattice: skipping reference shift corrections")
        return
    solenoids   = parsed_elements["sol"]

    ########################################
    # Get bound and geo solenoids
    ########################################
    bound_solenoids = []
    geo_solenoids   = []
    for ele_name, ele_vars in solenoids.items():

        if "bound" in ele_vars:
            bound_solenoids.append(ele_name)
        if "geo" in ele_vars:
            geo_solenoids.append(ele_name)

    ########################################
    # Get bound solenoids in the line
    ########################################
    bound_sols_in_line  = []
    geo_sols_in_line    = []
    for element in line.element_names:
        # Element must actually be a solenoid
        if not isinstance(environment.element_dict[element], xt.UniformSolenoid):  # type: ignore
            continue

        # Case where the element is a bound solenoid with the right name
        if element in bound_solenoids:
            bound_sols_in_line.append(element)
        # Case where the bound solenoid has the _bound suffix
        elif element.endswith("_bound") and element[:-6] in bound_solenoids:
            bound_sols_in_line.append(element)
        # Same cases, but for reversed elements
        # Case where the element is a bound solenoid with the right name
        elif element[1:] in bound_solenoids:
            bound_sols_in_line.append(element)
        # Case where the bound solenoid has the _bound suffix
        elif element.endswith("_bound") and element[1:-6] in bound_solenoids:
            bound_sols_in_line.append(element)

        # Case where the element is a geo solenoid with the right name
        if element in geo_solenoids:
            geo_sols_in_line.append(element)
        # Case where the geo solenoid has the _bound suffix
        elif element.endswith("_bound") and element[:-6] in geo_solenoids:
            geo_sols_in_line.append(element)
        # Same cases, but for reversed elements
        # Case where the element is a bound solenoid with the right name
        elif element[1:] in geo_solenoids:
            geo_sols_in_line.append(element)
        # Case where the geo solenoid has the _bound suffix
        elif element.endswith("_bound") and element[1:-6] in geo_solenoids:
            geo_sols_in_line.append(element)

    # If no bound solenoids are found in the line, return
    if len(bound_sols_in_line) == 0:
        return

    ########################################
    # Ensure an even number of boundary solenoids
    ########################################
    bound_solenoid_pairs    = []
    for i in range(0, len(bound_sols_in_line), 2):
        if i + 1 < len(bound_sols_in_line):
            bound_solenoid_pairs.append(
                (bound_sols_in_line[i], bound_sols_in_line[i + 1]))
        else:
            raise ValueError(
                f"Unmatched boundary solenoid {bound_sols_in_line[i]}: "
                "BOUND solenoids must come in entrance/exit pairs.")

    ############################################################################
    # Get the inbound and outbound boundary solenoids
    ############################################################################
    inbound_solenoids   = [pair[0] for pair in bound_solenoid_pairs]
    outbound_solenoids  = [pair[1] for pair in bound_solenoid_pairs]
    # For each of the pairs, one of them is a geomatric solenoid
    geometric_solenoids     = []
    non_geometric_solenoids = []
    for pair in bound_solenoid_pairs:
        if pair[0] in geo_sols_in_line:
            geometric_solenoids.append(pair[0])
            non_geometric_solenoids.append(pair[1])
        elif pair[1] in geo_sols_in_line:
            geometric_solenoids.append(pair[1])
            non_geometric_solenoids.append(pair[0])
        else:
            raise ValueError(f"Neither solenoid in pair {pair} is a geometric solenoid.")

    inbound_solenoids       = list(set(inbound_solenoids))
    outbound_solenoids      = list(set(outbound_solenoids))
    geometric_solenoids     = list(set(geometric_solenoids))
    non_geometric_solenoids = list(set(non_geometric_solenoids))

    # We only care about the compound solenoids (the ones with reference frame transforms)
    # These solenoids must have the _bound suffix
    inbound_solenoids       = [sol for sol in inbound_solenoids if sol.endswith("_bound")]
    outbound_solenoids      = [sol for sol in outbound_solenoids if sol.endswith("_bound")]
    geometric_solenoids     = [sol for sol in geometric_solenoids if sol.endswith("_bound")]
    non_geometric_solenoids = [sol for sol in non_geometric_solenoids if sol.endswith("_bound")]

    # Here we need to remove the _sol suffix for the reference shift correction
    inbound_solenoids       = [sol[:-6] for sol in inbound_solenoids]
    outbound_solenoids      = [sol[:-6] for sol in outbound_solenoids]
    geometric_solenoids     = [sol[:-6] for sol in geometric_solenoids]
    non_geometric_solenoids = [sol[:-6] for sol in non_geometric_solenoids]

    inbound_solenoids       = sorted(inbound_solenoids)
    outbound_solenoids      = sorted(outbound_solenoids)
    geometric_solenoids     = sorted(geometric_solenoids)
    non_geometric_solenoids = sorted(non_geometric_solenoids)

    logger.debug(
        "Reference shift solenoids:\n"
        f"  inbound:       {inbound_solenoids}\n"
        f"  outbound:      {outbound_solenoids}\n"
        f"  geometric:     {geometric_solenoids}\n"
        f"  non-geometric: {non_geometric_solenoids}")

    ############################################################################
    # DXY and CHI for all cases (inbound, geo, reverse_self, reverse_other)
    ############################################################################
    inbound_geo_forward_forward_solenoids       = []
    inbound_geo_forward_reverse_solenoids       = []
    inbound_geo_reverse_forward_solenoids       = []
    inbound_geo_reverse_reverse_solenoids       = []
    inbound_nongeo_forward_forward_solenoids    = []
    inbound_nongeo_forward_reverse_solenoids    = []
    inbound_nongeo_reverse_forward_solenoids    = []
    inbound_nongeo_reverse_reverse_solenoids    = []
    outbound_geo_forward_forward_solenoids      = []
    outbound_geo_forward_reverse_solenoids      = []
    outbound_geo_reverse_forward_solenoids      = []
    outbound_geo_reverse_reverse_solenoids      = []
    outbound_nongeo_forward_forward_solenoids   = []
    outbound_nongeo_forward_reverse_solenoids   = []
    outbound_nongeo_reverse_forward_solenoids   = []
    outbound_nongeo_reverse_reverse_solenoids   = []

    for inbound_solenoid, outbound_solenoid in bound_solenoid_pairs:

        # Reversal information
        inbound_reversed    = False
        outbound_reversed   = False
        if inbound_solenoid.startswith("-"):
            inbound_reversed    = True
        if outbound_solenoid.startswith("-"):
            outbound_reversed   = True

        # Inbound solnoids

        # Only care about the ones with reference shift transformations (should always be true)
        if inbound_solenoid.endswith("_bound"):
            inbound_solenoid    = inbound_solenoid[:-6]
            if inbound_solenoid in geometric_solenoids:

                if (not inbound_reversed) and (not outbound_reversed):
                    inbound_geo_forward_forward_solenoids.append(inbound_solenoid)
                elif (not inbound_reversed) and outbound_reversed:
                    inbound_geo_forward_reverse_solenoids.append(inbound_solenoid)
                elif inbound_reversed and (not outbound_reversed):
                    inbound_geo_reverse_forward_solenoids.append(inbound_solenoid)
                elif inbound_reversed and outbound_reversed:
                    inbound_geo_reverse_reverse_solenoids.append(inbound_solenoid)
            else:

                if (not inbound_reversed) and (not outbound_reversed):
                    inbound_nongeo_forward_forward_solenoids.append(inbound_solenoid)
                elif (not inbound_reversed) and outbound_reversed:
                    inbound_nongeo_forward_reverse_solenoids.append(inbound_solenoid)
                elif inbound_reversed and (not outbound_reversed):
                    inbound_nongeo_reverse_forward_solenoids.append(inbound_solenoid)
                elif inbound_reversed and outbound_reversed:
                    inbound_nongeo_reverse_reverse_solenoids.append(inbound_solenoid)

        # Only care about the boundary solenoids
        if outbound_solenoid.endswith("_bound"):
            outbound_solenoid    = outbound_solenoid[:-6]

            if outbound_solenoid in geometric_solenoids:

                if (not inbound_reversed) and (not outbound_reversed):
                    outbound_geo_forward_forward_solenoids.append(outbound_solenoid)
                elif (not inbound_reversed) and outbound_reversed:
                    outbound_geo_forward_reverse_solenoids.append(outbound_solenoid)
                elif inbound_reversed and (not outbound_reversed):
                    outbound_geo_reverse_forward_solenoids.append(outbound_solenoid)
                elif inbound_reversed and outbound_reversed:
                    outbound_geo_reverse_reverse_solenoids.append(outbound_solenoid)
            else:

                if (not inbound_reversed) and (not outbound_reversed):
                    outbound_nongeo_forward_forward_solenoids.append(outbound_solenoid)
                elif (not inbound_reversed) and outbound_reversed:
                    outbound_nongeo_forward_reverse_solenoids.append(outbound_solenoid)
                elif inbound_reversed and (not outbound_reversed):
                    outbound_nongeo_reverse_forward_solenoids.append(outbound_solenoid)
                elif inbound_reversed and outbound_reversed:
                    outbound_nongeo_reverse_reverse_solenoids.append(outbound_solenoid)

    inbound_geo_forward_forward_solenoids       = list(set(inbound_geo_forward_forward_solenoids))
    inbound_geo_forward_reverse_solenoids       = list(set(inbound_geo_forward_reverse_solenoids))
    inbound_geo_reverse_forward_solenoids       = list(set(inbound_geo_reverse_forward_solenoids))
    inbound_geo_reverse_reverse_solenoids       = list(set(inbound_geo_reverse_reverse_solenoids))
    inbound_nongeo_forward_forward_solenoids    = list(set(inbound_nongeo_forward_forward_solenoids))
    inbound_nongeo_forward_reverse_solenoids    = list(set(inbound_nongeo_forward_reverse_solenoids))
    inbound_nongeo_reverse_forward_solenoids    = list(set(inbound_nongeo_reverse_forward_solenoids))
    inbound_nongeo_reverse_reverse_solenoids    = list(set(inbound_nongeo_reverse_reverse_solenoids))
    outbound_geo_forward_forward_solenoids      = list(set(outbound_geo_forward_forward_solenoids))
    outbound_geo_forward_reverse_solenoids      = list(set(outbound_geo_forward_reverse_solenoids))
    outbound_geo_reverse_forward_solenoids      = list(set(outbound_geo_reverse_forward_solenoids))
    outbound_geo_reverse_reverse_solenoids      = list(set(outbound_geo_reverse_reverse_solenoids))
    outbound_nongeo_forward_forward_solenoids   = list(set(outbound_nongeo_forward_forward_solenoids))
    outbound_nongeo_forward_reverse_solenoids   = list(set(outbound_nongeo_forward_reverse_solenoids))
    outbound_nongeo_reverse_forward_solenoids   = list(set(outbound_nongeo_reverse_forward_solenoids))
    outbound_nongeo_reverse_reverse_solenoids   = list(set(outbound_nongeo_reverse_reverse_solenoids))

    logger.debug(
        "Reference shift solenoid classification:\n"
        f"  inbound_geo_forward_forward_solenoids     = {inbound_geo_forward_forward_solenoids}\n"
        f"  inbound_geo_forward_reverse_solenoids     = {inbound_geo_forward_reverse_solenoids}\n"
        f"  inbound_geo_reverse_forward_solenoids     = {inbound_geo_reverse_forward_solenoids}\n"
        f"  inbound_geo_reverse_reverse_solenoids     = {inbound_geo_reverse_reverse_solenoids}\n"
        f"  inbound_nongeo_forward_forward_solenoids  = {inbound_nongeo_forward_forward_solenoids}\n"
        f"  inbound_nongeo_forward_reverse_solenoids  = {inbound_nongeo_forward_reverse_solenoids}\n"
        f"  inbound_nongeo_reverse_forward_solenoids  = {inbound_nongeo_reverse_forward_solenoids}\n"
        f"  inbound_nongeo_reverse_reverse_solenoids  = {inbound_nongeo_reverse_reverse_solenoids}\n"
        f"  outbound_geo_forward_forward_solenoids    = {outbound_geo_forward_forward_solenoids}\n"
        f"  outbound_geo_forward_reverse_solenoids    = {outbound_geo_forward_reverse_solenoids}\n"
        f"  outbound_geo_reverse_forward_solenoids    = {outbound_geo_reverse_forward_solenoids}\n"
        f"  outbound_geo_reverse_reverse_solenoids    = {outbound_geo_reverse_reverse_solenoids}\n"
        f"  outbound_nongeo_forward_forward_solenoids = {outbound_nongeo_forward_forward_solenoids}\n"
        f"  outbound_nongeo_forward_reverse_solenoids = {outbound_nongeo_forward_reverse_solenoids}\n"
        f"  outbound_nongeo_reverse_forward_solenoids = {outbound_nongeo_reverse_forward_solenoids}\n"
        f"  outbound_nongeo_reverse_reverse_solenoids = {outbound_nongeo_reverse_reverse_solenoids}")

    ############################################################################
    # Flip the neccesary reference shifts
    ############################################################################
    def flip_reference_shifts(solenoid: str, dxy_sign: int, chi_sign: int) -> None:
        """
        Flip the sign of a bound solenoid's reference-shift components.

        Parameters
        ----------
        solenoid : str
            The solenoid's base name (without the "_bound"/"_dxy"/
            "_rot" suffix).
        dxy_sign : int
            Multiplies the `{solenoid}_dxy` Translation's
            shift_x/shift_y.
        chi_sign : int
            Multiplies the `{solenoid}_rot` Rotation's
            rot_y_rad/rot_x_rad/rot_s_rad.
        """
        translation_name = f"{solenoid}_dxy"
        rot_name = f"{solenoid}_rot"

        line[translation_name].shift_x *= dxy_sign
        line[translation_name].shift_y *= dxy_sign

        line[rot_name].rot_y_rad *= chi_sign
        line[rot_name].rot_x_rad *= chi_sign
        line[rot_name].rot_s_rad *= chi_sign

    # Signs verified by:
    #   test_sol_reference_transform_orbit_matches_sad_twiss      (internal marker)
    #   test_sol_reference_transform_restores_design_orbit_at_end (END restoration)
    # dxy_sign controls Translation.shift_{x,y}; chi_sign controls Rotation.rot_{x,y,s}_rad.

    ########################################
    # Inbound Geo Forward Forward Solenoids
    ########################################
    for inbound_geo_forward_forward_solenoid in inbound_geo_forward_forward_solenoids:
        flip_reference_shifts(
            inbound_geo_forward_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = +1)

    ########################################
    # Inbound Geo Forward Reverse Solenoids
    ########################################
    for inbound_geo_forward_reverse_solenoid in inbound_geo_forward_reverse_solenoids:
        flip_reference_shifts(
            inbound_geo_forward_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = +1)

    ########################################
    # Inbound Geo Reverse Forward Solenoids
    ########################################
    for inbound_geo_reverse_forward_solenoid in inbound_geo_reverse_forward_solenoids:
        flip_reference_shifts(
            inbound_geo_reverse_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Inbound Geo Reverse Reverse Solenoids
    ########################################
    for inbound_geo_reverse_reverse_solenoid in inbound_geo_reverse_reverse_solenoids:
        flip_reference_shifts(
            inbound_geo_reverse_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Inbound Non-Geo Forward Forward Solenoids
    ########################################
    for inbound_nongeo_forward_forward_solenoid in inbound_nongeo_forward_forward_solenoids:
        flip_reference_shifts(
            inbound_nongeo_forward_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Inbound Non-Geo Forward Reverse Solenoids
    ########################################
    for inbound_nongeo_forward_reverse_solenoid in inbound_nongeo_forward_reverse_solenoids:
        flip_reference_shifts(
            inbound_nongeo_forward_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Inbound Non-Geo Reverse Forward Solenoids
    ########################################
    for inbound_nongeo_reverse_forward_solenoid in inbound_nongeo_reverse_forward_solenoids:
        flip_reference_shifts(
            inbound_nongeo_reverse_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Inbound Non-Geo Reverse Reverse Solenoids
    ########################################
    for inbound_nongeo_reverse_reverse_solenoid in inbound_nongeo_reverse_reverse_solenoids:
        flip_reference_shifts(
            inbound_nongeo_reverse_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Outbound Geo Forward Forward Solenoids
    ########################################
    for outbound_geo_forward_forward_solenoid in outbound_geo_forward_forward_solenoids:
        flip_reference_shifts(
            outbound_geo_forward_forward_solenoid,
            dxy_sign    = -1,
            chi_sign    = -1)

    ########################################
    # Outbound Geo Forward Reverse Solenoids
    ########################################
    for outbound_geo_forward_reverse_solenoid in outbound_geo_forward_reverse_solenoids:
        flip_reference_shifts(
            outbound_geo_forward_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = +1)

    ########################################
    # Outbound Geo Reverse Forward Solenoids
    ########################################
    for outbound_geo_reverse_forward_solenoid in outbound_geo_reverse_forward_solenoids:
        flip_reference_shifts(
            outbound_geo_reverse_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Outbound Geo Reverse Reverse Solenoids
    ########################################
    for outbound_geo_reverse_reverse_solenoid in outbound_geo_reverse_reverse_solenoids:
        flip_reference_shifts(
            outbound_geo_reverse_reverse_solenoid,
            dxy_sign    = -1,
            chi_sign    = +1)

    ########################################
    # Outbound Non-Geo Forward Forward Solenoids
    ########################################
    for outbound_nongeo_forward_forward_solenoid in outbound_nongeo_forward_forward_solenoids:
        flip_reference_shifts(
            outbound_nongeo_forward_forward_solenoid,
            dxy_sign    = -1,
            chi_sign    = -1)

    ########################################
    # Outbound Non-Geo Forward Reverse Solenoids
    ########################################
    for outbound_nongeo_forward_reverse_solenoid in outbound_nongeo_forward_reverse_solenoids:
        flip_reference_shifts(
            outbound_nongeo_forward_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Outbound Non-Geo Reverse Forward Solenoids
    ########################################
    for outbound_nongeo_reverse_forward_solenoid in outbound_nongeo_reverse_forward_solenoids:
        flip_reference_shifts(
            outbound_nongeo_reverse_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Outbound Non-Geo Reverse Reverse Solenoids
    ########################################
    for outbound_nongeo_reverse_reverse_solenoid in outbound_nongeo_reverse_reverse_solenoids:
        flip_reference_shifts(
            outbound_nongeo_reverse_reverse_solenoid,
            dxy_sign    = -1,
            chi_sign    = -1)

    ############################################################################
    # Reorder the solenoid components
    ############################################################################
    inbound_geo_solenoids      = inbound_geo_forward_forward_solenoids + \
        inbound_geo_forward_reverse_solenoids + \
        inbound_geo_reverse_forward_solenoids + \
        inbound_geo_reverse_reverse_solenoids
    inbound_nongeo_solenoids    = inbound_nongeo_forward_forward_solenoids + \
        inbound_nongeo_forward_reverse_solenoids + \
        inbound_nongeo_reverse_forward_solenoids + \
        inbound_nongeo_reverse_reverse_solenoids
    # Outbound solenoids: xt.Rotation's zeta shift is proportional to the
    # transverse position (x/y) at the moment it runs (see xtrack's
    # track_yrotation.h/track_xrotation.h). Rotating before the translation
    # (inbound order, above) always runs at x=y=0, so it never picks up this
    # term. Rotating after the translation (outbound order) only picks it up
    # when inbound_reversed != outbound_reversed -- forward_forward and
    # reverse_reverse pairs (inbound_reversed == outbound_reversed) keep the
    # existing bound/dxy/dz/rot order; forward_reverse and reverse_forward
    # pairs need rotation-first instead, same as inbound.
    outbound_same_reversal_solenoids       = outbound_geo_forward_forward_solenoids + \
        outbound_geo_reverse_reverse_solenoids + \
        outbound_nongeo_forward_forward_solenoids + \
        outbound_nongeo_reverse_reverse_solenoids
    outbound_differing_reversal_solenoids  = outbound_geo_forward_reverse_solenoids + \
        outbound_geo_reverse_forward_solenoids + \
        outbound_nongeo_forward_reverse_solenoids + \
        outbound_nongeo_reverse_forward_solenoids

    inbound_geo_solenoids       = list(set(inbound_geo_solenoids))
    inbound_nongeo_solenoids    = list(set(inbound_nongeo_solenoids))
    outbound_same_reversal_solenoids       = list(set(outbound_same_reversal_solenoids))
    outbound_differing_reversal_solenoids  = list(set(outbound_differing_reversal_solenoids))

    ########################################
    # Get the current order of the element names
    ########################################
    element_names   = line.element_names.copy()                 # type: ignore

    ########################################
    # Reorder inbound geo solenoids
    ########################################
    for inbound_geo_solenoid in inbound_geo_solenoids:

        sol_start_ele   = f"{inbound_geo_solenoid}_bound"
        sol_end_ele     = f"{inbound_geo_solenoid}_rot"

        # Get the start and end indices
        start_idxs  = [i for i, name in enumerate(element_names) if name == sol_start_ele]
        end_idxs    = [i for i, name in enumerate(element_names) if name == sol_end_ele]

        for start_idx, end_idx in zip(start_idxs, end_idxs):
            assert start_idx < end_idx

            new_element_names   = []
            new_element_names   += element_names[:start_idx]
            bound_elements      = [
                f"{inbound_geo_solenoid}_rot",
                f"{inbound_geo_solenoid}_dz",
                f"{inbound_geo_solenoid}_dxy",
                f"{inbound_geo_solenoid}_bound"]
            new_element_names   += bound_elements
            new_element_names   += element_names[end_idx + 1:]

            element_names       = new_element_names

    ########################################
    # Reorder inbound non-geo solenoids
    ########################################
    for inbound_nongeo_solenoid in inbound_nongeo_solenoids:

        sol_start_ele   = f"{inbound_nongeo_solenoid}_bound"
        sol_end_ele     = f"{inbound_nongeo_solenoid}_rot"

        # Get the start and end indices
        start_idxs  = [i for i, name in enumerate(element_names) if name == sol_start_ele]
        end_idxs    = [i for i, name in enumerate(element_names) if name == sol_end_ele]

        for start_idx, end_idx in zip(start_idxs, end_idxs):
            assert start_idx < end_idx

            new_element_names   = []
            new_element_names   += element_names[:start_idx]
            bound_elements      = [
                    f"{inbound_nongeo_solenoid}_rot",
                    f"{inbound_nongeo_solenoid}_dz",
                    f"{inbound_nongeo_solenoid}_dxy",
                    f"{inbound_nongeo_solenoid}_bound"]
            new_element_names   += bound_elements
            new_element_names   += element_names[end_idx + 1:]

            element_names       = new_element_names

    ########################################
    # Reorder outbound solenoids (inbound_reversed == outbound_reversed):
    # unchanged bound/dxy/dz/rot
    ########################################
    for outbound_same_reversal_solenoid in outbound_same_reversal_solenoids:

        sol_start_ele   = f"{outbound_same_reversal_solenoid}_bound"
        sol_end_ele     = f"{outbound_same_reversal_solenoid}_rot"

        # Get the start and end indices
        start_idxs  = [i for i, name in enumerate(element_names) if name == sol_start_ele]
        end_idxs    = [i for i, name in enumerate(element_names) if name == sol_end_ele]

        for start_idx, end_idx in zip(start_idxs, end_idxs):
            assert start_idx < end_idx

            new_element_names   = []
            new_element_names   += element_names[:start_idx]
            bound_elements      = [
                f"{outbound_same_reversal_solenoid}_bound",
                f"{outbound_same_reversal_solenoid}_dxy",
                f"{outbound_same_reversal_solenoid}_dz",
                f"{outbound_same_reversal_solenoid}_rot"]
            new_element_names   += bound_elements
            new_element_names   += element_names[end_idx + 1:]

            element_names       = new_element_names

    ########################################
    # Reorder outbound solenoids (inbound_reversed != outbound_reversed):
    # rotation-first, same as inbound
    ########################################
    for outbound_differing_reversal_solenoid in outbound_differing_reversal_solenoids:

        sol_start_ele   = f"{outbound_differing_reversal_solenoid}_bound"
        sol_end_ele     = f"{outbound_differing_reversal_solenoid}_rot"

        # Get the start and end indices
        start_idxs  = [i for i, name in enumerate(element_names) if name == sol_start_ele]
        end_idxs    = [i for i, name in enumerate(element_names) if name == sol_end_ele]

        for start_idx, end_idx in zip(start_idxs, end_idxs):
            assert start_idx < end_idx

            new_element_names   = []
            new_element_names   += element_names[:start_idx]
            bound_elements      = [
                f"{outbound_differing_reversal_solenoid}_rot",
                f"{outbound_differing_reversal_solenoid}_dz",
                f"{outbound_differing_reversal_solenoid}_dxy",
                f"{outbound_differing_reversal_solenoid}_bound"]
            new_element_names   += bound_elements
            new_element_names   += element_names[end_idx + 1:]
            element_names       = new_element_names

    ########################################
    # Update the line
    ########################################
    line.element_names = element_names

    logger.info(
        f"Corrected reference shifts for {len(bound_solenoid_pairs)} "
        "solenoid pairs")
