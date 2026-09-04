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
import numpy as np
import xtrack as xt

from ..types import SadValue

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
# Create SAD Soft Quadrupolar Fringe Element
########################################
def create_sad_soft_quadrupolar_fringe(
        environment:       xt.Environment,
        name:              str,
        a:                 SadValue,
        b:                 SadValue,
        field_rotation:    SadValue,
        shift_x:           SadValue = 0.0,
        shift_y:           SadValue = 0.0) -> None:
    """
    Add one SAD K1/SK1 soft-edge map to an Xsuite environment.

    The physical map is stored in the element's canonical ``k``, ``R``, and
    ``T`` coefficients. Its five defining quantities are recorded once in
    ``Environment.metadata`` so reversal and the writer need not infer them
    from the Taylor tensors or add private fields to the Xsuite element.

    Parameters
    ----------
    environment : xtrack.Environment
        Environment receiving the new element.
    name : str
        Name of the new ``SecondOrderTaylorMap`` element.
    a : float or str
        Dimensionless signed F1 coefficient for this face.
    b : float or str
        F2 coefficient in metres for this face.
    field_rotation : float or str
        SAD transverse field-frame rotation in radians.
    shift_x : float or str, optional
        Horizontal displacement of the magnet axis in metres. Defaults to
        zero.
    shift_y : float or str, optional
        Vertical displacement of the magnet axis in metres. Defaults to zero.

    Returns
    -------
    None
    """
    k, R, T = sad_soft_quadrupolar_fringe_coefficients(
        environment,
        a = a,
        b = b)

    rot_s_rad = negate_sad_value(field_rotation)

    environment.new(
        name        = name,
        prototype   = xt.SecondOrderTaylorMap,
        length      = 0.0,
        k           = k,
        R           = R,
        T           = T,
        shift_x     = shift_x,
        shift_y     = shift_y,
        rot_s_rad   = rot_s_rad)

    sad2xs  = environment.metadata.setdefault("sad2xs", {})
    fringes = sad2xs.setdefault("soft_quadrupolar_fringes", {})
    fringes[name] = {
        "a":              a,
        "b":              b,
        "field_rotation": field_rotation,
        "shift_x":        shift_x,
        "shift_y":        shift_y}
