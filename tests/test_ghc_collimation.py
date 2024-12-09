"""
Test conversion of FCCee Z GHC 24.3 Lattice from SAD to XSuite
=============================================
Author(s): John P T Salvesen
Email:  john.salvesen@cern.ch
Date:   21-08-2024
"""

################################################################################
# Required Package(s)
################################################################################
from os import sys, path
import xtrack as xt
import matplotlib.pyplot as plt

################################################################################
# Load Module(s)
################################################################################
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from sad2xs import sad2xsuite

################################################################################
# Convert SAD to XSuite
################################################################################
# section = sad2xsuite(
line, line_markers  = sad2xsuite(
    sad_lattice_path        = 'lattices/ghc_collimation.sad',
    multipole_replacements  = None,
    ref_particle_mass0      = xt.ELECTRON_MASS_EV,
    bend_edge_model         = 'linear',
    ref_particle_p0c        = None,
    install_markers         = True)

################################################################################
# Build Trackers
################################################################################
line.build_tracker()

################################################################################
# Compare Surveys
################################################################################
sv = line.survey()

########################################
# Plot Comparisons
########################################
fig, axs    = plt.subplots(2, 2, figsize=(10, 8))

axs[0, 0].plot(sv.s, sv.X, linestyle = ':')
axs[0, 0].set_xlabel('s [m]')
axs[0, 0].set_ylabel('X [m]')
axs[0, 0].set_title('Horizontal Position')

axs[0, 1].plot(sv.s, sv.Y, linestyle = ':')
axs[0, 1].set_xlabel('s [m]')
axs[0, 1].set_ylabel('Y [m]')
axs[0, 1].set_title('Vertical Position')

axs[1, 0].plot(sv.s, sv.Z, linestyle = ':')
axs[1, 0].set_xlabel('s [m]')
axs[1, 0].set_ylabel('Z [m]')
axs[1, 0].set_title('Longitudinal Position')

axs[1, 1].plot(sv.Z, sv.X, linestyle = ':')
axs[1, 1].set_xlabel('Z [m]')
axs[1, 1].set_ylabel('X [m]')
axs[1, 1].set_title('Floor Plot')

plt.figure()
plt.plot(sv.Z, sv.X * 1E9, linestyle = ':')
plt.xlim(-10, 10)
plt.ylim(-10, 10)
plt.xlabel('Z [m]')
plt.ylabel('X [nm]')

########################################
# Survey Path Length
########################################
print('\n \n')
print('Path Length')
print(f'Survey Path Length: {sv.s[-1]} m')
print('\n \n')

################################################################################
# Twiss
################################################################################
twiss   = line.twiss4d()

########################################
# Plot
########################################
twiss.plot()
plt.title('Twiss')

########################################
# Twiss Path Length
########################################
print('Twiss Path')
print(f'Twiss Path Length: {max(twiss.s)}m')
print('\n \n')

########################################
# IP Beta
########################################
print('IP Beta')
print(f'IP Beta: ({min(twiss.betx)}, {min(twiss.bety)})m')
print('\n \n')

########################################
# Tune
########################################
print('Tune')
print(f'Tune: ({twiss.qx}, {twiss.qy})')
print('\n \n')

########################################
# Show All Plots
########################################
plt.show()
