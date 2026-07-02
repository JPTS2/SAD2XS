"""
(Unofficial) SAD to XSuite Converter: Element Converter
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       24-06-2026
"""

################################################################################
# Required Packages
################################################################################
import xtrack as xt
import numpy as np

from scipy.constants import c as clight
from scipy.constants import e as qe

from ..types import ConfigLike
from ..helpers import print_section_heading
from ._000_helpers import (
    parse_expression,
    get_element_misalignments,
    only_index_nonzero,
    divide_integrated_strength,
    define_strength_variable,
    values_provably_equal,
    values_provably_opposite,
)

################################################################################
# Aperture Constants
################################################################################
# Matches Xsuite's own "unconstrained" LimitRect default.
UNCONSTRAINED_APERTURE_BOUND = 1.0E10

################################################################################
# Convert all
################################################################################
def convert_elements(
        parsed_lattice_data:            dict,
        environment:                    xt.Environment,
        user_multipole_replacements:    dict | None,
        config:                         ConfigLike) -> None:
    """
    Docstring for convert_elements

    :param parsed_lattice_data: Description
    :type parsed_lattice_data: dict
    :param environment: Description
    :type environment: xt.Environment
    :param user_multipole_replacements: Description
    :type user_multipole_replacements: dict | None
    :param config: Description
    :type config: ConfigLike
    """

    ########################################
    # Get the required data
    ########################################
    parsed_elements = parsed_lattice_data["elements"]

    ########################################
    # Drifts
    ########################################
    if "drift" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Drifts", mode = "subsection")
        convert_drifts(
            parsed_elements = parsed_elements,
            environment     = environment)

    ########################################
    # Bends
    ########################################
    if "bend" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Bends", mode = "subsection")
        convert_bends(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)
        convert_correctors(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)

    ########################################
    # Quadrupoles
    ########################################
    if "quad" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Quadrupoles", mode = "subsection")
        convert_quadrupoles(
            parsed_elements = parsed_elements,
            environment     = environment)

    ########################################
    # Sextupoles
    ########################################
    if "sext" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Sextupoles", mode = "subsection")
        convert_sextupoles(
            parsed_elements = parsed_elements,
            environment     = environment)

    ########################################
    # Octupoles
    ########################################
    if "oct" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Octupoles", mode = "subsection")
        convert_octupoles(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)

    ########################################
    # Multipoles
    ########################################
    if "mult" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Multipoles", mode = "subsection")
        convert_multipoles(
            parsed_elements             = parsed_elements,
            environment                 = environment,
            user_multipole_replacements = user_multipole_replacements,
            config                      = config)

    ########################################
    # Cavities
    ########################################
    if "cavi" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Cavities", mode = "subsection")
        convert_cavities(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)

    ########################################
    # Apertures
    ########################################
    if "apert" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Apertures", mode = "subsection")
        convert_apertures(
            parsed_elements = parsed_elements,
            environment     = environment)

    ########################################
    # Solenoids
    ########################################
    if "sol" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Solenoids", mode = "subsection")
        convert_solenoids(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)

    ########################################
    # Coordinate Transformations
    ########################################
    if "coord" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Coordinate Transformations", mode = "subsection")
        convert_coordinate_transformations(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)

    ########################################
    # Markers
    ########################################
    if "mark" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Markers", mode = "subsection")
        convert_markers(
            parsed_elements = parsed_elements,
            environment     = environment)

    ########################################
    # Monitors
    ########################################
    if "moni" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Monitors", mode = "subsection")
        convert_monitors(
            parsed_elements = parsed_elements,
            environment     = environment)

    ########################################
    # Beam-Beam Interactions
    ########################################
    if "beambeam" in parsed_elements:
        if config._verbose:
            print_section_heading("Converting Beam-Beam Interactions", mode = "subsection")
        convert_beam_beam(
            parsed_elements = parsed_elements,
            environment     = environment)

################################################################################
# Convert drift
################################################################################
def convert_drifts(parsed_elements, environment):
    """
    Convert drifts from the SAD parsed data
    """

    drifts  = parsed_elements["drift"]

    for ele_name, ele_vars in drifts.items():

        ########################################
        # Assert Length
        ########################################
        if "l" in ele_vars:
            length = ele_vars["l"]
        else:
            raise ValueError(f"Drift {ele_name} missing length.")

        ########################################
        # Create Element
        ########################################
        environment.new(
            name      = ele_name,
            prototype = xt.Drift,
            length    = length)

################################################################################
# Convert Bends
################################################################################
def convert_bends(parsed_elements, environment, config):
    """
    Convert bends from the SAD parsed data
    """

    bends  = parsed_elements["bend"]

    for ele_name, ele_vars in bends.items():
        if "angle" in ele_vars:

            angle   = parse_expression(ele_vars["angle"])
            if angle == 0:
                continue

            if "l" not in ele_vars:
                k0l = parse_expression(ele_vars["angle"])
                k1l = parse_expression(ele_vars.get("k1", 0.0))
                shift_x, shift_y, rotation = get_element_misalignments(ele_vars)
                environment.new(
                    name      = ele_name,
                    prototype = xt.Multipole,
                    knl       = [k0l, k1l],
                    hxl       = k0l,
                    shift_x   = shift_x,
                    shift_y   = shift_y,
                    rot_s_rad = rotation)
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
            length          = parse_expression(ele_vars["l"])
            k0l             = parse_expression(ele_vars["angle"])
            k1l             = parse_expression(ele_vars.get("k1", 0.0))
            shift_x, shift_y, rotation  = get_element_misalignments(ele_vars)

            # Thin/zero-length bend → Multipole; hxl required for reference orbit
            # bending and dispersion generation (without it px and dpx are wrong)
            if isinstance(length, float) and np.isclose(length, 0.0):
                environment.new(
                    name      = ele_name,
                    prototype = xt.Multipole,
                    knl       = [k0l, k1l],
                    hxl       = k0l,
                    shift_x   = shift_x,
                    shift_y   = shift_y,
                    rot_s_rad = rotation)
                continue

            if "e1" in ele_vars:
                e1          = parse_expression(ele_vars["e1"])
            if "e2" in ele_vars:
                e2          = parse_expression(ele_vars["e2"])
            if "ae1" in ele_vars:
                ae1         = parse_expression(ele_vars["ae1"])
            if "ae2" in ele_vars:
                ae2         = parse_expression(ele_vars["ae2"])

            k0  = divide_integrated_strength(k0l, length)
            k1  = divide_integrated_strength(k1l, length)

            edge_entry_angle    = f"{e1} * {k0l} + {ae1}"
            edge_exit_angle     = f"{e2} * {k0l} + {ae2}"

            ########################################
            # Create variables
            ########################################
            k0  = define_strength_variable(environment, ele_name, "k0", k0)
            k1  = define_strength_variable(environment, ele_name, "k1", k1)

            ########################################
            # Create Element
            ########################################
            environment.new(
                name                = ele_name,
                prototype           = xt.Bend,
                length              = length,
                angle               = angle,
                k0                  = k0,
                k1                  = k1,
                edge_entry_angle    = edge_entry_angle,
                edge_exit_angle     = edge_exit_angle,
                shift_x             = shift_x,
                shift_y             = shift_y,
                rot_s_rad           = rotation)
            continue

################################################################################
# Convert Correctors
################################################################################
def convert_correctors(parsed_elements, environment, config):
    """
    Convert correctors from the SAD parsed data
    """

    bends  = parsed_elements["bend"]

    for ele_name, ele_vars in bends.items():

        is_corrector    = False
        if "angle" in ele_vars:
            angle   = parse_expression(ele_vars["angle"])
            if angle == 0:
                is_corrector    = True
        if "angle" not in ele_vars:
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
            if "l" in ele_vars:
                length      = parse_expression(ele_vars["l"])

            shift_x, shift_y, rotation  = get_element_misalignments(ele_vars)

            if length == 0:
                k0l = parse_expression(ele_vars.get("k0", 0.0))
                k1l = parse_expression(ele_vars.get("k1", 0.0))
                environment.new(
                    name      = ele_name,
                    prototype = xt.Multipole,
                    knl       = [k0l, k1l],
                    shift_x   = shift_x,
                    shift_y   = shift_y,
                    rot_s_rad = rotation)
                continue

            if "k0" in ele_vars:
                k0l = parse_expression(ele_vars["k0"])
            k0  = divide_integrated_strength(k0l, length)

            k1l = 0.0
            if "k1" in ele_vars:
                k1l = parse_expression(ele_vars["k1"])
            k1  = divide_integrated_strength(k1l, length)

            ########################################
            # Create variables
            ########################################
            k0  = define_strength_variable(environment, ele_name, "k0", k0)
            k1  = define_strength_variable(environment, ele_name, "k1", k1)

            ########################################
            # Create Element
            ########################################
            environment.new(
                name                = ele_name,
                prototype           = xt.Bend,
                length              = length,
                k0                  = k0,
                k1                  = k1,
                edge_entry_angle    = 0.0,
                edge_exit_angle     = 0.0,
                shift_x             = shift_x,
                shift_y             = shift_y,
                rot_s_rad           = rotation)
            continue

################################################################################
# Typed multipole helpers (QUAD / SEXT / OCT)
################################################################################
def _absorb_rotation_into_field(kl, n: int, rotation: float):
    """
    For a typed element with a pure normal field kl (skew = 0):
    if rotation (Xsuite sign, = -SAD ROTATE) is an integer multiple
    of π/(2n), rotate the field into (kl_eff, ksl_eff) and signal
    that the rotation has been absorbed (set to 0).

    n = 2 (quad), 3 (sext), 4 (oct).
    Returns (kl_eff, ksl_eff, absorbed: bool).
    """
    fundamental = np.pi / (2 * n)
    m           = rotation / fundamental
    if not np.isclose(m, round(m), atol = 1e-6):
        return kl, 0.0, False

    phase     = n * rotation                    # integer multiple of π/2
    cos_p     = int(round(np.cos(phase)))       # ∈ {-1, 0, 1}
    neg_sin_p = int(round(-np.sin(phase)))      # ∈ {-1, 0, 1}

    def _apply(factor):
        if factor == 0: return 0.0
        if factor == 1: return kl
        return -kl if isinstance(kl, (int, float)) else f"-{kl}"

    return _apply(cos_p), _apply(neg_sin_p), True

def _convert_typed_multipole(ele_name, ele_vars, environment, n, xtype, k_name):
    """
    Convert a typed multipole element (QUAD / SEXT / OCT).

    n       = 2 (quad), 3 (sext), 4 (oct)
    xtype   = xt.Quadrupole / xt.Sextupole / xt.Octupole
    k_name  = "k1" / "k2" / "k3"

    Any SAD ROTATE that is an integer multiple of π/(2n) is absorbed
    into the field components and the rotation is dropped from the
    Xsuite element.  All other rotations are preserved as rot_s_rad.
    """
    k_idx   = n - 1           # knl/ksl index
    ks_name = f"{k_name}s"    # "k1s", "k2s", "k3s"

    length = parse_expression(ele_vars.get("l", 0.0))

    ########################################
    # Thin/zero-length element → Multipole
    ########################################
    if isinstance(length, float) and np.isclose(length, 0.0):
        kl = parse_expression(ele_vars.get(k_name, 0.0))
        shift_x, shift_y, rotation = get_element_misalignments(ele_vars)
        if isinstance(rotation, float):
            kl, ksl, absorbed = _absorb_rotation_into_field(kl, n, rotation)
            if absorbed:
                rotation = 0.0
        else:
            ksl = 0.0
        knl_arr = [0.0] * (k_idx + 1)
        ksl_arr = [0.0] * (k_idx + 1)
        knl_arr[k_idx] = kl
        ksl_arr[k_idx] = ksl
        environment.new(
            name      = ele_name,
            prototype = xt.Multipole,
            knl       = knl_arr,
            ksl       = ksl_arr,
            shift_x   = shift_x,
            shift_y   = shift_y,
            rot_s_rad = rotation)
        return

    ########################################
    # Thick element
    ########################################
    kl  = 0.0
    ksl = 0.0

    shift_x, shift_y, rotation = get_element_misalignments(ele_vars)

    if k_name in ele_vars:
        kl = parse_expression(ele_vars[k_name])
        if isinstance(rotation, float):
            kl, ksl, absorbed = _absorb_rotation_into_field(kl, n, rotation)
            if absorbed:
                rotation = 0.0

    k  = divide_integrated_strength(kl,  length)
    ks = divide_integrated_strength(ksl, length)

    k  = define_strength_variable(environment, ele_name, k_name,  k)
    ks = define_strength_variable(environment, ele_name, ks_name, ks)

    environment.new(
        name        = ele_name,
        prototype   = xtype,
        length      = length,
        **{k_name: k, ks_name: ks},
        shift_x     = shift_x,
        shift_y     = shift_y,
        rot_s_rad   = rotation)

################################################################################
# Convert Quadrupoles
################################################################################
def convert_quadrupoles(parsed_elements, environment):
    """Convert quadrupoles from the SAD parsed data."""
    for ele_name, ele_vars in parsed_elements["quad"].items():
        _convert_typed_multipole(ele_name, ele_vars, environment, 2, xt.Quadrupole, "k1")

################################################################################
# Convert Sextupoles
################################################################################
def convert_sextupoles(parsed_elements, environment):
    """Convert sextupoles from the SAD parsed data."""
    for ele_name, ele_vars in parsed_elements["sext"].items():
        _convert_typed_multipole(ele_name, ele_vars, environment, 3, xt.Sextupole, "k2")

################################################################################
# Convert Octupoles
################################################################################
def convert_octupoles(parsed_elements, environment, config):
    """Convert octupoles from the SAD parsed data."""
    for ele_name, ele_vars in parsed_elements["oct"].items():
        _convert_typed_multipole(ele_name, ele_vars, environment, 4, xt.Octupole, "k3")

################################################################################
# Convert Multipoles
################################################################################
def convert_multipoles(
        parsed_elements,
        environment,
        user_multipole_replacements,
        config) -> None:
    """
    Convert multipoles from the SAD parsed data
    """

    mults   = parsed_elements["mult"]

    for ele_name, ele_vars in mults.items():

        ########################################
        # RF parameters are not supported on MULT
        ########################################
        for _rf_key in ("volt", "harm", "freq"):
            if _rf_key in ele_vars:
                raise NotImplementedError(
                    f"MULT element '{ele_name}' contains '{_rf_key}'. "
                    "RF parameters on MULT elements are not yet supported.")

        ########################################
        # Initialise parameters
        ########################################
        length      = 0.0

        ########################################
        # Read values
        ########################################
        if "l" in ele_vars:
            length      = parse_expression(ele_vars["l"])

        shift_x, shift_y, rotation  = get_element_misalignments(ele_vars)

        knl = []
        for kn in range(0, config.MAX_KNL_ORDER):
            knl.append(0.0)
            if f"k{kn}" in ele_vars:
                knl[kn] = parse_expression(ele_vars[f"k{kn}"])

        ksl = []
        for ks in range(0, config.MAX_KNL_ORDER):
            ksl.append(0.0)
            if f"sk{ks}" in ele_vars:
                ksl[ks] = parse_expression(ele_vars[f"sk{ks}"])

        ########################################
        # User Defined Multipole Replacements
        ########################################
        if user_multipole_replacements is not None:
            if any(ele_name.startswith(test_key) for test_key in user_multipole_replacements):
                replace_type    = None

                # Search the multipole replacements dict for the type of element
                for replacement in user_multipole_replacements:
                    if ele_name.startswith(replacement):
                        replace_type    = user_multipole_replacements[replacement]

                if "l" not in ele_vars or \
                    (isinstance(length, (float, int)) and abs(length) <= config.KNL_ZERO_TOL):
                    raise ValueError(
                        f"Cannot replace thin SAD multipole {ele_name} with {replace_type}.\n" + \
                        "Multipole replacement requires a non-zero length because integrated " + \
                        "strengths must be divided by length.\n" + \
                        "Remove this element from user_multipole_replacements or leave it as " + \
                        "an xt.Multipole.")

                ########################################
                # Bend Replacement (kick)
                ########################################
                if replace_type == "Bend":

                    if knl[0] != 0 and ksl[0] != 0:
                        if isinstance(knl[0], float) or isinstance(ksl[0], float):
                            k0l         = f"sqrt({knl[0]}**2 + {ksl[0]}**2)"
                            rotation    = f"{rotation} + arctan2({ksl[0]}, {knl[0]})"
                        else:
                            k0l         = np.sqrt(knl[0]**2 + ksl[0]**2)
                            rotation    = rotation + np.arctan2(ksl[0], knl[0])
                    elif knl[0] != 0:
                        k0l         = knl[0]
                    elif ksl[0] != 0:
                        k0l         = ksl[0]
                        if isinstance(rotation, float):
                            rotation    = rotation + np.pi / 2
                        else:
                            rotation    = f"{rotation} + np.pi / 2"
                    else:
                        k0l = 0.0

                    k0  = divide_integrated_strength(k0l, length)
                    k0  = define_strength_variable(environment, ele_name, "k0", k0)

                    ####################
                    # Create Element
                    ####################
                    environment.new(
                        name                = ele_name,
                        prototype           = xt.Bend,
                        length              = length,
                        k0                  = k0,
                        shift_x             = shift_x,
                        shift_y             = shift_y,
                        rot_s_rad           = rotation)
                    continue

                ########################################
                # Quadrupole Replacement
                ########################################
                elif replace_type == "Quadrupole":

                    k1l     = knl[1]
                    k1sl    = ksl[1]

                    k1  = divide_integrated_strength(k1l,  length)
                    k1s = divide_integrated_strength(k1sl, length)
                    k1  = define_strength_variable(environment, ele_name, "k1",  k1)
                    k1s = define_strength_variable(environment, ele_name, "k1s", k1s)

                    ####################
                    # Create Element
                    ####################
                    environment.new(
                        name                = ele_name,
                        prototype           = xt.Quadrupole,
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
                elif replace_type == "Sextupole":

                    k2l     = knl[2]
                    k2sl    = ksl[2]

                    k2  = divide_integrated_strength(k2l,  length)
                    k2s = divide_integrated_strength(k2sl, length)
                    k2  = define_strength_variable(environment, ele_name, "k2",  k2)
                    k2s = define_strength_variable(environment, ele_name, "k2s", k2s)

                    ####################
                    # Create Element
                    ####################
                    environment.new(
                        name                = ele_name,
                        prototype           = xt.Sextupole,
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
                elif replace_type == "Octupole":

                    k3l     = knl[3]
                    k3sl    = ksl[3]

                    k3  = divide_integrated_strength(k3l,  length)
                    k3s = divide_integrated_strength(k3sl, length)
                    k3  = define_strength_variable(environment, ele_name, "k3",  k3)
                    k3s = define_strength_variable(environment, ele_name, "k3s", k3s)

                    ####################
                    # Create Element
                    ####################
                    environment.new(
                        name                = ele_name,
                        prototype           = xt.Octupole,
                        length              = length,
                        k3                  = k3,
                        k3s                 = k3s,
                        shift_x             = shift_x,
                        shift_y             = shift_y,
                        rot_s_rad           = rotation)
                    continue
                else:
                    raise ValueError("Error: Unknown element replacement")

        ########################################
        # Automatic Simplification
        ########################################
        if config.SIMPLIFY_MULTIPOLES:

            ########################################
            # Correctors stored as multipoles
            ########################################
            if only_index_nonzero(
                    length  = length,
                    knl     = knl,
                    ksl     = ksl,
                    idx     = 0,
                    tol     = config.KNL_ZERO_TOL):

                if knl[0] != 0 and ksl[0] != 0:
                    if isinstance(knl[0], float) or isinstance(ksl[0], float):
                        k0l         = f"sqrt({knl[0]}**2 + {ksl[0]}**2)"
                        rotation    = f"{rotation} + arctan2({ksl[0]}, {knl[0]})"
                    else:
                        k0l         = np.sqrt(knl[0]**2 + ksl[0]**2)
                        rotation    = rotation + np.arctan2(ksl[0], knl[0])
                elif knl[0] != 0:
                    k0l         = knl[0]
                elif ksl[0] != 0:
                    k0l         = ksl[0]
                    if isinstance(rotation, float):
                        rotation    = rotation + np.pi / 2
                    else:
                        rotation    = f"{rotation} + np.pi / 2"
                else:
                    k0l = 0

                k0  = divide_integrated_strength(k0l, length)
                k0  = define_strength_variable(environment, ele_name, "k0", k0)

                ####################
                # Create Element
                ####################
                environment.new(
                    name                = ele_name,
                    prototype           = xt.Bend,
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
                    length  = length,
                    knl     = knl,
                    ksl     = ksl,
                    idx     = 1,
                    tol     = config.KNL_ZERO_TOL):

                k1l     = knl[1]
                k1sl    = ksl[1]

                k1  = divide_integrated_strength(k1l,  length)
                k1s = divide_integrated_strength(k1sl, length)
                k1  = define_strength_variable(environment, ele_name, "k1",  k1)
                k1s = define_strength_variable(environment, ele_name, "k1s", k1s)

                ####################
                # Create Element
                ####################
                environment.new(
                    name                = ele_name,
                    prototype           = xt.Quadrupole,
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
                    length  = length,
                    knl     = knl,
                    ksl     = ksl,
                    idx     = 2,
                    tol     = config.KNL_ZERO_TOL):

                k2l     = knl[2]
                k2sl    = ksl[2]

                k2  = divide_integrated_strength(k2l,  length)
                k2s = divide_integrated_strength(k2sl, length)
                k2  = define_strength_variable(environment, ele_name, "k2",  k2)
                k2s = define_strength_variable(environment, ele_name, "k2s", k2s)

                ####################
                # Create Element
                ####################
                environment.new(
                    name                = ele_name,
                    prototype           = xt.Sextupole,
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
                    length  = length,
                    knl     = knl,
                    ksl     = ksl,
                    idx     = 3,
                    tol     = config.KNL_ZERO_TOL):

                k3l     = knl[3]
                k3sl    = ksl[3]

                k3  = divide_integrated_strength(k3l,  length)
                k3s = divide_integrated_strength(k3sl, length)
                k3  = define_strength_variable(environment, ele_name, "k3",  k3)
                k3s = define_strength_variable(environment, ele_name, "k3s", k3s)

                ####################
                # Create Element
                ####################
                environment.new(
                    name                = ele_name,
                    prototype           = xt.Octupole,
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
            prototype   = xt.Multipole,
            _isthick    = True,
            length      = length,
            knl         = knl,
            ksl         = ksl,
            order       = config.MAX_KNL_ORDER,
            shift_x     = shift_x,
            shift_y     = shift_y,
            rot_s_rad   = rotation)
        continue

################################################################################
# Convert Cavities
################################################################################
def convert_cavities(parsed_elements, environment, config):
    """
    Convert cavities from the SAD parsed data
    """

    cavis   = parsed_elements["cavi"]

    for ele_name, ele_vars in cavis.items():

        ########################################
        # Initialise parameters
        ########################################
        length      = 0.0
        voltage     = 0.0
        freq        = 0.0
        phi         = np.pi

        ########################################
        # Read values
        ########################################
        if "l" in ele_vars:
            length      = parse_expression(ele_vars["l"])
        if "volt" in ele_vars:
            voltage = parse_expression(ele_vars["volt"])
        if "freq" in ele_vars:
            freq = parse_expression(ele_vars["freq"])
        if "phi" in ele_vars:
            phi_offset = parse_expression(ele_vars["phi"])
            if isinstance(phi_offset, float):
                phi         = np.pi + phi_offset
            elif isinstance(phi_offset, str):
                phi         = f"{np.pi} + {phi_offset}"
            else:
                raise ValueError(f"Unsupported type for phi offset: {type(phi_offset)}")

        if "harm" in ele_vars:
            harm                             = parse_expression(ele_vars["harm"])
            environment[f"harm_{ele_name}"] = harm
            harmonic                         = f"harm_{ele_name}"
            freq                             = 0
        else:
            harmonic = 0

        ########################################
        # Create variables
        ########################################
        environment[f"vol_{ele_name}"]      = voltage

        if freq != 0:
            environment[f"freq_{ele_name}"] = freq
            freq                            = f"freq_{ele_name} * (1 + fshift)"
        if phi != 0:
            environment[f"phase_{ele_name}"] = phi
            phi                              = f"phase_{ele_name}"

        ########################################
        # Create Element
        ########################################
        environment.new(
            name        = ele_name,
            prototype   = xt.Cavity,
            length      = length,
            voltage     = voltage,
            frequency   = freq,
            harmonic    = harmonic,
            phase       = phi)
        continue

################################################################################
# Convert Apertures
################################################################################
def convert_apertures(parsed_elements, environment):
    """
    Convert apertures from the SAD parsed data.

    A combined APERT with rectangular bounds that can't be proven symmetric
    is split into a LimitRect + LimitEllipse pair wrapped in a sub-line
    named after the element, mirroring convert_coordinate_transformations.
    """

    aperts  = parsed_elements["apert"]

    for ele_name, ele_vars in aperts.items():

        ########################################
        # Initialise parameters
        ########################################
        offset_x    = 0.0
        offset_y    = 0.0
        rotation    = 0.0
        a           = None
        b           = None
        dx1         = None
        dx2         = None
        dy1         = None
        dy2         = None
        aper_type   = None

        ########################################
        # Read values
        ########################################
        offset_x, offset_y, rotation = get_element_misalignments(ele_vars)
        if "ax" in ele_vars:
            a = parse_expression(ele_vars["ax"])
        if "ay" in ele_vars:
            b = parse_expression(ele_vars["ay"])
        if "dx1" in ele_vars:
            dx1 = parse_expression(ele_vars["dx1"])
        if "dx2" in ele_vars:
            dx2 = parse_expression(ele_vars["dx2"])
        if "dy1" in ele_vars:
            dy1 = parse_expression(ele_vars["dy1"])
        if "dy2" in ele_vars:
            dy2 = parse_expression(ele_vars["dy2"])

        ########################################
        # Determine type of aperture
        ########################################
        if any(v is not None for v in [dx1, dx2, dy1, dy2]) and \
                any(v is not None for v in [a, b]):
            aper_type   = "LimitRectEllipse"

            if dx1 is None and dx2 is None:
                dx1 = -1.0
                dx2 = +1.0
            elif dx1 is None and isinstance(dx2, float):
                if float(dx2) < 0:
                    dx1 = dx2
                    dx2 = +1.0
                else:
                    dx1 = -1.0
            elif dx2 is None and isinstance(dx1, float):
                if float(dx1) < 0:
                    dx2 = +1.0
                else:
                    dx2 = dx1
                    dx1 = -1.0
            elif isinstance(dx1, float) and isinstance(dx2, float):
                if dx1 > dx2:
                    tmp = dx1
                    dx1 = dx2
                    dx2 = tmp
            else:
                pass

            if dy1 is None and dy2 is None:
                dy1 = -1.0
                dy2 = +1.0
            elif dy1 is None and isinstance(dy2, float):
                if float(dy2) < 0:
                    dy1 = dy2
                    dy2 = +1.0
                else:
                    dy1 = -1.0
            elif dy2 is None and isinstance(dy1, float):
                if float(dy1) < 0:
                    dy2 = +1.0
                else:
                    dy2 = dy1
                    dy1 = -1.0
            elif isinstance(dy1, float) and isinstance(dy2, float):
                if dy1 > dy2:
                    tmp = dy1
                    dy1 = dy2
                    dy2 = tmp
            else:
                pass

            if a is None:
                a = 1.0
            if b is None:
                b = 1.0

            ########################################
            # Degenerate bounds (DX1 == DX2) leave that axis unconstrained
            ########################################
            x_degenerate = values_provably_equal(dx1, dx2)
            y_degenerate = values_provably_equal(dy1, dy2)

            if x_degenerate:
                dx1, dx2 = -UNCONSTRAINED_APERTURE_BOUND, UNCONSTRAINED_APERTURE_BOUND
            if y_degenerate:
                dy1, dy2 = -UNCONSTRAINED_APERTURE_BOUND, UNCONSTRAINED_APERTURE_BOUND

            if x_degenerate and y_degenerate:
                aper_type = "LimitEllipse"
            else:
                # LimitRectEllipse only supports bounds symmetric about its
                # own centre; split into LimitRect + LimitEllipse otherwise.
                symmetric = (
                    values_provably_opposite(dx1, dx2)
                    and values_provably_opposite(dy1, dy2))

                aper_type = "LimitRectEllipse" if symmetric else "LimitRectAndEllipse"

        elif any(v is not None for v in [dx1, dx2, dy1, dy2]):
            aper_type   = "LimitRect"

            if dx1 is None and dx2 is None:
                dx1 = -1.0
                dx2 = +1.0
            elif dx1 is None and isinstance(dx2, float):
                if float(dx2) < 0:
                    dx1 = dx2
                    dx2 = +1.0
                else:
                    dx1 = -1.0
            elif dx2 is None and isinstance(dx1, float):
                if float(dx1) < 0:
                    dx2 = +1.0
                else:
                    dx2 = dx1
                    dx1 = -1.0
            elif isinstance(dx1, float) and isinstance(dx2, float):
                if dx1 > dx2:
                    tmp = dx1
                    dx1 = dx2
                    dx2 = tmp
            else:
                # At least one is expression, cannot compare
                # This might cause issues
                pass

            if dy1 is None and dy2 is None:
                dy1 = -1.0
                dy2 = +1.0
            elif dy1 is None and isinstance(dy2, float):
                if float(dy2) < 0:
                    dy1 = dy2
                    dy2 = +1.0
                else:
                    dy1 = -1.0
            elif dy2 is None and isinstance(dy1, float):
                if float(dy1) < 0:
                    dy2 = +1.0
                else:
                    dy2 = dy1
                    dy1 = -1.0
            elif isinstance(dy1, float) and isinstance(dy2, float):
                if dy1 > dy2:
                    tmp = dy1
                    dy1 = dy2
                    dy2 = tmp
            else:
                # At least one is expression, cannot compare
                # This might cause issues
                pass

        elif any(v is not None for v in [a, b]):
            aper_type   = "LimitEllipse"

            if a is None:
                a = 1.0
            if b is None:
                b = 1.0

        else:
            raise ValueError(f"Error! Aperture {ele_name} has no valid definition.")

        ########################################
        # Create Element
        ########################################
        if aper_type == "LimitRect":
            environment.new(
                name      = ele_name,
                prototype = xt.LimitRect,
                min_x     = dx1,
                max_x     = dx2,
                min_y     = dy1,
                max_y     = dy2,
                shift_x   = offset_x,
                shift_y   = offset_y,
                rot_s_rad = rotation)
        elif aper_type == "LimitEllipse":
            environment.new(
                name      = ele_name,
                prototype = xt.LimitEllipse,
                a         = a,
                b         = b,
                shift_x   = offset_x,
                shift_y   = offset_y,
                rot_s_rad = rotation)
        elif aper_type == "LimitRectEllipse":
            environment.new(
                name      = ele_name,
                prototype = xt.LimitRectEllipse,
                max_x     = dx2,
                max_y     = dy2,
                a         = a,
                b         = b,
                shift_x   = offset_x,
                shift_y   = offset_y,
                rot_s_rad = rotation)
        elif aper_type == "LimitRectAndEllipse":
            rect_name       = f"{ele_name}_rect"
            ellipse_name    = f"{ele_name}_ellipse"
            environment.new(
                name      = rect_name,
                prototype = xt.LimitRect,
                min_x     = dx1,
                max_x     = dx2,
                min_y     = dy1,
                max_y     = dy2,
                shift_x   = offset_x,
                shift_y   = offset_y,
                rot_s_rad = rotation)
            environment.new(
                name      = ellipse_name,
                prototype = xt.LimitEllipse,
                a         = a,
                b         = b,
                shift_x   = offset_x,
                shift_y   = offset_y,
                rot_s_rad = rotation)
            environment.new_line(
                name       = ele_name,
                components = [rect_name, ellipse_name])
        else:
            raise ValueError(f"Error! Aperture {ele_name} has unsupported definition.")
        continue

################################################################################
# Convert Solenoids
################################################################################
def convert_solenoids(
        parsed_elements,
        environment,
        config) -> None:
    """
    Convert solenoids from the SAD parsed data
    """

    p0j     = environment["p0c"] * qe / clight
    brho    = p0j / (qe * environment["q0"])

    solenoids   = parsed_elements["sol"]

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
        bz  = parse_expression(ele_vars["bz"])
        ks  = bz / brho

        if "bound" in ele_vars:
            bound   = True
        else:
            bound   = False

        if "geo" in ele_vars:
            geo     = True
        else:
            geo     = False

        # Based on testing, when geo, use the dpx, dpy etc
        if "dx" in ele_vars:
            offset_x    = parse_expression(ele_vars["dx"])
        if "dy" in ele_vars:
            offset_y    = parse_expression(ele_vars["dy"])
        if "dz" in ele_vars:
            offset_z    = parse_expression(ele_vars["dz"])
        if "dpx" in ele_vars:
            rot_chi1    = parse_expression(ele_vars["dpx"])
        if "dpy" in ele_vars:
            rot_chi2    = parse_expression(ele_vars["dpy"])

        if not geo:
            # Then use the other rotations
            if ("dpx" not in ele_vars) and ("chi1" in ele_vars):
                rot_chi1    = parse_expression(ele_vars["chi1"])
            if ("dpy" not in ele_vars) and ("chi2" in ele_vars):
                rot_chi2    = parse_expression(ele_vars["chi2"])
            if ("dpz" not in ele_vars) and ("chi3" in ele_vars):
                rot_chi3    = parse_expression(ele_vars["chi3"])

        # Should not have dz in geo sol
        if geo and "dz" in ele_vars:
            if config._verbose:
                print(
                    f"Warning! Solenoid {ele_name} is a geo solenoid "
                    "but with dz defined: ignoring dz")
            offset_z = 0.0

        ########################################
        # Zero small values
        ########################################
        if isinstance(offset_x, float) and np.abs(offset_x) < config.TRANSFORM_SHIFT_TOL:
            offset_x = 0.0
        if isinstance(offset_y, float) and np.abs(offset_y) < config.TRANSFORM_SHIFT_TOL:
            offset_y = 0.0
        if isinstance(offset_z, float) and np.abs(offset_z) < config.TRANSFORM_SHIFT_TOL:
            offset_z = 0.0
        if isinstance(rot_chi1, float) and np.abs(rot_chi1) < config.TRANSFORM_ROT_TOL:
            rot_chi1 = 0.0
        if isinstance(rot_chi2, float) and np.abs(rot_chi2) < config.TRANSFORM_ROT_TOL:
            rot_chi2 = 0.0
        if isinstance(rot_chi3, float) and np.abs(rot_chi3) < config.TRANSFORM_ROT_TOL:
            rot_chi3 = 0.0

        ########################################
        # Shift Transforms
        ########################################
        sol_dx_factor   = -1 * config.COORD_SIGNS["dx"]
        sol_dy_factor   = -1 * config.COORD_SIGNS["dy"]
        sol_dz_factor   = -1

        if isinstance(offset_x, float):
            offset_x    = sol_dx_factor * offset_x
        elif isinstance(offset_x, str):
            offset_x    = f"{sol_dx_factor} * {offset_x}"
        else:
            raise ValueError(f"Unsupported type for offset_x: {type(offset_x)}")

        if isinstance(offset_y, float):
            offset_y    = sol_dy_factor * offset_y
        elif isinstance(offset_y, str):
            offset_y    = f"{sol_dy_factor} * {offset_y}"
        else:
            raise ValueError(f"Unsupported type for offset_y: {type(offset_y)}")

        if isinstance(offset_z, float):
            offset_z    = sol_dz_factor * offset_z
        elif isinstance(offset_z, str):
            offset_z    = f"{sol_dz_factor} * {offset_z}"
        else:
            raise ValueError(f"Unsupported type for offset_z: {type(offset_z)}")

        ########################################
        # Angle Transforms
        ########################################
        sol_chi1_factor = -1 * config.COORD_SIGNS["chi1"]
        sol_chi2_factor = -1 * config.COORD_SIGNS["chi2"]
        sol_chi3_factor = -1 * config.COORD_SIGNS["chi3"]

        if isinstance(rot_chi1, float):
            rot_chi1    = sol_chi1_factor * rot_chi1
        elif isinstance(rot_chi1, str):
            rot_chi1    = f"{sol_chi1_factor} * {rot_chi1}"
        else:
            raise ValueError(f"Unsupported type for rot_chi1: {type(rot_chi1)}")

        if isinstance(rot_chi2, float):
            rot_chi2    = sol_chi2_factor * rot_chi2
        elif isinstance(rot_chi2, str):
            rot_chi2    = f"{sol_chi2_factor} * {rot_chi2}"
        else:
            raise ValueError(f"Unsupported type for rot_chi2: {type(rot_chi2)}")

        if isinstance(rot_chi3, float):
            rot_chi3    = sol_chi3_factor * rot_chi3
        elif isinstance(rot_chi3, str):
            rot_chi3    = f"{sol_chi3_factor} * {rot_chi3}"
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
                name      = f"{ele_name}_bound",
                prototype = xt.UniformSolenoid,
                ks        = ks)

            environment.new(
                name      = f"{ele_name}_dxy",
                prototype = xt.Translation,
                shift_x   = offset_x,
                shift_y   = offset_y)

            environment.new(
                name       = f"{ele_name}_dz",
                prototype  = xt.TimeDelay,
                shift_zeta = offset_z)

            environment.new(
                name        = f"{ele_name}_rot",
                prototype   = xt.Rotation,
                rot_y_rad   = rot_chi1,
                rot_x_rad   = rot_chi2,
                rot_s_rad   = rot_chi3)

            # No ds shift: is ruins the survey
            # The ds difference is because SAD takes dz into account with s

            ########################################
            # Order the elements (reordered later)
            ########################################
            compound_solenoid_components = [
                f"{ele_name}_bound",
                f"{ele_name}_dxy",
                f"{ele_name}_dz",
                f"{ele_name}_rot"]
            environment.new_line(
                name        = ele_name,
                components  = compound_solenoid_components)
            continue
        else:
            environment.new(
                name      = f"{ele_name}",
                prototype = xt.UniformSolenoid,
                ks        = ks)
            continue

################################################################################
# Convert Markers
################################################################################
def convert_markers(parsed_elements, environment):
    """
    Convert markers from the SAD parsed data
    """

    markers   = parsed_elements["mark"]

    for ele_name, _ in markers.items():

        ########################################
        # Create Element
        ########################################
        environment.new(
                name      = ele_name,
                prototype = xt.Marker)
        continue

################################################################################
# Convert Monitors
################################################################################
def convert_monitors(parsed_elements, environment):
    """
    Convert monitors from the SAD parsed data
    """

    monitors   = parsed_elements["moni"]

    for ele_name, _ in monitors.items():

        ########################################
        # Create Element
        ########################################
        environment.new(
                name      = ele_name,
                prototype = xt.Marker)
        continue

################################################################################
# Convert Beam-Beam Interactions
################################################################################
def convert_beam_beam(parsed_elements, environment):
    """
    Convert beam-beam interactions from the SAD parsed data
    """

    beam_beams   = parsed_elements["beambeam"]

    for ele_name, _ in beam_beams.items():

        ########################################
        # Create Element
        ########################################
        environment.new(
                name      = ele_name,
                prototype = xt.Marker)
        continue

################################################################################
# Convert Coordinate Transformations
################################################################################
def convert_coordinate_transformations(
        parsed_elements,
        environment,
        config) -> None:
    """
    Convert coordinate transformations from the SAD parsed data
    """

    coord_transforms   = parsed_elements["coord"]
    for ele_name, ele_vars in coord_transforms.items():

        ########################################
        # Initialise parameters
        ########################################
        n_transforms    = 0

        dir_flag    = False

        offset_x    = 0.0
        offset_y    = 0.0
        rot_chi1    = 0.0
        rot_chi2    = 0.0
        rot_chi3    = 0.0

        ########################################
        # Read values
        ########################################
        if "dir" in ele_vars:
            dir_val = parse_expression(ele_vars["dir"])
            if dir_val != 0.0:
                dir_flag    = True

        if "dx" in ele_vars:
            offset_x    = parse_expression(ele_vars["dx"])
        if "dy" in ele_vars:
            offset_y    = parse_expression(ele_vars["dy"])
        if "chi1" in ele_vars:
            rot_chi1    = parse_expression(ele_vars["chi1"])
        if "chi2" in ele_vars:
            rot_chi2    = parse_expression(ele_vars["chi2"])
        if "chi3" in ele_vars:
            rot_chi3    = parse_expression(ele_vars["chi3"])

        ########################################
        # Zero small values
        ########################################
        if isinstance(offset_x, float) and np.abs(offset_x) < config.TRANSFORM_SHIFT_TOL:
            offset_x = 0.0
        if isinstance(offset_y, float) and np.abs(offset_y) < config.TRANSFORM_SHIFT_TOL:
            offset_y = 0.0
        if isinstance(rot_chi1, float) and np.abs(rot_chi1) < config.TRANSFORM_ROT_TOL:
            rot_chi1 = 0.0
        if isinstance(rot_chi2, float) and np.abs(rot_chi2) < config.TRANSFORM_ROT_TOL:
            rot_chi2 = 0.0
        if isinstance(rot_chi3, float) and np.abs(rot_chi3) < config.TRANSFORM_ROT_TOL:
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
        if dir_flag:
            coord_dx_factor   = -1 * config.COORD_SIGNS["dx"]
            coord_dy_factor   = +1 * config.COORD_SIGNS["dy"]
        else:
            coord_dx_factor   = +1 * config.COORD_SIGNS["dx"]
            coord_dy_factor   = +1 * config.COORD_SIGNS["dy"]

        if isinstance(offset_x, float):
            offset_x    = coord_dx_factor * offset_x
        elif isinstance(offset_x, str):
            offset_x    = f"{coord_dx_factor} * {offset_x}"
        else:
            raise ValueError(f"Unsupported type for offset_x: {type(offset_x)}")

        if isinstance(offset_y, float):
            offset_y    = coord_dy_factor * offset_y
        elif isinstance(offset_y, str):
            offset_y    = f"{coord_dy_factor} * {offset_y}"
        else:
            raise ValueError(f"Unsupported type for offset_y: {type(offset_y)}")

        ########################################
        # Angle Transforms
        ########################################
        if dir_flag:
            coord_chi1_factor   = +1 * config.COORD_SIGNS["chi1"]
            coord_chi2_factor   = -1 * config.COORD_SIGNS["chi2"]
            coord_chi3_factor   = +1 * config.COORD_SIGNS["chi3"]
        else:
            coord_chi1_factor   = +1 * config.COORD_SIGNS["chi1"]
            coord_chi2_factor   = +1 * config.COORD_SIGNS["chi2"]
            coord_chi3_factor   = +1 * config.COORD_SIGNS["chi3"]

        if isinstance(rot_chi1, float):
            rot_chi1    = coord_chi1_factor * rot_chi1
        elif isinstance(rot_chi1, str):
            rot_chi1    = f"{coord_chi1_factor} * {rot_chi1}"
        else:
            raise ValueError(f"Unsupported type for rot_chi1: {type(rot_chi1)}")

        if isinstance(rot_chi2, float):
            rot_chi2    = coord_chi2_factor * rot_chi2
        elif isinstance(rot_chi2, str):
            rot_chi2    = f"{coord_chi2_factor} * {rot_chi2}"
        else:
            raise ValueError(f"Unsupported type for rot_chi2: {type(rot_chi2)}")

        if isinstance(rot_chi3, float):
            rot_chi3    = coord_chi3_factor * rot_chi3
        elif isinstance(rot_chi3, str):
            rot_chi3    = f"{coord_chi3_factor} * {rot_chi3}"
        else:
            raise ValueError(f"Unsupported type for rot_chi3: {type(rot_chi3)}")

        ########################################
        # Compound Coordinate Transformation Element
        ########################################
        if n_transforms == 0:
            # In this case, it is some transform, but we don"t know what, so guess this
            environment.new(
                name      = ele_name,
                prototype = xt.Translation)
            if config._verbose:
                print(
                    f"Warning! Coordinate transformation {ele_name} has no transformations defined, " +\
                    "installing as Translation")
            continue
        elif n_transforms == 1:
            if offset_x != 0:
                environment.new(
                    name      = ele_name,
                    prototype = xt.Translation,
                    shift_x   = offset_x)
            if offset_y != 0:
                environment.new(
                    name      = ele_name,
                    prototype = xt.Translation,
                    shift_y   = offset_y)
            if rot_chi1 != 0:
                environment.new(
                    name        = ele_name,
                    prototype   = xt.Rotation,
                    rot_y_rad   = rot_chi1)
            if rot_chi2 != 0:
                environment.new(
                    name        = ele_name,
                    prototype   = xt.Rotation,
                    rot_x_rad   = rot_chi2)
            if rot_chi3 != 0:
                environment.new(
                    name        = ele_name,
                    prototype   = xt.Rotation,
                    rot_s_rad   = rot_chi3)
        elif n_transforms == 2 and offset_x != 0 and offset_y != 0:
            environment.new(
                name      = ele_name,
                prototype = xt.Translation,
                shift_x   = offset_x,
                shift_y   = offset_y)
        else:
            compound_coord_transform_components = []
            # Order from testing and agrees with the SAD manual online

            if dir_flag:
                # chi1 (rot_y_rad) First
                if rot_chi1 != 0:
                    environment.new(
                        name        = f"{ele_name}_chi1",
                        prototype   = xt.Rotation,
                        rot_y_rad   = rot_chi1)
                    compound_coord_transform_components.append(f"{ele_name}_chi1")
                # chi2 (rot_x_rad) Second
                if rot_chi2 != 0:
                    environment.new(
                        name        = f"{ele_name}_chi2",
                        prototype   = xt.Rotation,
                        rot_x_rad   = rot_chi2)
                    compound_coord_transform_components.append(f"{ele_name}_chi2")
                # chi3 (rot_s_rad) Third
                if rot_chi3 != 0:
                    environment.new(
                        name        = f"{ele_name}_chi3",
                        prototype   = xt.Rotation,
                        rot_s_rad   = rot_chi3)
                    compound_coord_transform_components.append(f"{ele_name}_chi3")
                # Transverse Shifts Last
                if offset_x != 0 or offset_y != 0:
                    environment.new(
                        name      = f"{ele_name}_dxy",
                        prototype = xt.Translation,
                        shift_x   = offset_x,
                        shift_y   = offset_y)
                    compound_coord_transform_components.append(f"{ele_name}_dxy")

                environment.new_line(
                    name        = ele_name,
                    components  = compound_coord_transform_components)
                continue
            else:
                # Transverse Shifts First
                if offset_x != 0 or offset_y != 0:
                    environment.new(
                        name      = f"{ele_name}_dxy",
                        prototype = xt.Translation,
                        shift_x   = offset_x,
                        shift_y   = offset_y)
                    compound_coord_transform_components.append(f"{ele_name}_dxy")
                # chi1 (rot_y_rad) Second
                if rot_chi1 != 0:
                    environment.new(
                        name        = f"{ele_name}_chi1",
                        prototype   = xt.Rotation,
                        rot_y_rad   = rot_chi1)
                    compound_coord_transform_components.append(f"{ele_name}_chi1")
                # chi2 (rot_x_rad) Third
                if rot_chi2 != 0:
                    environment.new(
                        name        = f"{ele_name}_chi2",
                        prototype   = xt.Rotation,
                        rot_x_rad   = rot_chi2)
                    compound_coord_transform_components.append(f"{ele_name}_chi2")
                # chi3 (rot_s_rad) Fourth
                if rot_chi3 != 0:
                    environment.new(
                        name        = f"{ele_name}_chi3",
                        prototype   = xt.Rotation,
                        rot_s_rad   = rot_chi3)
                    compound_coord_transform_components.append(f"{ele_name}_chi3")

                environment.new_line(
                    name        = ele_name,
                    components  = compound_coord_transform_components)
                continue
