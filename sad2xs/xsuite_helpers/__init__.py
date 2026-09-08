"""
================================================================================
Xsuite Helpers Package Initialisation
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-04
================================================================================
"""

################################################################################
# Xsuite Helper Functions
################################################################################
from .comparison_plots import PLOT_GROUPS, plot_xsuite_sad_comparison
from .coupled_optics import propagate_edwards_teng
from .reference_energy import (
    install_reference_energy_updates,
    update_reference_energy_updates)
from .symplecticity import check_symplecticity
from .twiss_alignment import align_xsuite_twiss_with_sad_twiss, compute_s_sad
from .twiss_assertions import assert_xsuite_matches_sad_twiss, DEFAULT_TWISS_TOLERANCES
