"""
(Unofficial) SAD to XSuite Converter

Element Converter
"""

################################################################################
# Required Packages
################################################################################
from tabnanny import verbose
import xtrack as xt
import numpy as np

from scipy.constants import c as clight
from scipy.constants import e as qe

from .._globals import print_section_heading, COORD_SIGNS, TRANSFORM_SHIFT_TOL, TRANSFORM_ROT_TOL, MAX_KNL_ORDER

################################################################################
# RAD2DEG Constant
################################################################################
RAD2DEG = 180.0 / np.pi

################################################################################
# Parsing of strings and floats
################################################################################
def parse_expression(expression: str):
    """
    Try to convert s to float; if that fails, return s stripped
    """
    if type(expression) is float:
        return expression
    elif type(expression) is int:
        return float(expression)
    elif type(expression) is str:
        expression_stripped  = expression.strip()
        try:
            return float(expression_stripped)
        except ValueError:
            return expression_stripped
    else:
        raise TypeError(f"Unsupported type: {type(expression)}. Expected str, int, or float.")

################################################################################
# Check that only one index in knl array is non zero
################################################################################
def only_index_nonzero(
    length: float,
    knl:    list,
    ksl:    list,
    idx:    int,
    tol:    float = 1E-12) -> bool:
    """
    Check that:
      1. length != 0 (within tol)
      2. All entries *except* at index `idx` in both knl and ksl are zero (within tol)
         - Elements may be floats or strings; non-numeric strings count as non-zero.
      3. If require_nonzero_at_idx: at least one of knl[idx], ksl[idx] is non-zero.
    """
    # 1) length check
    if abs(length) <= tol:
        return False

    # helper to test “is this value zero?”
    def is_zero(val) -> bool:
        try:
            return abs(float(val)) <= tol
        except (ValueError, TypeError):
            # non‐numeric ⇒ treat as non‐zero
            return False

    # 2) check every position except idx
    max_len = max(len(knl), len(ksl))
    for arr in (knl, ksl):
        if len(arr) < max_len:
            # pad shorter list with zeros
            arr = arr + [0] * (max_len - len(arr))
        for i, v in enumerate(arr):
            if i == idx:
                continue
            if not is_zero(v):
                return False

    # 3) ensure at least one of knl[idx], ksl[idx] is non‐zero
    if is_zero(knl[idx] if idx < len(knl) else 0) and \
        is_zero(ksl[idx] if idx < len(ksl) else 0):
        return False
    return True

################################################################################
# Get element misalignments
################################################################################
def get_element_misalignments(ele_vars, rotation_correction = 0.0):
        ########################################
        # Define as float zero
        ########################################
        shift_x     = 0.0
        shift_y     = 0.0
        rotation    = 0.0

        ########################################
        # Read values
        ########################################
        if 'dx' in ele_vars:
            shift_x     = parse_expression(ele_vars['dx'])
        if 'dy' in ele_vars:
            shift_y     = parse_expression(ele_vars['dy'])
        if 'rotate' in ele_vars:
            rotation    = parse_expression(ele_vars['rotate'])

        ########################################
        # Rotations in SAD are negative w.r.t. Xsuite
        ########################################
        if isinstance(rotation, str):
            rotation    = f"-{rotation} + {rotation_correction}"
        elif isinstance(rotation, (float, int)):
            rotation    = -rotation + rotation_correction
        else:
            raise TypeError(f"Error reading rotation: type {type(rotation)}")
        

        ########################################
        # Composition of rotations is different in SAD
        ########################################
        if isinstance(rotation, float) and isinstance(shift_x, float) and isinstance(shift_y, float):
            shift_r     = np.sqrt(shift_x**2 + shift_y**2)
            theta_rot   = np.arctan2(shift_y, shift_x)

            shift_x  = shift_r * np.cos(theta_rot - rotation)
            shift_y  = shift_r * np.sin(theta_rot - rotation)
            rotation = rotation
        else:
            shift_x     = str(shift_x)
            shift_y     = str(shift_y)
            rotation    = str(rotation)

            shift_r     = f"sqrt({shift_x}**2 + {shift_y}**2)"
            theta_rot   = f"arctan2({shift_y}, {shift_x})"

            shift_x  = f"{shift_r} * cos({theta_rot} - {rotation})"
            shift_y  = f"{shift_r} * sin({theta_rot} - {rotation})"
            rotation = rotation
        
        return shift_x, shift_y, rotation

################################################################################
# Convert all
################################################################################
def convert_elements(
        parsed_lattice_data:            dict,
        environment:                    xt.Environment,
        user_multipole_replacements:    dict | None = None,
        verbose:                        bool                = False) -> None:
    
    ########################################
    # Get the required data
    ########################################
    parsed_globals  = parsed_lattice_data['globals']
    parsed_elements = parsed_lattice_data['elements']

    ########################################
    # Drifts
    ########################################
    if 'drift' in parsed_elements:
        if verbose:
            print_section_heading("Converting Drifts", mode = 'subsection')
        convert_drifts(parsed_elements, environment)

    ########################################
    # Bends
    ########################################
    if 'bend' in parsed_elements:
        if verbose:
            print_section_heading("Converting Bends", mode = 'subsection')
        convert_bends(parsed_elements, environment)
        convert_correctors(parsed_elements, environment)

    ########################################
    # Quadrupoles
    ########################################
    if 'quad' in parsed_elements:
        if verbose:
            print_section_heading("Converting Quadrupoles", mode = 'subsection')
        convert_quadrupoles(parsed_elements, environment)

    ########################################
    # Sextupoles
    ########################################
    if 'sext' in parsed_elements:
        if verbose:
            print_section_heading("Converting Sextupoles", mode = 'subsection')
        convert_sextupoles(parsed_elements, environment)

    ########################################
    # Octupoles
    ########################################
    if 'oct' in parsed_elements:
        if verbose:
            print_section_heading("Converting Octupoles", mode = 'subsection')
        convert_octupoles(parsed_elements, environment)

    ########################################
    # Multipoles
    ########################################
    if 'mult' in parsed_elements:
        if verbose:
            print_section_heading("Converting Multipoles", mode = 'subsection')
        convert_multipoles(
            parsed_elements             = parsed_elements,
            environment                 = environment,
            user_multipole_replacements = user_multipole_replacements)

    ########################################
    # Cavities
    ########################################
    if 'cavi' in parsed_elements:
        if verbose:
            print_section_heading("Converting Cavities", mode = 'subsection')
        convert_cavities(parsed_elements, environment)

    ########################################
    # Apertures
    ########################################
    if 'apert' in parsed_elements:
        if verbose:
            print_section_heading("Converting Apertures", mode = 'subsection')
        convert_apertures(parsed_elements, environment)

    ########################################
    # Solenoids
    ########################################
    if 'sol' in parsed_elements:
        if verbose:
            print_section_heading("Converting Solenoids", mode = 'subsection')
        convert_solenoids(parsed_elements, parsed_globals, environment)

    ########################################
    # Coordinate Transformations
    ########################################
    if 'coord' in parsed_elements:
        if verbose:
            print_section_heading("Converting Coordinate Transformations", mode = 'subsection')
        convert_coordinate_transformations(parsed_elements, environment)

    ########################################
    # Markers
    ########################################
    if 'mark' in parsed_elements:
        if verbose:
            print_section_heading("Converting Markers", mode = 'subsection')
        convert_markers(parsed_elements, environment)

    ########################################
    # Monitors
    ########################################
    if 'moni' in parsed_elements:
        if verbose:
            print_section_heading("Converting Monitors", mode = 'subsection')
        convert_monitors(parsed_elements, environment)

    ########################################
    # Beam-Beam Interactions
    ########################################
    if 'beambeam' in parsed_elements:
        if verbose:
            print_section_heading("Converting Beam-Beam Interactions", mode = 'subsection')
        convert_beam_beam(parsed_elements, environment)

################################################################################
# Convert drift
################################################################################
def convert_drifts(parsed_elements, environment):
    """
    Convert drifts from the SAD parsed data
    """

    drifts  = parsed_elements['drift']

    for ele_name, ele_vars in drifts.items():

        ########################################
        # Assert Length
        ########################################
        if 'l' in ele_vars:
            length = ele_vars['l']
        else:
            raise ValueError(f"Drift {ele_name} missing length.")

        ########################################
        # Create Element
        ########################################
        environment.new(
            name    = ele_name,
            parent  = xt.Drift,
            length  = length)

################################################################################
# Convert Bends
################################################################################
def convert_bends(parsed_elements, environment):
    """
    Convert bends from the SAD parsed data
    """

    bends  = parsed_elements['bend']

    for ele_name, ele_vars in bends.items():
        if 'angle' in ele_vars:
            
            angle   = parse_expression(ele_vars['angle'])
            if angle == 0:
                continue

            if "l" not in ele_vars:
                # TODO: Improve the handling of this
                k0l             = parse_expression(ele_vars['angle'])
                if k0l != 0:
                    raise ValueError(f"Error! Bend {ele_name} missing length.")
                else:
                    print(f"Warning! Bend {ele_name} missing length and installed as marker")
                    environment.new(
                        name                = ele_name,
                        parent              = xt.Marker)
                    continue

            ########################################
            # Initialise parameters
            ########################################
            length      = 0.0
            k1l         = 0.0
            e1          = 0.0
            e2          = 0.0
            ae1         = 0.0
            ae2         = 0.0

            edge_entry_angle    = 0
            edge_exit_angle     = 0

            ########################################
            # Read values
            ########################################
            length          = float(parse_expression(ele_vars['l']))
            k0l             = parse_expression(ele_vars['angle'])
            
            if 'k1' in ele_vars:
                k1l         = parse_expression(ele_vars['k1'])
            if 'e1' in ele_vars:
                e1          = parse_expression(ele_vars['e1'])
            if 'e2' in ele_vars:
                e2          = parse_expression(ele_vars['e2'])
            if 'ae1' in ele_vars:
                ae1         = parse_expression(ele_vars['ae1'])
            if 'ae2' in ele_vars:
                ae2         = parse_expression(ele_vars['ae2'])

            shift_x, shift_y, rotation  = get_element_misalignments(ele_vars)

            if type(k0l) is float:
                k0  = k0l / length
            else:
                k0  = f"{k0l} / {length}"

            if type(k1l) is float:
                k1  = k1l / length
            else:
                k1  = f"{k1l} / {length}"

            edge_entry_angle    = f"{e1} * {k0l} + {ae1}"
            edge_exit_angle     = f"{e2} * {k0l} + {ae2}"

            ########################################
            # Create variables
            ########################################
            environment[f'k0_{ele_name}']   = k0
            k0                              = f"k0_{ele_name}"
            
            if k1 != 0:
                environment[f'k1_{ele_name}']   = k1
                k1                              = f"k1_{ele_name}"

            ########################################
            # Create Element
            ########################################
            environment.new(
                name                = ele_name,
                parent              = xt.Bend,
                length              = length,
                k0                  = k0,
                k1                  = k1,
                h                   = k0,
                edge_entry_angle    = edge_entry_angle,
                edge_exit_angle     = edge_exit_angle,
                shift_x             = shift_x,
                shift_y             = shift_y,
                rot_s_rad           = rotation)
            continue

################################################################################
# Convert Correctors
################################################################################
def convert_correctors(parsed_elements, environment):
    """
    Convert correctors from the SAD parsed data
    """

    bends  = parsed_elements['bend']

    for ele_name, ele_vars in bends.items():

        is_corrector    = False
        if 'angle' in ele_vars:
            angle   = parse_expression(ele_vars['angle'])
            if angle == 0:
                is_corrector    = True
        if 'angle' not in ele_vars:
            is_corrector    = True

        if is_corrector:

            ########################################
            # Initialise parameters
            ########################################
            length      = 0.0
            k0l         = 0.0

            ########################################
            # Read values
            ########################################
            if 'l' in ele_vars:
                length      = parse_expression(ele_vars['l'])

            shift_x, shift_y, rotation  = get_element_misalignments(ele_vars)

            if length == 0:
                print(f"Warning! Corrector {ele_name} missing length and installed as marker")

                environment.new(
                    name    = ele_name,
                    parent  = xt.Marker)
                continue

            if 'k0' in ele_vars:
                k0l             = parse_expression(ele_vars['k0'])
            if type(k0l) is float:
                k0  = k0l / ele_vars['l']
            else:
                k0  = f"{k0l} / {ele_vars['l']}"

            ########################################
            # Create variables
            ########################################
            environment[f'k0_{ele_name}']   = k0
            k0                              = f"k0_{ele_name}"

            ########################################
            # Create Element
            ########################################
            environment.new(
                name                = ele_name,
                parent              = xt.Bend,
                length              = length,
                k0                  = k0,
                k1                  = 0.0,
                h                   = 0.0,
                edge_entry_angle    = 0.0,
                edge_exit_angle     = 0.0,
                shift_x             = shift_x,
                shift_y             = shift_y,
                rot_s_rad           = rotation)
            continue

################################################################################
# Convert Quadrupoles
################################################################################
def convert_quadrupoles(parsed_elements, environment):
    """
    Convert quadrupoles from the SAD parsed data
    """

    quads  = parsed_elements['quad']

    for ele_name, ele_vars in quads.items():

        ########################################
        # Initialise parameters
        ########################################
        length      = 0.0
        k1l         = 0.0
        k1sl        = 0.0

        ########################################
        # Read values
        ########################################
        if 'l' in ele_vars:
            length      = parse_expression(ele_vars['l'])
        else:
            raise ValueError(f"Error! Quadrupole {ele_name} missing length.")

        shift_x, shift_y, rotation  = get_element_misalignments(ele_vars)

        if 'k1' in ele_vars:
            if not isinstance(rotation, float):
                k1l     = f"{ele_vars['k1']}"
            else:

                if np.isclose(rotation, +np.pi / 4, atol = 1E-6):
                    if isinstance(ele_vars['k1'], (float, int)):
                        k1sl    = -ele_vars['k1']
                    else:
                        k1sl    = f"-{ele_vars['k1']}"
                    shift_x, shift_y, rotation  = get_element_misalignments(
                        ele_vars            = ele_vars,
                        rotation_correction = -np.pi / 4)

                elif np.isclose(rotation, -np.pi / 4, atol = 1E-6):
                    if isinstance(ele_vars['k1'], (float, int)):
                        k1sl    = +ele_vars['k1']
                    else:
                        k1sl    = f"+{ele_vars['k1']}"
                    shift_x, shift_y, rotation  = get_element_misalignments(
                        ele_vars            = ele_vars,
                        rotation_correction = +np.pi / 4)

                else:
                    k1l     = ele_vars['k1']

        if isinstance(k1l, float):
            k1  = k1l / ele_vars['l']
        else:
            k1  = f"{k1l} / {ele_vars['l']}"
        
        if isinstance(k1sl, float):
            k1s = k1sl / ele_vars['l']
        else:
            k1s = f"{k1sl} / {ele_vars['l']}"

        ########################################
        # Create variables
        ########################################
        if k1 != 0:
            environment[f'k1_{ele_name}']   = k1
            k1                              = f"k1_{ele_name}"
        if k1s != 0:
            environment[f'k1s_{ele_name}']  = k1s
            k1s                             = f"k1s_{ele_name}"

        ########################################
        # Create Element
        ########################################
        environment.new(
            name        = ele_name,
            parent      = xt.Quadrupole,
            length      = length,
            k1          = k1,
            k1s         = k1s,
            shift_x     = shift_x,
            shift_y     = shift_y,
            rot_s_rad   = rotation)
        continue

################################################################################
# Convert Sextupoles
################################################################################
def convert_sextupoles(parsed_elements, environment):
    """
    Convert sextupoles from the SAD parsed data
    """

    sexts  = parsed_elements['sext']

    for ele_name, ele_vars in sexts.items():

        ########################################
        # Initialise parameters
        ########################################
        length      = 0.0
        k2l         = 0.0
        k2sl        = 0.0

        ########################################
        # Read values
        ########################################
        if 'l' in ele_vars:
            length      = parse_expression(ele_vars['l'])
        else:
            raise ValueError(f"Error! Sextupole {ele_name} missing length.")

        shift_x, shift_y, rotation  = get_element_misalignments(ele_vars)

        if 'k2' in ele_vars:
            if not isinstance(rotation, float):
                k2l     = f"{ele_vars['k2']}"
            else:

                if np.isclose(rotation, +np.pi / 6, atol = 1E-6):
                    if isinstance(ele_vars['k2'], (float, int)):
                        k2sl    = -ele_vars['k2']
                    else:
                        k2sl    = f"-{ele_vars['k2']}"
                    shift_x, shift_y, rotation  = get_element_misalignments(
                        ele_vars            = ele_vars,
                        rotation_correction = -np.pi / 6)

                elif np.isclose(rotation, -np.pi / 6, atol = 1E-6):
                    if isinstance(ele_vars['k2'], (float, int)):
                        k2sl    = +ele_vars['k2']
                    else:
                        k2sl    = f"+{ele_vars['k2']}"
                    shift_x, shift_y, rotation  = get_element_misalignments(
                        ele_vars            = ele_vars,
                        rotation_correction = +np.pi / 6)

                else:
                    k2l     = ele_vars['k2']

        if isinstance(k2l, float):
            k2  = k2l / ele_vars['l']
        else:
            k2  = f"{k2l} / {ele_vars['l']}"

        if isinstance(k2sl, float):
            k2s = k2sl / ele_vars['l']
        else:
            k2s = f"{k2sl} / {ele_vars['l']}"

        ########################################
        # Create variables
        ########################################
        if k2 != 0:
            environment[f'k2_{ele_name}']   = k2
            k2                              = f"k2_{ele_name}"
        if k2s != 0:
            environment[f'k2s_{ele_name}']  = k2s
            k2s                             = f"k2s_{ele_name}"

        ########################################
        # Create Element
        ########################################
        environment.new(
            name        = ele_name,
            parent      = xt.Sextupole,
            length      = length,
            k2          = k2,
            k2s         = k2s,
            shift_x     = shift_x,
            shift_y     = shift_y,
            rot_s_rad   = rotation)
        continue

################################################################################
# Convert Octupoles
################################################################################
def convert_octupoles(parsed_elements, environment):
    """
    Convert octupoles from the SAD parsed data
    """

    octs    = parsed_elements['oct']

    for ele_name, ele_vars in octs.items():

        if "l" not in ele_vars:
            # TODO: Improve the handling of this
            print(f"Warning! Octupole {ele_name} missing length and installed as marker")
            environment.new(
                name                = ele_name,
                parent              = xt.Marker)
            continue

        ########################################
        # Initialise parameters
        ########################################
        length      = 0.0
        k3l         = 0.0
        k3sl        = 0.0

        ########################################
        # Read values
        ########################################
        if 'l' in ele_vars:
            length      = parse_expression(ele_vars['l'])
        else:
            raise ValueError(f"Error! Octupole {ele_name} missing length.")

        shift_x, shift_y, rotation  = get_element_misalignments(ele_vars)

        if 'k3' in ele_vars:
            if not isinstance(rotation, float):
                k3l     = f"{ele_vars['k3']}"
            else:

                if np.isclose(rotation, +np.pi / 8, atol = 1E-6):
                    if isinstance(ele_vars['k3'], (float, int)):
                        k3sl    = -ele_vars['k3']
                    else:
                        k3sl    = f"-{ele_vars['k3']}"
                    shift_x, shift_y, rotation  = get_element_misalignments(
                        ele_vars            = ele_vars,
                        rotation_correction = -np.pi / 8)

                elif np.isclose(rotation, -np.pi / 8, atol = 1E-6):
                    if isinstance(ele_vars['k3'], (float, int)):
                        k3sl    = +ele_vars['k3']
                    else:
                        k3sl    = f"+{ele_vars['k3']}"
                    shift_x, shift_y, rotation  = get_element_misalignments(
                        ele_vars            = ele_vars,
                        rotation_correction = +np.pi / 8)

                else:
                    k3l     = ele_vars['k3']

        if isinstance(k3l, float):
            k3  = k3l / ele_vars['l']
        else:
            k3  = f"{k3l} / {ele_vars['l']}"

        if isinstance(k3sl, float):
            k3s = k3sl / ele_vars['l']
        else:
            k3s = f"{k3sl} / {ele_vars['l']}"

        ########################################
        # Create variables
        ########################################
        if k3 != 0:
            environment[f'k3_{ele_name}']   = k3
            k3                              = f"k3_{ele_name}"
        if k3s != 0:
            environment[f'k3s_{ele_name}']  = k3s
            k3s                             = f"k3s_{ele_name}"

        ########################################
        # Create Element
        ########################################
        environment.new(
            name        = ele_name,
            parent      = xt.Octupole,
            length      = length,
            k3          = k3,
            k3s         = k3s,
            shift_x     = shift_x,
            shift_y     = shift_y,
            rot_s_rad   = rotation)
        continue

################################################################################
# Convert Multipoles
################################################################################
def convert_multipoles(
        parsed_elements,
        environment,
        user_multipole_replacements = None,
        simplify_multipoles         = True):
    """
    Convert multipoles from the SAD parsed data
    """

    mults   = parsed_elements['mult']

    for ele_name, ele_vars in mults.items():

        ########################################
        # Initialise parameters
        ########################################
        length      = 0.0

        ########################################
        # Read values
        ########################################
        if 'l' in ele_vars:
            length      = parse_expression(ele_vars['l'])

        shift_x, shift_y, rotation  = get_element_misalignments(ele_vars)

        knl = []
        for kn in range(0, MAX_KNL_ORDER):
            knl.append(0.0)
            if f'k{kn}' in ele_vars:
                knl[kn] = parse_expression(ele_vars[f'k{kn}'])

        ksl = []
        for ks in range(0, MAX_KNL_ORDER):
            ksl.append(0.0)
            if f'sk{ks}' in ele_vars:
                ksl[ks] = parse_expression(ele_vars[f'sk{ks}'])

        ########################################
        # User Defined Multipole Replacements
        ########################################
        if user_multipole_replacements is not None:
            if any(ele_name.startswith(test_key) for test_key in user_multipole_replacements):
                replace_type    = None

                if not 'l' in ele_vars:
                    print(f'Warning! Multipole {ele_name} is a thin lens, replacement not supported for thin lens')
                    continue

                # Search the multipole replacements dict for the type of element
                for replacement in user_multipole_replacements:
                    if ele_name.startswith(replacement):
                        replace_type    = user_multipole_replacements[replacement]

                ########################################
                # Bend Replacement (kick)
                ########################################
                if replace_type == 'Bend':

                    if knl[0] != 0 and ksl[0] != 0:
                        if type(knl[0]) is float or type(ksl[0]) is float:
                            k0l         = f"sqrt({knl[0]}**2 + {ksl[0]}**2)"
                            rotation    = f"{rotation} + arctan2({ksl[0]}, {knl[0]})"
                        else:
                            k0l         = np.sqrt(knl[0]**2 + ksl[0]**2)
                            rotation    = rotation + np.arctan2(ksl[0], knl[0])
                    elif knl[0] != 0:
                        k0l         = knl[0]
                        rotation    = rotation
                    elif ksl[0] != 0:
                        k0l         = ksl[0]
                        if type(rotation) is float:
                            rotation    = rotation + np.pi / 2
                        else:
                            rotation    = f"{rotation} + np.pi / 2"
                    else:
                        k0l = 0.0
                    
                    if type(k0l) is float:
                        k0  = k0l / ele_vars['l']
                    else:
                        k0  = f"{k0l} / {ele_vars['l']}"

                    ####################
                    # Create variables
                    ####################
                    if k0 != 0:
                        environment[f'k0_{ele_name}']   = k0
                        k0                              = f"k0_{ele_name}"

                    ####################
                    # Create Element
                    ####################
                    environment.new(
                        name                = ele_name,
                        parent              = xt.Bend,
                        length              = length,
                        k0                  = k0,
                        shift_x             = shift_x,
                        shift_y             = shift_y,
                        rot_s_rad           = rotation)
                    continue

                ########################################
                # Quadrupole Replacement
                ########################################
                elif replace_type == 'Quadrupole':

                    k1l     = knl[1]
                    k1sl    = ksl[1]

                    if type(k1l) is float:
                        k1  = k1l / ele_vars['l']
                    else:
                        k1  = f"{k1l} / {ele_vars['l']}"
                    if type(k1sl) is float:
                        k1s = k1sl / ele_vars['l']
                    else:
                        k1s = f"{k1sl} / {ele_vars['l']}"

                    ####################
                    # Create variables
                    ####################
                    if k1 != 0:
                        environment[f'k1_{ele_name}']   = k1
                        k1                              = f"k1_{ele_name}"
                    if k1s != 0:
                        environment[f'k1s_{ele_name}']  = k1s
                        k1s                             = f"k1s_{ele_name}"

                    ####################
                    # Create Element
                    ####################
                    environment.new(
                        name                = ele_name,
                        parent              = xt.Quadrupole,
                        length              = length,
                        k1                  = k1,
                        k1s                 = k1s,
                        shift_x             = shift_x,
                        shift_y             = shift_y,
                        rot_s_rad           = rotation)
                    continue

                ########################################
                # Sextupole Replacement
                ########################################
                elif replace_type == 'Sextupole':

                    k2l     = knl[2]
                    k2sl    = ksl[2]

                    if type(k2l) is float:
                        k2  = k2l / ele_vars['l']
                    else:
                        k2  = f"{k2l} / {ele_vars['l']}"
                    if type(k2sl) is float:
                        k2s = k2sl / ele_vars['l']
                    else:
                        k2s = f"{k2sl} / {ele_vars['l']}"

                    ####################
                    # Create variables
                    ####################
                    if k2 != 0:
                        environment[f'k2_{ele_name}']   = k2
                        k2                              = f"k2_{ele_name}"
                    if k2s != 0:
                        environment[f'k2s_{ele_name}']  = k2s
                        k2s                             = f"k2s_{ele_name}"

                    ####################
                    # Create Element
                    ####################
                    environment.new(
                        name                = ele_name,
                        parent              = xt.Sextupole,
                        length              = length,
                        k2                  = k2,
                        k2s                 = k2s,
                        shift_x             = shift_x,
                        shift_y             = shift_y,
                        rot_s_rad           = rotation)
                    continue

                ########################################
                # Octupole Replacement
                ########################################
                elif replace_type == 'Octupole':

                    k3l     = knl[3]
                    k3sl    = ksl[3]

                    if type(k3l) is float:
                        k3  = k3l / ele_vars['l']
                    else:
                        k3  = f"{k3l} / {ele_vars['l']}"
                    if type(k3sl) is float:
                        k3s = k3sl / ele_vars['l']
                    else:
                        k3s = f"{k3sl} / {ele_vars['l']}"

                    ####################
                    # Create variables
                    ####################
                    if k3 != 0:
                        environment[f'k3_{ele_name}']   = k3
                        k3                              = f"k3_{ele_name}"
                    if k3s != 0:
                        environment[f'k3s_{ele_name}']  = k3s
                        k3s                             = f"k3s_{ele_name}"

                    ####################
                    # Create Element
                    ####################
                    environment.new(
                        name                = ele_name,
                        parent              = xt.Octupole,
                        length              = length,
                        k3                  = k3,
                        k3s                 = k3s,
                        shift_x             = shift_x,
                        shift_y             = shift_y,
                        rot_s_rad           = rotation)
                    continue
                else:
                    raise ValueError('Error: Unknown element replacement')

        ########################################
        # Automatic Simplification
        ########################################
        if simplify_multipoles:

            ########################################
            # Correctors stored as multipoles
            ########################################
            if only_index_nonzero(
                    length  = float(length),
                    knl     = knl,
                    ksl     = ksl,
                    idx     = 0):
                
                if knl[0] != 0 and ksl[0] != 0:
                    if type(knl[0]) is float or type(ksl[0]) is float:
                        k0l         = f"sqrt({knl[0]}**2 + {ksl[0]}**2)"
                        rotation    = f"{rotation} + arctan2({ksl[0]}, {knl[0]})"
                    else:
                        k0l         = np.sqrt(knl[0]**2 + ksl[0]**2)
                        rotation    = rotation + np.arctan2(ksl[0], knl[0])
                elif knl[0] != 0:
                    k0l         = knl[0]
                    rotation    = rotation
                elif ksl[0] != 0:
                    k0l         = ksl[0]
                    if type(rotation) is float:
                        rotation    = rotation + np.pi / 2
                    else:
                        rotation    = f"{rotation} + np.pi / 2"
                else:
                    k0l = 0
                
                if type(k0l) is float:
                    k0  = k0l / ele_vars['l']
                else:
                    k0  = f"{k0l} / {ele_vars['l']}"

                ####################
                # Create variables
                ####################
                if k0 != 0:
                    environment[f'k0_{ele_name}']   = k0
                    k0                              = f"k0_{ele_name}"

                ####################
                # Create Element
                ####################
                environment.new(
                    name                = ele_name,
                    parent              = xt.Bend,
                    length              = length,
                    k0                  = k0,
                    shift_x             = shift_x,
                    shift_y             = shift_y,
                    rot_s_rad           = rotation)
                continue

            ########################################
            # Quadrupoles stored as multipoles
            ########################################
            if only_index_nonzero(
                    length  = float(length),
                    knl     = knl,
                    ksl     = ksl,
                    idx     = 1):

                k1l     = knl[1]
                k1sl    = ksl[1]

                if type(k1l) is float:
                    k1  = k1l / ele_vars['l']
                else:
                    k1  = f"{k1l} / {ele_vars['l']}"
                if type(k1sl) is float:
                    k1s = k1sl / ele_vars['l']
                else:
                    k1s = f"{k1sl} / {ele_vars['l']}"

                ####################
                # Create variables
                ####################
                if k1 != 0:
                    environment[f'k1_{ele_name}']   = k1
                    k1                              = f"k1_{ele_name}"
                if k1s != 0:
                    environment[f'k1s_{ele_name}']  = k1s
                    k1s                             = f"k1s_{ele_name}"

                ####################
                # Create Element
                ####################
                environment.new(
                    name                = ele_name,
                    parent              = xt.Quadrupole,
                    length              = length,
                    k1                  = k1,
                    k1s                 = k1s,
                    shift_x             = shift_x,
                    shift_y             = shift_y,
                    rot_s_rad           = rotation)
                continue

            ########################################
            # Sextupoles stored as multipoles
            ########################################
            if only_index_nonzero(
                    length  = float(length),
                    knl     = knl,
                    ksl     = ksl,
                    idx     = 2):

                k2l     = knl[2]
                k2sl    = ksl[2]

                if type(k2l) is float:
                    k2  = k2l / ele_vars['l']
                else:
                    k2  = f"{k2l} / {ele_vars['l']}"
                if type(k2sl) is float:
                    k2s = k2sl / ele_vars['l']
                else:
                    k2s = f"{k2sl} / {ele_vars['l']}"

                ####################
                # Create variables
                ####################
                if k2 != 0:
                    environment[f'k2_{ele_name}']   = k2
                    k2                              = f"k2_{ele_name}"
                if k2s != 0:
                    environment[f'k2s_{ele_name}']  = k2s
                    k2s                             = f"k2s_{ele_name}"

                ####################
                # Create Element
                ####################
                environment.new(
                    name                = ele_name,
                    parent              = xt.Sextupole,
                    length              = length,
                    k2                  = k2,
                    k2s                 = k2s,
                    shift_x             = shift_x,
                    shift_y             = shift_y,
                    rot_s_rad           = rotation)
                continue

            ########################################
            # Octupoles stored as multipoles
            ########################################
            if only_index_nonzero(
                    length  = float(length),
                    knl     = knl,
                    ksl     = ksl,
                    idx     = 3):

                k3l     = knl[3]
                k3sl    = ksl[3]

                if type(k3l) is float:
                    k3  = k3l / ele_vars['l']
                else:
                    k3  = f"{k3l} / {ele_vars['l']}"
                if type(k3sl) is float:
                    k3s = k3sl / ele_vars['l']
                else:
                    k3s = f"{k3sl} / {ele_vars['l']}"

                ####################
                # Create variables
                ####################
                if k3 != 0:
                    environment[f'k3_{ele_name}']   = k3
                    k3                              = f"k3_{ele_name}"
                if k3s != 0:
                    environment[f'k3s_{ele_name}']  = k3s
                    k3s                             = f"k3s_{ele_name}"

                ####################
                # Create Element
                ####################
                environment.new(
                    name                = ele_name,
                    parent              = xt.Octupole,
                    length              = length,
                    k3                  = k3,
                    k3s                 = k3s,
                    shift_x             = shift_x,
                    shift_y             = shift_y,
                    rot_s_rad           = rotation)
                continue

        ########################################
        # True multipole element
        ########################################
        environment.new(
            name        = ele_name,
            parent      = xt.Multipole,
            _isthick    = True,
            length      = length,
            knl         = knl,
            ksl         = ksl,
            order       = MAX_KNL_ORDER,
            shift_x     = shift_x,
            shift_y     = shift_y,
            rot_s_rad   = rotation)
        continue

################################################################################
# Convert Cavities
################################################################################
def convert_cavities(parsed_elements, environment):
    """
    Convert cavities from the SAD parsed data
    """

    cavis   = parsed_elements['cavi']

    for ele_name, ele_vars in cavis.items():

        ########################################
        # Initialise parameters
        ########################################
        length      = 0.0
        voltage     = 0.0
        freq        = 0.0
        phi         = 180.0

        ########################################
        # Read values
        ########################################
        if 'l' in ele_vars:
            length      = parse_expression(ele_vars['l'])
        if 'volt' in ele_vars:
            voltage = parse_expression(ele_vars['volt'])
        if 'freq' in ele_vars:
            freq = parse_expression(ele_vars['freq'])
        if 'phi' in ele_vars:
            phi_offset = parse_expression(ele_vars['phi'])
            if type(phi_offset) is float:
                phi_offset  = np.rad2deg(phi_offset)
                phi         += phi_offset
            elif type(phi_offset) is str:
                phi_offset  = f"({RAD2DEG} * {phi_offset})"
                phi         = f"{phi} + {phi_offset}"
            else:
                raise ValueError(f"Unsupported type for phi offset: {type(phi_offset)}")

        if 'harm' in ele_vars:
            print(f"Cavity {ele_name} is harmonic and addressed later")

        ########################################
        # Create variables
        ########################################
        environment[f'vol_{ele_name}']      = voltage
        
        if freq != 0:
            environment[f'freq_{ele_name}'] = freq
            freq                            = f"freq_{ele_name} * (1 + fshift)"
        if phi != 0:
            environment[f'lag_{ele_name}']  = phi
            phi                             = f"lag_{ele_name}"

        ########################################
        # Create Element
        ########################################
        environment.new(
            name        = ele_name,
            parent      = xt.Cavity,
            length      = length,
            voltage     = voltage,
            frequency   = freq,
            lag         = phi)
        continue

################################################################################
# Convert Apertures
################################################################################
def convert_apertures(parsed_elements, environment):
    """
    Convert apertures from the SAD parsed data
    """

    aperts  = parsed_elements['apert']

    for ele_name, ele_vars in aperts.items():

        ########################################
        # Initialise parameters
        ########################################
        a       = 1.0
        b       = 1.0

        ########################################
        # Read values
        ########################################
        if 'ax' in ele_vars:
            a = parse_expression(ele_vars['ax'])
        if 'ay' in ele_vars:
            b = parse_expression(ele_vars['ay'])

        ########################################
        # Create Element
        ########################################
        environment.new(
            name    = ele_name,
            parent  = xt.LimitEllipse,
            a       = a,
            b       = b)
        continue

################################################################################
# Convert Solenoids
################################################################################
def convert_solenoids(parsed_elements, parsed_globals, environment):
    """
    Convert solenoids from the SAD parsed data
    """

    P0_J    = parsed_globals['momentum'] * qe / clight
    BRHO    = P0_J / qe / parsed_globals['charge']

    solenoids   = parsed_elements['sol']

    for ele_name, ele_vars in solenoids.items():

        ########################################
        # Initialise parameters
        ########################################
        bound       = False
        geo         = False

        offset_x    = 0.0
        offset_y    = 0.0
        offset_z    = 0.0
        rot_chi1    = 0.0
        rot_chi2    = 0.0
        rot_chi3    = 0.0

        # Per Oide, there is no offset s

        ########################################
        # Read values
        ########################################
        bz  = parse_expression(ele_vars['bz'])
        ks  = bz / BRHO

        if 'bound' in ele_vars:
            bound   = True
        else:
            bound   = False

        if 'geo' in ele_vars:
            geo     = True
        else:
            geo     = False

        # Based on testing, when geo, use the dpx, dpy etc
        if 'dx' in ele_vars:
            offset_x    = parse_expression(ele_vars['dx'])
        if 'dy' in ele_vars:
            offset_y    = parse_expression(ele_vars['dy'])
        if 'dz' in ele_vars:
            offset_z    = parse_expression(ele_vars['dz'])
            offset_s    = parse_expression(ele_vars['dz'])
        if 'dpx' in ele_vars:
            rot_chi1    = parse_expression(ele_vars['dpx'])
        if 'dpy' in ele_vars:
            rot_chi2    = parse_expression(ele_vars['dpy'])

        if not geo:
            # Then use the other rotations
            if ('dpx' not in ele_vars) and ('chi1' in ele_vars):
                rot_chi1    = parse_expression(ele_vars['chi1'])
            if ('dpy' not in ele_vars) and ('chi2' in ele_vars):
                rot_chi2    = parse_expression(ele_vars['chi2'])
            if ('dpz' not in ele_vars) and ('chi3' in ele_vars):
                rot_chi3    = parse_expression(ele_vars['chi3'])

        # Should not have dz in geo sol
        if geo and 'dz' in ele_vars:
            if verbose:
                print(f"Warning! Solenoid {ele_name} is a geo solenoid but with dz defined: ignoring dz")
            offset_z = 0.0

        ########################################
        # Zero small values
        ########################################
        if isinstance(offset_x, float) and np.abs(offset_x) < TRANSFORM_SHIFT_TOL:
            offset_x = 0.0
        if isinstance(offset_y, float) and np.abs(offset_y) < TRANSFORM_SHIFT_TOL:
            offset_y = 0.0
        if isinstance(offset_z, float) and np.abs(offset_z) < TRANSFORM_SHIFT_TOL:
            offset_z = 0.0
        if isinstance(rot_chi1, float) and np.abs(rot_chi1) < TRANSFORM_ROT_TOL:
            rot_chi1 = 0.0
        if isinstance(rot_chi2, float) and np.abs(rot_chi2) < TRANSFORM_ROT_TOL:
            rot_chi2 = 0.0
        if isinstance(rot_chi3, float) and np.abs(rot_chi3) < TRANSFORM_ROT_TOL:
            rot_chi3 = 0.0

        ########################################
        # Shift Transforms
        ########################################
        SOL_DX_FACTOR   = -1 * COORD_SIGNS['dx']
        SOL_DY_FACTOR   = -1 * COORD_SIGNS['dy']
        SOL_DZ_FACTOR   = -1

        if type(offset_x) is float:
            offset_x    = SOL_DX_FACTOR * offset_x
        elif type(offset_x) is str:
            offset_x    = f"{SOL_DX_FACTOR} * {offset_x}"
        else:
            raise ValueError(f"Unsupported type for offset_x: {type(offset_x)}")
        
        if type(offset_y) is float:
            offset_y    = SOL_DY_FACTOR * offset_y
        elif type(offset_y) is str:
            offset_y    = f"{SOL_DY_FACTOR} * {offset_y}"
        else:
            raise ValueError(f"Unsupported type for offset_y: {type(offset_y)}")

        if type(offset_z) is float:
            offset_z    = SOL_DZ_FACTOR * offset_z
        elif type(offset_z) is str:
            offset_z    = f"{SOL_DZ_FACTOR} * {offset_z}"
        else:
            raise ValueError(f"Unsupported type for offset_z: {type(offset_z)}")

        ########################################
        # Angle Transforms
        ########################################
        SOL_CHI1_FACTOR = -1 * COORD_SIGNS['chi1']
        SOL_CHI2_FACTOR = -1 * COORD_SIGNS['chi2']
        SOL_CHI3_FACTOR = -1 * COORD_SIGNS['chi3']

        if type(rot_chi1) is float:
            rot_chi1    = np.rad2deg(SOL_CHI1_FACTOR * rot_chi1)
        elif type(rot_chi1) is str:
            rot_chi1    = f"{SOL_CHI1_FACTOR} * {rot_chi1} * {RAD2DEG}"
        else:
            raise ValueError(f"Unsupported type for rot_chi1: {type(rot_chi1)}")
        
        if type(rot_chi2) is float:
            rot_chi2    = np.rad2deg(SOL_CHI2_FACTOR * rot_chi2)
        elif type(rot_chi2) is str:
            rot_chi2    = f"{SOL_CHI2_FACTOR} * {rot_chi2} * {RAD2DEG}"
        else:
            raise ValueError(f"Unsupported type for rot_chi2: {type(rot_chi2)}")
        
        if type(rot_chi3) is float:
            rot_chi3    = np.rad2deg(SOL_CHI3_FACTOR * rot_chi3)
        elif type(rot_chi3) is str:
            rot_chi3    = f"{SOL_CHI3_FACTOR} * {rot_chi3} * {RAD2DEG}"
        else:
            raise ValueError(f"Unsupported type for rot_chi3: {type(rot_chi3)}")

        ########################################
        # Compound Solenoid Element
        ########################################
        if bound:

            ########################################
            # Create the elements
            ########################################
            environment.new(
                name    = f'{ele_name}_bound',
                parent  = xt.Solenoid,
                ks      = ks)

            environment.new(
                name    = f'{ele_name}_dxy',
                parent  = xt.XYShift,
                dx      = offset_x,
                dy      = offset_y)
            
            environment.new(
                name    = f'{ele_name}_dz',
                parent  = xt.ZetaShift,
                dzeta   = offset_z)

            environment.new(
                name    = f'{ele_name}_chi2',
                parent  = xt.XRotation,
                angle   = rot_chi2)

            environment.new(
                name    = f'{ele_name}_chi1',
                parent  = xt.YRotation,
                angle   = rot_chi1)

            environment.new(
                name    = f'{ele_name}_chi3',
                parent  = xt.SRotation,
                angle   = rot_chi3)

            # ds kills things w.r.t sad
            # Considering the survey, it breaks everything
            # There is a discrepancy in s when it is removed
            # This is just because SAD takes dz into account with s
            # SAD s is based on particle path!

            ########################################
            # Order the elements (reordered later)
            ########################################
            compound_solenoid_components = [
                f'{ele_name}_bound',
                f'{ele_name}_dxy',
                f'{ele_name}_dz',
                f'{ele_name}_chi1',
                f'{ele_name}_chi2',
                f'{ele_name}_chi3']
            environment.new_line(
                name        = ele_name,
                components  = compound_solenoid_components)
            continue
        else:
            environment.new(
                name    = f'{ele_name}',
                parent  = xt.Solenoid,
                ks      = ks)
            continue

################################################################################
# Convert Markers
################################################################################
def convert_markers(parsed_elements, environment):
    """
    Convert markers from the SAD parsed data
    """

    markers   = parsed_elements['mark']

    for ele_name, ele_vars in markers.items():

        ########################################
        # Create Element
        ########################################
        environment.new(
                name    = ele_name,
                parent  = xt.Marker)
        continue

################################################################################
# Convert Monitors
################################################################################
def convert_monitors(parsed_elements, environment):
    """
    Convert monitors from the SAD parsed data
    """

    monitors   = parsed_elements['moni']

    for ele_name, ele_vars in monitors.items():

        ########################################
        # Create Element
        ########################################
        environment.new(
                name    = ele_name,
                parent  = xt.Marker)
        continue

################################################################################
# Convert Beam-Beam Interactions
################################################################################
def convert_beam_beam(parsed_elements, environment):
    """
    Convert beam-beam interactions from the SAD parsed data
    """

    beam_beams   = parsed_elements['beambeam']

    for ele_name, ele_vars in beam_beams.items():

        ########################################
        # Create Element
        ########################################
        environment.new(
                name    = ele_name,
                parent  = xt.Marker)
        continue

################################################################################
# Convert Coordinate Transformations
################################################################################
def convert_coordinate_transformations(parsed_elements, environment):
    """
    Convert coordinate transformations from the SAD parsed data
    """

    coord_transforms   = parsed_elements['coord']
    for ele_name, ele_vars in coord_transforms.items():

        ########################################
        # Initialise parameters
        ########################################
        n_transforms    = 0

        offset_x    = 0.0
        offset_y    = 0.0
        rot_chi1    = 0.0
        rot_chi2    = 0.0
        rot_chi3    = 0.0

        ########################################
        # Read values
        ########################################
        if 'dx' in ele_vars:
            offset_x    = parse_expression(ele_vars['dx'])
        if 'dy' in ele_vars:
            offset_y    = parse_expression(ele_vars['dy'])
        if 'chi1' in ele_vars:
            rot_chi1    = parse_expression(ele_vars['chi1'])
        if 'chi2' in ele_vars:
            rot_chi2    = parse_expression(ele_vars['chi2'])
        if 'chi3' in ele_vars:
            rot_chi3    = parse_expression(ele_vars['chi3'])

        ########################################
        # Zero small values
        ########################################
        if isinstance(offset_x, float) and np.abs(offset_x) < TRANSFORM_SHIFT_TOL:
            offset_x = 0.0
        if isinstance(offset_y, float) and np.abs(offset_y) < TRANSFORM_SHIFT_TOL:
            offset_y = 0.0
        if isinstance(rot_chi1, float) and np.abs(rot_chi1) < TRANSFORM_ROT_TOL:
            rot_chi1 = 0.0
        if isinstance(rot_chi2, float) and np.abs(rot_chi2) < TRANSFORM_ROT_TOL:
            rot_chi2 = 0.0
        if isinstance(rot_chi3, float) and np.abs(rot_chi3) < TRANSFORM_ROT_TOL:
            rot_chi3 = 0.0

        ########################################
        # Count Transforms
        ########################################
        if offset_x != 0:
            n_transforms += 1
        if offset_y != 0:
            n_transforms += 1
        if rot_chi1 != 0:
            n_transforms += 1
        if rot_chi2 != 0:
            n_transforms += 1
        if rot_chi3 != 0:
            n_transforms += 1

        ########################################
        # Shift Transforms
        ########################################
        COORD_DX_FACTOR   = COORD_SIGNS['dx']
        COORD_DY_FACTOR   = COORD_SIGNS['dy']

        if type(offset_x) is float:
            offset_x    = COORD_DX_FACTOR * offset_x
        elif type(offset_x) is str:
            offset_x    = f"{COORD_DX_FACTOR} * {offset_x}"
        else:
            raise ValueError(f"Unsupported type for offset_x: {type(offset_x)}")
        
        if type(offset_y) is float:
            offset_y    = COORD_DY_FACTOR * offset_y
        elif type(offset_y) is str:
            offset_y    = f"{COORD_DY_FACTOR} * {offset_y}"
        else:
            raise ValueError(f"Unsupported type for offset_y: {type(offset_y)}")

        ########################################
        # Angle Transforms
        ########################################
        COORD_CHI1_FACTOR   = COORD_SIGNS['chi1']
        COORD_CHI2_FACTOR   = COORD_SIGNS['chi2']
        COORD_CHI3_FACTOR   = COORD_SIGNS['chi3']

        if type(rot_chi1) is float:
            rot_chi1    = np.rad2deg(COORD_CHI1_FACTOR * rot_chi1)
        elif type(rot_chi1) is str:
            rot_chi1    = f"{COORD_CHI1_FACTOR} * {rot_chi1} * {RAD2DEG}"
        else:
            raise ValueError(f"Unsupported type for rot_chi1: {type(rot_chi1)}")
        
        if type(rot_chi2) is float:
            rot_chi2    = np.rad2deg(COORD_CHI2_FACTOR * rot_chi2)
        elif type(rot_chi2) is str:
            rot_chi2    = f"{COORD_CHI2_FACTOR} * {rot_chi2} * {RAD2DEG}"
        else:
            raise ValueError(f"Unsupported type for rot_chi2: {type(rot_chi2)}")
        
        if type(rot_chi3) is float:
            rot_chi3    = np.rad2deg(COORD_CHI3_FACTOR * rot_chi3)
        elif type(rot_chi3) is str:
            rot_chi3    = f"{COORD_CHI3_FACTOR} * {rot_chi3} * {RAD2DEG}"
        else:
            raise ValueError(f"Unsupported type for rot_chi3: {type(rot_chi3)}")

        ########################################
        # Compound Coordinate Transformation Element
        ########################################
        if n_transforms == 0:
            # In this case, it is some transform, but we don't know what, so guess this
            environment.new(
                name    = ele_name,
                parent  = xt.XYShift)
            print(f'Warning! Coordinate transformation {ele_name} has no transformations defined, installing as XYShift')
            continue
        elif n_transforms == 1:
            if offset_x != 0:
                environment.new(
                    name    = ele_name,
                    parent  = xt.XYShift,
                    dx      = offset_x)
            if offset_y != 0:
                environment.new(
                    name    = ele_name,
                    parent  = xt.XYShift,
                    dy      = offset_y)
            if rot_chi1 != 0:
                environment.new(
                    name    = ele_name,
                    parent  = xt.YRotation,
                    angle   = rot_chi1)
            if rot_chi2 != 0:
                environment.new(
                    name    = ele_name,
                    parent  = xt.XRotation,
                    angle   = rot_chi2)
            if rot_chi3 != 0:
                environment.new(
                    name    = ele_name,
                    parent  = xt.SRotation,
                    angle   = rot_chi3)
        elif n_transforms == 2 and offset_x != 0 and offset_y != 0:
            environment.new(
                name    = ele_name,
                parent  = xt.XYShift,
                dx      = offset_x,
                dy      = offset_y)
        else:
            compound_coord_transform_components = []
            # Order from testing and agrees with the SAD manual online

            # Transverse Shifts First
            if offset_x != 0 or offset_y != 0:
                environment.new(
                    name    = f'{ele_name}_dxy',
                    parent  = xt.XYShift,
                    dx      = offset_x,
                    dy      = offset_y)
                compound_coord_transform_components.append(f'{ele_name}_dxy')
            # YRotation Second
            if rot_chi1 != 0:
                environment.new(
                    name    = f'{ele_name}_chi1',
                    parent  = xt.YRotation,
                    angle   = rot_chi1)
                compound_coord_transform_components.append(f'{ele_name}_chi1')
            # XRotation Third
            if rot_chi2 != 0:
                environment.new(
                    name    = f'{ele_name}_chi2',
                    parent  = xt.XRotation,
                    angle   = rot_chi2)
                compound_coord_transform_components.append(f'{ele_name}_chi2')
            # SRotation Fourth
            if rot_chi3 != 0:
                environment.new(
                    name    = f'{ele_name}_chi3',
                    parent  = xt.SRotation,
                    angle   = rot_chi3)
                compound_coord_transform_components.append(f'{ele_name}_chi3')

            environment.new_line(
                name        = ele_name,
                components  = compound_coord_transform_components)
            continue