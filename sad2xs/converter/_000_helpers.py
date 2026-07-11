"""
================================================================================
Converter Helper Functions
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-10
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import xtrack as xt

from ..helpers import species_from_mass_and_charge

################################################################################
# Expression Parsing
################################################################################
def parse_expression(expression):
    """
    Convert a SAD expression value to a Python float or a stripped string.

    - int   -> float
    - float -> float
    - str   -> float if the string is numeric, otherwise stripped string
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

################################################################################
# Zero Check
################################################################################
def is_effectively_zero(val, tol: float = 1E-12) -> bool:
    """
    Return True if val is numerically zero within tol.
    String expressions cannot be evaluated and are always treated as non-zero.
    """
    try:
        return abs(float(val)) <= tol
    except (ValueError, TypeError):
        return False

################################################################################
# Provable Equality Check
################################################################################
def values_provably_equal(val_1, val_2, tol: float = 1E-9) -> bool:
    """
    Return True if two SAD-parsed values are numerically equal within tol,
    or the exact same deferred expression string.
    """
    if isinstance(val_1, (int, float)) and isinstance(val_2, (int, float)):
        return abs(float(val_1) - float(val_2)) <= tol
    if isinstance(val_1, str) and isinstance(val_2, str):
        return val_1.strip() == val_2.strip()
    return False

def values_provably_opposite(val_1, val_2, tol: float = 1E-9) -> bool:
    """
    Return True if two SAD-parsed values are numerically equal and opposite
    in sign within tol, or one deferred expression is a literal "-" prefix
    of the other.
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
def get_element_length(ele_vars: dict):
    """
    Extract element length from a parsed SAD parameter dict.
    Returns 0.0 if 'l' is absent.
    """
    return parse_expression(ele_vars.get("l", 0.0))

########################################
# Integrated Element Strength
########################################
def get_element_integrated_strength(ele_vars: dict, key: str, default: float = 0.0):
    """
    Extract a strength parameter from a parsed SAD parameter dict.
    Returns default if key is absent.
    """
    return parse_expression(ele_vars.get(key, default))

########################################
# Divide Integrated Strength by Length
########################################
def divide_integrated_strength(kl, length):
    """
    Divide integrated strength kl by element length to obtain a per-unit-length
    strength (e.g. k1l / l -> k1).

    Both kl and length may be a float or a string expression (deferred variable).
    - Returns 0.0 if kl is exactly zero.
    - Returns a float if both inputs are numeric.
    - Returns a string expression otherwise.

    Callers must ensure length is non-zero. This function is only valid for
    thick elements; the thin/thick split must occur before calling it.
    """
    if isinstance(kl, (int, float)) and kl == 0.0:
        return 0.0
    if isinstance(kl, (int, float)) and isinstance(length, (int, float)):
        return kl / length
    return f"{kl} / {length}"

########################################
# Define Strength Variable in Environment
########################################
def define_strength_variable(environment, ele_name: str, k_name: str, k_value):
    """
    Register a per-unit-length strength in the xtrack environment and return
    a reference expression to it.

    If k_value is non-zero, stores it as environment['{k_name}_{ele_name}']
    and returns the key string so it can be passed to environment.new().
    If k_value is zero, returns k_value unchanged without touching the
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
def parse_rf_parameters(environment, ele_name: str, ele_vars: dict):
    """
    Parse SAD VOLT/FREQ/PHI/HARM into Xsuite Cavity-ready values.

    HARM and FREQ are mutually exclusive in SAD; if HARM is present it takes
    priority and FREQ is discarded (harmonic tracks Xsuite's own revolution-
    frequency derivation). FREQ and PHI, when non-zero, are registered as
    deferred environment variables (freq_{name}, phase_{name}) so they can be
    tuned after conversion. VOLT is always registered as vol_{name} for the
    same reason, but is returned as a literal value, matching how it is
    passed directly to xt.Cavity today.

    Returns (voltage, frequency, harmonic, phase) ready to pass to
    environment.new(prototype=xt.Cavity, ...).
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
def combine_k0_sk0(knl0, ksl0, rotation):
    """
    Combine SAD MULT integrated K0/SK0 into a single (k0l, rotation) pair.

    knl0, ksl0, and rotation may each independently be a float or a string
    expression (deferred variable). A string expression is built whenever any
    of the three is deferred, since a mixed numeric/deferred computation
    cannot be evaluated directly; otherwise the combination is computed
    numerically.
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
# Compute Element Misalignments
################################################################################
def get_element_misalignments(ele_vars: dict, rotation_correction: float = 0.0):
    """
    Extract transverse misalignments and rotation from a parsed SAD element
    parameter dict.

    Rotations in SAD are opposite in sign to Xsuite; the returned rotation is
    already negated. rotation_correction (radians) is added after negation.

    Returns (shift_x, shift_y, rotation). Each value is a float or a string
    expression depending on whether the SAD parameter was numeric or deferred.
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
        length,
        knl:    list,
        ksl:    list,
        idx:    int,
        tol:    float) -> bool:
    """
    Return True if all of the following hold:
      1. length is non-zero (if numeric); a string length is assumed non-zero.
      2. Every entry in knl and ksl except at index idx is zero within tol.
         Non-numeric string values are treated as non-zero.
      3. At least one of knl[idx], ksl[idx] is non-zero within tol.
    """
    if isinstance(length, (int, float)):
        if abs(length) <= tol:
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
# Reference Particle Species
# Canonical definition: sad2xs/helpers.py
################################################################################
