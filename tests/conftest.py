"""
================================================================================
Shared pytest configuration
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-12
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import sys
from pathlib import Path

################################################################################
# Test Import Path
################################################################################
REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
