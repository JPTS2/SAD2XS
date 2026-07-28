"""
================================================================================
Ground-truth test: Xsuite model defaults and integrator kick batching
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-28
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import pytest
import xtrack as xt

################################################################################
# Test Parameters
#
# An angle-dominated starting particle: the difference between the exact and
# expanded transverse maps grows with angle, so a large px/py makes the
# `adaptive` default's choice unambiguous rather than lost in noise.
################################################################################
MOMENTUM_EV = 1.0E9
LENGTH_M    = 1.0

START_PARTICLE = dict(x = 0.0, px = 1.0E-2, y = 0.0, py = 1.0E-2)

# Observed separation between the exact and expanded results at these
# parameters is ~1.5e-6; the exact-vs-exact agreement is ~1e-17. The
# tolerance sits well clear of both.
EXACT_ATOL = 1.0E-12


################################################################################
# Helpers
################################################################################
def _track_single(element):
    """
    Track one particle through a single element and return its final x.
    """
    line = xt.Line(elements = [element], element_names = ["e1"])
    line.particle_ref = xt.Particles("electron", p0c = MOMENTUM_EV)
    line.build_tracker()
    particle = line.build_particles(**START_PARTICLE)
    line.track(particle)
    return float(particle.x[0])


################################################################################
# The `adaptive` model default
#
# SAD2XS sets `model` explicitly on every element it emits. These tests pin
# the reason: the Xsuite default does not resolve to the exact map.
# See docs/converter/models-integrators.md.
################################################################################
def test_drift_adaptive_default_matches_expanded_not_exact():
    """
    An `xt.Drift` left at its default model should track identically to
    `model='expanded'`, and measurably differently from `model='exact'`.

    If this fails, Xsuite's default has changed and SAD2XS's rationale for
    setting `model` explicitly needs revisiting.
    """
    default  = _track_single(xt.Drift(length = LENGTH_M))
    expanded = _track_single(xt.Drift(length = LENGTH_M, model = "expanded"))
    exact    = _track_single(xt.Drift(length = LENGTH_M, model = "exact"))

    assert default == pytest.approx(expanded, abs = EXACT_ATOL), (
        "xt.Drift at its default model should match model='expanded'. "
        f"Got default x = {default!r}, expanded x = {expanded!r}.")
    assert abs(default - exact) > EXACT_ATOL, (
        "xt.Drift at its default model should differ from model='exact'. "
        f"Got default x = {default!r}, exact x = {exact!r} — if these now "
        "agree, the Xsuite default has changed.")


def test_quadrupole_adaptive_default_matches_expanded_not_exact():
    """
    An unpowered `xt.Quadrupole` left at its default model should track
    identically to the expanded map, not the exact one.

    Unpowered is used deliberately: with `k1 = 0` the element is physically a
    drift, so any difference between models is the map choice alone.
    """
    default  = _track_single(xt.Quadrupole(length = LENGTH_M, k1 = 0.0))
    expanded = _track_single(xt.Quadrupole(
        length = LENGTH_M, k1 = 0.0, model = "drift-kick-drift-expanded"))
    exact    = _track_single(xt.Quadrupole(
        length = LENGTH_M, k1 = 0.0, model = "drift-kick-drift-exact"))

    assert default == pytest.approx(expanded, abs = EXACT_ATOL), (
        "xt.Quadrupole at its default model should match the expanded map. "
        f"Got default x = {default!r}, expanded x = {expanded!r}.")
    assert abs(default - exact) > EXACT_ATOL, (
        "xt.Quadrupole at its default model should differ from the exact "
        f"map. Got default x = {default!r}, exact x = {exact!r} — if these "
        "now agree, the Xsuite default has changed.")


################################################################################
# yoshida4 kick batching
#
# SAD2XS uses 14 kicks for yoshida4-tracked elements. The number is chosen
# for its slice count, not its face value: yoshida4 batches kicks into groups
# of seven, so every count in 8..14 costs the same and gives the same result.
# See docs/converter/models-integrators.md.
################################################################################
@pytest.mark.parametrize("kicks", [8, 10, 12, 14])
def test_yoshida4_kick_counts_in_one_slice_band_are_identical(kicks):
    """
    Every `num_multipole_kicks` in 8..14 maps to two yoshida4 slices and must
    give an identical result. This is what makes 14 free relative to 10.
    """
    reference = _track_single(xt.Sextupole(
        length = LENGTH_M, k2 = 1.0, model = "mat-kick-mat",
        integrator = "yoshida4", num_multipole_kicks = 8))
    tracked = _track_single(xt.Sextupole(
        length = LENGTH_M, k2 = 1.0, model = "mat-kick-mat",
        integrator = "yoshida4", num_multipole_kicks = kicks))

    assert tracked == reference, (
        f"yoshida4 with {kicks} kicks should be identical to 8 kicks: both "
        "map to two internal slices. If this fails, yoshida4's batching has "
        "changed and the kick-count rationale needs revisiting.")


def test_yoshida4_next_slice_band_differs():
    """
    Crossing from two slices to three must change the result.

    Without this, the test above would also pass if yoshida4 ignored
    `num_multipole_kicks` entirely.
    """
    two_slices = _track_single(xt.Sextupole(
        length = LENGTH_M, k2 = 1.0, model = "mat-kick-mat",
        integrator = "yoshida4", num_multipole_kicks = 14))
    three_slices = _track_single(xt.Sextupole(
        length = LENGTH_M, k2 = 1.0, model = "mat-kick-mat",
        integrator = "yoshida4", num_multipole_kicks = 21))

    assert two_slices != three_slices, (
        "yoshida4 at 14 kicks (two slices) and 21 kicks (three slices) "
        "should differ. If they agree, num_multipole_kicks is not reaching "
        "the integrator.")
