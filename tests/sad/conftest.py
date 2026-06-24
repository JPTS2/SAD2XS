"""
================================================================================
Shared fixtures for SAD syntax assumption tests
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-24
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import os
import subprocess

import pytest

from sad2xs.sad_helpers import twiss_sad

################################################################################
# Helpers
################################################################################
def _run_sad_twiss(lattice_body: str, tmp_path) -> None:
    lattice = tmp_path / "test.sad"
    lattice.write_text(f"MOMENTUM = 1.0 GEV;\n{lattice_body}\n")
    twiss_sad(
        lattice_filepath    = lattice.name,
        line_name           = "TEST",
        calc6d              = False,
        closed              = False,
        additional_commands = "")

################################################################################
# Fixtures
################################################################################
@pytest.fixture
def sad_accepts(tmp_path):
    def _accepts(lattice_body: str):
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            _run_sad_twiss(lattice_body, tmp_path)
        except subprocess.CalledProcessError as e:
            raise AssertionError(
                f"SAD unexpectedly rejected lattice.\n"
                f"stdout: {e.stdout}\nstderr: {e.stderr}") from e
        finally:
            os.chdir(cwd)
    return _accepts


@pytest.fixture
def sad_rejects(tmp_path):
    def _rejects(lattice_body: str):
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            _run_sad_twiss(lattice_body, tmp_path)
            raise AssertionError("SAD unexpectedly accepted lattice.")
        except (subprocess.CalledProcessError, ValueError):
            pass
        finally:
            os.chdir(cwd)
    return _rejects
