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
import pytest

from sad2xs.config import Config

################################################################################
# Converter Fixtures
################################################################################
@pytest.fixture
def sad2xs_config():
    """
    Return a quiet SAD2XS config suitable for deterministic conversion tests.
    """
    return Config(_verbose = False)
