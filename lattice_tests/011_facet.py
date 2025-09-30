"""
(Unofficial) SAD to XSuite Converter
"""
################################################################################
# Required Packages
################################################################################
import sad2xs as s2x
import xtrack as xt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from _sad_helpers import twiss_sad

################################################################################
# User Parameters
################################################################################
SAD_LATTICE_PATH    = 'lattices/facet2e.sad'
LINE_NAME           = 'ASC'
BMAD_TWISS_PATH     = 'lattices/twiss_facet2e_bmad.txt'

################################################################################
# Load Reference Data
################################################################################

########################################
# BMAD Twiss
########################################
bmad_twiss  = pd.read_csv(BMAD_TWISS_PATH, delim_whitespace = True)

bmad_twiss['l'][0]  = 0.0  # Fix first element length to zero
bmad_twiss['l']     = bmad_twiss['l'].astype(float)

tw_bmad      = xt.TwissTable({
    'name':     np.array(bmad_twiss['name']),
    's':        +1 * np.array(bmad_twiss['s'].values),
    'l':        +1 * np.array(bmad_twiss['l']),
    'x':        +1 * np.array(bmad_twiss['orbit.x']),
    'y':        +1 * np.array(bmad_twiss['orbit.y']),
    'betx':     +1 * np.array(bmad_twiss['beta.a']),
    'bety':     +1 * np.array(bmad_twiss['beta.b'])})

########################################
# SAD Twiss
########################################
tw_sad  = twiss_sad(
    lattice_filename        = SAD_LATTICE_PATH,
    line_name               = LINE_NAME,
    method                  = "4d",
    closed                  = False,
    reverse_element_order   = False,
    reverse_bend_direction  = False,
    additional_commands     = "")

################################################################################
# Convert Lattice
################################################################################
line    = s2x.convert_sad_to_xsuite(
    sad_lattice_path            = SAD_LATTICE_PATH,
    line_name                   = "ASC",
    excluded_elements           = None,
    user_multipole_replacements = None,
    reverse_element_order       = False,
    reverse_bend_direction      = False,
    reverse_charge              = False,
    output_directory            = 'out/',
    output_filename             = "facet2e",
    output_header               = "FACET-2E")

########################################
# TODO: Work out what is wrong with these
########################################
# For some reason, the bmad to SAD conversion makes these solenoids really strong multipoles
# They are sterngth zero in the BMAD lattice file anyway, so we set them to zero here
# For the SAD twiss these elements were set to 0 also
line['sol10111'].knl   = [0]
line['sol10111'].ksl   = [0]
line['sol10121'].knl   = [0]
line['sol10121'].ksl   = [0]

################################################################################
# Benchmark
################################################################################

########################################
# Get table
########################################
tt  = line.get_table(attr = True)

########################################
# Get survey
########################################
sv  = line.survey()
sv.plot()

########################################
# Get twiss with bmad initial conditions
########################################
tw_xs_bmad  = line.twiss4d(
    start               = xt.START,
    end                 = xt.END,
    betx                = tw_bmad.betx[0],
    bety                = tw_bmad.bety[0],
    alfx                = 6.73144693254608040,
    alfy                = -4.72668591663344007)
tw_xs_bmad.plot()

########################################
# Get twiss with sad initial conditions
########################################
tw_xs_sad  = line.twiss4d(
    start               = xt.START,
    end                 = xt.END,
    betx                = tw_sad.betx[0],
    bety                = tw_sad.bety[0],
    alfx                = tw_sad.alfx[0],
    alfy                = tw_sad.alfy[0])
tw_xs_sad.plot()

################################################################################
# Comparison vs BMAD
################################################################################

########################################
# Plot betas
########################################
fig, axs = plt.subplots(2, figsize = (12, 8), sharex = True)

axs[0].plot(tw_xs_bmad.s, tw_xs_bmad.betx, label = "XS", color = "b")
axs[0].plot(tw_bmad.s, tw_bmad.betx, label = "BMAD", color = "m", linestyle = '--')

axs[1].plot(tw_xs_bmad.s, tw_xs_bmad.bety, label = "XS", color = "b")
axs[1].plot(tw_bmad.s, tw_bmad.bety, label = "BMAD", color = "m", linestyle = '--')

fig.supxlabel('s [m]')
axs[0].set_ylabel('betx [m]')
axs[1].set_ylabel('bety [m]')
fig.suptitle('Comparison of XSuite and BMAD Twiss')

for ax in axs.flat:
    ax.legend()
    ax.grid()

########################################
# Plot relative betas
########################################
fig, axs = plt.subplots(2, figsize = (12, 8), sharex = True)

axs[0].plot(
    tw_bmad.s,
    (
        (np.interp(tw_bmad.s, tw_xs_bmad.s, tw_xs_bmad.betx) - tw_bmad.betx) /\
        np.interp(tw_bmad.s, tw_xs_bmad.s, tw_xs_bmad.betx)
    ) * 100)
axs[1].plot(
    tw_bmad.s,
    (
        (np.interp(tw_bmad.s, tw_xs_bmad.s, tw_xs_bmad.bety) - tw_bmad.bety) /\
        np.interp(tw_bmad.s, tw_xs_bmad.s, tw_xs_bmad.bety)
    ) * 100)

fig.supxlabel('s [m]')
axs[0].set_ylabel('∆betx / betx [%]')
axs[1].set_ylabel('∆bety / bety [%]')
axs[0].set_title('Difference between XSuite and BMAD Twiss')

for ax in axs.flat:
    ax.grid()
    ax.set_ylim(-0.1, 0.1)

################################################################################
# Comparison vs SAD
################################################################################

########################################
# Plot betas
########################################
fig, axs = plt.subplots(2, figsize = (12, 8), sharex = True)

axs[0].plot(tw_xs_sad.s, tw_xs_sad.betx, label = "XS", color = "b")
axs[0].plot(tw_sad.s, tw_sad.betx, label = "SAD", color = "r", linestyle = '--')

axs[1].plot(tw_xs_sad.s, tw_xs_sad.bety, label = "XS", color = "b")
axs[1].plot(tw_sad.s, tw_sad.bety, label = "SAD", color = "r", linestyle = '--')

fig.supxlabel('s [m]')
axs[0].set_ylabel('betx [m]')
axs[1].set_ylabel('bety [m]')
fig.suptitle('Comparison of XSuite and SAD Twiss')

for ax in axs.flat:
    ax.legend()
    ax.grid()

########################################
# Plot relative betas
########################################
fig, axs = plt.subplots(2, figsize = (12, 8), sharex = True)

axs[0].plot(
    tw_sad.s,
    (
        (np.interp(tw_sad.s, tw_xs_sad.s, tw_xs_sad.betx) - tw_sad.betx) /\
        np.interp(tw_sad.s, tw_xs_sad.s, tw_xs_sad.betx)
    ) * 100)
axs[1].plot(
    tw_sad.s,
    (
        (np.interp(tw_sad.s, tw_xs_sad.s, tw_xs_sad.bety) - tw_sad.bety) /\
        np.interp(tw_sad.s, tw_xs_sad.s, tw_xs_sad.bety)
    ) * 100)

fig.supxlabel('s [m]')
axs[0].set_ylabel('∆betx / betx [%]')
axs[1].set_ylabel('∆bety / bety [%]')
axs[0].set_title('Difference between XSuite and SAD Twiss')

for ax in axs.flat:
    ax.grid()
    ax.set_ylim(-0.1, 0.1)

################################################################################
# Show plots
################################################################################
plt.show()
