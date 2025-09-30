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
# Reference PyTest Function
################################################################################
def reference_coord_test(
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
def test_coord_dxdy():
    """
    Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdy",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (DX = TEST_VAL DY = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reversed
########################################
def test_coord_dxdy_rev():
    """
    Test the conversion of a SAD COORD element with DX and DY to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdy_rev",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (DX = TEST_VAL DY = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START -TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
################################################################################
# CHI1
################################################################################

########################################
# Forward
########################################
def test_coord_chi1():
    """
    Test the conversion of a SAD COORD element with CHI1 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_chi1",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (CHI1 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reversed
########################################
def test_coord_chi1_rev():
    """
    Test the conversion of a SAD COORD element with CHI1 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_chi1_rev",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (CHI1 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START -TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
################################################################################
# CHI2
################################################################################

########################################
# Forward
########################################
def test_coord_chi2():
    """
    Test the conversion of a SAD COORD element with CHI2 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_chi2",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (CHI2 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reversed
########################################
def test_coord_chi2_rev():
    """
    Test the conversion of a SAD COORD element with CHI2 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_chi2_rev",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (CHI2 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START -TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
################################################################################
# DXDY then CHI1
################################################################################

########################################
# Forward
########################################
def test_coord_dxdy_chi1():
    """
    Test the conversion of a SAD COORD element with DX and DY then CHI1 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdy_chi1",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD1 = (DX = STATIC_VAL DY = STATIC_VAL)
                        TEST_COORD2 = (CHI1 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD1 TEST_COORD2 END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Reversed
########################################
def test_coord_dxdy_chi1_rev():
    """
    Test the conversion of a SAD COORD element with DX and DY then CHI1 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdy_chi1_rev",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD1 = (DX = STATIC_VAL DY = STATIC_VAL)
                        TEST_COORD2 = (CHI1 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD1 -TEST_COORD2 END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DXDY then CHI2
################################################################################

########################################
# Forward
########################################
def test_coord_dxdy_chi2():
    """
    Test the conversion of a SAD COORD element with DX and DY then CHI2 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdy_chi2",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD1 = (DX = STATIC_VAL DY = STATIC_VAL)
                        TEST_COORD2 = (CHI2 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD1 TEST_COORD2 END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reversed
########################################
def test_coord_dxdy_chi2_rev():
    """
    Test the conversion of a SAD COORD element with DX and DY then CHI2 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdy_chi2_rev",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD1 = (DX = STATIC_VAL DY = STATIC_VAL)
                        TEST_COORD2 = (CHI2 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD1 -TEST_COORD2 END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
################################################################################
# DXDY then CHI3
################################################################################

########################################
# Forward
########################################
def test_coord_dxdy_chi3():
    """
    Test the conversion of a SAD COORD element with DX and DY then CHI3 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdy_chi3",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD1 = (DX = STATIC_VAL DY = STATIC_VAL)
                        TEST_COORD2 = (CHI3 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD1 TEST_COORD2 END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reversed
########################################
def test_coord_dxdy_chi3_rev():
    """
    Test the conversion of a SAD COORD element with DX and DY then CHI3 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdy_chi3_rev",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD1 = (DX = STATIC_VAL DY = STATIC_VAL)
                        TEST_COORD2 = (CHI3 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD1 -TEST_COORD2 END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DXDYCHI1
################################################################################

########################################
# Forward
########################################
def test_coord_dxdychi1():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI1 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdychi1",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reversed
########################################
def test_coord_dxdychi1_rev():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI1 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdychi1_rev",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START -TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
################################################################################
# DXDYCHI2
################################################################################

########################################
# Forward
########################################
def test_coord_dxdychi2():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI2 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdychi2",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (DX = TEST_VAL DY = TEST_VAL CHI2 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reversed
########################################
def test_coord_dxdychi2_rev():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI2 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdychi2_rev",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (DX = TEST_VAL DY = TEST_VAL CHI2 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START -TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
################################################################################
# DXDYCHI3
################################################################################

########################################
# Forward
########################################
def test_coord_dxdychi3():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI3 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdychi3",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (DX = TEST_VAL DY = TEST_VAL CHI3 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

########################################
# Reversed
########################################
def test_coord_dxdychi3_rev():
    """
    Test the conversion of a SAD COORD element with DX, DY and CHI3 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdychi3_rev",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (DX = TEST_VAL DY = TEST_VAL CHI3 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START -TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)

################################################################################
# DXDYCHI1CHI2CHI3
################################################################################

########################################
# Forward
########################################
def test_coord_dxdychi1chi2chi3():
    """
    Test the conversion of a SAD COORD element with DX, DY, CHI1, CHI2 and CHI3 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdychi1chi2chi3",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL CHI2 = TEST_VAL CHI3 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
    
########################################
# Reversed
########################################
def test_coord_dxdychi1chi2chi3_rev():
    """
    Test the conversion of a SAD COORD element with DX, DY, CHI1, CHI2 and CHI3 to XSuite.
    """
    reference_coord_test(
        test_name                  = "test_002_coord_dxdychi1chi2chi3_rev",
        sad_elements_line_string   = textwrap.dedent(f"""\
            COORD       TEST_COORD  = (DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL CHI2 = TEST_VAL CHI3 = TEST_VAL);
            MARK        START       = ()
                        END         = ();
            LINE        TEST_LINE   = (START -TEST_COORD END);
            """),
        sad_eval_marker            = "END",
        test_values                = TEST_VALUES,
        static_val                 = STATIC_OFFSET,
        plot                       = True)
