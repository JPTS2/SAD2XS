"""
================================================================================
Tests for public example lattice assets
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import os
import re
import runpy
import sys
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
PUBLIC_EXAMPLE_DIR = REPO_ROOT / "examples"

PUBLIC_EXAMPLE_LATTICES = [
    "fccee_zh.sad",
    "fccee_tt_collimation.sad",
    "fccee_sol.sad",
]

PUBLIC_EXAMPLE_SCRIPTS = sorted(
    path
    for path in PUBLIC_EXAMPLE_DIR.glob("[0-9][0-9][0-9]_*.py")
    if path.is_file())

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
@pytest.mark.parametrize("script_path", PUBLIC_EXAMPLE_SCRIPTS, ids = lambda p: p.name)
def test_public_example_script_runs_headlessly(script_path, tmp_path):
    """
    Public example scripts should run as committed. The scripts own their
    physics assertions; this test only disables interactive plot display and
    redirects generated output to pytest's temporary directory.
    """
    assert PUBLIC_EXAMPLE_SCRIPTS, "At least one public example script is expected."

    original_cwd = os.getcwd()
    original_sys_path = list(sys.path)
    try:
        if str(PUBLIC_EXAMPLE_DIR) not in sys.path:
            sys.path.insert(0, str(PUBLIC_EXAMPLE_DIR))

        runpy.run_path(
            str(script_path),
            init_globals = {
                "SHOW_PLOTS": False,
                "RUN_ASSERTS": True,
                "OUTPUT_DIR": str(tmp_path / script_path.stem),
            })
    finally:
        os.chdir(original_cwd)
        sys.path[:] = original_sys_path

def test_public_example_scripts_reference_committed_lattices():
    """
    Public example scripts should reference lattice files committed under
    examples/lattices. This catches scripts pointing to lattices that were
    renamed or removed.
    """
    assert PUBLIC_EXAMPLE_SCRIPTS, "At least one public example script is expected."

    for script_path in PUBLIC_EXAMPLE_SCRIPTS:
        content = script_path.read_text(encoding = "utf-8")
        referenced_lattices = sorted(
            lattice_filename
            for lattice_filename in set(re.findall(r"lattices/([^\"']+\.sad)", content))
            if "_rebuilt" not in lattice_filename)

        assert referenced_lattices, (
            f"Public example script {script_path.name} should reference at "
            "least one SAD lattice under examples/lattices.")

        for lattice_filename in referenced_lattices:
            lattice_path = PUBLIC_EXAMPLE_LATTICE_DIR / lattice_filename
            assert lattice_path.exists(), (
                f"Public example script {script_path.name} should reference "
                f"committed lattice {lattice_filename}.")
