"""
================================================================================
Shared Type Definitions
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-01
================================================================================
"""

################################################################################
# Required Modules
################################################################################
from __future__ import annotations
from typing import Protocol

################################################################################
# Parsed SAD Value Type
################################################################################
# A parsed SAD parameter value: either numeric, or a deferred
# expression string (an unresolved reference to a variable/expression
# defined elsewhere in the lattice file) -- see
# `converter._000_helpers.parse_expression`.
SadValue = float | str

################################################################################
# Config Type
################################################################################
class ConfigLike(Protocol):
    """
    Default configuration settings for the SAD to XSuite converter.
    """

    _verbose:                       bool
    _test_mode:                     bool
    _replace_repeated_elements:     bool
    _install_offset_markers:        bool
    _import_sad_bend_fringes:       bool
    _import_sad_quad_fringes:       bool
    _import_sad_mult_fringes:       bool

    ASCII_LOGO:                     str

    SAD_ALLOWED_ELEMENTS:           set[str]

    ref_particle_mass0:             float | None
    ref_particle_q0:                float | None
    ref_particle_p0c:               float | None

    COORD_SIGNS:                    dict[str, int]

    TRANSFORM_SHIFT_TOL:            float
    TRANSFORM_ROT_TOL:              float

    MAX_KNL_ORDER:                  int
    KNL_ZERO_TOL:                   float

    SIMPLIFY_MULTIPOLES:            bool

    MODEL_DRIFT:                    str
    MODEL_BEND:                     str
    MODEL_QUAD:                     str
    MODEL_SEXT:                     str
    MODEL_OCT:                      str
    MODEL_MULT:                     str
    MODEL_CAVI:                     str

    INTEGRATOR_BEND:                str
    INTEGRATOR_QUAD:                str
    INTEGRATOR_SEXT:                str
    INTEGRATOR_OCT:                 str
    INTEGRATOR_MULT:                str
    INTEGRATOR_SOL:                 str
    INTEGRATOR_CAVI:                str

    N_INTEGRATOR_KICKS_BEND:        int
    N_INTEGRATOR_KICKS_QUAD:        int
    N_INTEGRATOR_KICKS_SEXT:        int
    N_INTEGRATOR_KICKS_OCT:         int
    N_INTEGRATOR_KICKS_MULT:        int
    N_INTEGRATOR_KICKS_SOL:         int

    ABSOLUTE_TIME_CAVI:             bool

    N_SLICES_MULT_RF:               int

    EDGE_MODEL_BEND:                str
    EDGE_MODEL_QUAD:                str

    OUTPUT_STRING_SEP:              int
    OUTPUT_STRING_LENGTH:           int
    ALLOWED_ELEMENTS:               set[str]

    MARKER_INSERTION_TOLERANCE:     float
    MAGNET_LENGTH_PRECISION:        float
