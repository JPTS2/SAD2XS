"""
================================================================================
Tests for SAD executable availability
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
import shutil
import subprocess
from pathlib import Path

################################################################################
# SAD Executable Smoke Tests
################################################################################
def test_sad_executable_runs_installation_smoke_lattice(tmp_path):
    """
    The installed SAD executable should run the committed installation smoke
    lattice without returning an error.
    """
    lattice_path = Path(__file__).with_name("sad_installation_test.sad")
    sad_executable = shutil.which("sad")

    assert sad_executable is not None, (
        "The SAD executable should be available on PATH for installation smoke "
        "tests. Expected to resolve command: sad.")

    result = subprocess.run(
        [sad_executable, str(lattice_path)],
        capture_output = True,
        text           = True,
        cwd            = tmp_path,
        timeout        = 30)

    assert result.returncode == 0, (
        "The SAD executable should run the installation smoke lattice "
        "successfully. "
        f"cwd={tmp_path}; "
        f"returncode={result.returncode}; "
        f"stdout={result.stdout[-1000:]!r}; "
        f"stderr={result.stderr[-1000:]!r}.")
