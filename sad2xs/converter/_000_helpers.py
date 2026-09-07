"""
================================================================================
Converter Helper Functions
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-03
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import logging

import numpy as np
import xtrack as xt

from ..types import ConfigLike, SadValue

logger = logging.getLogger(__name__)

################################################################################
# Expression Parsing
################################################################################
def parse_expression(expression: int | float | str) -> SadValue:
    """
    Convert a SAD expression value to a Python float or a stripped
    string.

    Parameters
    ----------
    expression : int, float, or str
        A parsed SAD parameter value: `int`/`float` pass through as a
        float; `str` is returned as a float if numeric, otherwise as
        a stripped deferred-expression string (with `log(` mapped to
        `log10(` and `ln(` mapped to `log(`, matching SAD's own
        logarithm naming).

    Returns
    -------
    float or str
        The parsed value.

    Raises
    ------
    TypeError
        If `expression` is not an int, float, or str.
    """
    if isinstance(expression, float):
        return expression
    elif isinstance(expression, int):
        return float(expression)
    elif isinstance(expression, str):
        expression_stripped = expression.strip()
        try:
            return float(expression_stripped)
        except ValueError:
            expression_stripped = expression_stripped.replace("log(", "log10(")
            expression_stripped = expression_stripped.replace("ln(",  "log(")
            return expression_stripped
    else:
        raise TypeError(
            f"Unsupported type: {type(expression)}. Expected str, int, or float.")

########################################
# Negate SAD Value
########################################
def negate_sad_value(value: SadValue) -> SadValue:
    """
    Negate a numeric SAD value or deferred expression.

    Parameters
    ----------
    value : float or str
        Numeric value or expression to negate.

    Returns
    -------
    float or str
        Negated number, or a parenthesised negated expression.
    """
    return f"-({value})" if isinstance(value, str) else -value

################################################################################
# Element Length Validation
################################################################################
def validate_element_lengths(
        parsed_elements:    dict[str, dict],
        environment:        xt.Environment,
        minimum_length:     float) -> None:
    """
    Reject concrete nonzero lengths below the conversion precision.

    SAD distinguishes an exactly zero (thin) element from every nonzero
    (thick) element. Enforcing a minimum resolved length prevents different
    converter paths from making inconsistent tolerance-based decisions near
    zero. Length expressions are evaluated at their initial Xsuite values.

    Parameters
    ----------
    parsed_elements : dict
        Parsed SAD elements, grouped by element type and name.
    environment : xt.Environment
        Environment containing the converted SAD variables used to evaluate
        length expressions.
    minimum_length : float
        Smallest permitted absolute nonzero length, in metres.

    Raises
    ------
    ValueError
        If `minimum_length` is not positive, or a concrete element length is
        nonzero with an absolute value smaller than `minimum_length`.
    """
    if minimum_length <= 0.0:
        raise ValueError(
            "MAGNET_LENGTH_PRECISION must be greater than zero, got "
            f"{minimum_length!r}.")

    for element_type, elements in parsed_elements.items():
        for element_name, parameters in elements.items():
            if "l" not in parameters:
                continue

            length = parse_expression(parameters["l"])
            if isinstance(length, str):
                length = environment.eval(length)
            if length == 0.0:
                continue
            if abs(length) < minimum_length:
                raise ValueError(
                    f"{element_type.upper()} element {element_name!r} has "
                    f"nonzero length {length:.17g} m, below "
                    f"MAGNET_LENGTH_PRECISION={minimum_length:.17g} m. "
                    "Use exactly zero for a thin element or increase its "
                    "absolute length.")

################################################################################
# Zero Check
################################################################################
def is_effectively_zero(val: SadValue, tol: float = 1E-12) -> bool:
    """
    Return True if `val` is numerically zero within `tol`.

    String expressions cannot be evaluated and are always treated as
    non-zero.

    Parameters
    ----------
    val : float or str
        The value to check.
    tol : float, optional
        Absolute tolerance. Defaults to 1E-12.

    Returns
    -------
    bool
        True if `val` is numeric and `abs(val) <= tol`.
    """
    try:
        return abs(float(val)) <= tol
    except (ValueError, TypeError):
        return False

################################################################################
# Provable Equality Check
################################################################################
def values_provably_equal(val_1: SadValue, val_2: SadValue, tol: float = 1E-9) -> bool:
    """
    Return True if two SAD-parsed values are numerically equal within
    `tol`, or the exact same deferred expression string.

    Parameters
    ----------
    val_1 : float or str
        First value.
    val_2 : float or str
        Second value.
    tol : float, optional
        Absolute tolerance for the numeric case. Defaults to 1E-9.

    Returns
    -------
    bool
        True if both are numeric and equal within `tol`, or both are
        strings and equal after stripping whitespace.
    """
    if isinstance(val_1, (int, float)) and isinstance(val_2, (int, float)):
        return abs(float(val_1) - float(val_2)) <= tol
    if isinstance(val_1, str) and isinstance(val_2, str):
        return val_1.strip() == val_2.strip()
    return False

def values_provably_opposite(val_1: SadValue, val_2: SadValue, tol: float = 1E-9) -> bool:
    """
    Return True if two SAD-parsed values are numerically equal and
    opposite in sign within `tol`, or one deferred expression is a
    literal "-" prefix of the other.

    Parameters
    ----------
    val_1 : float or str
        First value.
    val_2 : float or str
        Second value.
    tol : float, optional
        Absolute tolerance for the numeric case. Defaults to 1E-9.

    Returns
    -------
    bool
        True if both are numeric and sum to ~0 within `tol`, or one
        string is `"-"` + the other after stripping whitespace.
    """
    if isinstance(val_1, (int, float)) and isinstance(val_2, (int, float)):
        return abs(float(val_1) + float(val_2)) <= tol
    if isinstance(val_1, str) and isinstance(val_2, str):
        v1, v2 = val_1.strip(), val_2.strip()
        return v1 == f"-{v2}" or v2 == f"-{v1}"
    return False

################################################################################
# Element Parameter Helpers
################################################################################

########################################
# Element Length
########################################
def get_element_length(ele_vars: dict[str, SadValue]) -> SadValue:
    """
    Extract element length from a parsed SAD parameter dict.

    Parameters
    ----------
    ele_vars : dict
        The element's parsed parameters.

    Returns
    -------
    float or str
        `ele_vars["l"]` (parsed via `parse_expression`), or 0.0 if
        "l" is absent.
    """
    return parse_expression(ele_vars.get("l", 0.0))

########################################
# Integrated Element Strength
########################################
def get_element_integrated_strength(
        ele_vars:   dict[str, SadValue],
        key:        str,
        default:    float               = 0.0) -> SadValue:
    """
    Extract a strength parameter from a parsed SAD parameter dict.

    Parameters
    ----------
    ele_vars : dict
        The element's parsed parameters.
    key : str
        The strength parameter's key (e.g. "k1", "angle").
    default : float, optional
        Value to return if `key` is absent. Defaults to 0.0.

    Returns
    -------
    float or str
        `ele_vars[key]` (parsed via `parse_expression`), or `default`
        if `key` is absent.
    """
    return parse_expression(ele_vars.get(key, default))

########################################
# Divide Integrated Strength by Length
########################################
def divide_integrated_strength(kl: SadValue, length: SadValue) -> SadValue:
    """
    Divide integrated strength `kl` by element `length` to obtain a
    per-unit-length strength (e.g. k1l / l -> k1).

    Both `kl` and `length` may be a float or a string expression
    (deferred variable). Callers must ensure `length` is non-zero;
    this function is only valid for thick elements, so the thin/thick
    split must occur before calling it.

    Parameters
    ----------
    kl : float or str
        Integrated strength.
    length : float or str
        Element length.

    Returns
    -------
    float or str
        0.0 if `kl` is exactly zero; a float if both inputs are
        numeric; otherwise a string expression `"{kl} / {length}"`.
    """
    if isinstance(kl, (int, float)) and kl == 0.0:
        return 0.0
    if isinstance(kl, (int, float)) and isinstance(length, (int, float)):
        return kl / length
    return f"{kl} / {length}"

########################################
# Define Strength Variable in Environment
########################################
def define_strength_variable(
        environment:    xt.Environment,
        ele_name:       str,
        k_name:         str,
        k_value:        SadValue) -> SadValue:
    """
    Register a per-unit-length strength in the xtrack environment and
    return a reference expression to it.

    Parameters
    ----------
    environment : xt.Environment
        The Xsuite environment to register the variable into.
    ele_name : str
        The element's name.
    k_name : str
        The strength parameter's name (e.g. "k1", "k0").
    k_value : float or str
        The strength value.

    Returns
    -------
    float or str
        If `k_value` is non-zero: stores it as
        `environment[`{k_name}_{ele_name}`]` and returns that key
        string, so it can be passed to `environment.new()`. If
        `k_value` is zero: returns it unchanged without touching the
        environment.
    """
    if k_value != 0:
        var_name = f"{k_name}_{ele_name}"
        environment[var_name] = k_value
        return var_name
    return k_value

################################################################################
# Parse RF Parameters (VOLT / FREQ / PHI / HARM)
################################################################################
def parse_rf_parameters(
        environment:    xt.Environment,
        ele_name:       str,
        ele_vars:       dict[str, SadValue]) -> tuple[float, SadValue, SadValue, SadValue]:
    """
    Parse SAD VOLT/FREQ/PHI/HARM into Xsuite Cavity-ready values.

    HARM and FREQ are mutually exclusive in SAD; if HARM is present it
    takes priority and FREQ is discarded (harmonic tracks Xsuite's
    own revolution-frequency derivation). FREQ and PHI, when
    non-zero, are registered as deferred environment variables
    (freq_{name}, phase_{name}) so they can be tuned after
    conversion; the returned frequency expression also multiplies by
    `(1 + fshift)`, SAD's global FSHIFT frequency-shift knob (parsed
    from the lattice file's FSHIFT global, defaulting to 0.0 -- see
    `parse_sad_file`). VOLT is always registered as vol_{name} for the
    same reason, but is returned as a literal value, matching how it
    is passed directly to xt.Cavity today.

    Parameters
    ----------
    environment : xt.Environment
        The Xsuite environment to register RF variables into.
    ele_name : str
        The element's name.
    ele_vars : dict
        The element's parsed parameters.

    Returns
    -------
    tuple of (float, float or str, float or str, float or str)
        `(voltage, frequency, harmonic, phase)`, ready to pass to
        `environment.new(prototype=xt.Cavity, ...)`.

    Raises
    ------
    ValueError
        If PHI is present but not a float or str.
    """
    voltage = 0.0
    freq    = 0.0
    phi     = np.pi

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
            raise ValueError(
                f"Unsupported type for phi offset of {ele_name}: "
                f"{type(phi_offset)}")

    if "harm" in ele_vars:
        harm                             = parse_expression(ele_vars["harm"])
        environment[f"harm_{ele_name}"] = harm
        harmonic                         = f"harm_{ele_name}"
        freq                             = 0
    else:
        harmonic = 0

    environment[f"vol_{ele_name}"]      = voltage

    if freq != 0:
        environment[f"freq_{ele_name}"] = freq
        freq                            = f"freq_{ele_name} * (1 + fshift)"
    if phi != 0:
        environment[f"phase_{ele_name}"] = phi
        phi                              = f"phase_{ele_name}"

    return voltage, freq, harmonic, phi

################################################################################
# Combine K0/SK0 Dipole Orders
################################################################################
def combine_k0_sk0(
        knl0:       SadValue,
        ksl0:       SadValue,
        rotation:   SadValue) -> tuple[SadValue, SadValue]:
    """
    Combine SAD MULT integrated K0/SK0 into a single (k0l, rotation)
    pair.

    `knl0`, `ksl0`, and `rotation` may each independently be a float
    or a string expression (deferred variable). A string expression
    is built whenever any of the three is deferred, since a mixed
    numeric/deferred computation cannot be evaluated directly;
    otherwise the combination is computed numerically.

    Parameters
    ----------
    knl0 : float or str
        Integrated normal dipole strength (K0L).
    ksl0 : float or str
        Integrated skew dipole strength (SK0L).
    rotation : float or str
        The element's rotation, in radians (Xsuite sign convention).

    Returns
    -------
    tuple of (float or str, float or str)
        `(k0l, rotation)`: the combined dipole strength and the
        rotation needed to orient it (adjusted from the input
        `rotation` when only `ksl0` is non-zero).
    """
    if knl0 != 0 and ksl0 != 0:
        if isinstance(knl0, str) or isinstance(ksl0, str) or isinstance(rotation, str):
            k0l      = f"sqrt({knl0}**2 + {ksl0}**2)"
            rotation = f"{rotation} + atan2(-({ksl0}), {knl0})"
        else:
            k0l      = np.sqrt(knl0**2 + ksl0**2)
            rotation = rotation + np.arctan2(-ksl0, knl0)
    elif knl0 != 0:
        k0l = knl0
    elif ksl0 != 0:
        k0l = ksl0
        if isinstance(rotation, str):
            rotation = f"{rotation} - {np.pi / 2}"
        else:
            rotation = rotation - np.pi / 2
    else:
        k0l = 0.0

    return k0l, rotation

################################################################################
# Canonical Dipole Rotation
################################################################################
def canonicalize_dipole_rotation(rotation: SadValue) -> tuple[SadValue, int]:
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

################################################################################
# Compute Element Misalignments
################################################################################
def get_element_misalignments(
        ele_vars:               dict[str, SadValue],
        rotation_correction:    float               = 0.0) -> tuple[SadValue, SadValue, SadValue]:
    """
    Extract transverse misalignments and rotation from a parsed SAD
    element parameter dict.

    Rotations in SAD are opposite in sign to Xsuite; the returned
    rotation is already negated. `rotation_correction` (radians) is
    added after negation.

    Parameters
    ----------
    ele_vars : dict
        The element's parsed parameters.
    rotation_correction : float, optional
        Radians added to the negated rotation. Defaults to 0.0.

    Returns
    -------
    tuple of (float or str, float or str, float or str)
        `(shift_x, shift_y, rotation)`. Each value is a float or a
        string expression depending on whether the SAD parameter was
        numeric or deferred.

    Raises
    ------
    TypeError
        If ROTATE parses to something other than a float, int, or
        str.
    """
    shift_x  = parse_expression(ele_vars.get("dx",     0.0))
    shift_y  = parse_expression(ele_vars.get("dy",     0.0))
    rotation = parse_expression(ele_vars.get("rotate", 0.0))

    if isinstance(rotation, str):
        rotation = f"-({rotation}) + {rotation_correction}"
    elif isinstance(rotation, (float, int)):
        rotation = -rotation + rotation_correction
    else:
        raise TypeError(f"Unexpected type for rotation: {type(rotation)}")

    return shift_x, shift_y, rotation

################################################################################
# Multipole Order Check
################################################################################
def only_index_nonzero(
        length: SadValue,
        knl:    list[SadValue],
        ksl:    list[SadValue],
        idx:    int,
        tol:    float) -> bool:
    """
    Check whether only one multipole order (index `idx`) is active.

    Parameters
    ----------
    length : float or str
        Element length. A string length is assumed non-zero.
    knl : list
        Integrated normal-strength values.
    ksl : list
        Integrated skew-strength values.
    idx : int
        The multipole order index that is allowed to be non-zero.
    tol : float
        Absolute tolerance for zero integrated strength (see
        `is_effectively_zero`). Length uses exact-zero semantics.

    Returns
    -------
    bool
        True if: `length` is non-zero (when numeric); every entry in
        `knl`/`ksl` except at `idx` is zero within `tol` (a
        non-numeric string value counts as non-zero); and at least
        one of `knl[idx]`/`ksl[idx]` is non-zero within `tol`.
    """
    if isinstance(length, (int, float)) and length == 0.0:
        return False

    max_len = max(len(knl), len(ksl))
    for arr in (knl, ksl):
        padded = arr + [0] * (max_len - len(arr))
        for i, v in enumerate(padded):
            if i == idx:
                continue
            if not is_effectively_zero(v, tol):
                return False

    knl_at_idx = knl[idx] if idx < len(knl) else 0
    ksl_at_idx = ksl[idx] if idx < len(ksl) else 0
    if is_effectively_zero(knl_at_idx, tol) and is_effectively_zero(ksl_at_idx, tol):
        return False

    return True

################################################################################
# SAD Hard Dipolar Fringe Maps
################################################################################
def sad_hard_dipolar_fringe_coefficients(
        k0:         float,
        sk0:        float,
        length:     float,
        is_exit:    bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate SAD's hard K0/SK0 edge through second polynomial order.

    The map is the quadratic truncation of the ``nord == 2`` branch of
    SAD's ``ttfrin``, conjugated by the normal/skew field rotation used by
    ``ttfrins``. ``k0`` and ``sk0`` are integrated strengths. The signed
    element length therefore enters explicitly when recovering the local
    field. The omitted longitudinal term begins at third transverse order.

    Parameters
    ----------
    k0, sk0 : float
        Integrated normal and skew dipole strengths.
    length : float
        Signed element length in metres.
    is_exit : bool
        Whether to calculate the exit-face map.

    Returns
    -------
    k : numpy.ndarray
        Zero constant six-dimensional Taylor coefficient.
    R : numpy.ndarray
        Identity linear ``6 x 6`` Taylor coefficient.
    T : numpy.ndarray
        Quadratic ``6 x 6 x 6`` Taylor coefficient in the element frame.

    Raises
    ------
    ValueError
        If ``length`` is zero while either integrated strength is nonzero.
    """
    magnitude = np.hypot(k0, sk0)
    if magnitude == 0.0:
        return np.zeros(6), np.eye(6), np.zeros((6, 6, 6))
    if length == 0.0:
        raise ValueError(
            "A nonzero SAD hard dipolar fringe requires a nonzero length.")

    face_sign = -1.0 if is_exit else 1.0
    scale     = face_sign * magnitude / length

    local = np.zeros((6, 6, 6))
    local[0, 2, 2] = 0.5 * scale
    local[3, 1, 2] = local[3, 2, 1] = -0.5 * scale

    angle    = np.arctan2(sk0, k0)
    cosine   = np.cos(angle)
    sine     = np.sin(angle)
    rotation = np.eye(6)
    rotation[0, 0] = rotation[1, 1] = cosine
    rotation[0, 2] = rotation[1, 3] = -sine
    rotation[2, 0] = rotation[3, 1] = sine
    rotation[2, 2] = rotation[3, 3] = cosine

    tensor = np.einsum(
        "ia,abc,bj,ck->ijk",
        rotation.T,
        local,
        rotation,
        rotation)
    return np.zeros(6), np.eye(6), tensor

################################################################################
# Second-Order Taylor-Map Composition
################################################################################
def compose_second_order_taylor_coefficients(
        first:      xt.SecondOrderTaylorMap,
        second:     xt.SecondOrderTaylorMap
        ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compose two Taylor maps, discarding polynomial orders above two.

    The returned coefficients represent ``second(first(z))`` in one common
    local frame. The input maps carry no alignment because the parent
    magnet's alignment is applied once to the final composite element.

    Parameters
    ----------
    first, second : xtrack.SecondOrderTaylorMap
        Maps in tracking order, expressed in the same local frame. Their
        alignment fields must be zero during coefficient composition.

    Returns
    -------
    k : numpy.ndarray
        Constant coefficient of the composite map.
    R : numpy.ndarray
        Linear coefficient of the composite map.
    T : numpy.ndarray
        Quadratic coefficient of the composite map.

    Raises
    ------
    ValueError
        If either input map still carries an alignment transformation.
    """
    alignment_fields = (
        "shift_x", "shift_y", "shift_s",
        "rot_x_rad", "rot_y_rad", "rot_s_rad",
        "rot_s_rad_no_frame", "rot_shift_anchor")
    for name, element in (("first", first), ("second", second)):
        if any(float(getattr(element, field)) != 0.0
                for field in alignment_fields):
            raise ValueError(
                f"The {name} Taylor map must be expressed in the common "
                "local frame before composition.")

    k_first  = np.asarray(first.k)
    R_first  = np.asarray(first.R)
    T_first  = np.asarray(first.T)
    k_second = np.asarray(second.k)
    R_second = np.asarray(second.R)
    T_second = np.asarray(second.T)

    k = k_second + R_second @ k_first + np.einsum(
        "imn,m,n->i", T_second, k_first, k_first)
    R = R_second @ R_first
    R += np.einsum("imn,m,nj->ij", T_second, k_first, R_first)
    R += np.einsum("imn,mj,n->ij", T_second, R_first, k_first)
    T = np.einsum("im,mjk->ijk", R_second, T_first)
    T += np.einsum(
        "imn,mj,nk->ijk", T_second, R_first, R_first)
    T += np.einsum(
        "imn,m,njk->ijk", T_second, k_first, T_first)
    T += np.einsum(
        "imn,mjk,n->ijk", T_second, T_first, k_first)
    return k, R, T


def rotate_second_order_taylor_coefficients(
        element:       xt.SecondOrderTaylorMap,
        rotation:      float
        ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Rotate Taylor coefficients into a parent element's local frame.

    The input map is defined in its own field frame. ``rotation`` is the
    Xtrack ``rot_s_rad`` that relates that field frame to the parent magnet
    frame. Only this relative field rotation is folded into ``k``, ``R`` and
    ``T``. The parent magnet's ``shift_x``, ``shift_y`` and ``rot_s_rad`` are
    not folded in; they must be assigned to the final composite fringe so the
    fringe remains on the same physical axis as its magnet.

    Parameters
    ----------
    element : xtrack.SecondOrderTaylorMap
        Unaligned Taylor map in its field frame.
    rotation : float
        Rotation from the parent magnet frame to the map's field frame, in
        Xtrack's ``rot_s_rad`` convention.

    Returns
    -------
    k : numpy.ndarray
        Constant coefficient in the parent magnet frame.
    R : numpy.ndarray
        Linear coefficient in the parent magnet frame.
    T : numpy.ndarray
        Quadratic coefficient in the parent magnet frame.

    Raises
    ------
    ValueError
        If the input map is aligned rather than being a field-frame map.
    """
    alignment_fields = (
        "shift_x", "shift_y", "shift_s",
        "rot_x_rad", "rot_y_rad", "rot_s_rad",
        "rot_s_rad_no_frame", "rot_shift_anchor")
    if any(float(getattr(element, name)) != 0.0
            for name in alignment_fields):
        raise ValueError(
            "The Taylor map must be unaligned before its field rotation is "
            "folded into the parent frame.")

    cosine      = np.cos(rotation)
    sine        = np.sin(rotation)
    coordinates = np.eye(6)
    coordinates[0, 0] = coordinates[1, 1] = cosine
    coordinates[0, 2] = coordinates[1, 3] = sine
    coordinates[2, 0] = coordinates[3, 1] = -sine
    coordinates[2, 2] = coordinates[3, 3] = cosine

    k = coordinates.T @ np.asarray(element.k)
    R = coordinates.T @ np.asarray(element.R) @ coordinates
    T = np.einsum(
        "ia,abc,bj,ck->ijk",
        coordinates.T,
        np.asarray(element.T),
        coordinates,
        coordinates)
    return k, R, T

################################################################################
# SAD Soft Quadrupolar Fringe Maps
################################################################################

########################################
# SAD Quadrupolar Field Rotation
########################################
def sad_quadrupolar_field_rotation(
        k1:     float,
        sk1:    float   = 0.0,
        length: float   = 1.0) -> float:
    """
    Return the rotation from the element frame to SAD's normal field frame.

    SAD represents the normal and skew linear fields by the complex quantity
    ``(K1 + i SK1) * L``. Rotating transverse coordinates by half its complex
    phase makes that field purely normal and focusing. The factor one-half is
    the quadrupole's two-fold azimuthal symmetry. A negative real field is
    therefore represented by a ``pi/2`` frame rotation rather than by a
    negative local gradient. This is SAD's ``akang`` operation in
    ``tfloor.f``.

    The same operation applies to a dedicated SAD ``QUAD`` and to the
    K1/SK1 component of a SAD ``MULT``.

    Parameters
    ----------
    k1 : float
        SAD normal linear multipole coefficient.
    sk1 : float, optional
        SAD skew linear multipole coefficient. Defaults to zero.
    length : float, optional
        Signed element length in metres. Its sign determines the field-frame
        orientation for a reversed-length element. Defaults to one metre.

    Returns
    -------
    float
        Counter-clockwise transverse frame rotation in radians, using SAD's
        sign convention.
    """
    value = complex(k1, sk1) * length
    if value.imag == 0.0:
        return np.pi / 2.0 if value.real < 0.0 else 0.0
    return 0.5 * np.arctan2(value.imag, value.real)

########################################
# Calculate SAD Soft Quadrupolar Fringe Map
########################################
def sad_soft_quadrupolar_fringe_coefficients(
        environment:       xt.Environment,
        a:                 SadValue,
        b:                 SadValue
        ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate a centred SAD K1/SK1 soft-edge map in the element frame.

    These coefficients are the second-order expansion of SAD's ``tqlfre``
    map at zero local longitudinal field, about ``delta = 0``. The map uses
    Xsuite ``pzeta`` for SAD ``delta`` and is therefore intended for the
    ultrarelativistic electron and positron lattices supported by SAD2XS.
    This is the quadrupole-field fringe shared by SAD ``QUAD`` elements and
    the K1/SK1 component of SAD ``MULT`` elements; it does not represent the
    other MULT fringe mechanisms. The caller places this normal-field map in
    the magnet frame with Xsuite's standard ``rot_s_rad`` transform.

    Parameters
    ----------
    environment : xtrack.Environment
        Environment used to resolve string expressions and create live Xdeps
        expressions when a QUAD strength is varied.
    a : float or str
        Dimensionless signed F1 coefficient. The caller changes its sign
        between the entrance and exit faces.
    b : float or str
        F2 coefficient in metres. Its sign is unchanged between faces.

    Returns
    -------
    k : numpy.ndarray
        Constant six-dimensional Taylor coefficient in the element frame.
    R : numpy.ndarray
        Linear ``6 x 6`` Taylor coefficient in the element frame.
    T : numpy.ndarray
        Quadratic ``6 x 6 x 6`` Taylor coefficient in the element frame.
    """
    a_value = environment.vars.new_expr(a) if isinstance(a, str) else a
    b_value = environment.vars.new_expr(b) if isinstance(b, str) else b
    if isinstance(a_value, (int, float, np.number)):
        exp_a       = np.exp(a_value)
        exp_minus_a = np.exp(-a_value)
    else:
        exp_a       = environment.functions.exp(a_value)
        exp_minus_a = environment.functions.exp(-a_value)

    k = np.zeros(6, dtype = object)
    R = np.zeros((6, 6), dtype = object)
    T = np.zeros((6, 6, 6), dtype = object)

    R[0, 0] = exp_a
    R[0, 1] = b_value
    R[1, 1] = exp_minus_a
    R[2, 2] = exp_minus_a
    R[2, 3] = -b_value
    R[3, 3] = exp_a
    R[4, 4] = 1.0
    R[5, 5] = 1.0

    T[0, 0, 5] = T[0, 5, 0] = -a_value * exp_a / 2.0
    T[0, 1, 5] = T[0, 5, 1] = -b_value
    T[1, 1, 5] = T[1, 5, 1] = a_value * exp_minus_a / 2.0
    T[2, 2, 5] = T[2, 5, 2] = a_value * exp_minus_a / 2.0
    T[2, 3, 5] = T[2, 5, 3] = b_value
    T[3, 3, 5] = T[3, 5, 3] = -a_value * exp_a / 2.0
    T[4, 1, 1] = -b_value * exp_minus_a * (1.0 + a_value / 2.0)
    T[4, 3, 3] = b_value * exp_a * (1.0 - a_value / 2.0)
    T[4, 0, 1] = T[4, 1, 0] = -a_value / 2.0
    T[4, 2, 3] = T[4, 3, 2] = a_value / 2.0

    return k, R, T

########################################
# Create SAD Fringe Taylor Map
########################################
def create_sad_fringe_taylor_map(
        environment:        xt.Environment,
        name:               str,
        soft_quadrupole:    dict | None = None,
        hard_dipole:        dict | None = None,
        alignment:          dict | None = None,
        is_exit:            bool = False) -> None:
    """
    Add one supported SAD fringe Taylor map to an Xsuite environment.

    The physical map is stored in the element's canonical ``k``, ``R``, and
    ``T`` coefficients. Its defining quantities are recorded once in
    ``Environment.metadata`` so reversal and the writer need not infer them
    from the Taylor tensors or add private fields to the Xsuite element. The
    soft-quadrupole and hard-dipole components are each optional. Their maps
    are composed in the parent magnet's local frame before the common magnet
    alignment is applied once to the resulting element.

    Parameters
    ----------
    environment : xtrack.Environment
        Environment receiving the new element.
    name : str
        Name of the new ``SecondOrderTaylorMap`` element.
    soft_quadrupole : dict or None, optional
        Soft component containing numeric or deferred ``a`` and ``b``, plus
        an optional concrete ``relative_rotation`` from the parent magnet
        frame to the soft-field frame. Defaults to no soft-quadrupole
        component; the rotation defaults to zero when the component is present.
    hard_dipole : dict or None, optional
        Hard component containing concrete integrated ``k0``, integrated
        ``sk0``, and signed ``length``. Defaults to no hard-dipole component.
    alignment : dict or None, optional
        Common parent-magnet ``shift_x``, ``shift_y``, and ``rot_s_rad``.
        Deferred values remain supported for a soft-only map; a hard
        component requires concrete alignment. Defaults to the unshifted,
        unrotated frame.
    is_exit : bool, optional
        Whether this is the exit face. This determines both the hard-edge
        sign and the order of hard and soft map composition. Defaults to
        ``False``.

    Returns
    -------
    None
    """
    ########################################
    # Initialise Parent Alignment
    ########################################
    alignment = {} if alignment is None else alignment.copy()
    alignment.setdefault("shift_x",   0.0)
    alignment.setdefault("shift_y",   0.0)
    alignment.setdefault("rot_s_rad", 0.0)

    ########################################
    # Build Soft Quadrupolar Component
    ########################################
    if soft_quadrupole is None:
        k, R, T = np.zeros(6), np.eye(6), np.zeros((6, 6, 6))
    else:
        k, R, T = sad_soft_quadrupolar_fringe_coefficients(
            environment,
            a = soft_quadrupole["a"],
            b = soft_quadrupole["b"])
        relative_rotation = soft_quadrupole.get("relative_rotation", 0.0)
        if relative_rotation != 0.0:
            soft = xt.SecondOrderTaylorMap(k = k, R = R, T = T)
            k, R, T = rotate_second_order_taylor_coefficients(
                soft, relative_rotation)

    ########################################
    # Compose Hard Dipolar Component
    ########################################
    if hard_dipole is not None:
        concrete_values = (
            hard_dipole["k0"],
            hard_dipole["sk0"],
            hard_dipole["length"],
            alignment["shift_x"],
            alignment["shift_y"],
            alignment["rot_s_rad"])
        if any(not isinstance(value, (int, float, np.number))
               for value in concrete_values):
            raise ValueError(
                "A hard SAD fringe Taylor map requires concrete strengths, "
                "length, and alignment.")
        hard_k, hard_R, hard_T = sad_hard_dipolar_fringe_coefficients(
            hard_dipole["k0"],
            hard_dipole["sk0"],
            hard_dipole["length"],
            is_exit)
        hard = xt.SecondOrderTaylorMap(k = hard_k, R = hard_R, T = hard_T)
        soft = xt.SecondOrderTaylorMap(k = k, R = R, T = T)
        if is_exit:
            k, R, T = compose_second_order_taylor_coefficients(soft, hard)
        else:
            k, R, T = compose_second_order_taylor_coefficients(hard, soft)

    ########################################
    # Create Fringe Element
    ########################################
    environment.new(
        name        = name,
        prototype   = xt.SecondOrderTaylorMap,
        length      = 0.0,
        k           = k,
        R           = R,
        T           = T,
        **alignment)

    ########################################
    # Store Physical Parameters
    ########################################
    sad2xs  = environment.metadata.setdefault("sad2xs", {})
    fringes = sad2xs.setdefault("fringe_taylor_maps", {})
    if soft_quadrupole is None:
        metadata = {
            "a":              0.0,
            "b":              0.0,
            "field_rotation": -alignment["rot_s_rad"]}
    else:
        relative_rotation = soft_quadrupole.get("relative_rotation", 0.0)
        parent_rotation   = alignment["rot_s_rad"]
        if relative_rotation == 0.0:
            field_rotation = negate_sad_value(parent_rotation)
        elif all(isinstance(value, (int, float, np.number))
                 for value in (relative_rotation, parent_rotation)):
            field_rotation = -relative_rotation - parent_rotation
        else:
            raise ValueError(
                "A rotated SAD soft fringe requires concrete relative and "
                "parent rotations.")
        metadata = {
            "a":              soft_quadrupole["a"],
            "b":              soft_quadrupole["b"],
            "field_rotation": field_rotation}
        if relative_rotation != 0.0:
            metadata["relative_rotation"] = relative_rotation
    metadata["shift_x"] = alignment["shift_x"]
    metadata["shift_y"] = alignment["shift_y"]
    if hard_dipole is not None or "relative_rotation" in metadata:
        metadata["parent_rotation"] = alignment["rot_s_rad"]
        metadata["is_exit"]         = is_exit
    if hard_dipole is not None:
        metadata["hard_dipole"] = hard_dipole
    fringes[name] = metadata

################################################################################
# SAD MULT Fringe Parameters
################################################################################
def sad_mult_fringe_parameters(
        ele_name:    str,
        ele_vars:    dict[str, SadValue],
        length:      SadValue,
        knl:         list[SadValue],
        ksl:         list[SadValue],
        alignment:   dict,
        config:      ConfigLike) -> dict:
    """
    Derive the supported orbital fringe parameters of a thick SAD MULT.

    MULT strengths remain numeric by design: the writer does not create
    per-order optics variables for MULT arrays. Active hard K0/SK0 and K1/SK1
    edges, soft F1/F2 quadrupolar maps, and the parent frame are therefore
    evaluated once during conversion.

    Parameters
    ----------
    ele_name : str
        SAD MULT element name, used in diagnostics.
    ele_vars : dict
        Parsed parameters for that MULT.
    length : float or str
        Signed MULT length in metres.
    knl, ksl : list
        Integrated normal and skew multipole strengths.
    alignment : dict
        Parent MULT ``shift_x``, ``shift_y``, and ``rot_s_rad`` values.
    config : ConfigLike
        Converter configuration controlling MULT-fringe import.

    Returns
    -------
    dict
        Numeric physical parameters and the active entrance/exit faces. A
        policy-only record is returned when native typed edges must be
        suppressed without creating a physical fringe component; an empty
        dictionary means the MULT needs no fringe handling.

    Raises
    ------
    ValueError
        If a parameter needed by an active supported fringe is deferred.
    """
    if isinstance(length, (int, float, np.number)) and length == 0.0:
        return {}

    supported_strengths = list(knl[:2]) + list(ksl[:2])
    has_supported_field = any(
        not is_effectively_zero(value, tol = 0.0)
        for value in supported_strengths)
    if not config._import_sad_mult_fringes:
        if has_supported_field:
            return {"edge_policy_only": True, "hard_faces": ()}
        return {}

    ########################################
    # Select Active Faces
    ########################################
    fringe_mode = parse_expression(ele_vars.get("fringe", 0.0))
    if not isinstance(fringe_mode, float):
        raise ValueError(
            "FRINGE must be a concrete number to import a MULT fringe, got "
            f"a deferred expression: {fringe_mode!r}.")
    fringe_mode = int(fringe_mode)

    soft_face_names = []
    if fringe_mode in (1, 3):
        soft_face_names.append("in")
    if fringe_mode in (2, 3):
        soft_face_names.append("out")

    ########################################
    # Read Hard-Fringe Switch
    ########################################
    disfrin = parse_expression(ele_vars.get("disfrin", 0.0))
    if not isinstance(disfrin, float):
        raise ValueError(
            "DISFRIN must be a concrete number to import a MULT fringe, got "
            f"a deferred expression: {disfrin!r}.")
    hard_enabled = disfrin == 0.0
    if not hard_enabled:
        hard_faces = []
    elif fringe_mode == 1:
        hard_faces = ["in"]
    elif fringe_mode == 2:
        hard_faces = ["out"]
    else:
        hard_faces = ["in", "out"]

    faces = [
        side for side in ("in", "out")
        if side in soft_face_names or side in hard_faces]
    if not faces:
        if has_supported_field:
            return {"edge_policy_only": True, "hard_faces": ()}
        return {}
    if not isinstance(length, (int, float, np.number)):
        raise ValueError(
            f"L must be a concrete number to import the active fringe of "
            f"SAD MULT {ele_name}, got {length!r}.")

    ########################################
    # Read Soft Quadrupolar Faces
    ########################################
    soft_faces = {}
    has_quadrupole = not (
        is_effectively_zero(knl[1], tol = 0.0)
        and is_effectively_zero(ksl[1], tol = 0.0))
    if has_quadrupole and soft_face_names:
        face_values = {
            key: parse_expression(ele_vars.get(key, 0.0))
            for key in (
                "f1", "f2", "f1k1f", "f2k1f", "f1k1b", "f2k1b")}
        for name, value in face_values.items():
            if not isinstance(value, float):
                raise ValueError(
                    f"{name.upper()} must be a concrete number to import the "
                    "soft quadrupolar MULT fringe, got a deferred expression: "
                    f"{value!r}.")

        for side, suffix in (("in", "f"), ("out", "b")):
            if side not in soft_face_names:
                continue
            f1_raw = face_values["f1"] + face_values[f"f1k1{suffix}"]
            f2_raw = face_values["f2"] + face_values[f"f2k1{suffix}"]
            if f1_raw != 0.0 or f2_raw != 0.0:
                soft_faces[side] = (f1_raw, f2_raw)

    ########################################
    # Validate Required Parameters
    ########################################
    scalar_values = {"drot": parse_expression(ele_vars.get("drot", 0.0))}
    if soft_faces:
        scalar_values["rotate"] = parse_expression(ele_vars.get("rotate", 0.0))
    for name, value in scalar_values.items():
        if not isinstance(value, float):
            raise ValueError(
                f"{name.upper()} must be a concrete number to import the "
                f"MULT fringe, got a deferred expression: {value!r}.")

    if hard_enabled and any(
            not isinstance(value, (int, float, np.number))
            for value in supported_strengths):
        raise ValueError(
            f"Active hard fringes on SAD MULT {ele_name} require concrete "
            "K0, SK0, K1, and SK1 values.")
    rotation = alignment["rot_s_rad"]
    if hard_enabled and not isinstance(rotation, (int, float, np.number)):
        raise ValueError(
            f"Active hard fringes on SAD MULT {ele_name} require a concrete "
            f"ROTATE value, got {rotation!r}.")
    has_supported_hard_edge = hard_enabled and any(
        not is_effectively_zero(value, tol = 0.0)
        for value in supported_strengths)
    if has_supported_hard_edge and any(
            not isinstance(alignment[key], (int, float, np.number))
            for key in ("shift_x", "shift_y")):
        raise ValueError(
            f"Active hard fringes on SAD MULT {ele_name} require concrete "
            "DX and DY values.")

    k1  = knl[1]
    sk1 = ksl[1]
    if soft_faces and any(
            not isinstance(value, (int, float, np.number))
            for value in (k1, sk1, rotation)):
        raise ValueError(
            f"The active soft fringe of SAD MULT {ele_name} requires "
            "concrete K1, SK1, and ROTATE values.")

    ########################################
    # Build Physical Description
    ########################################
    result = {
        "faces":          tuple(faces),
        "hard_faces":     tuple(hard_faces),
        "length":         float(length),
        "alignment":      alignment,
        "k0":             knl[0],
        "sk0":            ksl[0],
        "k1":             k1,
        "sk1":            sk1,
        "soft":           {}}

    ########################################
    # Record Unsupported Components
    ########################################
    has_dipole = not (
        is_effectively_zero(knl[0], tol = 0.0)
        and is_effectively_zero(ksl[0], tol = 0.0))
    result["unsupported_soft_dipole"] = (
        has_dipole and bool(soft_face_names) and any(
            not is_effectively_zero(parse_expression(ele_vars[key]), tol = 0.0)
            for key in ("fb1", "fb2") if key in ele_vars))
    result["unsupported_higher_hard"] = hard_enabled and any(
        not is_effectively_zero(value, tol = 0.0)
        for value in knl[2:] + ksl[2:])

    ########################################
    # Calculate Soft Quadrupolar Maps
    ########################################
    if soft_faces and (k1 != 0.0 or sk1 != 0.0):
        magnitude = np.hypot(k1, sk1) / abs(length)
        result["field_rotation"] = (
            scalar_values["rotate"]
            + sad_quadrupolar_field_rotation(k1, sk1, length))
        for side, (f1_raw, f2_raw) in soft_faces.items():
            a = -magnitude * f1_raw * abs(f1_raw) / 24.0
            b = magnitude * f2_raw
            result["soft"][side] = (a, b)

    has_active_fringe = (
        bool(result["soft"])
        or has_supported_hard_edge
        or result["unsupported_soft_dipole"]
        or result["unsupported_higher_hard"])
    if not has_active_fringe and hard_enabled:
        return {}
    if scalar_values["drot"] != 0.0:
        logger.warning(
            f"SAD MULT {ele_name} has an active fringe and nonzero DROT. "
            "SAD2XS does not apply DROT to the MULT body, so its fringe is "
            "being skipped rather than rotated inconsistently.")
        return {"edge_policy_only": True, "hard_faces": ()}
    if not has_active_fringe:
        return {"edge_policy_only": True, "hard_faces": ()}
    return result

########################################
# Create SAD MULT Hard Quadrupolar Edge
########################################
def _create_sad_mult_hard_quadrupolar_edge(
        environment:    xt.Environment,
        name:           str,
        fringe:         dict,
        alignment:      dict,
        is_exit:        bool) -> None:
    """
    Add one native K1/SK1 hard edge in the parent MULT frame.

    Parameters
    ----------
    environment : xtrack.Environment
        Environment receiving the edge.
    name : str
        Name of the new ``MultipoleEdge``.
    fringe : dict
        Numeric output of `sad_mult_fringe_parameters`.
    alignment : dict
        Parent MULT ``shift_x``, ``shift_y``, and ``rot_s_rad`` values.
    is_exit : bool
        Whether to create the exit rather than entrance edge.

    Returns
    -------
    None
    """
    environment.elements[name] = xt.MultipoleEdge(
        kn          = [0.0, fringe["k1"] / fringe["length"]],
        ks          = [0.0, fringe["sk1"] / fringe["length"]],
        order       = 1,
        is_exit     = is_exit,
        **alignment)
    sad2xs = environment.metadata.setdefault("sad2xs", {})
    hard_edges = sad2xs.setdefault("mult_hard_quadrupolar_edges", {})
    hard_edges[name] = {}

########################################
# Install SAD MULT Fringes
########################################
def install_sad_mult_fringes(
        environment:    xt.Environment,
        ele_name:       str,
        fringe:         dict,
        representation: str) -> None:
    """
    Wrap an already-created MULT body with its supported physical face maps.

    Parameters
    ----------
    environment : xtrack.Environment
        Environment containing the converted MULT body.
    ele_name : str
        Name shared by the SAD MULT and its converted body or body subline.
    fringe : dict
        Output of `sad_mult_fringe_parameters`.
    representation : {"multipole", "quadrupole", "bend", "discarded"}
        Converted body representation. A true Multipole receives explicit
        hard K0/SK0 and K1/SK1 edges. Quadrupole and Bend use their native
        hard edges and retain only fringe terms consistent with that body.

    Returns
    -------
    None
    """
    if not fringe:
        return

    ########################################
    # Configure Native Body Edges
    ########################################
    if representation in ("quadrupole", "bend"):
        edge_entry_active = "in" in fringe["hard_faces"]
        edge_exit_active  = "out" in fringe["hard_faces"]
        body = environment[ele_name]
        body.edge_entry_active = edge_entry_active
        body.edge_exit_active  = edge_exit_active
        sad2xs = environment.metadata.setdefault("sad2xs", {})
        native_edges = sad2xs.setdefault("mult_native_fringe_faces", {})
        native_edges[ele_name] = {
            "edge_entry_active": edge_entry_active,
            "edge_exit_active":  edge_exit_active}

    if fringe.get("edge_policy_only", False):
        return

    ########################################
    # Identify Retained Components
    ########################################
    soft              = fringe["soft"]
    has_k0            = fringe["k0"] != 0.0 or fringe["sk0"] != 0.0
    has_k1            = fringe["k1"] != 0.0 or fringe["sk1"] != 0.0
    retains_soft      = representation in ("multipole", "quadrupole")
    explicit_hard     = representation == "multipole"

    ########################################
    # Warn for Discarded Components
    ########################################
    if soft and not retains_soft:
        logger.warning(
            f"SAD MULT {ele_name} has an active K1 soft-edge fringe, but its "
            "replacement discards K1/SK1. That fringe is being skipped "
            "because retaining it would contradict the replacement.")
        soft = {}
    if has_k0 and representation in ("quadrupole", "discarded"):
        logger.warning(
            f"SAD MULT {ele_name} has an active K0/SK0 hard fringe, but its "
            "replacement discards K0/SK0. That fringe is being skipped.")
    if has_k1 and representation in ("bend", "discarded"):
        logger.warning(
            f"SAD MULT {ele_name} has an active K1/SK1 hard fringe, but its "
            "replacement discards K1/SK1. That fringe is being skipped.")

    ########################################
    # Build Explicit Fringe Components
    ########################################
    alignment = fringe["alignment"]
    face_components = {"in": [], "out": []}
    for side in fringe["faces"]:
        is_exit       = side == "out"
        hard_face     = side in fringe["hard_faces"]
        hard_k0       = fringe["k0"] if hard_face and explicit_hard else 0.0
        hard_sk0      = fringe["sk0"] if hard_face and explicit_hard else 0.0
        hard_k1       = hard_face and explicit_hard and has_k1
        taylor_active = side in soft or hard_k0 != 0.0 or hard_sk0 != 0.0

        if not is_exit and hard_k1:
            name = f"{ele_name}_hard_edge_in"
            _create_sad_mult_hard_quadrupolar_edge(
                environment, name, fringe, alignment, is_exit = False)
            face_components[side].append(name)

        if taylor_active:
            soft_component = None
            if side in soft:
                a, b = soft[side]
                if is_exit:
                    a = -a
                field_rotation = fringe["field_rotation"]
                soft_component = {
                    "a":                  a,
                    "b":                  b,
                    "relative_rotation": (
                        -field_rotation - alignment["rot_s_rad"])}
            hard_component = None
            if hard_k0 != 0.0 or hard_sk0 != 0.0:
                hard_component = {
                    "k0":     hard_k0,
                    "sk0":    hard_sk0,
                    "length": fringe["length"]}
            name = f"{ele_name}_fringe_{side}"
            create_sad_fringe_taylor_map(
                environment,
                name             = name,
                soft_quadrupole  = soft_component,
                hard_dipole      = hard_component,
                alignment        = alignment,
                is_exit          = is_exit)
            face_components[side].append(name)

        if is_exit and hard_k1:
            name = f"{ele_name}_hard_edge_out"
            _create_sad_mult_hard_quadrupolar_edge(
                environment, name, fringe, alignment, is_exit = True)
            face_components[side].append(name)

    ########################################
    # Create MULT Compound
    ########################################
    components = face_components["in"] + [ele_name] + face_components["out"]
    if components != [ele_name]:
        environment.new_line(
            name = f"{ele_name}_compound", components = components)
