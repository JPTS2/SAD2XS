"""
(Unofficial) SAD to XSuite Converter

Solenoid Converter
"""

################################################################################
# Required Packages
################################################################################
import numpy as np
import xtrack as xt

from tqdm import tqdm

from .._globals import print_section_heading, MAX_KNL_ORDER, N_MULTIPOLE_KICKS_SOL

################################################################################
# Conversion Function
################################################################################
def convert_solenoids(
        parsed_lattice_data:    dict,
        environment:            xt.Environment,
        verbose:                bool                = False) -> None:

    ########################################
    # Get the required data
    ########################################
    parsed_elements = parsed_lattice_data['elements']

    ########################################
    # Check if there are any solenoids
    ########################################
    if 'sol' not in parsed_elements:
        if verbose:
            print_section_heading("No solenoids in line", mode = 'subsection')
        return
    else:
        solenoids   = parsed_elements['sol']

    ########################################
    # Get bound and geo solenoids
    ########################################
    bound_solenoids = []
    geo_solenoids   = []
    for ele_name, ele_vars in solenoids.items():

        if 'bound' in ele_vars:
            bound_solenoids.append(ele_name)
        if 'geo' in ele_vars:
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
            if not isinstance(environment.element_dict[element], xt.Solenoid):  # type: ignore
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
                bound_solenoid_pairs.append((bound_sols_in_line[i], bound_sols_in_line[i + 1]))
                bound_solenoid_pair_indicies.append((bound_solenoid_indicies[i], bound_solenoid_indicies[i + 1]))
            else:
                raise ValueError("Unmatched solenoid found in the line.")

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
        s_start_ele         = 0
        s_end_ele           = 0


        INTERPOLATE         = False
        
        ########################################
        # Get the elements between bound solenoids
        ########################################
        for (sol_start, sol_end), (start_idx, end_idx) in zip(bound_solenoid_pairs, bound_solenoid_pair_indicies):

            if start_idx > end_idx:
                raise ValueError(f"Start solenoid {sol_start} is after end solenoid {sol_end} in line {line_name}.")

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

                # !!!!! INTERPOLATION MODE
                # # Calculate ks at the start and end of the element by interpolating
                if INTERPOLATE:

                    # Adjust the s_start based on the previous element
                    s_start_ele = s_end_ele
                    # Get the length of the current element
                    try:
                        ele_length  = line[element].length
                    except AttributeError:
                        # Some elements (like markers) have no length
                        ele_length  = 0
                    s_end_ele   = s_start_ele + ele_length
                    
                    if segment_length != 0:
                        ks_ele_start   = ((ks_ahead - ks_previous) / segment_length) * s_start_ele + ks_previous
                        ks_ele_end     = ((ks_ahead - ks_previous) / segment_length) * s_end_ele + ks_previous
                        # Mean at the centre of the element
                        ks              = (ks_ele_start + ks_ele_end) / 2
                    else:
                        ks_ele_start   = ks_previous
                        ks_ele_end     = ks_ahead
                        ks             = (ks_ele_start + ks_ele_end) / 2

                # If the element is a solenoid, update the current solenoidal field
                if isinstance(environment.element_dict[element], xt.Solenoid):  # type: ignore

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
                        if isinstance(environment.element_dict[ahead_element], xt.Solenoid):    # type: ignore
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

                    # Reset the segment lengths as new segment
                    s_start_ele = 0
                    s_end_ele   = ele_length

                    continue

                # Drift conversion
                elif isinstance(environment.element_dict[element], xt.Drift):   # type: ignore

                    length              = line[element].length
                    new_element_name    = f"{element}_{solenoid_suffix}"

                    if INTERPOLATE:
                        rand_int            = np.random.randint(1, 1000)
                        new_element_name    = f"{element}_{solenoid_suffix}_{rand_int}"

                    if new_element_name not in environment.element_dict:        # type: ignore
                        environment.new(
                            name    = new_element_name,
                            parent  = xt.Solenoid,
                            length  = length,
                            ks      = ks)
                    line.element_names[idx] = new_element_name

                    if verbose:
                        print(f"Converted drift {element} to solenoid {new_element_name} with ks = {ks}")
                    continue

                # Bend conversion
                elif isinstance(environment.element_dict[element], xt.Bend):        # type: ignore

                    assert line[element].h == 0, "Bend with non-zero angle found between solenoids."

                    length      = line[element].length
                    k0          = line[element].k0
                    k1          = line[element].k1
                    shift_x     = line[element].shift_x
                    shift_y     = line[element].shift_y
                    rotation    = line[element].rot_s_rad
                    knl         = [f'{k0} * {length}', f'{k1} * {length}']

                    new_element_name    = f"{element}_{solenoid_suffix}"

                    if new_element_name not in environment.element_dict:        # type: ignore
                        environment.new(
                            name				= new_element_name,
                            parent				= xt.Solenoid,
                            length				= length,
                            ks					= ks,
                            knl					= knl,
                            num_multipole_kicks	= N_MULTIPOLE_KICKS_SOL,
                            order				= MAX_KNL_ORDER,
                            mult_shift_x		= shift_x,
                            mult_shift_y		= shift_y,
                            rot_s_rad           = rotation)
                    line.element_names[idx] = new_element_name

                    if verbose:
                        print(f"Converted Bend {element} to solenoid {new_element_name} with ks = {ks}")
                    continue
                    
                # Quadrupole conversion
                elif isinstance(environment.element_dict[element], xt.Quadrupole):   # type: ignore

                    length      = line[element].length
                    k1          = line[element].k1
                    k1s         = line[element].k1s
                    shift_x     = line[element].shift_x
                    shift_y     = line[element].shift_y
                    rotation    = line[element].rot_s_rad
                    knl         = [0, f'{k1} * {length}']
                    ksl         = [0, f'{k1s} * {length}']

                    new_element_name    = f"{element}_{solenoid_suffix}"

                    if new_element_name not in environment.element_dict:        # type: ignore
                        environment.new(
                            name				= new_element_name,
                            parent				= xt.Solenoid,
                            length				= length,
                            ks					= ks,
                            knl					= knl,
                            ksl					= ksl,
                            num_multipole_kicks	= N_MULTIPOLE_KICKS_SOL,
                            order				= MAX_KNL_ORDER,
                            mult_shift_x		= shift_x,
                            mult_shift_y		= shift_y,
                            rot_s_rad           = rotation)
                    line.element_names[idx] = new_element_name

                    if verbose:
                        print(f"Converted Quadrupole {element} to solenoid {new_element_name} with ks = {ks}")
                    continue
                    
                # Sextupole conversion
                elif isinstance(environment.element_dict[element], xt.Sextupole):   # type: ignore

                    length      = line[element].length
                    k2          = line[element].k2
                    k2s         = line[element].k2s
                    shift_x     = line[element].shift_x
                    shift_y     = line[element].shift_y
                    rotation    = line[element].rot_s_rad
                    knl         = [0, 0, f'{k2} * {length}']
                    ksl         = [0, 0, f'{k2s} * {length}']

                    new_element_name    = f"{element}_{solenoid_suffix}"

                    if new_element_name not in environment.element_dict:     # type: ignore
                        environment.new(
                            name				= new_element_name,
                            parent				= xt.Solenoid,
                            length				= length,
                            ks					= ks,
                            knl					= knl,
                            ksl					= ksl,
                            num_multipole_kicks	= N_MULTIPOLE_KICKS_SOL,
                            order				= MAX_KNL_ORDER,
                            mult_shift_x		= shift_x,
                            mult_shift_y		= shift_y,
                            rot_s_rad           = rotation)
                    line.element_names[idx] = new_element_name

                    if verbose:
                        print(f"Converted Sextupole {element} to solenoid {new_element_name} with ks = {ks}")
                    continue

                # Octupole conversion
                elif isinstance(environment.element_dict[element], xt.Octupole):    # type: ignore

                    length      = line[element].length
                    k3          = line[element].k3
                    k3s         = line[element].k3s
                    shift_x     = line[element].shift_x
                    shift_y     = line[element].shift_y
                    rotation    = line[element].rot_s_rad
                    knl         = [0, 0, 0, f'{k3} * {length}']
                    ksl         = [0, 0, 0, f'{k3s} * {length}']

                    new_element_name    = f"{element}_{solenoid_suffix}"

                    if new_element_name not in environment.element_dict:    # type: ignore
                        environment.new(
                            name				= new_element_name,
                            parent				= xt.Solenoid,
                            length				= length,
                            ks					= ks,
                            knl					= knl,
                            ksl					= ksl,
                            num_multipole_kicks	= N_MULTIPOLE_KICKS_SOL,
                            order				= MAX_KNL_ORDER,
                            mult_shift_x		= shift_x,
                            mult_shift_y		= shift_y,
                            rot_s_rad           = rotation)
                    line.element_names[idx] = new_element_name

                    if verbose:
                        print(f"Converted Octupole {element} to solenoid {new_element_name} with ks = {ks}")
                    continue

                # Multipole conversion
                elif isinstance(environment.element_dict[element], xt.Multipole):   # type: ignore

                    length      = line[element].length
                    knl         = line[element].knl
                    ksl         = line[element].ksl
                    shift_x     = line[element].shift_x
                    shift_y     = line[element].shift_y
                    rotation    = line[element].rot_s_rad

                    environment.element_dict.pop(element)                       # type: ignore
                    environment.new(
                        name				= element,
                        parent				= xt.Solenoid,
                        length				= length,
                        ks					= ks,
                        knl					= knl,
                        ksl					= ksl,
                        num_multipole_kicks	= N_MULTIPOLE_KICKS_SOL,
                        order				= MAX_KNL_ORDER,
                        mult_shift_x		= shift_x,
                        mult_shift_y		= shift_y,
                        rot_s_rad           = rotation)

                    if verbose:
                        print(f"Converted Multipole {element} to solenoid with ks = {ks}")
                    continue

                # Generic Magnet conversion (currently unused)
                elif isinstance(environment.element_dict[element], xt.Magnet):  # type: ignore

                    length      = line[element].length
                    knl         = line[element].knl
                    ksl         = line[element].ksl
                    shift_x     = line[element].shift_x
                    shift_y     = line[element].shift_y
                    rotation    = line[element].rot_s_rad

                    environment.element_dict.pop(element)                       # type: ignore
                    environment.new(
                        name				= element,
                        parent				= xt.Solenoid,
                        length				= length,
                        ks					= ks,
                        knl					= knl,
                        ksl					= ksl,
                        num_multipole_kicks	= N_MULTIPOLE_KICKS_SOL,
                        order               = MAX_KNL_ORDER,
                        mult_shift_x		= shift_x,
                        mult_shift_y		= shift_y,
                        rot_s_rad           = rotation)

                    if verbose:
                        print(f"Converted Multipole {element} to solenoid with ks = {ks}")
                    continue
                
                elif isinstance(
                    environment.element_dict[element],      # type: ignore
                    (
                        xt.XYShift,
                        xt.ZetaShift,
                        xt.XRotation,
                        xt.YRotation,
                        xt.SRotation,
                        xt.Marker,
                        xt.LimitEllipse)):  
                    # Known elements that don't need conversion
                    continue
                elif verbose:
                    print(f"Element {element} in line {line_name} has not been converted")

###############################################################################
# Reference shift corrections
###############################################################################
def solenoid_reference_shift_corrections(
        line:                   xt.Line,
        parsed_lattice_data:    dict,
        environment:            xt.Environment,
        reverse_line:           bool                = False,
        verbose:                bool                = False) -> None:

    ########################################
    # Get the required data
    ########################################
    parsed_elements = parsed_lattice_data['elements']

    ########################################
    # Check if there are any solenoids
    ########################################
    if 'sol' not in parsed_elements:
        if verbose:
            print_section_heading("No solenoids in line", mode = 'subsection')
        return
    else:
        solenoids   = parsed_elements['sol']

    ########################################
    # Get bound and geo solenoids
    ########################################
    bound_solenoids = []
    geo_solenoids   = []
    for ele_name, ele_vars in solenoids.items():

        if 'bound' in ele_vars:
            bound_solenoids.append(ele_name)
        if 'geo' in ele_vars:
            geo_solenoids.append(ele_name)

    ########################################
    # Get bound solenoids in the line
    ########################################
    bound_sols_in_line  = []
    geo_sols_in_line    = []
    for element in line.element_names:
        
        # Element must actually be a solenoid
        if not isinstance(environment.element_dict[element], xt.Solenoid):  # type: ignore
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
            raise ValueError("Unmatched solenoid found in the line.")

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
    inbound_solenoids       = [sol for sol in inbound_solenoids if sol.endswith('_bound')]
    outbound_solenoids      = [sol for sol in outbound_solenoids if sol.endswith('_bound')]
    geometric_solenoids     = [sol for sol in geometric_solenoids if sol.endswith('_bound')]
    non_geometric_solenoids = [sol for sol in non_geometric_solenoids if sol.endswith('_bound')]

    # Here we need to remove the _sol suffix for the reference shift correction
    inbound_solenoids       = [sol[:-6] for sol in inbound_solenoids]
    outbound_solenoids      = [sol[:-6] for sol in outbound_solenoids]
    geometric_solenoids     = [sol[:-6] for sol in geometric_solenoids]
    non_geometric_solenoids = [sol[:-6] for sol in non_geometric_solenoids]

    inbound_solenoids       = sorted(inbound_solenoids)
    outbound_solenoids      = sorted(outbound_solenoids)
    geometric_solenoids     = sorted(geometric_solenoids)
    non_geometric_solenoids = sorted(non_geometric_solenoids)

    if verbose:
        print_section_heading("Reference Shift Solenoids:", mode = 'subsection')
        print(f"Inbound solenoids with ref transforms: {inbound_solenoids}")
        print(f"Outbound solenoids with ref transforms: {outbound_solenoids}")
        print(f"Geometric solenoids with ref transforms: {geometric_solenoids}")
        print(f"Non-geometric solenoids with ref transforms: {non_geometric_solenoids}")

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
        if inbound_solenoid.startswith('-'):
            inbound_reversed    = True
        if outbound_solenoid.startswith('-'):
            outbound_reversed   = True

        # Inbound solnoids

        # Only care about the ones with reference shift transformations (should always be true)
        if inbound_solenoid.endswith('_bound'):
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
        if outbound_solenoid.endswith('_bound'):
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

    if verbose:
        print(f"inbound_geo_forward_forward_solenoids     = {inbound_geo_forward_forward_solenoids}")
        print(f"inbound_geo_forward_reverse_solenoids     = {inbound_geo_forward_reverse_solenoids}")
        print(f"inbound_geo_reverse_forward_solenoids     = {inbound_geo_reverse_forward_solenoids}")
        print(f"inbound_geo_reverse_reverse_solenoids     = {inbound_geo_reverse_reverse_solenoids}")
        print(f"inbound_nongeo_forward_forward_solenoids  = {inbound_nongeo_forward_forward_solenoids}")
        print(f"inbound_nongeo_forward_reverse_solenoids  = {inbound_nongeo_forward_reverse_solenoids}")
        print(f"inbound_nongeo_reverse_forward_solenoids  = {inbound_nongeo_reverse_forward_solenoids}")
        print(f"inbound_nongeo_reverse_reverse_solenoids  = {inbound_nongeo_reverse_reverse_solenoids}")
        print(f"outbound_geo_forward_forward_solenoids    = {outbound_geo_forward_forward_solenoids}")
        print(f"outbound_geo_forward_reverse_solenoids    = {outbound_geo_forward_reverse_solenoids}")
        print(f"outbound_geo_reverse_forward_solenoids    = {outbound_geo_reverse_forward_solenoids}")
        print(f"outbound_geo_reverse_reverse_solenoids    = {outbound_geo_reverse_reverse_solenoids}")
        print(f"outbound_nongeo_forward_forward_solenoids = {outbound_nongeo_forward_forward_solenoids}")
        print(f"outbound_nongeo_forward_reverse_solenoids = {outbound_nongeo_forward_reverse_solenoids}")
        print(f"outbound_nongeo_reverse_forward_solenoids = {outbound_nongeo_reverse_forward_solenoids}")
        print(f"outbound_nongeo_reverse_reverse_solenoids = {outbound_nongeo_reverse_reverse_solenoids}")

    ############################################################################
    # Flip the neccesary reference shifts
    ############################################################################
    def flip_reference_shifts(solenoid, dxy_sign, chi_sign):
        xy_shift_name   = f"{solenoid}_dxy"
        chi1_shift_name = f"{solenoid}_chi1"
        chi2_shift_name = f"{solenoid}_chi2"
        chi3_shift_name = f"{solenoid}_chi3"

        line[xy_shift_name].dx      *= dxy_sign
        line[xy_shift_name].dy      *= dxy_sign

        line[chi1_shift_name].angle *= chi_sign
        line[chi2_shift_name].angle *= chi_sign
        line[chi3_shift_name].angle *= chi_sign

    ########################################
    # Inbound Geo Forward Forward Solenoids (Complete: test_003)
    ########################################
    for inbound_geo_forward_forward_solenoid in inbound_geo_forward_forward_solenoids:
        flip_reference_shifts(
            inbound_geo_forward_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = +1)

    ########################################
    # Inbound Geo Forward Reverse Solenoids (Complete: test_003)
    ########################################
    for inbound_geo_forward_reverse_solenoid in inbound_geo_forward_reverse_solenoids:
        flip_reference_shifts(
            inbound_geo_forward_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = +1)

    ########################################
    # Inbound Geo Reverse Forward Solenoids (Complete: test_003)
    ########################################
    for inbound_geo_reverse_forward_solenoid in inbound_geo_reverse_forward_solenoids:
        flip_reference_shifts(
            inbound_geo_reverse_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)
        
    ########################################
    # Inbound Geo Reverse Reverse Solenoids (Complete: test_003)
    ########################################
    for inbound_geo_reverse_reverse_solenoid in inbound_geo_reverse_reverse_solenoids:
        flip_reference_shifts(
            inbound_geo_reverse_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Inbound Non-Geo Forward Forward Solenoids (Complete: test_005)
    ########################################
    for inbound_nongeo_forward_forward_solenoid in inbound_nongeo_forward_forward_solenoids:
        flip_reference_shifts(
            inbound_nongeo_forward_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)
        
    ########################################
    # Inbound Non-Geo Forward Reverse Solenoids (Complete: test_005)
    ########################################
    for inbound_nongeo_forward_reverse_solenoid in inbound_nongeo_forward_reverse_solenoids:
        flip_reference_shifts(
            inbound_nongeo_forward_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Inbound Non-Geo Reverse Forward Solenoids (Complete: test_005)
    ########################################
    for inbound_nongeo_reverse_forward_solenoid in inbound_nongeo_reverse_forward_solenoids:
        flip_reference_shifts(
            inbound_nongeo_reverse_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Inbound Non-Geo Reverse Reverse Solenoids (Complete: test_005)
    ########################################
    for inbound_nongeo_reverse_reverse_solenoid in inbound_nongeo_reverse_reverse_solenoids:
        flip_reference_shifts(
            inbound_nongeo_reverse_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)
        
    ########################################
    # Outbound Geo Forward Forward Solenoids (Complete: test_006)
    ########################################
    for outbound_geo_forward_forward_solenoid in outbound_geo_forward_forward_solenoids:
        flip_reference_shifts(
            outbound_geo_forward_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)
        
    ########################################
    # Outbound Geo Forward Reverse Solenoids (Complete: test_006)
    ########################################
    for outbound_geo_forward_reverse_solenoid in outbound_geo_forward_reverse_solenoids:
        flip_reference_shifts(
            outbound_geo_forward_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = +1)

    ########################################
    # Outbound Geo Reverse Forward Solenoids (Complete: test_006)
    ########################################
    for outbound_geo_reverse_forward_solenoid in outbound_geo_reverse_forward_solenoids:
        flip_reference_shifts(
            outbound_geo_reverse_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = +1)
        
    ########################################
    # Outbound Geo Reverse Reverse Solenoids (Complete: test_006)
    ########################################
    for outbound_geo_reverse_reverse_solenoid in outbound_geo_reverse_reverse_solenoids:
        flip_reference_shifts(
            outbound_geo_reverse_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = +1)

    ########################################
    # Outbound Non-Geo Forward Forward Solenoids (Complete: test_004)
    ########################################
    for outbound_nongeo_forward_forward_solenoid in outbound_nongeo_forward_forward_solenoids:
        flip_reference_shifts(
            outbound_nongeo_forward_forward_solenoid,
            dxy_sign    = -1,
            chi_sign    = -1)

    ########################################
    # Outbound Non-Geo Forward Reverse Solenoids (Complete: test_004)
    ########################################
    for outbound_nongeo_forward_reverse_solenoid in outbound_nongeo_forward_reverse_solenoids:
        flip_reference_shifts(
            outbound_nongeo_forward_reverse_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Outbound Non-Geo Reverse Forward Solenoids (Complete: test_004)
    ########################################
    for outbound_nongeo_reverse_forward_solenoid in outbound_nongeo_reverse_forward_solenoids:
        flip_reference_shifts(
            outbound_nongeo_reverse_forward_solenoid,
            dxy_sign    = +1,
            chi_sign    = -1)

    ########################################
    # Outbound Non-Geo Reverse Reverse Solenoids (Complete: test_004)
    ########################################
    for outbound_nongeo_reverse_reverse_solenoid in outbound_nongeo_reverse_reverse_solenoids:
        flip_reference_shifts(
            outbound_nongeo_reverse_reverse_solenoid,
            dxy_sign    = -1,
            chi_sign    = -1)

    ############################################################################
    # Move DZ Shifts onto the outbound solenoid (even when bound)
    ############################################################################
    for inbound_solenoid, outbound_solenoid in bound_solenoid_pairs:

        # Should always be true, but just in case
        if not inbound_solenoid.endswith('_bound'):
            raise ValueError(f"Inbound solenoid {inbound_solenoid} doesn't end with bound?")
        else:
            inbound_solenoid    = inbound_solenoid[:-6]

        if not outbound_solenoid.endswith('_bound'):
            raise ValueError(f"Outbound solenoid {outbound_solenoid} doesn't end with bound?")
        else:
            outbound_solenoid   = outbound_solenoid[:-6]

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
    outbound_geo_solenoids      = outbound_geo_forward_forward_solenoids + \
        outbound_geo_forward_reverse_solenoids + \
        outbound_geo_reverse_forward_solenoids + \
        outbound_geo_reverse_reverse_solenoids
    outbound_nongeo_solenoids   = outbound_nongeo_forward_forward_solenoids + \
        outbound_nongeo_forward_reverse_solenoids + \
        outbound_nongeo_reverse_forward_solenoids + \
        outbound_nongeo_reverse_reverse_solenoids
    
    inbound_geo_solenoids       = list(set(inbound_geo_solenoids))
    inbound_nongeo_solenoids    = list(set(inbound_nongeo_solenoids))
    outbound_geo_solenoids      = list(set(outbound_geo_solenoids))
    outbound_nongeo_solenoids   = list(set(outbound_nongeo_solenoids))

    ########################################
    # Get the current order of the element names
    ########################################
    element_names   = line.element_names.copy()

    ########################################
    # Reorder inbound geo solenoids
    ########################################
    for inbound_geo_solenoid in tqdm(inbound_geo_solenoids):
        
        sol_start_ele   = f"{inbound_geo_solenoid}_bound"
        sol_end_ele     = f"{inbound_geo_solenoid}_chi3"
        
        # Get the start and end indices
        start_idxs  = [i for i, name in enumerate(element_names) if name == sol_start_ele]
        end_idxs    = [i for i, name in enumerate(element_names) if name == sol_end_ele]

        for start_idx, end_idx in zip(start_idxs, end_idxs):
            assert start_idx < end_idx

            new_element_names   = []
            new_element_names   += element_names[:start_idx]
            bound_elements      = [
                f'{inbound_geo_solenoid}_chi3',
                f'{inbound_geo_solenoid}_chi2',
                f'{inbound_geo_solenoid}_chi1',
                f'{inbound_geo_solenoid}_dz',
                f'{inbound_geo_solenoid}_dxy',
                f'{inbound_geo_solenoid}_bound']
            new_element_names   += bound_elements
            new_element_names   += element_names[end_idx + 1:]

            element_names       = new_element_names

    ########################################
    # Reorder inbound non-geo solenoids
    ########################################
    for inbound_nongeo_solenoid in tqdm(inbound_nongeo_solenoids):

        sol_start_ele   = f"{inbound_nongeo_solenoid}_bound"
        sol_end_ele     = f"{inbound_nongeo_solenoid}_chi3"
        
        # Get the start and end indices
        start_idxs  = [i for i, name in enumerate(element_names) if name == sol_start_ele]
        end_idxs    = [i for i, name in enumerate(element_names) if name == sol_end_ele]

        for start_idx, end_idx in zip(start_idxs, end_idxs):
            assert start_idx < end_idx

            new_element_names   = []
            new_element_names   += element_names[:start_idx]
            if not reverse_line:
                bound_elements      = [
                    f'{inbound_nongeo_solenoid}_chi1',
                    f'{inbound_nongeo_solenoid}_chi2',
                    f'{inbound_nongeo_solenoid}_chi3',
                    f'{inbound_nongeo_solenoid}_dz',
                    f'{inbound_nongeo_solenoid}_dxy',
                    f'{inbound_nongeo_solenoid}_bound']
            else:
                bound_elements      = [
                    f'{inbound_nongeo_solenoid}_chi3',
                    f'{inbound_nongeo_solenoid}_chi2',
                    f'{inbound_nongeo_solenoid}_chi1',
                    f'{inbound_nongeo_solenoid}_dz',
                    f'{inbound_nongeo_solenoid}_dxy',
                    f'{inbound_nongeo_solenoid}_bound']
            new_element_names   += bound_elements
            new_element_names   += element_names[end_idx + 1:]
            
            element_names       = new_element_names

    ########################################
    # Reorder outbound geo solenoids
    ########################################
    for outbound_geo_solenoid in tqdm(outbound_geo_solenoids):

        sol_start_ele   = f"{outbound_geo_solenoid}_bound"
        sol_end_ele     = f"{outbound_geo_solenoid}_chi3"
        
        # Get the start and end indices
        start_idxs  = [i for i, name in enumerate(element_names) if name == sol_start_ele]
        end_idxs    = [i for i, name in enumerate(element_names) if name == sol_end_ele]

        for start_idx, end_idx in zip(start_idxs, end_idxs):
            assert start_idx < end_idx

            new_element_names   = []
            new_element_names   += element_names[:start_idx]
            bound_elements      = [
                f'{outbound_geo_solenoid}_bound',
                f'{outbound_geo_solenoid}_dxy',
                f'{outbound_geo_solenoid}_dz',
                f'{outbound_geo_solenoid}_chi1',
                f'{outbound_geo_solenoid}_chi2',
                f'{outbound_geo_solenoid}_chi3']
            new_element_names   += bound_elements
            new_element_names   += element_names[end_idx + 1:]
            
            element_names       = new_element_names

    ########################################
    # Reorder outbound non-geo solenoids
    ########################################
    for outbound_nongeo_solenoid in tqdm(outbound_nongeo_solenoids):

        sol_start_ele   = f"{outbound_nongeo_solenoid}_bound"
        sol_end_ele     = f"{outbound_nongeo_solenoid}_chi3"
        
        # Get the start and end indices
        start_idxs  = [i for i, name in enumerate(element_names) if name == sol_start_ele]
        end_idxs    = [i for i, name in enumerate(element_names) if name == sol_end_ele]

        for start_idx, end_idx in zip(start_idxs, end_idxs):
            assert start_idx < end_idx
            
            new_element_names   = []
            new_element_names   += element_names[:start_idx]
            bound_elements      = [
                f'{outbound_nongeo_solenoid}_bound',
                f'{outbound_nongeo_solenoid}_dxy',
                f'{outbound_nongeo_solenoid}_dz',
                f'{outbound_nongeo_solenoid}_chi1',
                f'{outbound_nongeo_solenoid}_chi2',
                f'{outbound_nongeo_solenoid}_chi3']
            new_element_names   += bound_elements
            new_element_names   += element_names[end_idx + 1:]
            element_names       = new_element_names

    ########################################
    # Update the line
    ########################################
    line.element_names = element_names
