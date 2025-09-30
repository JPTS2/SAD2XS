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
        # Get table XSuite Lattice
        ########################################
        tt      = line.get_table(attr = True)

        ########################################
        # Twiss XSuite Lattice
        ########################################
        tw_xs   = line.twiss4d(
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

        S_SAD[iteration]    = tw_sad["s", sad_eval_marker]
        S_XS[iteration]     = tw_xs["s_sad", xs_eval_marker]
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

        ########################################################################
        # Diagnostics: Outputs if the test fails
        ########################################################################
        if not (np.isclose(S_SAD[iteration], S_XS[iteration], rtol = DELTA_S_RTOL, atol = DELTA_S_ATOL) and \
                np.isclose(X_SAD[iteration], X_XS[iteration], rtol = DELTA_X_RTOL, atol = DELTA_X_ATOL) and \
                np.isclose(Y_SAD[iteration], Y_XS[iteration], rtol = DELTA_Y_RTOL, atol = DELTA_Y_ATOL) and \
                np.isclose(PX_SAD[iteration], PX_XS[iteration], rtol = DELTA_PX_RTOL, atol = DELTA_PX_ATOL) and \
                np.isclose(PY_SAD[iteration], PY_XS[iteration], rtol = DELTA_PY_RTOL, atol = DELTA_PY_ATOL)):

            print("SAD")
            tw_sad.cols["s x px y py"].show()
            print("Xsuite")
            tw_xs.cols["s_sad x px y py"].show()

            delta_s_in_pre      = (tw_xs["s_sad", "start"] - tw_sad["s", "START"]) * 1E9
            delta_s_in_post     = (tw_xs["s_sad", "sol_start"] - tw_sad["s", "SOL_START"]) * 1E9
            delta_x_in_pre      = (tw_xs["x", "start"] - tw_sad["x", "START"]) * 1E9
            delta_x_in_post     = (tw_xs["x", "sol_start"] - tw_sad["x", "SOL_START"]) * 1E9
            delta_y_in_pre      = (tw_xs["y", "start"] - tw_sad["y", "START"]) * 1E9
            delta_y_in_post     = (tw_xs["y", "sol_start"] - tw_sad["y", "SOL_START"]) * 1E9
            delta_px_in_pre     = (tw_xs["px", "start"] - tw_sad["px", "START"]) * 1E9
            delta_px_in_post    = (tw_xs["px", "sol_start"] - tw_sad["px", "SOL_START"]) * 1E9
            delta_py_in_pre     = (tw_xs["py", "start"] - tw_sad["py", "START"]) * 1E9
            delta_py_in_post    = (tw_xs["py", "sol_start"] - tw_sad["py", "SOL_START"]) * 1E9

            delta_s_out_pre     = (tw_xs["s_sad", "sol_end"] - tw_sad["s", "SOL_END"]) * 1E9
            delta_s_out_post    = (tw_xs["s_sad", "end"] - tw_sad["s", "END"]) * 1E9
            delta_x_out_pre     = (tw_xs["x", "sol_end"] - tw_sad["x", "SOL_END"]) * 1E9
            delta_x_out_post    = (tw_xs["x", "end"] - tw_sad["x", "END"]) * 1E9
            delta_y_out_pre     = (tw_xs["y", "sol_end"] - tw_sad["y", "SOL_END"]) * 1E9
            delta_y_out_post    = (tw_xs["y", "end"] - tw_sad["y", "END"]) * 1E9
            delta_px_out_pre    = (tw_xs["px", "sol_end"] - tw_sad["px", "SOL_END"]) * 1E9
            delta_px_out_post   = (tw_xs["px", "end"] - tw_sad["px", "END"]) * 1E9
            delta_py_out_pre    = (tw_xs["py", "sol_end"] - tw_sad["py", "SOL_END"]) * 1E9
            delta_py_out_post   = (tw_xs["py", "end"] - tw_sad["py", "END"]) * 1E9

            print("Inbound Before transforms (element START)")
            print(f"Xsuite: s  = {tw_xs["s_sad", "start"]:.3f}, x = {tw_xs["x", "start"]:.3f}, y = {tw_xs["y", "start"]:.3f}, px = {tw_xs["px", "start"]:.3f}, py = {tw_xs["py", "start"]:.3f}")
            print(f"SAD:    s  = {tw_sad["s", "START"]:.3f}, x = {tw_sad["x", "START"]:.3f}, y = {tw_sad["y", "START"]:.3f}, px = {tw_sad["px", "START"]:.3f}, py = {tw_sad["py", "START"]:.3f}")
            print(f"Delta:  s = {delta_s_in_pre:.3f}, x = {delta_x_in_pre:.3f}, y = {delta_y_in_pre:.3f}, px = {delta_px_in_pre:.3f}, py = {delta_py_in_pre:.3f}")

            print("Inbound Post transforms (element SOL_START)")
            print(f"Xsuite: s  = {tw_xs["s_sad", "sol_start"]:.3f}, x = {tw_xs["x", "sol_start"]:.3f}, y = {tw_xs["y", "sol_start"]:.3f}, px = {tw_xs["px", "sol_start"]:.3f}, py = {tw_xs["py", "sol_start"]:.3f}")
            print(f"SAD:    s  = {tw_sad["s", "SOL_START"]:.3f}, x = {tw_sad["x", "SOL_START"]:.3f}, y = {tw_sad["y", "SOL_START"]:.3f}, px = {tw_sad["px", "SOL_START"]:.3f}, py = {tw_sad["py", "SOL_START"]:.3f}")
            print(f"Delta:  s = {delta_s_in_post:.3f}, x = {delta_x_in_post:.3f}, y = {delta_y_in_post:.3f}, px = {delta_px_in_post:.3f}, py = {delta_py_in_post:.3f}")

            print("Outbound Pre transforms (element SOL_END)")
            print(f"Xsuite: s  = {tw_xs["s_sad", "sol_end"]:.3f}, x = {tw_xs["x", "sol_end"]:.3f}, y = {tw_xs["y", "sol_end"]:.3f}, px = {tw_xs["px", "sol_end"]:.3f}, py = {tw_xs["py", "sol_end"]:.3f}")
            print(f"SAD:    s  = {tw_sad["s", "SOL_END"]:.3f}, x = {tw_sad["x", "SOL_END"]:.3f}, y = {tw_sad["y", "SOL_END"]:.3f}, px = {tw_sad["px", "SOL_END"]:.3f}, py = {tw_sad["py", "SOL_END"]:.3f}")
            print(f"Delta:  s = {delta_s_out_pre:.3f}, x = {delta_x_out_pre:.3f}, y = {delta_y_out_pre:.3f}, px = {delta_px_out_pre:.3f}, py = {delta_py_out_pre:.3f}")

            print("Outbound Post transforms (element END)")
            print(f"Xsuite: s  = {tw_xs["s_sad", "end"]:.3f}, x = {tw_xs["x", "end"]:.3f}, y = {tw_xs["y", "end"]:.3f}, px = {tw_xs["px", "end"]:.3f}, py = {tw_xs["py", "end"]:.3f}")
            print(f"SAD:    s  = {tw_sad["s", "END"]:.3f}, x = {tw_sad["x", "END"]:.3f}, y = {tw_sad["y", "END"]:.3f}, px = {tw_sad["px", "END"]:.3f}, py = {tw_sad["py", "END"]:.3f}")
            print(f"Delta:  s = {delta_s_out_post:.3f}, x = {delta_x_out_post:.3f}, y = {delta_y_out_post:.3f}, px = {delta_px_out_post:.3f}, py = {delta_py_out_post:.3f}")

            print("Transform sizes Xsuite")
            print("In:")
            print(f"dx = {line['sol_in_dxy'].dx}, dy = {line['sol_in_dxy'].dy}, dz = {line['sol_in_dz'].dzeta}")
            print(f"chi1 = {line['sol_in_chi1'].angle}, chi2 = {line['sol_in_chi2'].angle}, chi3 = {line['sol_in_chi3'].angle}")
            print("Out:")
            print(f"dx = {line['sol_out_dxy'].dx}, dy = {line['sol_out_dxy'].dy}, dz = {line['sol_out_dz'].dzeta}")
            print(f"chi1 = {line['sol_out_chi1'].angle}, chi2 = {line['sol_out_chi2'].angle}, chi3 = {line['sol_out_chi3'].angle}")

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

# ################################################################################
# # Very weak sol (checking expansion of the square root)
# ################################################################################
# def test_sol_on_very_weak():
#     """
#     Test the conversion of a SAD SOL element with ref shifts at entry to XSuite.
#     """
#     reference_sol_test(
#         test_name                  = "test_007_very_weak_sol",
#         sad_elements_line_string   = textwrap.dedent(f"""\
#             DRIFT       SHORT_DRIFT = (L = 0.10);

#             SOL         SOL_IN      = (BZ = 0.000001 BOUND =1  DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL CHI2 = TEST_VAL GEO = 1)
#                         SOL_OUT     = (BZ = 0.000001 BOUND =1);

#             MARK        START       = ()
#                         END         = ()
#                         SOL_START   = ()
#                         SOL_END     = ();

#             LINE        SOL_DRIFT   = (SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT
#                 SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT
#                 SHORT_DRIFT SHORT_DRIFT)
#                         TEST_LINE   = (START
#                 SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
#             """),
#         sad_eval_marker            = "END",
#         test_values                = generate_symlog_array(-6, -1, 11),
#         static_val                 = STATIC_OFFSET,
#         plot                       = True)

# ################################################################################
# # Weak sol (checking expansion of the square root)
# ################################################################################
# def test_sol_on_weak():
#     """
#     Test the conversion of a SAD SOL element with ref shifts at entry to XSuite.
#     """
#     reference_sol_test(
#         test_name                  = "test_007_weak_sol",
#         sad_elements_line_string   = textwrap.dedent(f"""\
#             DRIFT       SHORT_DRIFT = (L = 0.10);

#             SOL         SOL_IN      = (BZ = 0.001 BOUND =1  DX = TEST_VAL DY = TEST_VAL CHI1 = TEST_VAL CHI2 = TEST_VAL GEO = 1)
#                         SOL_OUT     = (BZ = 0.001 BOUND =1);

#             MARK        START       = ()
#                         END         = ()
#                         SOL_START   = ()
#                         SOL_END     = ();

#             LINE        SOL_DRIFT   = (SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT
#                 SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT
#                 SHORT_DRIFT SHORT_DRIFT)
#                         TEST_LINE   = (START
#                 SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
#             """),
#         sad_eval_marker            = "END",
#         test_values                = generate_symlog_array(-6, -1, 11),
#         static_val                 = STATIC_OFFSET,
#         plot                       = True)

################################################################################
# Sol (checking expansion of the square root)
################################################################################
def test_sol_on():
    """
    Test the conversion of a SAD SOL element with ref shifts at entry to XSuite.
    """
    reference_sol_test(
        test_name                  = "test_007_sol",
        sad_elements_line_string   = textwrap.dedent(f"""\
            DRIFT       SHORT_DRIFT = (L = 0.10);

            SOL         SOL_IN      = (BZ = 1.00 BOUND =1  DX = TEST_VAL DY = TEST_VAL DPX = TEST_VAL DPY = TEST_VAL GEO = 1)
                        SOL_OUT     = (BZ = 1.00 BOUND =1);

            MARK        START       = ()
                        END         = ()
                        SOL_START   = ()
                        SOL_END     = ();

            LINE        SOL_DRIFT   = (SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT
                SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT SHORT_DRIFT
                SHORT_DRIFT SHORT_DRIFT)
                        TEST_LINE   = (START
                SOL_IN SOL_START SOL_DRIFT SOL_END SOL_OUT END);
            """),
        sad_eval_marker            = "END",
        test_values                = generate_symlog_array(-6, -1, 11),
        static_val                 = STATIC_OFFSET,
        plot                       = True)
