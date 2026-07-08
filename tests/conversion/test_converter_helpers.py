"""
================================================================================
Tests for SAD2XS converter helper functions
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-29
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import pytest
import xtrack as xt

from sad2xs.converter._000_helpers import (
    combine_k0_sk0,
    divide_integrated_strength,
    define_strength_variable,
    get_element_integrated_strength,
    get_element_length,
    get_element_misalignments,
    is_effectively_zero,
    only_index_nonzero,
    species_from_mass_and_charge,
    values_provably_equal,
    values_provably_opposite)

################################################################################
# parse_expression
################################################################################
# Unit tests: tests/parser/test_deferred_expressions.py
#   - test_parse_expression_converts_numeric_types
#   - test_parse_expression_preserves_symbolic_text
#   - test_parse_expression_rejects_unsupported_types
# Integration tests (log/ln substitution):
#   tests/conversion/pipeline/test_math_function_expressions.py
#   - test_math_function_expression_converts_to_correct_value[LOG-...]
#   - test_math_function_expression_converts_to_correct_value[LN-...]

################################################################################
# is_effectively_zero
################################################################################
def test_is_effectively_zero_returns_true_for_zero():
    """
    Exact zero should be identified as effectively zero.
    """
    assert is_effectively_zero(0.0), (
        "Exact zero should be effectively zero.")

def test_is_effectively_zero_returns_false_for_nonzero():
    """
    A non-negligible value should not be identified as effectively zero.
    """
    assert not is_effectively_zero(1.0), (
        "A non-negligible value should not be effectively zero.")

def test_is_effectively_zero_returns_false_for_string():
    """
    A string expression cannot be evaluated and should be treated as non-zero.
    """
    assert not is_effectively_zero("expr"), (
        "String expressions should be treated as non-zero.")

def test_is_effectively_zero_respects_custom_tolerance():
    """
    A value within a custom tolerance should be identified as effectively zero.
    """
    assert is_effectively_zero(0.5, tol=1.0), (
        "A value within the supplied tolerance should be effectively zero.")

################################################################################
# values_provably_equal
################################################################################
def test_values_provably_equal_returns_true_for_equal_numbers():
    assert values_provably_equal(0.01, 0.01)

def test_values_provably_equal_returns_false_for_different_numbers():
    assert not values_provably_equal(0.01, 0.02)

def test_values_provably_equal_returns_true_for_identical_expressions():
    assert values_provably_equal("w", "w")

def test_values_provably_equal_returns_false_for_different_expressions():
    assert not values_provably_equal("w", "v")

def test_values_provably_equal_returns_false_for_mixed_types():
    assert not values_provably_equal(0.01, "w")

################################################################################
# values_provably_opposite
################################################################################
def test_values_provably_opposite_returns_true_for_opposite_numbers():
    assert values_provably_opposite(0.01, -0.01)

def test_values_provably_opposite_returns_false_for_equal_numbers():
    assert not values_provably_opposite(0.01, 0.01)

def test_values_provably_opposite_returns_true_for_negated_expression():
    assert values_provably_opposite("w", "-w")
    assert values_provably_opposite("-w", "w")

def test_values_provably_opposite_returns_false_for_unrelated_expressions():
    assert not values_provably_opposite("w", "v")

def test_values_provably_opposite_returns_false_for_mixed_types():
    assert not values_provably_opposite(0.01, "w")

################################################################################
# get_element_length
################################################################################
def test_get_element_length_returns_parsed_value():
    """
    When 'l' is present, the parsed length value should be returned.
    """
    assert get_element_length({"l": 2.0}) == pytest.approx(2.0), (
        "Element length should return the parsed 'l' value.")

def test_get_element_length_defaults_to_zero():
    """
    When 'l' is absent, the length should default to 0.0.
    """
    assert get_element_length({}) == pytest.approx(0.0), (
        "Element length should default to 0.0 when 'l' is absent.")

################################################################################
# get_element_integrated_strength
################################################################################
def test_get_element_integrated_strength_returns_parsed_value():
    """
    When the key is present, the parsed strength value should be returned.
    """
    assert get_element_integrated_strength({"k1l": 0.5}, "k1l") == pytest.approx(0.5), (
        "Integrated strength should return the parsed value when the key is present.")

def test_get_element_integrated_strength_returns_custom_default():
    """
    When the key is absent, the supplied default should be returned.
    """
    assert get_element_integrated_strength({}, "k1l", 1.5) == pytest.approx(1.5), (
        "Integrated strength should return the supplied default when the key is absent.")

################################################################################
# divide_integrated_strength
################################################################################
@pytest.mark.parametrize("kl", [0.0, 0])
def test_divide_integrated_strength_zero_kl_returns_zero(kl):
    """
    Zero integrated strength should short-circuit to 0.0 regardless of length type.
    """
    assert divide_integrated_strength(kl, 2.0) == 0.0, (
        "Zero kl should return 0.0 without performing division.")
    assert divide_integrated_strength(kl, "l_var") == 0.0, (
        "Zero kl should return 0.0 even when length is a string expression.")

def test_divide_integrated_strength_both_numeric_returns_float():
    """
    Two numeric inputs should return a float quotient.
    """
    assert divide_integrated_strength(0.5, 2.0) == pytest.approx(0.25), (
        "Numeric kl / numeric length should return a float quotient.")

def test_divide_integrated_strength_numeric_kl_string_length_returns_expression():
    """
    A string length should produce a string expression rather than divide.
    """
    assert divide_integrated_strength(0.5, "l_var") == "0.5 / l_var", (
        "Numeric kl with string length should produce a string expression.")

def test_divide_integrated_strength_string_kl_returns_expression():
    """
    A string kl should always produce a string expression.
    """
    assert divide_integrated_strength("k1l_var", 2.0) == "k1l_var / 2.0", (
        "String kl should produce a string expression.")

def test_divide_integrated_strength_zero_length_raises():
    """
    Zero length with nonzero kl should raise ZeroDivisionError. The caller is
    responsible for ensuring length is non-zero before calling this function.
    """
    with pytest.raises(ZeroDivisionError):
        divide_integrated_strength(0.5, 0.0)

################################################################################
# define_strength_variable
################################################################################
@pytest.mark.parametrize("zero_value", [0, 0.0])
def test_define_strength_variable_zero_skips_registration(zero_value):
    """
    Zero strength should be returned unchanged without touching the environment.
    """
    env    = xt.Environment()
    result = define_strength_variable(env, "ele", "k1", zero_value)

    assert result == zero_value, (
        "Zero strength should be returned unchanged.")
    assert "k1_ele" not in env.vars, (
        "Zero strength should not register a variable in the environment.")

def test_define_strength_variable_nonzero_float_registers_and_returns_key():
    """
    A nonzero float strength should be stored in the environment and the
    variable name returned so it can be passed to environment.new().
    """
    env    = xt.Environment()
    result = define_strength_variable(env, "qf", "k1", 0.25)

    assert result == "k1_qf", (
        "Returned key should follow the '{k_name}_{ele_name}' convention.")
    assert env["k1_qf"] == pytest.approx(0.25), (
        "Strength value should be stored in the environment under that key.")

def test_define_strength_variable_string_expression_registers_and_returns_key():
    """
    A string strength expression should be stored in the environment as a
    deferred expression and the variable name returned.
    """
    env            = xt.Environment()
    env["k1l_var"] = 0.5
    env["l_var"]   = 2.0
    result         = define_strength_variable(env, "qf", "k1", "k1l_var / l_var")

    assert result == "k1_qf", (
        "Returned key should follow the '{k_name}_{ele_name}' convention.")
    assert env["k1_qf"] == pytest.approx(0.25), (
        "The stored string expression should resolve to the correct value.")

################################################################################
# combine_k0_sk0
################################################################################
@pytest.mark.parametrize(
    "knl0, ksl0, rotation, expected_k0l, expected_rotation",
    [
        # Both numeric: computed directly, not deferred.
        (0.1, 0.05, 0.0,
         np.sqrt(0.1**2 + 0.05**2), np.arctan2(-0.05, 0.1)),
        # One or both of K0/SK0 deferred: string expression, still resolves.
        ("k0v", 0.05, 0.0,
         np.sqrt(0.1**2 + 0.05**2), np.arctan2(-0.05, 0.1)),
        (0.1, "sk0v", 0.0,
         np.sqrt(0.1**2 + 0.05**2), np.arctan2(-0.05, 0.1)),
        ("k0v", "sk0v", 0.0,
         np.sqrt(0.1**2 + 0.05**2), np.arctan2(-0.05, 0.1)),
        # Numeric K0/SK0 but deferred rotation: still forces string expression.
        (0.1, 0.05, "rotv",
         np.sqrt(0.1**2 + 0.05**2), 0.2 + np.arctan2(-0.05, 0.1)),
        # Only K0 nonzero: passed through unchanged, no rotation shift.
        (0.1, 0.0, 0.0,
         0.1, 0.0),
        # Only SK0 nonzero: passed through, rotation shifted by -pi/2.
        (0.0, 0.1, 0.0,
         0.1, -np.pi / 2),
        (0.0, 0.1, "rotv",
         0.1, 0.2 - np.pi / 2),
        # Neither nonzero.
        (0.0, 0.0, 0.0,
         0.0, 0.0),
    ])
def test_combine_k0_sk0(knl0, ksl0, rotation, expected_k0l, expected_rotation):
    """
    combine_k0_sk0 should resolve to the same magnitude/rotation whether K0,
    SK0, or rotation itself is numeric or a deferred SAD expression. String
    results are evaluated through a real Xsuite environment (not just
    compared as text) so a name the environment can't resolve (e.g. a stray
    `np.pi` instead of its numeric value) is actually caught.
    """
    env         = xt.Environment()
    env["k0v"]  = 0.1
    env["sk0v"] = 0.05
    env["rotv"] = 0.2

    k0l, rotation_out = combine_k0_sk0(knl0, ksl0, rotation)

    resolved_k0l      = env.eval(k0l)         if isinstance(k0l,         str) else k0l
    resolved_rotation = env.eval(rotation_out) if isinstance(rotation_out, str) else rotation_out

    assert resolved_k0l == pytest.approx(expected_k0l), (
        "combine_k0_sk0 should resolve to the numeric-equivalent magnitude, "
        "whether inputs are numeric or deferred expressions.")
    assert resolved_rotation == pytest.approx(expected_rotation), (
        "combine_k0_sk0 should resolve to the numeric-equivalent rotation, "
        "whether inputs are numeric or deferred expressions.")

################################################################################
# get_element_misalignments
################################################################################
def test_get_element_misalignments_defaults_to_zero():
    """
    Missing dx, dy, and rotate should all default to zero.
    """
    shift_x, shift_y, rotation = get_element_misalignments({})

    assert shift_x  == pytest.approx(0.0), "Default shift_x should be 0.0."
    assert shift_y  == pytest.approx(0.0), "Default shift_y should be 0.0."
    assert rotation == pytest.approx(0.0), "Default rotation should be 0.0."

def test_get_element_misalignments_negates_numeric_rotation():
    """
    A numeric SAD rotation should be negated on output, since SAD and Xsuite
    rotation conventions have opposite signs.
    """
    _, _, rotation = get_element_misalignments({"rotate": 0.1})

    assert rotation == pytest.approx(-0.1), (
        "Numeric SAD rotation should be negated to match Xsuite convention.")

def test_get_element_misalignments_applies_rotation_correction():
    """
    A nonzero rotation_correction should be added after negating the SAD rotation.
    """
    _, _, rotation = get_element_misalignments({"rotate": 0.1}, rotation_correction=0.05)

    assert rotation == pytest.approx(-0.1 + 0.05), (
        "rotation_correction should be added after negating the SAD rotation.")

def test_get_element_misalignments_negates_simple_string_rotation():
    """
    A simple string rotate expression should be wrapped in parentheses and negated.
    """
    _, _, rotation = get_element_misalignments({"rotate": "rot_var"})

    assert rotation == "-(rot_var) + 0.0", (
        "String rotate should be parenthesised before negation.")

def test_get_element_misalignments_negates_compound_string_rotation():
    """
    A compound string rotate expression must be fully parenthesised before negation.
    Without parentheses, '-(a + b)' and '-a + b' differ.
    """
    _, _, rotation = get_element_misalignments({"rotate": "rot_a + rot_b"})

    assert rotation == "-(rot_a + rot_b) + 0.0", (
        "Compound string rotate must be fully parenthesised before negation.")

################################################################################
# only_index_nonzero
################################################################################
def test_only_index_nonzero_returns_false_for_zero_length():
    """
    A zero-length element cannot have a physical multipole effect and should
    return False.
    """
    assert not only_index_nonzero(0.0, [1.0], [], 0, tol=1e-12), (
        "Zero numeric length should return False.")

def test_only_index_nonzero_string_length_does_not_crash():
    """
    A symbolic length cannot be evaluated at parse time and should be treated
    as non-zero. Regression test: the previous implementation called abs(length)
    directly on the string, raising TypeError.
    """
    assert only_index_nonzero("l_var", [1.0], [], 0, tol=1e-12), (
        "String length should be treated as non-zero and not raise TypeError.")

def test_only_index_nonzero_returns_true_when_only_idx_nonzero():
    """
    When only the target index carries strength, the element can be promoted
    to a typed element and the function should return True.
    """
    assert only_index_nonzero(1.0, [0.0, 0.5], [0.0, 0.0], 1, tol=1e-12), (
        "Should return True when only the target index is nonzero.")

def test_only_index_nonzero_returns_false_when_another_index_nonzero():
    """
    Strength at any non-target index means the element cannot be simplified
    to a single-order type and the function should return False.
    """
    assert not only_index_nonzero(1.0, [0.5, 0.5], [], 1, tol=1e-12), (
        "Should return False when a non-target index is also nonzero.")

def test_only_index_nonzero_returns_false_when_idx_itself_zero():
    """
    If the target index carries no strength, there is nothing to promote and
    the function should return False.
    """
    assert not only_index_nonzero(1.0, [0.0, 0.0], [], 1, tol=1e-12), (
        "Should return False when the target index is itself zero.")

def test_only_index_nonzero_string_value_at_non_idx_returns_false():
    """
    A string expression at a non-target index cannot be evaluated and must be
    treated as nonzero, preventing element promotion.
    """
    assert not only_index_nonzero(1.0, ["expr", 0.5], [], 1, tol=1e-12), (
        "A string value at a non-target index should be treated as nonzero, "
        "returning False.")

################################################################################
# species_from_mass_and_charge
################################################################################
def test_species_from_mass_and_charge_identifies_electron():
    """
    Electron mass with negative charge should identify as electron.
    """
    assert species_from_mass_and_charge(xt.ELECTRON_MASS_EV, -1.0) == "electron", (
        "Electron mass and negative charge should identify as 'electron'.")

def test_species_from_mass_and_charge_identifies_positron():
    """
    Electron mass with positive charge should identify as positron.
    """
    assert species_from_mass_and_charge(xt.ELECTRON_MASS_EV, +1.0) == "positron", (
        "Electron mass and positive charge should identify as 'positron'.")

def test_species_from_mass_and_charge_identifies_proton():
    """
    Proton mass with positive charge should identify as proton.
    """
    assert species_from_mass_and_charge(xt.PROTON_MASS_EV, +1.0) == "proton", (
        "Proton mass and positive charge should identify as 'proton'.")

def test_species_from_mass_and_charge_identifies_antiproton():
    """
    Proton mass with negative charge should identify as antiproton.
    """
    assert species_from_mass_and_charge(xt.PROTON_MASS_EV, -1.0) == "antiproton", (
        "Proton mass and negative charge should identify as 'antiproton'.")

def test_species_from_mass_and_charge_returns_none_for_unknown_mass():
    """
    An unrecognised particle mass should return None rather than guessing.
    """
    assert species_from_mass_and_charge(12345.0, +1.0) is None, (
        "An unrecognised particle mass should return None.")
