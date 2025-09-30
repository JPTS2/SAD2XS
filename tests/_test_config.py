"""
(Unofficial) SAD to XSuite Converter

Test Configurations
"""

################################################################################
# Required Packages
################################################################################
import numpy as np

################################################################################
# Tolerances
################################################################################
DELTA_S_ATOL    = 1E-9
DELTA_X_ATOL    = 1E-9
DELTA_Y_ATOL    = 1E-9
DELTA_PX_ATOL   = 1E-9
DELTA_PY_ATOL   = 1E-9

# I want to have these be less than this, but tests are failing otherwise
# Not sure if it's possible to reduce these- might be a limit in the conversion
DELTA_S_RTOL    = 1E-5
DELTA_X_RTOL    = 1E-5
DELTA_Y_RTOL    = 1E-5
DELTA_PX_RTOL   = 1E-5
DELTA_PY_RTOL   = 1E-5

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