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

from _sad_helpers import twiss_sad, rebuild_sad_lattice
from _config import *

################################################################################
# Reference PyTest Function
################################################################################
def reference_cavi_test(
        test_name:                  str,
        sad_elements_line_string:   str,
        sad_eval_marker:            str                 = "END",
        test_values:                np.ndarray          = TEST_VALUES,
        plot:                       bool                = True,
        # twiss_init:                 xt.TwissInit | None = None,
        scan_zeta_init:             bool                = False,
        scan_delta_init:            bool                = False):
    """
    Reference Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """

    ############################################################################
    # Scan
    ############################################################################
    S_SAD       = np.zeros_like(test_values)
    S_XS        = np.zeros_like(test_values)
    ZETA_SAD    = np.zeros_like(test_values)
    ZETA_XS     = np.zeros_like(test_values)
    DELTA_SAD   = np.zeros_like(test_values)
    DELTA_XS    = np.zeros_like(test_values)

    for iteration, test_val in enumerate(tqdm(test_values)):

        ########################################################################
        # Write Test Lattice
        ########################################################################
        with open("test_lattice.sad", "w") as f:
            f.write(textwrap.dedent(f"""\
            MOMENTUM    = 1.0 GEV;
            TEST_VAL    = {test_val};
            """))

        with open("test_lattice.sad", "a") as f:
            f.write(sad_elements_line_string)

        ########################################################################
        # Twiss SAD Lattice
        ########################################################################
        if not scan_delta_init:
            tw_sad  = twiss_sad(
                lattice_filename        = 'test_lattice.sad',
                line_name               = 'TEST_LINE',
                method                  = "6d",
                closed                  = False,
                reverse_element_order   = False,
                reverse_bend_direction  = False,
                rf_enabled              = True,
                additional_commands     = "")
        else:
            tw_sad  = twiss_sad(
                lattice_filename        = 'test_lattice.sad',
                line_name               = 'TEST_LINE',
                method                  = "6d",
                closed                  = False,
                reverse_element_order   = False,
                reverse_bend_direction  = False,
                rf_enabled              = True,
                delta0                  = test_val)
        
        ########################################################################
        # Rebuild SAD Lattice
        ########################################################################
        rebuild_sad_lattice(
            lattice_filename    = 'test_lattice.sad',
            line_name           = 'TEST_LINE')

        ########################################################################
        # Convert Lattice
        ########################################################################
        line    = s2x.convert_sad_to_xsuite(
            sad_lattice_path    = 'test_lattice.sad',
            output_directory    = "N/A",
            _verbose            = False,
            _test_mode          = True)

        ########################################
        # Get table XSuite Lattice
        ########################################
        tt      = line.get_table(attr = True)

        ########################################
        # Twiss XSuite Lattice
        ########################################
        if scan_zeta_init and scan_delta_init:
            tw_xs   = line.twiss(
                method              = "6d",
                _continue_if_lost   = True,
                start               = xt.START,
                end                 = xt.END,
                betx                = 1,
                bety                = 1,
                zeta                = test_val,
                delta               = test_val)
        elif scan_zeta_init:
            tw_xs   = line.twiss(
                method              = "6d",
                _continue_if_lost   = True,
                start               = xt.START,
                end                 = xt.END,
                betx                = 1,
                bety                = 1,
                zeta                = test_val)
        elif scan_delta_init:
            tw_xs   = line.twiss(
                method              = "6d",
                _continue_if_lost   = True,
                start               = xt.START,
                end                 = xt.END,
                betx                = 1,
                bety                = 1,
                delta               = test_val)
        else:
            tw_xs   = line.twiss(
                method              = "6d",
                _continue_if_lost   = True,
                start               = xt.START,
                end                 = xt.END,
                betx                = 1,
                bety                = 1)
        
        ########################################
        # Calculate SAD s
        ########################################
        ds              = np.concatenate([[0], tw_xs.s[1:] - tw_xs.s[:-1]])
        dzeta           = np.concatenate([[0], tw_xs.zeta[1:] - tw_xs.zeta[:-1]])
        # Ignore the dzeta at ZetaShift elements
        zeta_shifts     = tt.element_type == "ZetaShift"
        zeta_shifts     = np.concatenate([[0], zeta_shifts[:-1]])
        dzeta           = np.where(zeta_shifts, 0, dzeta)

        s_sad           = np.zeros_like(tw_xs.s)
        for i in range(1, len(s_sad)):
            s_sad[i]    = s_sad[i-1] + ds[i] - dzeta[i]
        tw_xs["s_sad"]     = s_sad

        ########################################################################
        # Save data for comparison
        ########################################################################
        xs_eval_marker      = sad_eval_marker.lower()

        S_SAD[iteration]        = tw_sad["s", sad_eval_marker]
        S_XS[iteration]         = tw_xs["s_sad", xs_eval_marker]
        ZETA_SAD[iteration]     = tw_sad["zeta", sad_eval_marker]
        ZETA_XS[iteration]      = tw_xs["zeta", xs_eval_marker]
        DELTA_SAD[iteration]    = tw_sad["delta", sad_eval_marker]
        DELTA_XS[iteration]     = tw_xs["delta", xs_eval_marker]

        ########################################################################
        # Delete test lattice
        ########################################################################
        os.remove("test_lattice.sad")

        ########################################################################
        # Diagnostics: Outputs if the test fails
        ########################################################################
        if not (np.isclose(S_SAD[iteration], S_XS[iteration], rtol = DELTA_S_RTOL, atol = DELTA_S_ATOL) and \
                np.isclose(ZETA_SAD[iteration], ZETA_XS[iteration], rtol = DELTA_X_RTOL, atol = DELTA_X_ATOL) and \
                np.isclose(DELTA_SAD[iteration], DELTA_XS[iteration], rtol = DELTA_Y_RTOL, atol = DELTA_Y_ATOL)):

            print("SAD")
            tw_sad.cols["s zeta delta"].show()
            print("Xsuite")
            tw_xs.cols["s_sad zeta delta"].show()

    ############################################################################
    # Plot
    ############################################################################
    if plot:

        symlog_threshold    = np.nanmin(
            np.where(test_values > 0, test_values, np.nan))

        if not np.all(np.isclose(S_SAD, S_XS, rtol = DELTA_S_RTOL, atol = DELTA_S_ATOL)):
            fig, axs    = plt.subplots(
                nrows       = 2,
                ncols       = 1,
                figsize     = (12, 6),
            sharex      = True,
            gridspec_kw = {'height_ratios': [3, 1]})

            axs[0].plot(test_values, S_SAD, label = "SAD", color = "r")
            axs[0].plot(test_values, S_XS, label = "XS", color = "b", linestyle='--')
            axs[1].plot(test_values, S_XS - S_SAD)

            axs[1].set_xlabel("Drift Length [m]")
            axs[0].set_ylabel('s [m]')
            axs[1].set_ylabel('∆s [m]')

            for ax in axs:
                ax.set_yscale('symlog', linthresh = symlog_threshold)
                ax.grid()
            axs[0].legend()
            plt.subplots_adjust(hspace = 0)
            plt.savefig(f"outputs/{test_name}_s.png", dpi = 300, bbox_inches = 'tight')

        if not (
                np.all(np.isclose(ZETA_SAD, ZETA_XS, rtol = DELTA_X_RTOL, atol = DELTA_X_ATOL)) and
                np.all(np.isclose(DELTA_SAD, DELTA_XS, rtol = DELTA_Y_RTOL, atol = DELTA_Y_ATOL))):
            fig, axs    = plt.subplots(
                nrows       = 2,
                ncols       = 2,
                figsize     = (12, 6),
                sharex      = True,
            gridspec_kw = {'height_ratios': [3, 1]})

            axs[0, 0].plot(test_values, ZETA_SAD, label = "SAD", color = "r")
            axs[0, 0].plot(test_values, ZETA_XS, label = "XS", color = "b", linestyle='--')
            axs[1, 0].plot(test_values, ZETA_XS - ZETA_SAD)

            axs[0, 1].plot(test_values, DELTA_SAD, label = "SAD", color = "r")
            axs[0, 1].plot(test_values, DELTA_XS, label = "XS", color = "b", linestyle='--')
            axs[1, 1].plot(test_values, DELTA_XS - DELTA_SAD)

            axs[1, 0].set_xlabel("Transform Parameter")
            axs[1, 1].set_xlabel("Transform Parameter")
            axs[0, 0].set_ylabel('zeta [m]')
            axs[1, 0].set_ylabel('∆zeta [m]')
            axs[0, 1].set_ylabel('delta [m]')
            axs[1, 1].set_ylabel('∆delta [m]')

            for ax in axs.flatten():
                ax.set_yscale('symlog', linthresh = symlog_threshold)
                ax.grid()
            axs[0, 0].legend()
            axs[0, 1].legend()
            plt.subplots_adjust(hspace = 0)
            plt.savefig(f"outputs/{test_name}_zeta_delta.png", dpi = 300, bbox_inches = 'tight')

        plt.close("all")

    ############################################################################
    # Assertions
    ############################################################################
    assert np.all(
        np.isclose(S_SAD, S_XS, rtol = DELTA_S_RTOL, atol = DELTA_S_ATOL)), \
        "s values do not match between SAD and XSuite."
    assert np.all(
        np.isclose(ZETA_SAD, ZETA_XS, rtol = DELTA_ZETA_RTOL, atol = DELTA_ZETA_ATOL)), \
        "x values do not match between SAD and XSuite."
    assert np.all(
        np.isclose(DELTA_SAD, DELTA_XS, rtol = DELTA_DELTA_RTOL, atol = DELTA_DELTA_ATOL)), \
        "y values do not match between SAD and XSuite."

################################################################################
# Scan thin cavity lag
################################################################################
def test_thin_cavi_lag():
    """
    Test the conversion of a SAD SOL element with ref shifts at entry to XSuite.
    """
    reference_cavi_test(
        test_name                  = "test_008_cavi",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       TEST_DRIFT  = (L = 1.00);

            CAVI        TEST_CAVI   = (L = 0.00  VOLT = 10000000  PHI = TEST_VAL  FREQ = 100000000);

            MARK        START       = ()
                        END         = ();

            LINE        TEST_LINE   = (START TEST_DRIFT TEST_CAVI TEST_DRIFT END);
            """),
        sad_eval_marker            = "END",
        test_values                = np.linspace(-2 * np.pi, 2 * np.pi, 11),
        plot                       = True)

################################################################################
# Scan thick cavity lag
################################################################################
def test_thick_cavi_lag():
    """
    Test the conversion of a SAD SOL element with ref shifts at entry to XSuite.
    """
    reference_cavi_test(
        test_name                  = "test_008_cavi",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       TEST_DRIFT  = (L = 1.00);

            CAVI        TEST_CAVI   = (L = 1.00  VOLT = 10000000  PHI = TEST_VAL  FREQ = 100000000);

            MARK        START       = ()
                        END         = ();

            LINE        TEST_LINE   = (START TEST_DRIFT TEST_CAVI TEST_DRIFT END);
            """),
        sad_eval_marker            = "END",
        test_values                = np.linspace(-2 * np.pi, 2 * np.pi, 11),
        plot                       = True)

################################################################################
# Scan thin cavity zeta
################################################################################
def test_thin_cavi_zeta():
    """
    Test the conversion of a SAD SOL element with ref shifts at entry to XSuite.
    """
    reference_cavi_test(
        test_name                   = "test_008_cavi",
        sad_elements_line_string    = textwrap.dedent(f"""\
            DRIFT       TEST_DRIFT  = (L = 1.00);

            CAVI        TEST_CAVI   = (L = 0.00  VOLT = 10000000  PHI = 0.00  FREQ = 100000000);

            MARK        START       = (DZ = TEST_VAL)
                        END         = ();

            LINE        TEST_LINE   = (START TEST_DRIFT TEST_CAVI TEST_DRIFT END);
            """),
        sad_eval_marker             = "END",
        test_values                 = np.linspace(-1E-1, 1E-1, 11),
        plot                        = True,
        scan_zeta_init              = True)

################################################################################
# Scan thick cavity zeta
################################################################################
def test_thick_cavi_zeta():
    """
    Test the conversion of a SAD SOL element with ref shifts at entry to XSuite.
    """
    reference_cavi_test(
        test_name                  = "test_008_cavi",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       TEST_DRIFT  = (L = 1.00);

            CAVI        TEST_CAVI   = (L = 1.00  VOLT = 10000000  PHI = 0.00  FREQ = 100000000);

            MARK        START       = (DZ = TEST_VAL)
                        END         = ();

            LINE        TEST_LINE   = (START TEST_DRIFT TEST_CAVI TEST_DRIFT END);
            """),
        sad_eval_marker            = "END",
        test_values                = np.linspace(-1E-1, 1E-1, 11),
        plot                       = True,
        scan_zeta_init             = True)

################################################################################
# Scan thin cavity delta
################################################################################
def test_thin_cavi_delta():
    """
    Test the conversion of a SAD SOL element with ref shifts at entry to XSuite.
    """
    reference_cavi_test(
        test_name                   = "test_008_cavi",
        sad_elements_line_string    = textwrap.dedent(f"""\
            DRIFT       TEST_DRIFT  = (L = 1.00);

            CAVI        TEST_CAVI   = (L = 0.00  VOLT = 10000000  PHI = 0.00  FREQ = 100000000);

            MARK        START       = ()
                        END         = ();

            LINE        TEST_LINE   = (START TEST_DRIFT TEST_CAVI TEST_DRIFT END);
            """),
        sad_eval_marker             = "END",
        test_values                 = np.linspace(-1E-1, 1E-1, 11),
        plot                        = True,
        scan_delta_init             = True)

################################################################################
# Scan thick cavity delta
################################################################################
def test_thick_cavi_delta():
    """
    Test the conversion of a SAD SOL element with ref shifts at entry to XSuite.
    """
    reference_cavi_test(
        test_name                  = "test_008_cavi",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       TEST_DRIFT  = (L = 1.00);

            CAVI        TEST_CAVI   = (L = 1.00  VOLT = 10000000  PHI = 0.00  FREQ = 100000000);

            MARK        START       = ()
                        END         = ();

            LINE        TEST_LINE   = (START TEST_DRIFT TEST_CAVI TEST_DRIFT END);
            """),
        sad_eval_marker            = "END",
        test_values                = np.linspace(-1E-1, 1E-1, 11),
        plot                       = True,
        scan_delta_init            = True)
