"""
================================================================================
Shared pytest configuration for tests/xsuite_helpers
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-22
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import matplotlib.pyplot as plt
import pytest

################################################################################
# Figure Cleanup
################################################################################
@pytest.fixture(autouse = True)
def _close_figures():
    """
    Close every matplotlib figure after each test -- comparison-plot tests
    create several figures per call and never show/save them, so without
    this pyplot's global figure registry grows unbounded across the file.
    """
    yield
    plt.close("all")
