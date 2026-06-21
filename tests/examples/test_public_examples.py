"""
================================================================================
Tests for public example lattice assets
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
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
from sad2xs.config import Config

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
# Public Example Lattice Conversion Smoke Tests
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


################################################################################
# Public Example Write and Reload Tests
################################################################################
@pytest.mark.parametrize("lattice_filename", PUBLIC_EXAMPLE_LATTICES)
def test_public_example_lattice_writes_and_reloads(lattice_filename, tmp_path):
    """
    The full user workflow for public example lattices should succeed: convert,
    write with write_lattice and write_optics, reload in a fresh Xsuite
    environment, and recover a non-empty line with a reference particle. This
    tests the path a user follows when running the committed examples.
    """
    lattice_path = PUBLIC_EXAMPLE_LATTICE_DIR / lattice_filename

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _verbose         = False,
        _test_mode       = True)

    output_dir   = tmp_path / "output"
    output_dir.mkdir()
    stem         = Path(lattice_filename).stem
    lattice_out  = f"{stem}_lattice"
    optics_out   = f"{stem}_optics"

    s2x.write_lattice(
        line                    = line,
        output_filename         = lattice_out,
        output_directory        = str(output_dir),
        output_header           = f"Write+reload test: {lattice_filename}",
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = optics_out,
        output_directory  = str(output_dir),
        output_header     = f"Write+reload test: {lattice_filename}",
        config            = Config(_verbose = False))

    env = xt.Environment()
    env.call(str(output_dir / f"{lattice_out}.py"))
    env.call(str(output_dir / f"{optics_out}.py"))

    reloaded = env.lines["line"]

    assert len(reloaded.element_names) > 0, (
        f"Reloaded line from {lattice_filename} should be non-empty. "
        f"Got {len(reloaded.element_names)} elements.")
    assert reloaded.particle_ref is not None, (
        f"Reloaded line from {lattice_filename} should carry a reference "
        "particle after write+reload.")


################################################################################
# Public Example Script Contract Tests
################################################################################
def test_public_example_scripts_reference_committed_lattices():
    """
    Public example scripts should reference lattice files committed under
    examples/lattices. Each script file must exist, the lattice it references
    must exist, and the lattice filename must appear verbatim in the script
    content. The content check catches a script that references a lattice by
    a name that no longer exists or was renamed.
    """
    script_to_lattice = {
        "001_fccee_zh.py":             "fccee_zh.sad",
        "002_fccee_tt_collimation.py": "fccee_tt_collimation.sad",
        "003_fccee_sol.py":            "fccee_sol.sad",
        "004_fccee_sol_e-e+.py":       "fccee_sol.sad",
    }

    for script_name, lattice_filename in script_to_lattice.items():
        script_path  = REPO_ROOT / "examples" / script_name
        lattice_path = PUBLIC_EXAMPLE_LATTICE_DIR / lattice_filename

        assert script_path.exists(), (
            f"Public example script {script_name} should be committed.")
        assert lattice_path.exists(), (
            f"Public example script {script_name} should reference committed "
            f"lattice {lattice_filename}.")

        content = script_path.read_text(encoding = "utf-8")
        assert lattice_filename in content, (
            f"Public example script {script_name} should reference lattice "
            f"'{lattice_filename}' by name in its content. This catches a "
            "script pointing to a lattice that was renamed or removed.")
