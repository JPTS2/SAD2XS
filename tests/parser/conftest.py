"""
================================================================================
Shared fixtures for SAD parser tests
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

################################################################################
# Fixtures
################################################################################
@pytest.fixture
def write_lattice(tmp_path):
    """
    Write a temporary SAD lattice file for parser tests.
    """
    def _write_lattice(content, filename = "test_lattice.sad"):
        lattice_path = tmp_path / filename
        lattice_path.write_text(textwrap.dedent(content))
        return lattice_path

    return _write_lattice
