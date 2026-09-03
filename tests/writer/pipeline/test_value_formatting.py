"""
================================================================================
Tests for scalar value formatting in the writer
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
import pytest

from sad2xs.output_writer._000_helpers import get_knl_string, get_value_string

################################################################################
# Constants
################################################################################
ROUNDTRIP_VALUES = [
    0.0,
    -0.0,
    1.0,
    0.0015,
    -3.125E-05,
    1.0E-30,
    1.0E+20,
    1 / 3,
    np.float64(0.006),
    np.float32(0.25)]

################################################################################
# Numbers
################################################################################
@pytest.mark.parametrize("value", ROUNDTRIP_VALUES)
def test_get_value_string_reads_back_as_the_same_float(value):
    """Every emitted number must reload as the exact input float."""
    emitted = get_value_string(value)
    assert eval(emitted) == float(value), \
        f"{value!r} emitted as {emitted}, which reads back as {eval(emitted)}"


def test_get_value_string_is_shortest_representation():
    """A value with a short exact form is not padded out to fixed width."""
    assert get_value_string(0.0015) == "0.0015"
    assert get_value_string(0.0) == "0.0"


def test_get_value_string_keeps_values_below_fixed_point_resolution():
    """A tiny value must survive, not round to zero."""
    assert eval(get_value_string(1.0E-30)) == 1.0E-30


def test_get_value_string_writes_numpy_scalars_as_plain_floats():
    """A NumPy scalar must not emit its own repr wrapper."""
    assert "np.float64" not in get_value_string(np.float64(0.006))

################################################################################
# Non-finite values
################################################################################
def test_get_value_string_writes_positive_infinity_as_a_callable_literal():
    """Infinity has no literal spelling, so it is emitted as a float call."""
    assert eval(get_value_string(float("inf"))) == float("inf")


def test_get_value_string_writes_negative_infinity_as_a_callable_literal():
    """Negative infinity must keep its sign through the round trip."""
    assert eval(get_value_string(float("-inf"))) == float("-inf")


def test_get_value_string_writes_nan_as_a_callable_literal():
    """NaN has no literal spelling, so it is emitted as a float call."""
    assert np.isnan(eval(get_value_string(float("nan"))))

################################################################################
# Expressions
################################################################################
def test_get_value_string_writes_expressions_with_double_quotes():
    """An optics-variable expression is emitted as a double-quoted string."""
    assert get_value_string("k1_q1 * 0.5") == '"k1_q1 * 0.5"'

################################################################################
# KNL/KSL arrays
################################################################################
def test_get_knl_string_uses_the_same_formatting():
    """Multipole arrays share the scalar formatting."""
    assert get_knl_string(np.array([1.0, 0.0, 0.25, 0.0])) == "[1.0, 0.0, 0.25]"


def test_get_knl_string_omits_an_all_zero_array():
    """An all-zero array stays empty rather than listing zeros."""
    assert get_knl_string(np.zeros(4)) == "[]"
