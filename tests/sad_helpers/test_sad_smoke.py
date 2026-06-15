"""
================================================================================
Tests for SAD helper smoke behaviour
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-11
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import textwrap

import pytest

from sad2xs.sad_helpers import twiss_sad

################################################################################
# SAD Helper Smoke Tests
################################################################################
def test_twiss_sad_runs_minimal_lattice_and_returns_twiss_table(
        tmp_path,
        monkeypatch):
    """
    twiss_sad should run SAD on a minimal transfer-line lattice and return
    Twiss data for the requested line.
    """
    lattice_path = tmp_path / "sad_helper_smoke.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_DRIFT  = (L = 1.0);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT END);
        """))

    monkeypatch.chdir(tmp_path)

    twiss = twiss_sad(
        lattice_filepath = lattice_path.name,
        line_name        = "TEST_LINE",
        closed           = False,
        calc6d           = False,
        wall_time        = 30)

    assert "START" in twiss.name, (
        "twiss_sad should return a Twiss table containing the START marker.")
    assert "END" in twiss.name, (
        "twiss_sad should return a Twiss table containing the END marker.")
    assert twiss["s", "END"] == pytest.approx(1.0), (
        "twiss_sad should preserve the minimal lattice length in the returned "
        "Twiss table.")
