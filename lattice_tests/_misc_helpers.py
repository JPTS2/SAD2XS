"""
Helpers for lattice testing
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       30-09-2025
"""

################################################################################
# Required Modules
################################################################################
import xtrack as xt
import numpy as np
import matplotlib.pyplot as plt

################################################################################
# Check Symplecticity
################################################################################
def check_symplecticity(twiss, line, tt = None):
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
# SAD vs Xsuite Comparison Plots
################################################################################
def create_comparison_plots(twiss_xsuite, twiss_sad):

    fig, axs = plt.subplots(2, figsize = (12, 8), sharex = True)
    axs[0].plot(twiss_sad.s, twiss_sad.x, label = 'SAD', color = "r")
    axs[0].plot(twiss_xsuite.s, twiss_xsuite.x, label = 'Xsuite', color = "b", linestyle = "--")
    axs[1].plot(twiss_sad.s, twiss_sad.y, label = 'SAD', color = "r")
    axs[1].plot(twiss_xsuite.s, twiss_xsuite.y, label = 'Xsuite', color = "b", linestyle = "--")
    axs[0].legend()
    axs[0].set_ylabel(r'$x$ [m]')
    axs[1].set_ylabel(r'$y$ [m]')
    axs[1].set_xlabel('s [m]')

    fig, axs = plt.subplots(2, figsize = (12, 8), sharex = True)
    axs[0].plot(twiss_sad.s, twiss_sad.px, label = 'SAD', color = "r")
    axs[0].plot(twiss_xsuite.s, twiss_xsuite.px, label = 'Xsuite', color = "b", linestyle = "--")
    axs[1].plot(twiss_sad.s, twiss_sad.py, label = 'SAD', color = "r")
    axs[1].plot(twiss_xsuite.s, twiss_xsuite.py, label = 'Xsuite', color = "b", linestyle = "--")
    axs[0].legend()
    axs[0].set_ylabel(r'$p_{x}$ [m]')
    axs[1].set_ylabel(r'$p_{y}$ [m]')
    axs[1].set_xlabel('s [m]')

    fig, axs = plt.subplots(2, figsize = (12, 8), sharex = True)
    axs[0].plot(twiss_sad.s, twiss_sad.zeta, label = 'SAD', color = "r")
    axs[0].plot(twiss_xsuite.s, twiss_xsuite.zeta, label = 'Xsuite', color = "b", linestyle = "--")
    axs[1].plot(twiss_sad.s, twiss_sad.delta, label = 'SAD', color = "r")
    axs[1].plot(twiss_xsuite.s, twiss_xsuite.delta, label = 'Xsuite', color = "b", linestyle = "--")
    axs[0].legend()
    axs[0].set_ylabel(r'$\zeta$ [m]')
    axs[1].set_ylabel(r'$\delta$ [m]')
    axs[1].set_xlabel('s [m]')

    fig, axs = plt.subplots(2, figsize = (12, 8), sharex = True)
    axs[0].plot(twiss_sad.s, twiss_sad.betx, label = 'SAD', color = "r")
    axs[0].plot(twiss_xsuite.s, twiss_xsuite.betx, label = 'Xsuite', color = "b", linestyle = "--")
    axs[1].plot(twiss_sad.s, twiss_sad.bety, label = 'SAD', color = "r")
    axs[1].plot(twiss_xsuite.s, twiss_xsuite.bety, label = 'Xsuite', color = "b", linestyle = "--")
    axs[0].legend()
    axs[0].set_ylabel(r'$\beta_{x}$ [m]')
    axs[1].set_ylabel(r'$\beta_{y}$ [m]')
    axs[1].set_xlabel('s [m]')

    fig, axs = plt.subplots(2, figsize = (12, 8), sharex = True)
    axs[0].plot(twiss_sad.s, twiss_sad.alfx, label = 'SAD', color = "r")
    axs[0].plot(twiss_xsuite.s, twiss_xsuite.alfx, label = 'Xsuite', color = "b", linestyle = "--")
    axs[1].plot(twiss_sad.s, twiss_sad.alfy, label = 'SAD', color = "r")
    axs[1].plot(twiss_xsuite.s, twiss_xsuite.alfy, label = 'Xsuite', color = "b", linestyle = "--")
    axs[0].legend()
    axs[0].set_ylabel(r'$\alpha_{x}$ [m]')
    axs[1].set_ylabel(r'$\alpha_{y}$ [m]')
    axs[1].set_xlabel('s [m]')

    fig, axs = plt.subplots(2, figsize = (12, 8), sharex = True)
    axs[0].plot(twiss_sad.s, twiss_sad.dx, label = 'SAD', color = "r")
    axs[0].plot(twiss_xsuite.s, twiss_xsuite.dx, label = 'Xsuite', color = "b", linestyle = "--")
    axs[1].plot(twiss_sad.s, twiss_sad.dy, label = 'SAD', color = "r")
    axs[1].plot(twiss_xsuite.s, twiss_xsuite.dy, label = 'Xsuite', color = "b", linestyle = "--")
    axs[0].legend()
    axs[0].set_ylabel(r'$D_{x}$ [m]')
    axs[1].set_ylabel(r'$D_{y}$ [m]')
    axs[1].set_xlabel('s [m]')

    fig, axs = plt.subplots(2, figsize = (12, 8), sharex = True)
    axs[0].plot(twiss_sad.s, twiss_sad.dpx, label = 'SAD', color = "r")
    axs[0].plot(twiss_xsuite.s, twiss_xsuite.dpx, label = 'Xsuite', color = "b", linestyle = "--")
    axs[1].plot(twiss_sad.s, twiss_sad.dpy, label = 'SAD', color = "r")
    axs[1].plot(twiss_xsuite.s, twiss_xsuite.dpy, label = 'Xsuite', color = "b", linestyle = "--")
    axs[0].legend()
    axs[0].set_ylabel(r'$D_{px}$ [m]')
    axs[1].set_ylabel(r'$D_{py}$ [m]')
    axs[1].set_xlabel('s [m]')
