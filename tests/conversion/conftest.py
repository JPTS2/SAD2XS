"""
================================================================================
Shared fixtures for SAD conversion tests
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
import textwrap

import pytest

from sad2xs.config import Config

################################################################################
# File Fixtures
################################################################################
@pytest.fixture
def write_lattice(tmp_path):
    """
    Write a temporary SAD lattice file for conversion tests.
    """
    def _write_lattice(content, filename = "test_lattice.sad"):
        lattice_path = tmp_path / filename
        lattice_path.write_text(textwrap.dedent(content))
        return lattice_path

    return _write_lattice

################################################################################
# Converter Fixtures
################################################################################
@pytest.fixture
def sad2xs_config():
    """
    Return a quiet SAD2XS config suitable for deterministic conversion tests.
    """
    return Config(_verbose = False)
