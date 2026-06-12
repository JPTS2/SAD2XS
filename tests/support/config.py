"""
================================================================================
Test Configuration File
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
import numpy as np

################################################################################
# Tolerances
################################################################################
DELTA_S_ATOL        = 1E-9
DELTA_X_ATOL        = 1E-9
DELTA_Y_ATOL        = 1E-9
DELTA_PX_ATOL       = 1E-9
DELTA_PY_ATOL       = 1E-9
DELTA_ZETA_ATOL     = 1E-9
DELTA_DELTA_ATOL    = 1E-9

# Not sure if it's possible to reduce these- might be a limit in the conversion
DELTA_S_RTOL        = 1E-5
DELTA_X_RTOL        = 1E-5
DELTA_Y_RTOL        = 1E-5
DELTA_PX_RTOL       = 1E-5
DELTA_PY_RTOL       = 1E-5
DELTA_ZETA_RTOL     = 1E-5
DELTA_DELTA_RTOL    = 1E-5

################################################################################
# Test Values to scan over
################################################################################
def generate_symlog_array(lower_power, upper_power, n_points):
    pos = np.logspace(upper_power, lower_power, n_points // 2)
    pos = pos[::-1]
    neg = -pos[::-1]

    if n_points % 2 == 1:
        return np.concatenate([neg, [0.0], pos])
    else:
        return np.concatenate([neg, pos])

TEST_VALUES             = generate_symlog_array(-6, -1, 11)
POSITIVE_TEST_VALUES    = np.logspace(-6, -1, 11)
STATIC_OFFSET           = float(1E-2)

################################################################################
# Protected Names
################################################################################
PROTECTED_ELEMENT_NAMES = {
    "fshift",
    "mass0",
    "p0c",
    "q0",
}
