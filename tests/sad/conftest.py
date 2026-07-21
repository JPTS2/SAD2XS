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

import pytest

from sad2xs.sad_helpers import twiss_sad

################################################################################
# Shared Constants
#
# Default values used across tests/sad/*.py that build their own lattice
# strings directly (rather than going through the sad_accepts/sad_rejects
# fixtures, which already hardcode MOMENTUM = 1.0 GEV via _run_sad_twiss
# below). Centralised here so every file uses the same defaults rather than
# each redefining its own copy.
################################################################################
DEFAULT_MOMENTUM_GEV    = 1.0
ELECTRON_MASS_MEV       = 0.51099895    # positron/electron mass
PROTON_MASS_MEV         = 938.27208816  # proton mass

################################################################################
# Helpers
################################################################################
def _run_sad_twiss(lattice_body: str, tmp_path) -> None:
    """
    Write a SAD lattice from `lattice_body` under a fixed MOMENTUM and run
    twiss_sad on it, to provoke SAD's own accept/reject verdict.
    """
    lattice = tmp_path / "test.sad"
    lattice.write_text(f"MOMENTUM = {DEFAULT_MOMENTUM_GEV} GEV;\n{lattice_body}\n")
    twiss_sad(
        lattice_filepath    = lattice.name,
        line_name           = "TEST",
        calc6d              = False,
        closed              = False,
        additional_commands = "")

def assert_particle_survived(result: dict, particle_index: int = 0) -> None:
    """
    Assert that a track_sad result reports the given particle as alive.

    SAD's "state" flag is 1 for a surviving particle and 0 for one lost on
    an aperture or other boundary. A lost particle's other returned
    coordinates (x, px, y, py, ...) are SAD-internal sentinel values, not
    physical results — any orbit/energy assertion made on a lost particle's
    coordinates is checking noise, not physics. Call this immediately after
    track_sad and before any assertion on the returned coordinates.
    """
    state = result["state"][particle_index]
    assert state == 1, (
        f"Particle {particle_index} was lost during tracking (state={state}), "
        "not survived (state=1). Its returned x/px/y/py/zeta/delta are SAD's "
        "lost-particle sentinel values, not physical results — check the "
        "lattice is valid before trusting any orbit assertion on this result.")

################################################################################
# Fixtures
################################################################################
@pytest.fixture
def sad_accepts(tmp_path):
    """
    Fixture returning a callable that asserts real SAD parses and twisses
    the given lattice body without error.
    """
    def _accepts(lattice_body: str):
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            _run_sad_twiss(lattice_body, tmp_path)
        except RuntimeError as e:
            # run_sad embeds SAD's stdout/stderr in the RuntimeError message
            raise AssertionError(
                f"SAD unexpectedly rejected lattice.\n{e}") from e
        finally:
            os.chdir(cwd)
    return _accepts


@pytest.fixture
def sad_rejects(tmp_path):
    """
    Fixture returning a callable that asserts real SAD rejects the given
    lattice body (raises RuntimeError or ValueError).
    """
    def _rejects(lattice_body: str):
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            _run_sad_twiss(lattice_body, tmp_path)
            raise AssertionError("SAD unexpectedly accepted lattice.")
        except (RuntimeError, ValueError):
            pass
        finally:
            os.chdir(cwd)
    return _rejects
