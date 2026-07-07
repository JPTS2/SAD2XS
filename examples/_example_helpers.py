"""
================================================================================
Helpers for SAD2XS examples
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-07
================================================================================
"""
################################################################################
# Required Modules
################################################################################
import os
import re
import sys
from pathlib import Path

import xtrack as xt
import numpy as np
import matplotlib.pyplot as plt

################################################################################
# Example Comparison Settings
################################################################################
DEFAULT_OUTPUT_DIR              = "out"
DEFAULT_MIN_MATCHED_ELEMENTS    = 5000
MATCH_S_TOLERANCE               = 1.0

TWISS_COLUMN_TOLERANCES         = {
    "x":     dict(atol = 1E-7,  rtol = 1E-3),
    "px":    dict(atol = 1E-8,  rtol = 1E-3),
    "y":     dict(atol = 1E-7,  rtol = 1E-3),
    "py":    dict(atol = 1E-8,  rtol = 1E-3),
    "zeta":  dict(atol = 1E-9,  rtol = 1E-3),
    "delta": dict(atol = 1E-12, rtol = 1E-3),
    "betx":  dict(atol = 1E-4,  rtol = 1E-3),
    "bety":  dict(atol = 1E-4,  rtol = 1E-3),
    "alfx":  dict(atol = 1E-4,  rtol = 1E-3),
    "alfy":  dict(atol = 1E-4,  rtol = 1E-3),
    "dx":    dict(atol = 1E-5,  rtol = 1E-3),
    "dpx":   dict(atol = 1E-6,  rtol = 1E-3),
    "dy":    dict(atol = 1E-5,  rtol = 1E-3),
    "dpy":   dict(atol = 1E-6,  rtol = 1E-3),
    "mux":   dict(atol = 1E-6,  rtol = 1E-3),
    "muy":   dict(atol = 1E-6,  rtol = 1E-3)}
EDWARDS_TENG_COLUMNS            = {
    "betx": "betx_edw_teng",
    "bety": "bety_edw_teng",
    "alfx": "alfx_edw_teng",
    "alfy": "alfy_edw_teng"}
RELATIVE_TWISS_COLUMNS          = {"zeta"}

################################################################################
# Runtime Setup
################################################################################
def configure_example_runtime(output_dir = DEFAULT_OUTPUT_DIR) -> str:
    """
    Configure paths for running an example script from any working directory.

    The examples and SAD helper functions use paths relative to the examples
    folder. This function adds the repository root to `sys.path`, changes the
    working directory to the examples folder, creates the output folder, and
    returns it as a string for `convert_sad_to_xsuite`.
    """
    example_dir = Path(__file__).resolve().parent
    repo_root   = example_dir.parent

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    os.chdir(example_dir)

    Path(output_dir).mkdir(parents = True, exist_ok = True)

    return str(output_dir)

################################################################################
# SAD vs Xsuite Comparison
################################################################################
_NAME_INDEX_RE = re.compile(r"^(.*)\.(\d+)$")

def _split_name(name: str):
    """
    Split a SAD/Xsuite element name into base name and repetition index.
    """
    match = _NAME_INDEX_RE.match(name)
    if match:
        return match.group(1).lower(), int(match.group(2))
    return name.lower(), None

def _comparison_column_name(column, xsuite_columns):
    """
    Return the Xsuite column to compare or plot against a SAD column.
    """
    if xsuite_columns is None:
        return column
    return xsuite_columns.get(column, column)

def matched_sad_xsuite_twiss(line, twiss_xsuite, twiss_sad):
    """
    Match Xsuite and SAD Twiss rows by physical element name.

    SAD numbers repeated copies from 1, while SAD2XS/Xsuite numbers them from
    0. Drifts and SAD-internal "$" prototype names are excluded because their
    auto-splitting/numbering does not correspond between the two codes.
    """
    tw      = twiss_xsuite.to_pandas()
    tt      = line.get_table(attr = True).to_pandas()[["name", "element_type"]]
    tw      = tw.merge(tt, on = "name", how = "left")
    tw_sad  = (
        twiss_sad.to_pandas() if hasattr(twiss_sad, "to_pandas") else twiss_sad.copy())

    xs_base, xs_idx         = zip(*tw["name"].map(_split_name))
    tw["base"], tw["idx"]   = xs_base, xs_idx
    sad_base, sad_idx       = zip(*tw_sad["name"].map(_split_name))
    tw_sad["base"]          = sad_base
    tw_sad["idx"]           = [i - 1 if i is not None else None for i in sad_idx]

    tw["key"]     = list(zip(tw["base"], tw["idx"]))
    tw_sad["key"] = list(zip(tw_sad["base"], tw_sad["idx"]))

    non_drift_xs   = tw[
        (tw["element_type"] != "Drift")
        & (~tw["base"].str.contains(r"\$"))]
    non_dollar_sad = tw_sad[~tw_sad["base"].str.contains(r"\$")]

    xs_counts   = non_drift_xs["key"].value_counts()
    sad_counts  = non_dollar_sad["key"].value_counts()
    common_keys = sorted(
        set(xs_counts[xs_counts == 1].index)
        & set(sad_counts[sad_counts == 1].index),
        key = str)

    xs_rows     = non_drift_xs.set_index("key").loc[common_keys]
    sad_rows    = non_dollar_sad.set_index("key").loc[common_keys]

    same_position = (
        np.abs(xs_rows["s"].to_numpy() - sad_rows["s"].to_numpy())
        < MATCH_S_TOLERANCE)
    return xs_rows[same_position], sad_rows[same_position]

def _comparison_values(xs_rows, sad_rows, sad_column, xsuite_column):
    """
    Return arrays in the convention used for the example comparison.
    """
    xs_values  = xs_rows[xsuite_column].to_numpy()
    sad_values = sad_rows[sad_column].to_numpy()

    if sad_column in RELATIVE_TWISS_COLUMNS:
        xs_values  = xs_values - xs_values[0]
        sad_values = sad_values - sad_values[0]

    return xs_values, sad_values

def assert_twiss_matches_sad(
        line,
        twiss_xsuite,
        twiss_sad,
        min_matched_elements,
        xsuite_columns = None):
    """
    Assert element-by-element Xsuite/SAD Twiss agreement for an example lattice.

    Use `xsuite_columns` to compare SAD columns against explicitly chosen
    Xsuite columns. Coupled SAD beta/alpha comparisons should pass
    `EDWARDS_TENG_COLUMNS` after computing Xsuite Twiss with
    `coupling_edw_teng=True`.
    """
    xs_rows, sad_rows = matched_sad_xsuite_twiss(
        line            = line,
        twiss_xsuite    = twiss_xsuite,
        twiss_sad       = twiss_sad)

    assert len(xs_rows) >= min_matched_elements, (
        f"Only matched {len(xs_rows)} named elements between Xsuite and SAD "
        f"Twiss; expected at least {min_matched_elements}.")

    for sad_column, tol in TWISS_COLUMN_TOLERANCES.items():
        xsuite_column = _comparison_column_name(sad_column, xsuite_columns)
        xs_values, sad_values = _comparison_values(
            xs_rows        = xs_rows,
            sad_rows       = sad_rows,
            sad_column     = sad_column,
            xsuite_column  = xsuite_column)
        np.testing.assert_allclose(
            xs_values,
            sad_values,
            atol    = tol["atol"],
            rtol    = tol["rtol"],
            err_msg = (
                f"Xsuite '{xsuite_column}' disagrees with SAD "
                f"'{sad_column}' beyond tolerance."))

################################################################################
# Check Symplecticity
################################################################################
def check_symplecticity(twiss, line, tt = None):
    """
    Print a basic symplecticity check for a Twiss table and line.

    Parameters
    ----------
    twiss
        Xsuite Twiss table containing an `R_matrix` entry.
    line
        Xsuite line used to compute element-by-element matrices if the overall
        matrix is not symplectic at the configured tolerance.
    tt
        Optional line table. If omitted, `line.get_table(attr=True)` is used.
    """
    J   = np.array([
        [0, +1, 0, 0, 0, 0],
        [-1, 0, 0, 0, 0, 0],
        [0, 0, 0, +1, 0, 0],
        [0, 0, -1, 0, 0, 0],
        [0, 0, 0, 0, 0, +1],
        [0, 0, 0, 0, -1, 0]])

    ########################################
    # Get table
    ########################################
    if tt is None:
        tt = line.get_table(attr = True)

    ########################################
    # Overall
    ########################################
    M           = twiss.R_matrix
    residual    = (M.T @ J @ M) - J
    for row in residual:
        print(" ".join(f"{x:+12.5E}" for x in row))

    symplectic  = np.allclose(residual, 0, atol = 1E-6)
    print("Overall R Matrix symplecticity (1E-6 level): ", symplectic)
    print("Maximum deviation:                           ", np.max(np.abs(residual)))

    ########################################
    # EBE if there is an issue
    ########################################
    if not symplectic:
        # Need to exclude _end_ponit with -1
        for test_ele, end_ele in zip(tt.name[:-2], tt.name[1:-1]):
            test_particle   = xt.Particles(
                p0c     = line.particle_ref.p0c,
                mass0   = line.particle_ref.mass0,
                q0      = line.particle_ref.q0)
            M_ele   = line.compute_one_turn_matrix_finite_differences(
                start               = test_ele,
                end                 = end_ele,
                particle_on_co      = test_particle,
                steps_r_matrix      = twiss.steps_r_matrix)["R_matrix"]
            residual    = (M_ele.T @ J @ M_ele) - J
            symplectic  = np.allclose(residual, 0, atol = 1E-6)
            if not symplectic:
                print(f"Non-symplectic element (1E-6 level):    {test_ele}")


################################################################################
# Zero small values
################################################################################
def zero_small_values(array, tol = 1E-12):
    """
    Set small values in an array to zero for clearer comparison plots.

    Parameters
    ----------
    array
        Array-like object to modify in place.
    tol
        Absolute threshold below which values are set to zero.

    Returns
    -------
    array
        The same array object, with small values zeroed.
    """
    array[np.abs(array) < tol] = 0
    return array

################################################################################
# SAD vs Xsuite Comparison Plots
################################################################################
def create_comparison_plots(
        twiss_xsuite,
        twiss_sad,
        suptitle        = None,
        zero_tol        = 1E-12,
        figsize         = (8, 4),
        xsuite_columns  = None):
    """
    Create standard SAD-versus-Xsuite optics comparison plots.

    Parameters
    ----------
    twiss_xsuite
        Xsuite Twiss table to compare.
    twiss_sad
        SAD reference Twiss table, usually returned by `twiss_sad`.
    suptitle
        Optional prefix added to each figure title.
    zero_tol
        Absolute threshold used to hide small numerical noise in plotted data.
    figsize
        Matplotlib figure size passed to each generated plot.
    xsuite_columns
        Optional mapping from SAD column names to Xsuite column names. Use this
        to plot SAD `betx/bety/alfx/alfy` against Xsuite Edwards-Teng columns.
    """

    ########################################
    # Orbit (x, y)
    ########################################
    fig, axs = plt.subplots(2, figsize = figsize, sharex = True)

    axs[0].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.x, tol = zero_tol),
        label       = 'SAD',
        color       = "r")
    axs[0].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("x", xsuite_columns)),
            tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.y, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("y", xsuite_columns)),
            tol = zero_tol),
        color       = "b",
        linestyle   = "--")
    
    axs[0].legend()
    axs[0].set_ylabel(r'$x$ [m]')
    axs[1].set_ylabel(r'$y$ [m]')
    axs[1].set_xlabel('s [m]')

    if suptitle is not None:
        fig.suptitle(f"{suptitle}: Orbit (x, y)")
    else:
        fig.suptitle("Orbit (x, y)")
    fig.tight_layout()
    fig.align_labels()
    fig.align_titles()

    ########################################
    # Orbit (px, py)
    ########################################
    fig, axs = plt.subplots(2, figsize = figsize, sharex = True)

    axs[0].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.px, tol = zero_tol),
        label       = 'SAD',
        color       = "r")
    axs[0].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("px", xsuite_columns)),
            tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.py, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("py", xsuite_columns)),
            tol = zero_tol),
        color       = "b",
        linestyle   = "--")

    axs[0].legend()
    axs[0].set_ylabel(r'$p_{x}$ [1]')
    axs[1].set_ylabel(r'$p_{y}$ [1]')
    axs[1].set_xlabel('s [m]')

    if suptitle is not None:
        fig.suptitle(f"{suptitle}: Orbit (px, py)")
    else:
        fig.suptitle("Orbit (px, py)")
    fig.tight_layout()
    fig.align_labels()
    fig.align_titles()

    ########################################
    # Longitudinal Plane (zeta, delta)
    ########################################
    fig, axs = plt.subplots(2, figsize = figsize, sharex = True)

    axs[0].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.zeta, tol = zero_tol),
        label       = 'SAD',
        color       = "r")
    axs[0].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("zeta", xsuite_columns)),
            tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.delta, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("delta", xsuite_columns)),
            tol = zero_tol),
        color       = "b",
        linestyle   = "--")
    
    axs[0].legend()
    axs[0].set_ylabel(r'$\zeta$ [m]')
    axs[1].set_ylabel(r'$\delta$ [1]')
    axs[1].set_xlabel('s [m]')

    if suptitle is not None:
        fig.suptitle(fr"{suptitle}: Longitudinal Plane ($\zeta$, $\delta$)")
    else:
        fig.suptitle(r"Longitudinal Plane ($\zeta$, $\delta$)")
    fig.tight_layout()
    fig.align_labels()
    fig.align_titles()

    ########################################
    # Beta Functions
    ########################################
    fig, axs = plt.subplots(2, figsize = figsize, sharex = True)

    axs[0].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.betx, tol = zero_tol),
        label       = 'SAD',
        color       = "r")
    axs[0].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("betx", xsuite_columns)),
            tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.bety, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("bety", xsuite_columns)),
            tol = zero_tol),
        color       = "b",
        linestyle   = "--")

    axs[0].legend()
    axs[0].set_ylabel(r'$\beta_{x}$ [m]')
    axs[1].set_ylabel(r'$\beta_{y}$ [m]')
    axs[1].set_xlabel('s [m]')

    if suptitle is not None:
        fig.suptitle(f"{suptitle}: " + "Beta Functions ($\\beta_{x}$, $\\beta_{y}$)")
    else:
        fig.suptitle("Beta Functions ($\\beta_{x}$, $\\beta_{y}$)")
    fig.tight_layout()
    fig.align_labels()
    fig.align_titles()

    ########################################
    # Alpha Functions
    ########################################
    fig, axs = plt.subplots(2, figsize = figsize, sharex = True)

    axs[0].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.alfx, tol = zero_tol),
        label       = 'SAD',
        color       = "r")
    axs[0].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("alfx", xsuite_columns)),
            tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.alfy, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("alfy", xsuite_columns)),
            tol = zero_tol),
        color       = "b",
        linestyle   = "--")

    axs[0].legend()
    axs[0].set_ylabel(r'$\alpha_{x}$ [1]')
    axs[1].set_ylabel(r'$\alpha_{y}$ [1]')
    axs[1].set_xlabel('s [m]')

    if suptitle is not None:
        fig.suptitle(f"{suptitle}: " + "Alpha Functions ($\\alpha_{x}$, $\\alpha_{y}$)")
    else:
        fig.suptitle("Alpha Functions ($\\alpha_{x}$, $\\alpha_{y}$)")
    fig.tight_layout()
    fig.align_labels()
    fig.align_titles()

    ########################################
    # Dispersion
    ########################################
    fig, axs = plt.subplots(2, figsize = figsize, sharex = True)

    axs[0].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.dx, tol = zero_tol),
        label       = 'SAD',
        color       = "r")
    axs[0].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("dx", xsuite_columns)),
            tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.dy, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("dy", xsuite_columns)),
            tol = zero_tol),
        color       = "b",
        linestyle   = "--")

    axs[0].legend()
    axs[0].set_ylabel(r'$D_{x}$ [m]')
    axs[1].set_ylabel(r'$D_{y}$ [m]')
    axs[1].set_xlabel('s [m]')

    if suptitle is not None:
        fig.suptitle(f"{suptitle}: " + "Dispersion ($D_{x}$, $D_{y}$)")
    else:
        fig.suptitle("Dispersion ($D_{x}$, $D_{y}$)")
    fig.tight_layout()
    fig.align_labels()
    fig.align_titles()

    ########################################
    # Derivative Dispersion
    ########################################
    fig, axs = plt.subplots(2, figsize = figsize, sharex = True)

    axs[0].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.dpx, tol = zero_tol),
        label       = 'SAD',
        color       = "r")
    axs[0].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("dpx", xsuite_columns)),
            tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.dpy, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(
            getattr(twiss_xsuite, _comparison_column_name("dpy", xsuite_columns)),
            tol = zero_tol),
        color       = "b",
        linestyle   = "--")

    axs[0].legend()
    axs[0].set_ylabel(r'$D_{px}$ [1]')
    axs[1].set_ylabel(r'$D_{py}$ [1]')
    axs[1].set_xlabel('s [m]')

    if suptitle is not None:
        fig.suptitle(f"{suptitle}: " + "Dispersion ($D_{px}$, $D_{py}$)")
    else:
        fig.suptitle("Dispersion ($D_{px}$, $D_{py}$)")
    fig.tight_layout()
    fig.align_labels()
    fig.align_titles()
