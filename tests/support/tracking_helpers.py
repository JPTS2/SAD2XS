"""
================================================================================
Shared Xsuite particle-tracking helper for conversion element tests
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
import xtrack as xt

################################################################################
# Build + Track
################################################################################
def track_xsuite_particles(line, x_init, px_init, y_init, py_init, zeta_init, delta_init):
    """
    Build an Xsuite positron bunch from the same initial coordinates passed to
    track_sad, track it for one turn, and return the tracked particles.
    """
    xs_particles = xt.Particles(
        "positron",
        p0c     = 1.0E9,
        x       = x_init.copy(),
        px      = px_init.copy(),
        y       = y_init.copy(),
        py      = py_init.copy(),
        zeta    = zeta_init.copy(),
        delta   = delta_init.copy())

    line.track(xs_particles, num_turns = 1)

    return xs_particles
