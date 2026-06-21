"""
================================================================================
Tests for synthetic example lattices
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
from pathlib import Path

import pytest
import xtrack as xt

import sad2xs as s2x

################################################################################
# Test Data
################################################################################
EXAMPLE_LATTICE_DIR = Path(__file__).with_name("lattices")

SYNTHETIC_FCC_LATTICES = [
    "fcc_h_dummy.sad",
    "fcc_tt_coll_dummy.sad",
    "fcc_sol_dummy.sad",
]

################################################################################
# Synthetic Lattice Smoke Tests
################################################################################
@pytest.mark.parametrize("lattice_filename", SYNTHETIC_FCC_LATTICES)
def test_synthetic_fcc_style_lattice_converts(lattice_filename):
    """
    Synthetic FCC-style lattices should convert without relying on generated
    temporary files, plots, or legacy test helpers.
    """
    lattice_path = EXAMPLE_LATTICE_DIR / lattice_filename

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _verbose         = False,
        _test_mode       = True)

    assert isinstance(line, xt.Line), (
        f"Synthetic example lattice {lattice_filename} should convert to an "
        "Xsuite Line.")
    assert line.element_names[0] == "start", (
        f"Synthetic example lattice {lattice_filename} should preserve the "
        "START marker at the beginning of RING.")
    assert line.element_names[-1] == "end", (
        f"Synthetic example lattice {lattice_filename} should preserve the "
        "END marker at the end of RING.")
    assert line.particle_ref is not None, (
        f"Synthetic example lattice {lattice_filename} should attach a "
        "reference particle.")
