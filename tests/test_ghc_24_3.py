"""
Test conversion of FCCee Z GHC 24.3 Lattice from SAD to XSuite
=============================================
Author(s): John P T Salvesen
Email:  john.salvesen@cern.ch
Date:   20-11-2024
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
# Load Reference JSON
################################################################################
# JSON converted from SAD to MADX using SAD2MADX (K. Oide)
# Then converted from MADX to XSuite (M. Hofer)
line_sad2mad    = xt.Line.from_json('lattices/ghc_24_3_mh.json')

# Set reference particle
line_sad2mad.particle_ref   = xt.Particles(
    p0c     = 45.6E9,
    mass0   = xt.ELECTRON_MASS_EV)

################################################################################
# Convert SAD to XSuite
################################################################################
line_sad2xs, line_sad2xs_markers    = sad2xsuite(
    sad_lattice_path        = 'lattices/ghc_24_3.sad',
    multipole_replacements  = None,
    ref_particle_mass0      = xt.ELECTRON_MASS_EV,
    bend_edge_model         = 'linear',
    ref_particle_p0c        = None,
    install_markers         = True)

################################################################################
# Build Trackers
################################################################################
line_sad2mad.build_tracker()
line_sad2xs.build_tracker()

################################################################################
# Compare Surveys
################################################################################
sv_sad2mad  = line_sad2mad.survey()
sv_sad2xs   = line_sad2xs.survey()

########################################
# Plot Comparisons
########################################
fig, axs = plt.subplots(2, 2, figsize=(10, 8))

axs[0, 0].plot(sv_sad2mad.s, sv_sad2mad.X, linestyle = ':', label='SAD2MAD')
axs[0, 0].plot(sv_sad2xs.s, sv_sad2xs.X, linestyle = ':', label='SAD2XS')
axs[0, 0].set_xlabel('s [m]')
axs[0, 0].set_ylabel('X [m]')
axs[0, 0].set_title('Horizontal Position')

axs[0, 1].plot(sv_sad2mad.s, sv_sad2mad.Y, linestyle = ':', label='SAD2MAD')
axs[0, 1].plot(sv_sad2xs.s, sv_sad2xs.Y, linestyle = ':', label='SAD2XS')
axs[0, 1].set_xlabel('s [m]')
axs[0, 1].set_ylabel('Y [m]')
axs[0, 1].set_title('Vertical Position')

axs[1, 0].plot(sv_sad2mad.s, sv_sad2mad.Z, linestyle = ':', label='SAD2MAD')
axs[1, 0].plot(sv_sad2xs.s, sv_sad2xs.Z, linestyle = ':', label='SAD2XS')
axs[1, 0].set_xlabel('s [m]')
axs[1, 0].set_ylabel('Z [m]')
axs[1, 0].set_title('Longitudinal Position')

axs[1, 1].plot(sv_sad2mad.Z, sv_sad2mad.X, linestyle = ':', label='SAD2MAD')
axs[1, 1].plot(sv_sad2xs.Z, sv_sad2xs.X, linestyle = ':', label='SAD2XS')
axs[1, 1].set_xlabel('Z [m]')
axs[1, 1].set_ylabel('X [m]')
axs[1, 1].set_title('Floor Plot')
plt.legend()

plt.figure()
plt.plot(sv_sad2mad.Z, sv_sad2mad.X * 1E9, linestyle = ':', label='SAD2MAD')
plt.plot(sv_sad2xs.Z, sv_sad2xs.X * 1E9, linestyle = ':', label='SAD2XS')
plt.xlim(-10, 10)
plt.ylim(-10, 10)
plt.xlabel('Z [m]')
plt.ylabel('X [nm]')
plt.legend()

########################################
# Survey Path Length
########################################
print('\n \n')
print('Survey Path Comparison')
print(f'SAD2MAD Survey Path Length: {sv_sad2mad.s[-1]} m')
print(f'SAD2XS Survey Path Length: {sv_sad2xs.s[-1]} m')
print(f'Survey Path Length Difference: {sv_sad2mad.s[-1] - sv_sad2xs.s[-1]} m')
print('\n \n')

################################################################################
# Twiss
################################################################################
twiss_sad2mad   = line_sad2mad.twiss4d()
twiss_sad2xs    = line_sad2xs.twiss4d()

########################################
# Plot Comparisons
########################################
twiss_sad2mad.plot()
plt.title('SAD2MAD')

twiss_sad2xs.plot()
plt.title('SAD2XS')

########################################
# Twiss Path Length
########################################
print('Twiss Path Comparison')
print(f'SAD2MAD Twiss Path Length: {max(twiss_sad2mad.s)}m')
print(f'SAD2XS Twiss Path Length: {max(twiss_sad2xs.s)}m')
print(f'Twiss Path Length Difference: {max(twiss_sad2mad.s) - max(twiss_sad2xs.s)}m')
print('\n \n')

########################################
# IP Beta
########################################
print('IP Beta Comparison')
print(f'SAD2MAD IP Beta: ({min(twiss_sad2mad.betx)}, {min(twiss_sad2mad.bety)})m')
print(f'SAD2XS IP Beta: ({min(twiss_sad2xs.betx)}, {min(twiss_sad2xs.bety)})m')
print(f'IP Beta Difference: ({min(twiss_sad2mad.betx) - min(twiss_sad2xs.betx)},'
    f'{min(twiss_sad2mad.bety) - min(twiss_sad2xs.bety)})m')
print('\n \n')

########################################
# Tune
########################################
print('Tune Comparison')
print(f'SAD2MAD Tune: ({twiss_sad2mad.qx}, {twiss_sad2mad.qy})')
print(f'SAD2XS Tune: ({twiss_sad2xs.qx}, {twiss_sad2xs.qy})')
print(f'Tune Difference: ({twiss_sad2mad.qx - twiss_sad2xs.qx},'
    f'{twiss_sad2mad.qy - twiss_sad2xs.qy})')
print('\n \n')

########################################
# Show All Plots
########################################
plt.show()
