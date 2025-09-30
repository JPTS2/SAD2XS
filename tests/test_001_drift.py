"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Required Packages
################################################################################
import os
import sad2xs as s2x
import xtrack as xt
import numpy as np
import textwrap
import matplotlib.pyplot as plt
from tqdm import tqdm

from _sad_helpers import sad_twiss
from _test_config import *

################################################################################
# PyTest Function
################################################################################
def test_drift():
    """
    Test the conversion of a SAD DRIFT element to XSuite.
    """

    ############################################################################
    # Scan
    ############################################################################
    S_SAD       = np.zeros_like(POSITIVE_TEST_VALUES)
    S_XS        = np.zeros_like(POSITIVE_TEST_VALUES)
    X_SAD       = np.zeros_like(POSITIVE_TEST_VALUES)
    X_XS        = np.zeros_like(POSITIVE_TEST_VALUES)
    Y_SAD       = np.zeros_like(POSITIVE_TEST_VALUES)
    Y_XS        = np.zeros_like(POSITIVE_TEST_VALUES)
    PX_SAD      = np.zeros_like(POSITIVE_TEST_VALUES)
    PX_XS       = np.zeros_like(POSITIVE_TEST_VALUES)
    PY_SAD      = np.zeros_like(POSITIVE_TEST_VALUES)
    PY_XS       = np.zeros_like(POSITIVE_TEST_VALUES)

    for iteration, TEST_VAL in enumerate(tqdm(POSITIVE_TEST_VALUES)):

        ########################################################################
        # Write Test Lattice
        ########################################################################
        with open("test_lattice.sad", "w") as f:
            f.write(textwrap.dedent(f"""\
            MOMENTUM    = 1.0 GEV;
            TEST_VAL    = {TEST_VAL};

            DRIFT       TEST_DRIFT  = (L = TEST_VAL);

            MARK        START       = ()
                        END         = ();

            LINE        TEST_LINE   = (START TEST_DRIFT END);
            """))

        ########################################################################
        # Twiss SAD Lattice
        ########################################################################
        tw_sad  = sad_twiss(
            lattice_filename    = 'test_lattice.sad',
            line_name           = 'TEST_LINE')

        ########################################################################
        # Convert Lattice
        ########################################################################
        line    = s2x.convert_sad_to_xsuite(
            sad_lattice_path    = 'test_lattice.sad',
            output_directory    = None,
            _verbose            = False,
            _test_mode          = True)

        ########################################
        # Twiss XSuite Lattice
        ########################################
        tw_xs   = line.twiss4d(
            _continue_if_lost   = True,
            start               = xt.START,
            end                 = xt.END,
            betx                = 1,
            bety                = 1)

        ########################################################################
        # Save data for comparison
        ########################################################################
        S_SAD[iteration]    = tw_sad["s", "END"]
        S_XS[iteration]     = tw_xs["s", "end"]
        X_SAD[iteration]    = tw_sad["x", "END"]
        X_XS[iteration]     = tw_xs["x", "end"]
        Y_SAD[iteration]    = tw_sad["y", "END"]
        Y_XS[iteration]     = tw_xs["y", "end"]
        PX_SAD[iteration]   = tw_sad["px", "END"]
        PX_XS[iteration]    = tw_xs["px", "end"]
        PY_SAD[iteration]   = tw_sad["py", "END"]
        PY_XS[iteration]    = tw_xs["py", "end"]

        ########################################################################
        # Delete test lattice
        ########################################################################
        os.remove("test_lattice.sad")

    ############################################################################
    # Assertions
    ############################################################################
    assert np.all(
        np.isclose(S_SAD, S_XS, rtol = DELTA_S_RTOL, atol = DELTA_S_ATOL)), \
        "s values do not match between SAD and XSuite."
    assert np.all(
        np.isclose(X_SAD, X_XS, rtol = DELTA_X_RTOL, atol = DELTA_X_ATOL)), \
        "x values do not match between SAD and XSuite."
    assert np.all(
        np.isclose(Y_SAD, Y_XS, rtol = DELTA_Y_RTOL, atol = DELTA_Y_ATOL)), \
        "y values do not match between SAD and XSuite."
    assert np.all(
        np.isclose(PX_SAD, PX_XS, rtol = DELTA_PX_RTOL, atol = DELTA_PX_ATOL)), \
        "px values do not match between SAD and XSuite."
    assert np.all(
        np.isclose(PY_SAD, PY_XS, rtol = DELTA_PY_RTOL, atol = DELTA_PY_ATOL)), \
        "py values do not match between SAD and XSuite."

    ############################################################################
    # Plot
    ############################################################################
    symlog_threshold    = np.nanmin(
        np.where(POSITIVE_TEST_VALUES > 0, POSITIVE_TEST_VALUES, np.nan))

    if not np.all(np.isclose(S_SAD, S_XS, rtol = DELTA_S_RTOL, atol = DELTA_S_ATOL)):
        fig, axs    = plt.subplots(
            nrows       = 2,
            ncols       = 1,
            figsize     = (12, 6),
        sharex      = True,
        gridspec_kw = {'height_ratios': [3, 1]})

        axs[0].plot(POSITIVE_TEST_VALUES, S_SAD, label = "SAD", color = "r")
        axs[0].plot(POSITIVE_TEST_VALUES, S_XS, label = "XS", color = "b", linestyle='--')
        axs[1].plot(POSITIVE_TEST_VALUES, S_XS - S_SAD)

        axs[1].set_xlabel("Drift Length [m]")
        axs[0].set_ylabel('s [m]')
        axs[1].set_ylabel('∆s [m]')

        for ax in axs:
            ax.set_xscale('symlog', linthresh = symlog_threshold)
            ax.set_yscale('symlog', linthresh = symlog_threshold)
            ax.grid()
        axs[0].legend()
        plt.subplots_adjust(hspace = 0)
        plt.savefig(f"outputs/test_001_drift_s.png", dpi = 300, bbox_inches = 'tight')

    plt.close("all")
