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
import matplotlib.pyplot as plt

################################################################################
# User Parameters
################################################################################
SAD_LATTICE_PATH            = "lattices/fccee_sol.sad"
REBUILT_SAD_LATTICE_PATH    = "lattices/fccee_sol_rebuilt.sad"
LINE_NAME                   = "RING"

################################################################################
# Load Reference Data
################################################################################
s2x.sad_helpers.rebuild_sad_lattice(
    lattice_filepath    = SAD_LATTICE_PATH,
    line_name           = LINE_NAME,
    additional_commands = """
LINE["DISFRIN", "ESL*"]     = 1;
LINE["DISFRIN", "ESR*"]     = 1;
LINE["DISFRIN", "ESCR*"]    = 1;
LINE["DISFRIN", "ESCL*"]    = 1;
LINE["F1", "ESL*"]          = 0;
LINE["F1", "ESR*"]          = 0;
LINE["F1", "ESCL*"]         = 0;
LINE["F1", "ESCR*"]         = 0;""",
    output_filepath     = REBUILT_SAD_LATTICE_PATH)

tw_sad  = s2x.sad_helpers.twiss_sad(
    lattice_filepath        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    calc6d                  = False,
    closed                  = True,
    reverse_element_order   = False,
    reverse_bend_direction  = False,
    additional_commands     = "")

em_sad  = s2x.sad_helpers.emit_sad(
    lattice_filepath        = REBUILT_SAD_LATTICE_PATH,
    line_name               = LINE_NAME)

################################################################################
# Convert Lattice
################################################################################
line    = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = REBUILT_SAD_LATTICE_PATH,
    line_name                   = LINE_NAME,
    excluded_elements           = None,
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_bend_direction      = False,
    reverse_charge              = False,
    output_directory            = "out",
    output_filename             = "fcc_sol",
    output_header               = "FCC-ee LCC With Solenoid")

########################################
# Delete rebuilt line
########################################
os.remove(REBUILT_SAD_LATTICE_PATH)

################################################################################
# Swap out solenoids
################################################################################
tt      = line.get_table(attr = True)
tt_ip2  = tt.rows[(tt.s > tt["s", "ip.2"] - 20) & (tt.s < tt["s", "ip.2"] + 20)]

pritn()

################################################################################
# Match Reference Frame Transforms
################################################################################

########################################
# Sol Out
########################################
opt = line.match(
    method  = "4d",
    solve   = False,
    vary    = [
        xt.VaryList(
            vars    = [
                "dx_esr1_dxy", "dy_esr1_dxy", "chi1_esr0_chi1", "chi2_esr0_chi2"],
            step    = 1E-10)],
    targets = [
        xt.TargetSet(
            tars    = ["x", "px", "y", "py"],
            value   = 0,
            tol     = 1E-16,
            at      = xt.END)],
    start       = "ip.0",
    end         = "-bc0.0",
    init        = xt.TwissInit())
opt.solve()

########################################
# Sol In
########################################
opt = line.match(
    method  = "4d",
    solve   = False,
    vary    = [
        xt.VaryList(
            vars    = [
                "dx_esl1_dxy", "dy_esl1_dxy", "chi1_esl0_chi1", "chi2_esl0_chi2"],
            step    = 1E-10)],
    targets = [
        xt.TargetSet(
            tars    = ["x", "px", "y", "py"],
            value   = 0,
            tol     = 1E-16,
            at      = xt.END)],
    start       = "ip.0",
    end         = "ip.2",
    init        = xt.TwissInit())
opt.solve()

################################################################################
# Test Twiss
################################################################################
line.configure_radiation(model = None)
tw0 = line.twiss4d(init = xt.TwissInit())
fig, ax = plt.subplots(1, 1, figsize = (8, 4))
ax.plot(tw_sad.s, tw_sad.y, c = "r", label = "SAD")
ax.plot(tw0.s, tw0.y, c = "b", linestyle = "--", label = "Xsuite")
ax.legend()
ax.set_xlim(0, 40000)
ax.set_yscale("symlog", linthresh = 1E-12)
ax.set_xlabel("s [m]")
ax.set_ylabel("y [m]")
ax.set_title("4D Open")

line.configure_radiation(model = None)
tw1 = line.twiss4d()
fig, ax = plt.subplots(1, 1, figsize = (8, 4))
ax.plot(tw_sad.s, tw_sad.y, c = "r", label = "SAD")
ax.plot(tw1.s, tw1.y, c = "b", linestyle = "--", label = "Xsuite")
ax.legend()
ax.set_xlim(0, 40000)
ax.set_yscale("symlog", linthresh = 1E-12)
ax.set_xlabel("s [m]")
ax.set_ylabel("y [m]")
ax.set_title("4D Closed")

line.configure_radiation(model = None)
tw2 = line.twiss6d()
fig, ax = plt.subplots(1, 1, figsize = (8, 4))
ax.plot(tw_sad.s, tw_sad.y, c = "r", label = "SAD")
ax.plot(tw2.s, tw2.y, c = "b", linestyle = "--", label = "Xsuite")
ax.legend()
ax.set_xlim(0, 40000)
ax.set_yscale("symlog", linthresh = 1E-12)
ax.set_xlabel("s [m]")
ax.set_ylabel("y [m]")
ax.set_title("6D Closed")

# ################################################################################
# # Slice
# ################################################################################

# ########################################
# # Check the table first
# ########################################
# tt0 = line.get_table(attr = True)
# fig, ax = plt.subplots(1)
# ax.step(tt0.s, tt0.ks, where = "post")
# ax.set_xlim(tt0["s", "ip.2"] - 50, tt0["s", "ip.2"] + 50)

# ########################################
# # Slice Solenoids
# ########################################
# slicing_strategies  = [
#     xt.Strategy(slicing = None),
#     xt.Strategy(
#         slicing         = xt.Teapot(100, mode = "thick"),
#         element_type    = xt.UniformSolenoid)]
# line.slice_thick_elements(slicing_strategies = slicing_strategies)

# ########################################
# # Check the table after
# ########################################
# tt1  = line.get_table(attr = True)
# fig, ax = plt.subplots(1)
# ax.step(tt1.s, tt1.ks, where = "post")
# ax.set_xlim(tt1["s", "ip.2"] - 50, tt1["s", "ip.2"] + 50)

# ########################################
# # Plot IR Orbit
# ########################################
# line.configure_radiation(model = None)
# tw3 = line.twiss6d()

# fig, axs    = plt.subplots(2, 1, figsize = (8, 4))
# axs[0].plot(tw_sad.s - tw_sad["s", "IP.3"], tw_sad.x, c = "r", label = "SAD")
# axs[0].plot(tw2.s - tw2["s", "ip.2"], tw2.x, c = "b", linestyle = "--", label = "Xsuite")
# axs[0].plot(tw3.s - tw3["s", "ip.2"], tw3.x, c = "m", linestyle = ":", label = "Xsuite Sliced")
# axs[1].plot(tw_sad.s - tw_sad["s", "IP.3"], tw_sad.y, c = "r", label = "SAD")
# axs[1].plot(tw2.s - tw2["s", "ip.2"], tw2.y, c = "b", linestyle = "--", label = "Xsuite")
# axs[1].plot(tw3.s - tw3["s", "ip.2"], tw3.y, c = "m", linestyle = ":", label = "Xsuite Sliced")
# axs[0].legend()
# axs[0].set_xlim(-3, +3)
# axs[0].set_xlabel("s [m]")
# axs[0].set_ylabel("x [m]")
# axs[1].set_ylabel("y [m]")
# axs[0].set_title("IR Orbit")

# fig, axs    = plt.subplots(2, 1, figsize = (8, 4))
# axs[0].plot(tw_sad.s - tw_sad["s", "IP.3"], tw_sad.px, c = "r", label = "SAD")
# axs[0].plot(tw2.s - tw2["s", "ip.2"], tw2.px, c = "b", linestyle = "--", label = "Xsuite")
# axs[0].plot(tw3.s - tw3["s", "ip.2"], tw3.px, c = "m", linestyle = ":", label = "Xsuite Sliced")
# axs[1].plot(tw_sad.s - tw_sad["s", "IP.3"], tw_sad.py, c = "r", label = "SAD")
# axs[1].plot(tw2.s - tw2["s", "ip.2"], tw2.py, c = "b", linestyle = "--", label = "Xsuite")
# axs[1].plot(tw3.s - tw3["s", "ip.2"], tw3.py, c = "m", linestyle = ":", label = "Xsuite Sliced")
# axs[0].legend()
# axs[0].set_xlim(-3, +3)
# axs[0].set_xlabel("s [m]")
# axs[0].set_ylabel("px [rad]")
# axs[1].set_ylabel("py [rad]")
# axs[0].set_title("IR Momentum")

# fig, axs    = plt.subplots(2, 1, figsize = (8, 4))
# axs[0].plot(tw_sad.s - tw_sad["s", "IP.3"], tw_sad.betx, c = "r", label = "SAD")
# axs[0].plot(tw2.s - tw2["s", "ip.2"], tw2.betx, c = "b", linestyle = "--", label = "Xsuite")
# axs[0].plot(tw3.s - tw3["s", "ip.2"], tw3.betx, c = "m", linestyle = ":", label = "Xsuite Sliced")
# axs[1].plot(tw_sad.s - tw_sad["s", "IP.3"], tw_sad.bety, c = "r", label = "SAD")
# axs[1].plot(tw2.s - tw2["s", "ip.2"], tw2.bety, c = "b", linestyle = "--", label = "Xsuite")
# axs[1].plot(tw3.s - tw3["s", "ip.2"], tw3.bety, c = "m", linestyle = ":", label = "Xsuite Sliced")
# axs[0].legend()
# axs[0].set_xlim(-3, +3)
# axs[0].set_xlabel("s [m]")
# axs[0].set_ylabel("betx [m]")
# axs[1].set_ylabel("bety [m]")
# axs[0].set_title("IR Orbit")

################################################################################
# Twiss
################################################################################

########################################
# No Radiation
########################################
tw4         = line.twiss(spin = True)
tilt_norad  = np.arctan2(np.sqrt(tw4.spin_x**2 + tw4.spin_z**2), tw4.spin_y)
fig, ax = plt.subplots(1, 1, figsize = (8, 4))
ax.plot(tw4.s - tw4["s", "ip.2"], tilt_norad * 1E3, c = "b")
ax.set_xlim(-20, +20)
ax.set_ylim(0)
ax.set_xlabel("s [m]")
ax.set_ylabel("n0 [mrad]")
ax.set_title("No Radiation Tilt")

fig, ax = plt.subplots(1, 1, figsize = (8, 4))
ax.plot(tw4.s - tw4["s", "ip.2"], tw4.spin_y, c = "b")
ax.set_xlim(-20, +20)
ax.set_xlabel("s [m]")
ax.set_ylabel("n0 [mrad]")
ax.set_title("No Radiation Spin y")

fig, ax = plt.subplots(1, 1, figsize = (8, 4))
ax.plot(tw4.s - tw4["s", "ip.2"], np.arccos(tw4.spin_y), c = "b")
ax.set_xlim(-20, +20)
ax.set_ylim(0)
ax.set_xlabel("s [m]")
ax.set_ylabel("n0 [mrad]")
ax.set_title("No Radiation Angle y")

########################################
# Radiation
########################################
line.configure_radiation(model = "mean")
line.compensate_radiation_energy_loss()
tw5         = line.twiss(
    spin                = True,
    eneloss_and_damping = True,
    polarization        = True)
tilt_rad    = np.arctan2(np.sqrt(tw5.spin_x**2 + tw5.spin_z**2), tw5.spin_y)
fig, ax = plt.subplots(1, 1, figsize = (8, 4))
ax.plot(tw5.s - tw5["s", "ip.2"], tilt_rad * 1E3, c = "b")
ax.set_xlim(-20, +20)
ax.set_ylim(0)
ax.set_xlabel("s [m]")
ax.set_ylabel("n0 [mrad]")
ax.set_title("Radiation Tilt")

########################################
# Radiation
########################################
fig, ax = plt.subplots(1, 1, figsize = (8, 4))
ax.plot(tw5.s, tilt_rad * 1E3, c = "b")
ax.set_xlim(22600, 22720)
ax.set_ylim(0)
ax.set_xlabel("s [m]")
ax.set_ylabel("n0 [mrad]")
ax.set_title("Radiation Tilt")

################################################################################
# Show Plots
################################################################################
plt.show()


fig, ax = plt.subplots(1, 1, figsize = (8, 4))
ax.plot(tw4.s, tilt_norad * 1E3, c = "b")
ax.set_xlabel("s [m]")
ax.set_ylabel("n0 [mrad]")
ax.set_title("No Radiation Tilt")

test_tw = tw4.rows[(tw4.s > tw4["s", "ip.2"] - 5) & (tw4.s < tw4["s", "ip.2"] + 5)]

fig, axs = plt.subplots(3, 1)
axs[0].plot(test_tw.s, test_tw.y)
axs[1].plot(test_tw.s, test_tw.spin_z)
axs[2].plot(test_tw.s, test_tw.spin_x)

fig, ax = plt.subplots(1, 1)
ax.scatter(test_tw.spin_z, test_tw.spin_x, c = test_tw.s)
plt.show()
