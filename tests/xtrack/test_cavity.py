"""
================================================================================
Ground-truth test: Xsuite Cavity transverse RF-focusing
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-29
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
# Low reference momentum, strong VOLT (a large fraction of the reference
# energy in a single element) -- the regime where SAD's own RF-focusing
# kick (see docs/reference/sad-behaviour.md) is not negligible, so its absence in
# Xsuite is unambiguous rather than lost in numerical noise.
################################################################################
MOMENTUM_GEV = 0.05
MASS_MEV     = 0.51099895000
VOLT         = 1.0E8
FREQUENCY    = 2.856E9

################################################################################
# Cavity RF-Focusing
#
# Parametrised over RF phase (on-crest and zero-crossing) to pair with
# tests/sad/test_mult.py's ground truth: SAD's own RF-focusing kick is
# present at both phases (nonzero even at the zero-crossing, larger nearer
# the crest -- see tests/sad/test_mult.py and docs/reference/sad-behaviour.md).
# Xsuite's Cavity gives zero coupling at every phase, since the coupling
# calculation is disabled entirely, independent of the phase value passed.
################################################################################
@pytest.mark.parametrize(
    "phase", [np.pi / 2, 0.0], ids = ["on_crest", "zero_crossing"])
def test_xsuite_cavity_has_no_transverse_rf_focusing_coupling(phase):
    """
    Xsuite's Cavity applies zero transverse coupling in its energy kick, at
    every RF phase.

    Tracks a particle entering with a pure x offset and px=0, and asserts it
    leaves with exactly zero px. Confirmed by tracking, not by reading the
    source. If this fails, xtrack has gained the term and both the converter
    warning and docs/reference/sad-behaviour.md need revisiting.
    """
    env = xt.Environment()
    env.particle_ref = xt.Particles(
        mass0 = MASS_MEV * 1.0E6,
        q0    = 1,
        p0c   = MOMENTUM_GEV * 1.0E9)
    env.new(
        name        = "cav",
        prototype   = xt.Cavity,
        voltage     = VOLT,
        frequency   = FREQUENCY,
        phase       = phase)

    line = env.new_line(name = "test", components = ["cav"])
    line.particle_ref = env.particle_ref.copy()

    particles = line.build_particles(x = [1.0E-6], px = [0.0])
    line.track(particles)

    assert particles.state[0] == 1, "Particle should survive tracking."
    assert particles.px[0] == pytest.approx(0.0, abs = 1E-15), (
        "Xsuite's Cavity should apply exactly zero x -> px coupling. If "
        "this fails, xtrack has gained a transverse RF-focusing term and "
        "the RF-focusing warning/docs note need revisiting.")
