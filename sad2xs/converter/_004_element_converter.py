"""
================================================================================
Element Converter
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
import logging

import xtrack as xt
import numpy as np

from scipy.constants import c as clight
from scipy.constants import e as qe

from ..types import ConfigLike
from ..helpers import log_section_heading
from ._000_helpers import (
    parse_expression,
    get_element_misalignments,
    is_effectively_zero,
    only_index_nonzero,
    divide_integrated_strength,
    define_strength_variable,
    combine_k0_sk0,
    parse_rf_parameters,
    values_provably_equal,
    values_provably_opposite,
)

logger  = logging.getLogger(__name__)

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
    Convert every parsed SAD element into the Xsuite environment.

    Dispatches to one converter function per element type present in
    `parsed_lattice_data`, in a fixed order (drifts, bends/correctors,
    quadrupoles, sextupoles, octupoles, multipoles, cavities, apertures,
    solenoids, coordinate transformations, markers, monitors, beam-beam,
    maps). After conversion, warns once if the lattice contains any
    Cavity elements, since SAD2XS does not model SAD's transverse
    RF-focusing kick.

    Parameters
    ----------
    parsed_lattice_data : dict
        Parsed lattice data, as returned by `parse_sad_file`.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
    user_multipole_replacements : dict or None
        Per-element overrides controlling how specific MULT elements
        convert (see `convert_multipoles`).
    config : ConfigLike
        Converter configuration (tolerances, multipole order, etc.).
    """

    ########################################
    # Get the required data
    ########################################
    parsed_elements = parsed_lattice_data["elements"]

    ########################################
    # Drifts
    ########################################
    if "drift" in parsed_elements:
        log_section_heading("Converting Drifts", mode = "section")
        convert_drifts(
            parsed_elements = parsed_elements,
            environment     = environment)
        logger.info(f"Converted {len(parsed_elements['drift'])} drift definitions")

    ########################################
    # Bends
    ########################################
    if "bend" in parsed_elements:
        log_section_heading("Converting Bends", mode = "section")
        convert_bends(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)
        convert_correctors(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)
        logger.info(
            f"Converted {len(parsed_elements['bend'])} bend definitions "
            "(bends and correctors)")

    ########################################
    # Quadrupoles
    ########################################
    if "quad" in parsed_elements:
        log_section_heading("Converting Quadrupoles", mode = "section")
        convert_quadrupoles(
            parsed_elements = parsed_elements,
            environment     = environment)
        logger.info(f"Converted {len(parsed_elements['quad'])} quadrupole definitions")

    ########################################
    # Sextupoles
    ########################################
    if "sext" in parsed_elements:
        log_section_heading("Converting Sextupoles", mode = "section")
        convert_sextupoles(
            parsed_elements = parsed_elements,
            environment     = environment)
        logger.info(f"Converted {len(parsed_elements['sext'])} sextupole definitions")

    ########################################
    # Octupoles
    ########################################
    if "oct" in parsed_elements:
        log_section_heading("Converting Octupoles", mode = "section")
        convert_octupoles(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)
        logger.info(f"Converted {len(parsed_elements['oct'])} octupole definitions")

    ########################################
    # Multipoles
    ########################################
    if "mult" in parsed_elements:
        log_section_heading("Converting Multipoles", mode = "section")
        convert_multipoles(
            parsed_elements             = parsed_elements,
            environment                 = environment,
            user_multipole_replacements = user_multipole_replacements,
            config                      = config)
        logger.info(f"Converted {len(parsed_elements['mult'])} multipole definitions")

    ########################################
    # Cavities
    ########################################
    if "cavi" in parsed_elements:
        log_section_heading("Converting Cavities", mode = "section")
        convert_cavities(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)
        logger.info(f"Converted {len(parsed_elements['cavi'])} cavity definitions")

    ########################################
    # Apertures
    ########################################
    if "apert" in parsed_elements:
        log_section_heading("Converting Apertures", mode = "section")
        convert_apertures(
            parsed_elements = parsed_elements,
            environment     = environment)
        logger.info(f"Converted {len(parsed_elements['apert'])} aperture definitions")

    ########################################
    # Solenoids
    ########################################
    if "sol" in parsed_elements:
        log_section_heading("Converting Solenoids", mode = "section")
        convert_solenoids(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)
        logger.info(f"Converted {len(parsed_elements['sol'])} solenoid definitions")

    ########################################
    # Coordinate Transformations
    ########################################
    if "coord" in parsed_elements:
        log_section_heading("Converting Coordinate Transformations", mode = "section")
        convert_coordinate_transformations(
            parsed_elements = parsed_elements,
            environment     = environment,
            config          = config)
        logger.info(
            f"Converted {len(parsed_elements['coord'])} coordinate "
            "transformation definitions")

    ########################################
    # Markers
    ########################################
    if "mark" in parsed_elements:
        log_section_heading("Converting Markers", mode = "section")
        convert_markers(
            parsed_elements = parsed_elements,
            environment     = environment)
        logger.info(f"Converted {len(parsed_elements['mark'])} marker definitions")

    ########################################
    # Monitors
    ########################################
    if "moni" in parsed_elements:
        log_section_heading("Converting Monitors", mode = "section")
        convert_monitors(
            parsed_elements = parsed_elements,
            environment     = environment)
        logger.info(f"Converted {len(parsed_elements['moni'])} monitor definitions")

    ########################################
    # Beam-Beam Interactions
    ########################################
    if "beambeam" in parsed_elements:
        log_section_heading("Converting Beam-Beam Interactions", mode = "section")
        convert_beam_beam(
            parsed_elements = parsed_elements,
            environment     = environment)
        logger.info(
            f"Converted {len(parsed_elements['beambeam'])} beam-beam definitions")

    ########################################
    # Maps
    ########################################
    if "map" in parsed_elements:
        log_section_heading("Converting Maps", mode = "section")
        convert_maps(
            parsed_elements = parsed_elements,
            environment     = environment)
        logger.info(f"Converted {len(parsed_elements['map'])} map definitions")

    ########################################
    # RF Focusing Check
    ########################################
    log_section_heading("Checking for Unmodelled RF Focusing", mode = "section")
    cavity_names = [
        name for name, ele in environment.elements.items()
        if isinstance(ele, xt.Cavity)]
    if cavity_names:
        logger.warning(
            "This lattice contains "
            f"{len(cavity_names)} cavity element(s). SAD2XS's Xsuite Cavity "
            "elements do not model SAD's transverse RF-focusing kick -- see "
            "docs/sad-behaviour.md for details.")
        logger.debug(
            "Cavity elements: "
            + ", ".join(cavity_names))

################################################################################
# Convert drift
################################################################################
def convert_drifts(parsed_elements, environment):
    """
    Convert SAD DRIFT elements into Xsuite Drift elements.

    Warns once for the whole lattice if any drift has a negative
    length (SAD2XS converts these as-is, but they commonly indicate
    overlapping element geometry or survey rounding in the source
    lattice, and are likely to break tracking/Twiss or offset-marker
    insertion).

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data (element
        type -> {name: {param: value}}).
    environment : xt.Environment
        The Xsuite environment to create converted elements into.

    Raises
    ------
    ValueError
        If a DRIFT element has no length.
    """

    drifts  = parsed_elements["drift"]
    negative_length_drifts = []

    for ele_name, ele_vars in drifts.items():

        ########################################
        # Assert Length
        ########################################
        if "l" in ele_vars:
            length = ele_vars["l"]
        else:
            raise ValueError(f"Drift {ele_name} missing length.")

        parsed_length = parse_expression(length)
        if isinstance(parsed_length, (int, float)) and parsed_length < 0:
            negative_length_drifts.append(ele_name)

        ########################################
        # Create Element
        ########################################
        environment.new(
            name      = ele_name,
            prototype = xt.Drift,
            length    = length)

    if negative_length_drifts:
        logger.warning(
            "This lattice contains "
            f"{len(negative_length_drifts)} drift(s) with negative length. "
            "SAD2XS converts negative-length drifts as-is: they commonly "
            "arise from overlapping element geometry or survey rounding in "
            "the source SAD lattice, and are likely to break Xsuite "
            "tracking/twiss or downstream offset-marker insertion.")
        logger.debug(
            "Negative-length drifts: "
            + ", ".join(negative_length_drifts))

################################################################################
# Convert Bends
################################################################################
def _canonicalize_dipole_rotation(rotation):
    """
    Return the SAD-origin canonical dipole rotation and field sign.

    Xsuite Bend has one dipole field direction plus an element
    rotation. For SAD-origin dipoles, equivalent pi and -pi/2 rotations
    are represented by a field sign flip instead; vertical dipoles use
    +pi/2. Symbolic (deferred) rotations are passed through unchanged
    with a field sign of +1, since their runtime value is not known at
    conversion time.

    Parameters
    ----------
    rotation : float or str
        The element's rotation, in radians (Xsuite sign convention),
        or a deferred expression string.

    Returns
    -------
    tuple of (float or str, int)
        `(canonical_rotation, field_sign)`, where `field_sign` is +1 or
        -1 and should multiply the dipole field strength (e.g. k0l).
    """
    if not isinstance(rotation, (int, float, np.number)):
        return rotation, +1

    if np.isclose(rotation, 0.0):
        return 0.0, +1
    if np.isclose(abs(rotation), np.pi):
        return 0.0, -1
    if np.isclose(rotation, np.pi / 2):
        return np.pi / 2, +1
    if np.isclose(rotation, -np.pi / 2):
        return np.pi / 2, -1

    return rotation, +1


def _has_nonzero_offset(shift_x, shift_y, tol) -> bool:
    """
    True if either misalignment is symbolic or numerically nonzero.

    A symbolic (deferred) value is treated conservatively as possibly
    nonzero, since its runtime value is not known at conversion time.

    Parameters
    ----------
    shift_x : float or str
        Horizontal misalignment, or a deferred expression string.
    shift_y : float or str
        Vertical misalignment, or a deferred expression string.
    tol : float
        Absolute tolerance below which a numeric value counts as zero.

    Returns
    -------
    bool
        True if `shift_x` or `shift_y` is non-numeric or exceeds `tol`.
    """
    return not (
        is_effectively_zero(shift_x, tol)
        and is_effectively_zero(shift_y, tol))


def _bend_fringe_edge_kwargs(ele_vars, config) -> dict:
    """
    Derive Xsuite Bend edge fint/hgap kwargs from a SAD BEND's fringe
    parameters.

    Returns {} if fringe import is disabled
    (`config._import_sad_bend_fringes`) or the SAD FRINGE flag gates
    both edges off. FRINGE = -1 disables the entry edge only, FRINGE =
    -2 disables the exit edge only. The closed form (edge_*_fint =
    F1 + FB1/FB2, edge_*_hgap = 1/12) and the FRINGE gating convention
    are documented in docs/sad-behaviour.md.

    Parameters
    ----------
    ele_vars : dict
        The BEND element's parsed parameters.
    config : ConfigLike
        Converter configuration; only `_import_sad_bend_fringes` is
        used.

    Returns
    -------
    dict
        Keyword arguments for `xt.Bend` (`edge_entry_fint`,
        `edge_entry_hgap`, `edge_exit_fint`, `edge_exit_hgap`, as
        applicable), or {} if fringe import does not apply.

    Raises
    ------
    ValueError
        If FRINGE, F1, FB1, or FB2 is a deferred expression rather
        than a concrete number.
    """
    if not config._import_sad_bend_fringes:
        return {}

    fringe = parse_expression(ele_vars.get("fringe", 0.0))
    if fringe == 0.0:
        return {}
    if not isinstance(fringe, float):
        raise ValueError(
            f"FRINGE must be a concrete number to import fringe fields, "
            f"got a deferred expression: {fringe!r}.")

    entry_active = fringe != -2.0
    exit_active  = fringe != -1.0

    f1  = parse_expression(ele_vars.get("f1", 0.0))
    fb1 = parse_expression(ele_vars.get("fb1", 0.0))
    fb2 = parse_expression(ele_vars.get("fb2", 0.0))
    for name, value in (("F1", f1), ("FB1", fb1), ("FB2", fb2)):
        if not isinstance(value, float):
            raise ValueError(
                f"{name} must be a concrete number to import fringe "
                f"fields, got a deferred expression: {value!r}.")

    kwargs = {}
    if entry_active:
        kwargs["edge_entry_fint"] = f1 + fb1
        kwargs["edge_entry_hgap"] = 1 / 12
    if exit_active:
        kwargs["edge_exit_fint"] = f1 + fb2
        kwargs["edge_exit_hgap"] = 1 / 12
    return kwargs


def convert_bends(parsed_elements, environment, config):
    """
    Convert SAD BEND elements with ANGLE != 0 into Xsuite Bend or
    Multipole elements.

    A thin (L=0 or no L) bend converts to a Multipole with `hxl` set to
    k0l, so it still bends the reference orbit and generates
    dispersion. A thick bend converts to an `xt.Bend`, with
    E1/E2/AE1/AE2 combined into edge_entry_angle/edge_exit_angle and,
    if `config._import_sad_bend_fringes` is set, F1/FB1/FB2 imported as
    native Xsuite edge fringe parameters (see
    `_bend_fringe_edge_kwargs`). BEND elements with ANGLE == 0 or no
    ANGLE are correctors, handled by `convert_correctors` instead.

    Any rotation that SAD encodes as a field-sign flip (pi or -pi/2,
    see `_canonicalize_dipole_rotation`) is absorbed into k0/k1 rather
    than left as an element rotation.

    Warns once for the whole lattice if any ANGLE != 0 bend also has a
    nonzero DX/DY: SAD2XS cannot reproduce SAD's reference-orbit
    convention for a displaced curved element (the converted lattice
    keeps the design curvature fixed regardless of the shift).

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
    config : ConfigLike
        Converter configuration (misalignment tolerances, fringe-import
        flag).
    """

    bends  = parsed_elements["bend"]

    # Bends with ANGLE != 0 and a nonzero DX/DY: SAD2XS cannot reproduce
    # SAD's reference-orbit convention for a displaced curved element.
    # Reported once for the whole lattice below, not once per element.
    offset_bends = []

    for ele_name, ele_vars in bends.items():
        if "angle" in ele_vars:

            angle   = parse_expression(ele_vars["angle"])
            if angle == 0:
                continue

            if "l" not in ele_vars:
                k0l = parse_expression(ele_vars["angle"])
                k1l = parse_expression(ele_vars.get("k1", 0.0))
                shift_x, shift_y, rotation = get_element_misalignments(ele_vars)
                if _has_nonzero_offset(shift_x, shift_y, config.TRANSFORM_SHIFT_TOL):
                    offset_bends.append(ele_name)
                rotation, field_sign = _canonicalize_dipole_rotation(rotation)
                if field_sign == -1:
                    k0l = -k0l if isinstance(k0l, (int, float, np.number)) else f"-({k0l})"
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
            if _has_nonzero_offset(shift_x, shift_y, config.TRANSFORM_SHIFT_TOL):
                offset_bends.append(ele_name)

            # Thin/zero-length bend → Multipole; hxl required for reference orbit
            # bending and dispersion generation (without it px and dpx are wrong)
            if isinstance(length, float) and np.isclose(length, 0.0):
                rotation, field_sign = _canonicalize_dipole_rotation(rotation)
                if field_sign == -1:
                    k0l = -k0l if isinstance(k0l, (int, float, np.number)) else f"-({k0l})"
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
            rotation, field_sign = _canonicalize_dipole_rotation(rotation)
            if field_sign == -1:
                if isinstance(angle, (int, float, np.number)):
                    angle = -angle
                else:
                    angle = f"-({angle})"
                if isinstance(k0, (int, float, np.number)):
                    k0 = -k0
                else:
                    k0 = f"-({k0})"
                edge_entry_angle    = f"-({edge_entry_angle})"
                edge_exit_angle     = f"-({edge_exit_angle})"

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
                rot_s_rad           = rotation,
                **_bend_fringe_edge_kwargs(ele_vars, config))
            continue

    if offset_bends:
        logger.warning(
            "This lattice contains "
            f"{len(offset_bends)} bend(s) with ANGLE != 0 and a nonzero "
            "DX/DY. SAD2XS cannot reproduce SAD's reference-orbit "
            "convention for a displaced curved element: the converted "
            "lattice keeps the design curvature fixed regardless of the "
            "shift, while SAD reconstructs the reference orbit through the "
            "displaced element.")
        logger.debug(
            "Offset bends: "
            + ", ".join(offset_bends))

################################################################################
# Convert Correctors
################################################################################
def convert_correctors(parsed_elements, environment, config):
    """
    Convert SAD BEND elements with ANGLE == 0 (or no ANGLE) into Xsuite
    corrector Bend/Multipole elements.

    A thin (L=0) corrector converts to a Multipole carrying K0/K1 as a
    pure kick. A thick corrector converts to an `xt.Bend` with angle
    implicitly zero (design curvature h=0), K0/K1 as its field
    strengths, and both edge angles fixed at zero. If
    `config._import_sad_bend_fringes` is set, the same fringe-import
    path as `convert_bends` applies (see `_bend_fringe_edge_kwargs`).

    BEND elements with a nonzero ANGLE are real bends, handled by
    `convert_bends` instead; this function is a no-op for those.

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
    config : ConfigLike
        Converter configuration (fringe-import flag).
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
                rotation, field_sign = _canonicalize_dipole_rotation(rotation)
                if field_sign == -1:
                    k0l = -k0l if isinstance(k0l, (int, float, np.number)) else f"-({k0l})"
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
            rotation, field_sign = _canonicalize_dipole_rotation(rotation)
            if field_sign == -1:
                k0 = -k0 if isinstance(k0, (int, float, np.number)) else f"-({k0})"

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
                rot_s_rad           = rotation,
                **_bend_fringe_edge_kwargs(ele_vars, config))
            continue

################################################################################
# Typed multipole helpers (QUAD / SEXT / OCT)
################################################################################
def _absorb_rotation_into_field(kl, n: int, rotation: float):
    """
    Absorb a typed multipole's rotation into its field, where possible.

    For a typed element (QUAD/SEXT/OCT, n = 2/3/4) with a pure normal
    field `kl` (skew = 0): if `rotation` (Xsuite sign, = -SAD ROTATE)
    is an integer multiple of pi/(2n), the field has that many-fold
    rotational symmetry and the rotation can be represented exactly as
    a (kl_eff, ksl_eff) pair instead of an element rotation.

    Parameters
    ----------
    kl : float or str
        The element's integrated normal-field strength (skew assumed
        zero on input).
    n : int
        The multipole order: 2 (quad), 3 (sext), or 4 (oct).
    rotation : float
        The element's rotation, in radians (Xsuite sign convention).

    Returns
    -------
    tuple of (float or str, float or str, bool)
        `(kl_eff, ksl_eff, absorbed)`. If `absorbed` is False, `kl_eff`
        equals the input `kl`, `ksl_eff` is 0.0, and `rotation` should
        be kept as the element's rotation.
    """
    fundamental = np.pi / (2 * n)
    m           = rotation / fundamental
    if not np.isclose(m, round(m), atol = 1e-6):
        return kl, 0.0, False

    phase     = n * rotation                    # integer multiple of π/2
    cos_p     = int(round(np.cos(phase)))       # ∈ {-1, 0, 1}
    neg_sin_p = int(round(-np.sin(phase)))      # ∈ {-1, 0, 1}

    def _scaled_kl(sign_factor):
        """
        Scale `kl` by a {-1, 0, 1} coefficient from the rotation phase.

        Parameters
        ----------
        sign_factor : int
            One of -1, 0, or 1 (a rounded cos/sin of the rotation
            phase).

        Returns
        -------
        float or str
            0.0 if `sign_factor` is 0, `kl` unchanged if +1, or the
            negation of `kl` if -1.
        """
        if sign_factor == 0: return 0.0
        if sign_factor == 1: return kl
        return -kl if isinstance(kl, (int, float)) else f"-{kl}"

    return _scaled_kl(cos_p), _scaled_kl(neg_sin_p), True

def _convert_typed_multipole(ele_name, ele_vars, environment, n, xtype, k_name):
    """
    Convert a typed multipole element (QUAD, SEXT, or OCT).

    A thin (L=0 or no L) element converts to a Multipole carrying the
    integrated strength at index `n - 1`. A thick element converts to
    `xtype` (`xt.Quadrupole`/`Sextupole`/`Octupole`) with the strength
    divided by length and registered as a live optics variable (see
    `define_strength_variable`).

    Any SAD ROTATE that is an integer multiple of pi/(2n) is absorbed
    into the field components (see `_absorb_rotation_into_field`) and
    the rotation is dropped from the Xsuite element; all other
    rotations are preserved as `rot_s_rad`.

    Parameters
    ----------
    ele_name : str
        The element's name.
    ele_vars : dict
        The element's parsed parameters.
    environment : xt.Environment
        The Xsuite environment to create the converted element into.
    n : int
        The multipole order: 2 (quad), 3 (sext), or 4 (oct).
    xtype : type
        The Xsuite element class for the thick case: `xt.Quadrupole`,
        `xt.Sextupole`, or `xt.Octupole`.
    k_name : str
        The SAD/Xsuite normal-strength parameter name: "k1", "k2", or
        "k3".
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
                logger.debug(
                    f"Absorbed rotation {rotation} rad of {ele_name} "
                    "into its field components")
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
                logger.debug(
                    f"Absorbed rotation {rotation} rad of {ele_name} "
                    "into its field components")
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
    """
    Convert SAD QUAD elements into Xsuite Quadrupole/Multipole elements.

    Thin wrapper around `_convert_typed_multipole` for order n=2
    (strength parameter "k1").

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
    """
    for ele_name, ele_vars in parsed_elements["quad"].items():
        _convert_typed_multipole(ele_name, ele_vars, environment, 2, xt.Quadrupole, "k1")

################################################################################
# Convert Sextupoles
################################################################################
def convert_sextupoles(parsed_elements, environment):
    """
    Convert SAD SEXT elements into Xsuite Sextupole/Multipole elements.

    Thin wrapper around `_convert_typed_multipole` for order n=3
    (strength parameter "k2").

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
    """
    for ele_name, ele_vars in parsed_elements["sext"].items():
        _convert_typed_multipole(ele_name, ele_vars, environment, 3, xt.Sextupole, "k2")

################################################################################
# Convert Octupoles
################################################################################
def convert_octupoles(parsed_elements, environment, config):
    """
    Convert SAD OCT elements into Xsuite Octupole/Multipole elements.

    Thin wrapper around `_convert_typed_multipole` for order n=4
    (strength parameter "k3").

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
    config : ConfigLike
        Accepted for interface consistency with the other element-type
        converters; not used directly by this function.
    """
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
    Convert SAD MULT elements into Xsuite elements.

    Each MULT is handled by the first applicable case, in order:

    1. RF-carrying (VOLT/HARM/FREQ present): sliced into alternating
       Multipole/Cavity element pairs (`config.N_SLICES_MULT_RF`
       slices, 1 if thin), wrapped in a sub-line named after the
       element, since Xsuite has no single element combining a
       multipole kick with RF.
    2. User-replaced (`user_multipole_replacements`, by name prefix):
       converted to the requested single-purpose element (Bend,
       Quadrupole, Sextupole, or Octupole), using only the field order
       that element type supports.
    3. Auto-simplified (`config.SIMPLIFY_MULTIPOLES`): if only one
       field order (k0/sk0, k1/sk1, k2/sk2, or k3/sk3) is non-zero,
       converted to the corresponding single-purpose element.
    4. Otherwise: converted to a true Xsuite Multipole carrying every
       order up to `config.MAX_KNL_ORDER`.

    Cases 2-3 both canonicalize any k0/sk0-only rotation the same way
    `convert_bends` does (see `_canonicalize_dipole_rotation`), and
    both require a non-zero length (integrated strengths must be
    divided by length).

    Warns once for the whole lattice if any MULT was auto-simplified
    to a Bend/corrector: Xsuite's bend fringe model does not exactly
    reproduce SAD's MULT dipole fringe convention (residual optics
    differences scale as O(theta^4)).

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
    user_multipole_replacements : dict or None
        Maps a name prefix to a replacement element type ("Bend",
        "Quadrupole", "Sextupole", or "Octupole"); any MULT whose name
        starts with a listed prefix is converted to that type instead
        of a generic Multipole.
    config : ConfigLike
        Converter configuration (`MAX_KNL_ORDER`, `SIMPLIFY_MULTIPOLES`,
        `KNL_ZERO_TOL`, `N_SLICES_MULT_RF`).

    Raises
    ------
    ValueError
        If a thin (zero-length) MULT is targeted by
        `user_multipole_replacements`, or if an unknown replacement
        type is given.
    """

    mults   = parsed_elements["mult"]
    dipole_simplified_mults = []

    for ele_name, ele_vars in mults.items():

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
        # RF Parameters (VOLT/HARM/FREQ) -- interleaved Multipole/Cavity slices
        ########################################
        if any(_rf_key in ele_vars for _rf_key in ("volt", "harm", "freq")):
            # RF parameters take priority over both SIMPLIFY_MULTIPOLES and
            # user_multipole_replacements, the same way they already take
            # priority over SIMPLIFY_MULTIPOLES below -- an RF-carrying MULT
            # is never a candidate for single-purpose-element replacement.
            voltage, freq, harmonic, phi = parse_rf_parameters(
                environment = environment,
                ele_name    = ele_name,
                ele_vars    = ele_vars)

            n_slices = 1 if is_effectively_zero(length, config.KNL_ZERO_TOL) \
                else config.N_SLICES_MULT_RF

            # NOTE: slices are always uniform (each an equal fraction of the
            # total), so a reversed line reference to this element is a true
            # no-op today -- _005_line_converter.py's generated-subline path
            # already preserves component order, and reused Multipole/Cavity
            # elements are direction-symmetric. This would need dedicated
            # reorder logic (there is no existing one to reuse -- bound
            # solenoids solve reversal differently, via a post-hoc scan of
            # the flattened line, not a generated-subline reversal) only if
            # slicing is ever made non-uniform.
            components = []
            for i in range(n_slices):
                mult_name = f"{ele_name}_mult_{i}"
                cavi_name = f"{ele_name}_cavi_{i}"

                environment.new(
                    name        = mult_name,
                    prototype   = xt.Multipole,
                    _isthick    = True,
                    length      = divide_integrated_strength(length, n_slices),
                    knl         = [divide_integrated_strength(k, n_slices) for k in knl],
                    ksl         = [divide_integrated_strength(k, n_slices) for k in ksl],
                    order       = config.MAX_KNL_ORDER,
                    shift_x     = shift_x,
                    shift_y     = shift_y,
                    rot_s_rad   = rotation)

                environment.new(
                    name        = cavi_name,
                    prototype   = xt.Cavity,
                    length      = 0.0,
                    voltage     = divide_integrated_strength(voltage, n_slices),
                    frequency   = freq,
                    harmonic    = harmonic,
                    phase       = phi)

                components += [mult_name, cavi_name]

            environment.new_line(name = ele_name, components = components)
            continue

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

                logger.info(
                    f"Replaced multipole {ele_name} with {replace_type} "
                    "(user_multipole_replacements)")

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

                    k0l, rotation           = combine_k0_sk0(knl[0], ksl[0], rotation)
                    rotation, field_sign    = _canonicalize_dipole_rotation(rotation)
                    if field_sign == -1:
                        k0l = -k0l if isinstance(k0l, (int, float, np.number)) else f"-({k0l})"

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
                    raise ValueError(
                        f"Unknown replacement type '{replace_type}' for "
                        f"multipole {ele_name} in user_multipole_replacements. "
                        "Supported: 'Bend', 'Quadrupole', 'Sextupole', "
                        "'Octupole'.")

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

                dipole_simplified_mults.append(ele_name)

                k0l, rotation           = combine_k0_sk0(knl[0], ksl[0], rotation)
                rotation, field_sign    = _canonicalize_dipole_rotation(rotation)
                if field_sign == -1:
                    k0l = -k0l if isinstance(k0l, (int, float, np.number)) else f"-({k0l})"

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
                logger.debug(
                    f"Simplified multipole {ele_name} to corrector "
                    "(SIMPLIFY_MULTIPOLES: only k0/sk0 non-zero)")
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
                logger.debug(
                    f"Simplified multipole {ele_name} to Quadrupole "
                    "(SIMPLIFY_MULTIPOLES: only k1/sk1 non-zero)")
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
                logger.debug(
                    f"Simplified multipole {ele_name} to Sextupole "
                    "(SIMPLIFY_MULTIPOLES: only k2/sk2 non-zero)")
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
                logger.debug(
                    f"Simplified multipole {ele_name} to Octupole "
                    "(SIMPLIFY_MULTIPOLES: only k3/sk3 non-zero)")
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

    if dipole_simplified_mults:
        logger.warning(
            "SAD MULT elements with only K0/SK0 were converted to Xsuite "
            "Bend/corrector elements. Xsuite's bend fringe model does not "
            "exactly reproduce SAD's MULT dipole fringe convention; residual "
            "optics differences scale as O(theta^4).")
        logger.debug(
            "Dipole-only MULT elements converted to Bend/corrector elements: "
            + ", ".join(dipole_simplified_mults))

################################################################################
# Convert Cavities
################################################################################
def convert_cavities(parsed_elements, environment, config):
    """
    Convert SAD CAVI elements into Xsuite Cavity elements.

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
    config : ConfigLike
        Converter configuration; forwarded to `parse_rf_parameters` for
        VOLT/HARM/FREQ handling.
    """

    cavis   = parsed_elements["cavi"]

    for ele_name, ele_vars in cavis.items():

        ########################################
        # Initialise parameters
        ########################################
        length      = 0.0

        ########################################
        # Read values
        ########################################
        if "l" in ele_vars:
            length      = parse_expression(ele_vars["l"])

        voltage, freq, harmonic, phi = parse_rf_parameters(
            environment = environment,
            ele_name    = ele_name,
            ele_vars    = ele_vars)

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
    Convert SAD APERT elements into Xsuite aperture elements.

    Chooses LimitRect, LimitEllipse, or LimitRectEllipse depending on
    which of AX/AY/DX1/DX2/DY1/DY2 are present. A combined APERT with
    rectangular bounds that can't be proven symmetric about its own
    centre is split into a LimitRect + LimitEllipse pair wrapped in a
    sub-line named after the element (mirroring
    `convert_coordinate_transformations`), since `xt.LimitRectEllipse`
    only supports symmetric bounds.

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.

    Raises
    ------
    ValueError
        If an APERT element has no recognised bound parameters, or its
        derived aperture type is unsupported.
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
    Convert SAD SOL elements into Xsuite UniformSolenoid elements.

    An unbound SOL (no BOUND) is a plain UniformSolenoid with
    ks = BZ / brho. A bound SOL (BOUND present) additionally carries
    geometric offset/rotation, and is installed as a sub-line of
    [UniformSolenoid, Translation (DX/DY), TimeDelay (DZ), Rotation
    (CHI1/CHI2/CHI3)] -- reordered later in the pipeline (see
    `sad2xs.converter._006_solenoid_converter`). Offset/rotation
    sources depend on GEO: when GEO is set, DPX/DPY (not CHI1/CHI2) are
    used, and DZ is invalid.

    Warns once for the whole lattice if any solenoid lacks DISFRIN=1:
    SAD2XS does not model the SAD solenoid fringe kick, so the
    converted lattice behaves as if DISFRIN=1 had been set everywhere.

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
        Must already have "p0c" and "q0" registered (used to compute
        brho).
    config : ConfigLike
        Converter configuration (misalignment tolerances, coordinate
        sign conventions).

    Raises
    ------
    ValueError
        If a computed offset/rotation value is neither a float nor a
        deferred-expression string.
    """

    # environment["q0"] must be the imported charge here, not a
    # reverse_charge_sign-corrected one -- see docs/line-reversals.md.
    p0j     = environment["p0c"] * qe / clight
    brho    = p0j / (qe * environment["q0"])

    solenoids   = parsed_elements["sol"]

    ########################################
    # Track solenoids missing DISFRIN=1
    ########################################
    # Reported once for the whole lattice below, not once per element.
    no_disfrin_solenoids = []

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
        # BZ is optional in SAD: an unset SOL element is a pure geometry/
        # boundary marker with no field, i.e. BZ = 0.
        bz  = parse_expression(ele_vars["bz"]) if "bz" in ele_vars else 0.0
        ks  = bz / brho

        # The parser stores numeric literals as floats: DISFRIN = 1 -> 1.0
        if ele_vars.get("disfrin") != 1.0:
            no_disfrin_solenoids.append(ele_name)

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
            logger.warning(
                f"Solenoid {ele_name} is a geo solenoid "
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
            raise ValueError(
                f"Unsupported type for offset_x of {ele_name}: {type(offset_x)}")

        if isinstance(offset_y, float):
            offset_y    = sol_dy_factor * offset_y
        elif isinstance(offset_y, str):
            offset_y    = f"{sol_dy_factor} * {offset_y}"
        else:
            raise ValueError(
                f"Unsupported type for offset_y of {ele_name}: {type(offset_y)}")

        if isinstance(offset_z, float):
            offset_z    = sol_dz_factor * offset_z
        elif isinstance(offset_z, str):
            offset_z    = f"{sol_dz_factor} * {offset_z}"
        else:
            raise ValueError(
                f"Unsupported type for offset_z of {ele_name}: {type(offset_z)}")

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
            raise ValueError(
                f"Unsupported type for rot_chi1 of {ele_name}: {type(rot_chi1)}")

        if isinstance(rot_chi2, float):
            rot_chi2    = sol_chi2_factor * rot_chi2
        elif isinstance(rot_chi2, str):
            rot_chi2    = f"{sol_chi2_factor} * {rot_chi2}"
        else:
            raise ValueError(
                f"Unsupported type for rot_chi2 of {ele_name}: {type(rot_chi2)}")

        if isinstance(rot_chi3, float):
            rot_chi3    = sol_chi3_factor * rot_chi3
        elif isinstance(rot_chi3, str):
            rot_chi3    = f"{sol_chi3_factor} * {rot_chi3}"
        else:
            raise ValueError(
                f"Unsupported type for rot_chi3 of {ele_name}: {type(rot_chi3)}")

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

    if no_disfrin_solenoids:
        logger.warning(
            "This lattice contains "
            f"{len(no_disfrin_solenoids)} solenoid(s) without DISFRIN=1 set. "
            "SAD2XS does not model the SAD solenoid fringe kick: the "
            "converted lattice will behave as if DISFRIN=1 had been set "
            "for every solenoid, regardless of the source SAD file.")
        logger.debug(
            "Solenoids without DISFRIN=1: "
            + ", ".join(no_disfrin_solenoids))

################################################################################
# Convert Markers
################################################################################
def convert_markers(parsed_elements, environment):
    """
    Convert SAD MARK elements into Xsuite Marker elements.

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
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
    Convert SAD MONI elements into Xsuite Marker elements.

    SAD2XS does not model beam-position-monitor behaviour; MONI
    elements are installed as zero-length, transparent Markers.

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
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
    Convert SAD beam-beam elements into Xsuite Marker elements.

    SAD2XS does not model beam-beam interactions; these elements are
    installed as zero-length, transparent Markers.

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
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
# Convert Maps
################################################################################
def convert_maps(parsed_elements, environment):
    """
    Convert SAD MAP elements into Xsuite Marker elements.

    Only empty MAP elements are understood; a MAP with parameters is
    not supported since its physical meaning is not known. Installed as
    zero-length, transparent Markers.

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.

    Raises
    ------
    ValueError
        If a MAP element has any non-empty parameters.
    """

    maps   = parsed_elements["map"]

    for ele_name, ele_vars in maps.items():

        ########################################
        # Reject Parametrised Maps
        ########################################
        if ele_vars:
            raise ValueError(
                f"MAP element '{ele_name}' has non-empty parameters "
                f"{ele_vars!r}. SAD2XS only supports MAP elements with no "
                "parameters (installed as Xsuite Markers); MAP elements "
                "with parameters are not understood and not supported.")

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
    Convert SAD COORD elements into Xsuite Translation/Rotation
    elements.

    Chooses the simplest representation for the number of active
    transforms: a single Translation/Rotation for one active
    transform, a combined Translation for DX+DY only, or -- for
    anything more complex -- a sub-line of individually-named
    Translation/Rotation elements in the order CHI1, CHI2, CHI3, then
    DX/DY (or the reverse, DX/DY first, if DIR is set), per the SAD
    manual's stated convention. A COORD with no recognised transform at
    all is installed as a no-op Translation, with a warning.

    Parameters
    ----------
    parsed_elements : dict
        The "elements" sub-dictionary of parsed lattice data.
    environment : xt.Environment
        The Xsuite environment to create converted elements into.
    config : ConfigLike
        Converter configuration (misalignment tolerances, coordinate
        sign conventions).

    Raises
    ------
    ValueError
        If a computed offset/rotation value is neither a float nor a
        deferred-expression string.
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
            raise ValueError(
                f"Unsupported type for offset_x of {ele_name}: {type(offset_x)}")

        if isinstance(offset_y, float):
            offset_y    = coord_dy_factor * offset_y
        elif isinstance(offset_y, str):
            offset_y    = f"{coord_dy_factor} * {offset_y}"
        else:
            raise ValueError(
                f"Unsupported type for offset_y of {ele_name}: {type(offset_y)}")

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
            raise ValueError(
                f"Unsupported type for rot_chi1 of {ele_name}: {type(rot_chi1)}")

        if isinstance(rot_chi2, float):
            rot_chi2    = coord_chi2_factor * rot_chi2
        elif isinstance(rot_chi2, str):
            rot_chi2    = f"{coord_chi2_factor} * {rot_chi2}"
        else:
            raise ValueError(
                f"Unsupported type for rot_chi2 of {ele_name}: {type(rot_chi2)}")

        if isinstance(rot_chi3, float):
            rot_chi3    = coord_chi3_factor * rot_chi3
        elif isinstance(rot_chi3, str):
            rot_chi3    = f"{coord_chi3_factor} * {rot_chi3}"
        else:
            raise ValueError(
                f"Unsupported type for rot_chi3 of {ele_name}: {type(rot_chi3)}")

        ########################################
        # Compound Coordinate Transformation Element
        ########################################
        if n_transforms == 0:
            # In this case, it is some transform, but we don"t know what, so guess this
            environment.new(
                name      = ele_name,
                prototype = xt.Translation)
            logger.warning(
                f"Coordinate transformation {ele_name} has no transformations "
                "defined, installing as Translation")
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
