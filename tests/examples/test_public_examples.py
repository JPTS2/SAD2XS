"""
================================================================================
Tests for public example lattice assets
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-15
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
REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_EXAMPLE_LATTICE_DIR = REPO_ROOT / "examples" / "lattices"

PUBLIC_EXAMPLE_LATTICES = [
    "fccee_zh.sad",
    "fccee_tt_collimation.sad",
    "fccee_sol.sad",
]

################################################################################
# Public Example Lattice Smoke Tests
################################################################################
@pytest.mark.parametrize("lattice_filename", PUBLIC_EXAMPLE_LATTICES)
def test_public_example_lattice_converts_in_test_mode(lattice_filename):
    """
    Public committed example lattices should remain loadable by the converter.
    """
    lattice_path = PUBLIC_EXAMPLE_LATTICE_DIR / lattice_filename

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _verbose         = False,
        _test_mode       = True)

    assert isinstance(line, xt.Line), (
        f"Public example lattice {lattice_filename} should convert to an "
        "Xsuite Line.")
    assert len(line.element_names) > 0, (
        f"Public example lattice {lattice_filename} should produce a non-empty "
        "Xsuite line.")
    assert line.particle_ref is not None, (
        f"Public example lattice {lattice_filename} should attach a reference "
        "particle.")


def test_public_example_scripts_reference_committed_lattices():
    """
    Public example scripts should reference lattice files committed under
    examples/lattices.
    """
    script_to_lattice = {
        "001_fccee_zh.py":             "fccee_zh.sad",
        "002_fccee_tt_collimation.py": "fccee_tt_collimation.sad",
        "003_fccee_sol.py":            "fccee_sol.sad",
        "004_fccee_sol_e-e+.py":       "fccee_sol.sad",
    }

    for script_name, lattice_filename in script_to_lattice.items():
        script_path = REPO_ROOT / "examples" / script_name
        lattice_path = PUBLIC_EXAMPLE_LATTICE_DIR / lattice_filename

        assert script_path.exists(), (
            f"Public example script {script_name} should be committed.")
        assert lattice_path.exists(), (
            f"Public example script {script_name} should reference committed "
            f"lattice {lattice_filename}.")
