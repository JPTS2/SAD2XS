"""
================================================================================
Tests for sad2xs.xsuite_helpers.symplecticity
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-17
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import xtrack as xt

from sad2xs.xsuite_helpers import check_symplecticity

################################################################################
# Helpers
################################################################################
def _build_fodo_line():
    """
    A small, linear (no radiation) FODO cell -- stable, genuinely symplectic.
    """
    env = xt.Environment()
    env.particle_ref = xt.Particles(p0c = 1.0E9)
    line = env.new_line(components = [
        env.new("qf", xt.Quadrupole, k1 = +0.8, length = 0.5, at = 0.25),
        env.new("qd", xt.Quadrupole, k1 = -0.8, length = 0.5, at = 2.25)])
    line.build_tracker()
    return line

################################################################################
# check_symplecticity
################################################################################
def test_linear_fodo_is_symplectic():
    """
    A linear (no radiation) one-turn matrix must be symplectic to numerical
    precision -- the standard default `atol` should accept it.
    """
    line    = _build_fodo_line()
    twiss   = line.twiss4d()

    is_symplectic, max_deviation   = check_symplecticity(twiss, line)

    assert is_symplectic
    assert max_deviation < 1.0E-6

def test_returns_bool_and_float():
    """
    check_symplecticity should return (is_symplectic, max_deviation) as a
    bool (or numpy's bool_ subtype) and a float.
    """
    line    = _build_fodo_line()
    twiss   = line.twiss4d()

    is_symplectic, max_deviation   = check_symplecticity(twiss, line)

    assert isinstance(is_symplectic, (bool, __import__("numpy").bool_))
    assert isinstance(max_deviation, float)

def test_element_by_element_fallback_runs_without_error():
    """
    An impossibly tight `atol` forces the overall check to fail, which must
    trigger the element-by-element fallback path without raising.
    """
    line    = _build_fodo_line()
    twiss   = line.twiss4d()

    is_symplectic, max_deviation   = check_symplecticity(twiss, line, atol = 0.0)

    assert not is_symplectic
    assert max_deviation >= 0.0

def test_accepts_precomputed_table():
    """A precomputed `tt` (line.get_table(attr=True)) is accepted and
    produces the same result as when check_symplecticity computes it
    internally."""
    line    = _build_fodo_line()
    twiss   = line.twiss4d()
    tt      = line.get_table(attr = True)

    is_symplectic, _   = check_symplecticity(twiss, line, tt = tt, atol = 0.0)

    assert not is_symplectic
