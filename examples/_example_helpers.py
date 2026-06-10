"""
Helpers for example lattice comparisons.
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       30-09-2025
"""

################################################################################
# Required Modules
################################################################################
import os
import sys
from pathlib import Path

import xtrack as xt
import numpy as np
import matplotlib.pyplot as plt

################################################################################
# Runtime Setup
################################################################################
def configure_example_runtime() -> str:
    """
    Configure paths for running an example script from any working directory.

    The examples and SAD helper functions use paths relative to the examples
    folder. This function adds the repository root to `sys.path`, changes the
    working directory to the examples folder, creates the ignored `out` folder,
    and returns the output directory as a string for `convert_sad_to_xsuite`.
    """
    example_dir = Path(__file__).resolve().parent
    repo_root   = example_dir.parent

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    os.chdir(example_dir)

    output_dir = "out"
    Path(output_dir).mkdir(exist_ok = True)

    return output_dir

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
        suptitle    = None,
        zero_tol    = 1E-12,
        figsize     = (8, 4)):
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
        zero_small_values(twiss_xsuite.x, tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.y, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(twiss_xsuite.y, tol = zero_tol),
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
        zero_small_values(twiss_xsuite.px, tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.py, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(twiss_xsuite.py, tol = zero_tol),
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
        zero_small_values(twiss_xsuite.zeta, tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.delta, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(twiss_xsuite.delta, tol = zero_tol),
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
        zero_small_values(twiss_xsuite.betx, tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.bety, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(twiss_xsuite.bety, tol = zero_tol),
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
        zero_small_values(twiss_xsuite.alfx, tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.alfy, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(twiss_xsuite.alfy, tol = zero_tol),
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
        zero_small_values(twiss_xsuite.dx, tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.dy, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(twiss_xsuite.dy, tol = zero_tol),
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
        zero_small_values(twiss_xsuite.dpx, tol = zero_tol),
        label       = 'Xsuite',
        color       = "b",
        linestyle   = "--")
    axs[1].plot(
        zero_small_values(twiss_sad.s, tol = zero_tol),
        zero_small_values(twiss_sad.dpy, tol = zero_tol),
        color       = "r")
    axs[1].plot(
        zero_small_values(twiss_xsuite.s, tol = zero_tol),
        zero_small_values(twiss_xsuite.dpy, tol = zero_tol),
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
