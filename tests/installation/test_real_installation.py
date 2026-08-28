"""
================================================================================
Real end-to-end SAD installation
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-08-27
================================================================================

Every other installer test monkeypatches its subprocess calls, and the SAD
smoke test uses the binary already present in the CI image. Neither exercises
the installer end to end. This file does: it clones and builds SAD, then runs
the committed smoke lattice through the launcher it generated.

Opt-in, because it needs the network and takes minutes. See
tests/installation/README.md for the manual procedure and its recorded result.
"""
################################################################################
# Required Packages
################################################################################
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("SAD2XS_REAL_INSTALL_TEST") != "1",
    reason = "Set SAD2XS_REAL_INSTALL_TEST=1 to build SAD from source (minutes, needs network)")

SMOKE_LATTICE   = Path(__file__).parent / "sad_installation_test.sad"
BUILD_TIMEOUT_S = 1800

################################################################################
# End-to-End Installation
################################################################################
def test_installer_builds_sad_and_the_launcher_runs_the_smoke_lattice(tmp_path):
    """
    A real install should produce a launcher that runs a SAD lattice.

    Covers what the monkeypatched tests cannot: that the toolchain
    environment actually compiles SAD, and that the generated launcher
    resolves its paths when invoked from an unrelated directory.
    """
    console_script = shutil.which("sad2xs-install-sad")
    assert console_script is not None, (
        "sad2xs-install-sad should be on PATH; reinstall the package.")

    prefix  = tmp_path / "prefix"
    bin_dir = tmp_path / "bin"

    # Shell configuration must be untouched. Absence is recorded alongside
    # content, so creating a file that was not there is caught too.
    rc_files = {
        path: path.read_bytes() if path.is_file() else None
        for path in (Path.home() / ".zshrc", Path.home() / ".bashrc")}

    install = subprocess.run(
        [console_script, "--prefix", str(prefix), "--bin-dir", str(bin_dir)],
        capture_output  = True,
        text            = True,
        timeout         = BUILD_TIMEOUT_S,
        check           = False)

    assert install.returncode == 0, (
        f"Install failed ({install.returncode}). Tail:\n"
        f"{install.stdout[-2000:]}\n{install.stderr[-2000:]}")

    launcher    = bin_dir / "sad"
    executable  = prefix / "src" / "bin" / "gs"

    assert os.access(executable, os.X_OK), (
        "The build should produce a runnable SAD binary.")
    assert os.access(launcher, os.X_OK), (
        "The install should produce a runnable launcher.")

    for path, content in rc_files.items():
        if content is None:
            assert not path.exists(), (
                f"The installer must not create {path}.")
        else:
            assert path.read_bytes() == content, (
                f"The installer must not modify {path}.")

    # Run from elsewhere: the launcher has to resolve its own paths rather
    # than rely on the directory it was invoked from.
    smoke = subprocess.run(
        [str(launcher), str(SMOKE_LATTICE)],
        cwd             = tmp_path,
        capture_output  = True,
        text            = True,
        timeout         = 120,
        check           = False)

    assert smoke.returncode == 0, (
        f"The smoke lattice should run to completion. Output:\n"
        f"{smoke.stdout[-2000:]}\n{smoke.stderr[-2000:]}")
