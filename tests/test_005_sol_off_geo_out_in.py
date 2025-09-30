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

from _sad_helpers import sad_twiss, rebuild_sad_lattice
from _test_config import *

################################################################################
# Reference PyTest Function
################################################################################
def reference_sol_test(
        test_name:                  str,
        sad_elements_line_string:   str,
        sad_eval_marker:            str         = "END",
        test_values:                np.ndarray  = TEST_VALUES,
        static_val:                 float       = STATIC_OFFSET,
        plot:                       bool        = True):
    """
    Reference Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """

    ############################################################################
    # Scan
    ############################################################################
    S_SAD       = np.zeros_like(test_values)
    S_XS        = np.zeros_like(test_values)
    X_SAD       = np.zeros_like(test_values)
    X_XS        = np.zeros_like(test_values)
    Y_SAD       = np.zeros_like(test_values)
    Y_XS        = np.zeros_like(test_values)
    PX_SAD      = np.zeros_like(test_values)
    PX_XS       = np.zeros_like(test_values)
    PY_SAD      = np.zeros_like(test_values)
    PY_XS       = np.zeros_like(test_values)

    for iteration, test_val in enumerate(tqdm(test_values)):

        ########################################################################
        # Write Test Lattice
        ########################################################################
        with open("test_lattice.sad", "w") as f:
            f.write(textwrap.dedent(f"""\
            MOMENTUM    = 1.0 GEV;
            TEST_VAL    = {test_val};
            STATIC_VAL  = {static_val};
            """))

        with open("test_lattice.sad", "a") as f:
            f.write(sad_elements_line_string)

        ########################################################################
        # Twiss SAD Lattice
        ########################################################################
        tw_sad  = sad_twiss(
            lattice_filename    = 'test_lattice.sad',
            line_name           = 'TEST_LINE')

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
        # Diagnostics: Outputs if the test fails
        ########################################################################
        print("SAD")
        tw_sad.cols["s x px y py"].show()
        print("Xsuite")
        tw_xs.cols["s x px y py"].show()

        ########################################################################
        # Save data for comparison
        ########################################################################
        xs_eval_marker      = sad_eval_marker.lower()

        S_SAD[iteration]    = tw_sad["s", sad_eval_marker]
        S_XS[iteration]     = tw_xs["s", xs_eval_marker]
        X_SAD[iteration]    = tw_sad["x", sad_eval_marker]
        X_XS[iteration]     = tw_xs["x", xs_eval_marker]
        Y_SAD[iteration]    = tw_sad["y", sad_eval_marker]
        Y_XS[iteration]     = tw_xs["y", xs_eval_marker]
        PX_SAD[iteration]   = tw_sad["px", sad_eval_marker]
        PX_XS[iteration]    = tw_xs["px", xs_eval_marker]
        PY_SAD[iteration]   = tw_sad["py", sad_eval_marker]
        PY_XS[iteration]    = tw_xs["py", xs_eval_marker]

        ########################################################################
        # Delete test lattice
        ########################################################################
        os.remove("test_lattice.sad")

    ############################################################################
    # Plot
    ############################################################################
    if plot:

        symlog_threshold    = np.nanmin(
            np.where(TEST_VALUES > 0, TEST_VALUES, np.nan))

        if not np.all(np.isclose(S_SAD, S_XS, rtol = DELTA_S_RTOL, atol = DELTA_S_ATOL)):
            fig, axs    = plt.subplots(
                nrows       = 2,
                ncols       = 1,
                figsize     = (12, 6),
            sharex      = True,
            gridspec_kw = {'height_ratios': [3, 1]})

            axs[0].plot(TEST_VALUES, S_SAD, label = "SAD", color = "r")
            axs[0].plot(TEST_VALUES, S_XS, label = "XS", color = "b", linestyle='--')
            axs[1].plot(TEST_VALUES, S_XS - S_SAD)

            axs[1].set_xlabel("Drift Length [m]")
            axs[0].set_ylabel('s [m]')
            axs[1].set_ylabel('∆s [m]')

            for ax in axs:
                ax.set_xscale('symlog', linthresh = symlog_threshold)
                ax.set_yscale('symlog', linthresh = symlog_threshold)
                ax.grid()
            axs[0].legend()
            plt.subplots_adjust(hspace = 0)
            plt.savefig(f"outputs/{test_name}_s.png", dpi = 300, bbox_inches = 'tight')

        if not (
                np.all(np.isclose(X_SAD, X_XS, rtol = DELTA_X_RTOL, atol = DELTA_X_ATOL)) and
                np.all(np.isclose(Y_SAD, Y_XS, rtol = DELTA_Y_RTOL, atol = DELTA_Y_ATOL))):
            fig, axs    = plt.subplots(
                nrows       = 2,
                ncols       = 2,
                figsize     = (12, 6),
                sharex      = True,
            gridspec_kw = {'height_ratios': [3, 1]})

            axs[0, 0].plot(TEST_VALUES, X_SAD, label = "SAD", color = "r")
            axs[0, 0].plot(TEST_VALUES, X_XS, label = "XS", color = "b", linestyle='--')
            axs[1, 0].plot(TEST_VALUES, X_XS - X_SAD)

            axs[0, 1].plot(TEST_VALUES, Y_SAD, label = "SAD", color = "r")
            axs[0, 1].plot(TEST_VALUES, Y_XS, label = "XS", color = "b", linestyle='--')
            axs[1, 1].plot(TEST_VALUES, Y_XS - Y_SAD)

            axs[1, 0].set_xlabel("Transform Parameter")
            axs[1, 1].set_xlabel("Transform Parameter")
            axs[0, 0].set_ylabel('x [m]')
            axs[1, 0].set_ylabel('∆x [m]')
            axs[0, 1].set_ylabel('y [m]')
            axs[1, 1].set_ylabel('∆y [m]')

            for ax in axs.flatten():
                ax.set_xscale('symlog', linthresh = symlog_threshold)
                ax.set_yscale('symlog', linthresh = symlog_threshold)
                ax.grid()
            axs[0, 0].legend()
            axs[0, 1].legend()
            plt.subplots_adjust(hspace = 0)
            plt.savefig(f"outputs/{test_name}_xy.png", dpi = 300, bbox_inches = 'tight')

        if not (
                np.all(np.isclose(PX_SAD, PX_XS, rtol = DELTA_X_RTOL, atol = DELTA_X_ATOL)) and
                np.all(np.isclose(PY_SAD, PY_XS, rtol = DELTA_Y_RTOL, atol = DELTA_Y_ATOL))):
            fig, axs    = plt.subplots(
                nrows       = 2,
                ncols       = 2,
                figsize     = (12, 6),
                sharex      = True,
                gridspec_kw = {'height_ratios': [3, 1]})

            axs[0, 0].plot(TEST_VALUES, PX_SAD, label = "SAD", color = "r")
            axs[0, 0].plot(TEST_VALUES, PX_XS, label = "XS", color = "b", linestyle='--')
            axs[1, 0].plot(TEST_VALUES, PX_XS - PX_SAD)

            axs[0, 1].plot(TEST_VALUES, PY_SAD, label = "SAD", color = "r")
            axs[0, 1].plot(TEST_VALUES, PY_XS, label = "XS", color = "b", linestyle='--')
            axs[1, 1].plot(TEST_VALUES, PY_XS - PY_SAD)

            axs[1, 0].set_xlabel("Transform Parameter")
            axs[1, 1].set_xlabel("Transform Parameter")
            axs[0, 0].set_ylabel('px [m]')
            axs[1, 0].set_ylabel('∆px [m]')
            axs[0, 1].set_ylabel('py [m]')
            axs[1, 1].set_ylabel('∆py [m]')

            for ax in axs.flatten():
                ax.set_xscale('symlog', linthresh = symlog_threshold)
                ax.set_yscale('symlog', linthresh = symlog_threshold)
                ax.grid()
            axs[0, 0].legend()
            axs[0, 1].legend()
            plt.subplots_adjust(hspace = 0)
            plt.savefig(f"outputs/{test_name}_pxpy.png", dpi = 300, bbox_inches = 'tight')

        plt.close("all")

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

################################################################################
# DXDY
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_dxdy():
    """
    Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdy",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_dxdy_rev_in():
    """
    Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdy_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse Out
########################################
def test_sol_off_in_dxdy_rev_out():
    """
    Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdy_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Both Reversed
########################################
def test_sol_off_in_dxdy_rev_both():
    """
    Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdy_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DZ
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_dz():
    """
    Test the conversion of a SAD COORD element with DZ to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dz",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DZ = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_dz_rev_in():
    """
    Test the conversion of a SAD COORD element with DZ to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dz_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DZ = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse Out
########################################
def test_sol_off_in_dz_rev_out():
    """
    Test the conversion of a SAD COORD element with DZ to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dz_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DZ = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Both Reversed
########################################
def test_sol_off_in_dz_rev_both():
    """
    Test the conversion of a SAD COORD element with DZ to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dz_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DZ = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DPX
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_dpx():
    """
    Test the conversion of a SAD COORD element with DPX to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dpx",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DPX = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_dpx_rev_in():
    """
    Test the conversion of a SAD COORD element with DPX to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dpx_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DPX = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse Out
########################################
def test_sol_off_in_dpx_rev_out():
    """
    Test the conversion of a SAD COORD element with DPX to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dpx_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DPX = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Both Reversed
########################################
def test_sol_off_in_dpx_rev_both():
    """
    Test the conversion of a SAD COORD element with DPX to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dpx_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DPX = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DPY
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_dpy():
    """
    Test the conversion of a SAD COORD element with DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dpy",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_dpy_rev_in():
    """
    Test the conversion of a SAD COORD element with DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dpy_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse Out
########################################
def test_sol_off_in_dpy_rev_out():
    """
    Test the conversion of a SAD COORD element with DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dpy_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Both Reversed
########################################
def test_sol_off_in_dpy_rev_both():
    """
    Test the conversion of a SAD COORD element with DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dpy_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# CHI1
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_chi1():
    """
    Test the conversion of a SAD COORD element with CHI1 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_chi1",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 CHI1 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_chi1_rev_in():
    """
    Test the conversion of a SAD COORD element with CHI1 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_chi1_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 CHI1 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Reverse Out
########################################
def test_sol_off_in_chi1_rev_out():
    """
    Test the conversion of a SAD COORD element with CHI1 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_chi1_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 CHI1 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Both Reversed
########################################
def test_sol_off_in_chi1_rev_both():
    """
    Test the conversion of a SAD COORD element with CHI1 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_chi1_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 CHI1 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# CHI2
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_chi2():
    """
    Test the conversion of a SAD COORD element with CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_chi2",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_chi2_rev_in():
    """
    Test the conversion of a SAD COORD element with CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_chi2_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Reverse Out
########################################
def test_sol_off_in_chi2_rev_out():
    """
    Test the conversion of a SAD COORD element with CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_chi2_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Both Reversed
########################################
def test_sol_off_in_chi2_rev_both():
    """
    Test the conversion of a SAD COORD element with CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_chi2_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DXDYDPX
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_dxdydpx():
    """
    Test the conversion of a SAD COORD element with DX, DY and DPX to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpx",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPX = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_dxdydpx_rev_in():
    """
    Test the conversion of a SAD COORD element with DX, DY and DPX to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpx_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPX = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Reverse Out
########################################
def test_sol_off_in_dxdydpx_rev_out():
    """
    Test the conversion of a SAD COORD element with DX, DY and DPX to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpx_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPX = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Both Reversed
########################################
def test_sol_off_in_dxdydpx_rev_both():
    """
    Test the conversion of a SAD COORD element with DX, DY and DPX to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpx_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPX = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DXDYDPY
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_dxdydpy():
    """
    Test the conversion of a SAD COORD element with DX, DY and DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpy",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_dxdydpy_rev_in():
    """
    Test the conversion of a SAD COORD element with DX, DY and DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpy_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Reverse Out
########################################
def test_sol_off_in_dxdydpy_rev_out():
    """
    Test the conversion of a SAD COORD element with DX, DY and DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpy_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Both Reversed
########################################
def test_sol_off_in_dxdydpy_rev_both():
    """
    Test the conversion of a SAD COORD element with DX, DY and DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpy_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DXDYCHI1
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_dxdychi1():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI1 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi1",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_dxdychi1_rev_in():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI1 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi1_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse Out
########################################
def test_sol_off_in_dxdychi1_rev_out():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI1 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi1_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Both Reversed
########################################
def test_sol_off_in_dxdychi1_rev_both():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI1 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi1_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DXDYCHI2
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_dxdychi2():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi2",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_dxdychi2_rev_in():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi2_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse Out
########################################
def test_sol_off_in_dxdychi2_rev_out():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi2_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Both Reversed
########################################
def test_sol_off_in_dxdychi2_rev_both():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi2_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DXDYDPXDPY
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_dxdydpxdpy():
    """
    Test the conversion of a SAD COORD element with DX, DY, DPX and DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpxdpy",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPX = TEST_VAL DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_dxdydpxdpy_rev_in():
    """
    Test the conversion of a SAD COORD element with DX, DY, DPX and DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpxdpy_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPX = TEST_VAL DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse Out
########################################
def test_sol_off_in_dxdydpxdpy_rev_out():
    """
    Test the conversion of a SAD COORD element with DX, DY, DPX and DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpxdpy_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPX = TEST_VAL DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Both Reversed
########################################
def test_sol_off_in_dxdydpxdpy_rev_both():
    """
    Test the conversion of a SAD COORD element with DX, DY, DPX and DPY to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdydpxdpy_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL DPX = TEST_VAL DPY = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DXDYCHI1CHI2
################################################################################

########################################
# Forward
########################################
def test_sol_off_in_dxdychi1chi2():
    """
    Test the conversion of a SAD COORD element with DX, DY, CHI1 and CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi1chi2",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reverse In
########################################
def test_sol_off_in_dxdychi1chi2_rev_in():
    """
    Test the conversion of a SAD COORD element with DX, DY, CHI1 and CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi1chi2_rev_in",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Reverse Out
########################################
def test_sol_off_in_dxdychi1chi2_rev_out():
    """
    Test the conversion of a SAD COORD element with DX, DY, CHI1 and CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi1chi2_rev_out",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Both Reversed
########################################
def test_sol_off_in_dxdychi1chi2_rev_both():
    """
    Test the conversion of a SAD COORD element with DX, DY, CHI1 and CHI2 to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_005_sol_off_in_dxdychi1chi2_rev_both",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SOL_DRIFT   = (L = 1.00);

            SOL         SOL_IN      = (BZ = 0 BOUND =1)
                        SOL_OUT     = (BZ = 0 BOUND =1 DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL CHI2 = TEST_VAL GEO = 1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        TEST_LINE   = (START
                -SOL_IN SOL_START SOL_DRIFT SOL_END -SOL_OUT END);
            """),
        sad_eval_marker            = "SOL_START",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
