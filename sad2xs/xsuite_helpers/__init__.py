"""
(Unofficial) SAD to XSuite Converter: Xsuite Helpers Initialisation
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-16
"""

################################################################################
# Xsuite Helper Functions
################################################################################
from .comparison_plots import plot_xsuite_sad_comparison
from .reference_energy import (
    install_reference_energy_updates,
    update_reference_energy_updates)
from .symplecticity import check_symplecticity
from .twiss_alignment import align_xsuite_twiss_with_sad_twiss, compute_s_sad
from .twiss_assertions import assert_xsuite_matches_sad_twiss
