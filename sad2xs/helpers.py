"""
(Unofficial) SAD to XSuite Converter: Helpers
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-27
"""

################################################################################
# Required Packages
################################################################################
import xtrack as xt

################################################################################
# Reference Particle Species
################################################################################
def species_from_mass_and_charge(mass0_ev, q0):
    """Map (mass, charge) to an xtrack species string, or None if unrecognised."""
    if abs(mass0_ev - xt.ELECTRON_MASS_EV) / xt.ELECTRON_MASS_EV < 1e-3:
        return "electron" if q0 < 0 else "positron"
    if abs(mass0_ev - xt.PROTON_MASS_EV) / xt.PROTON_MASS_EV < 1e-3:
        return "antiproton" if q0 < 0 else "proton"
    return None

################################################################################
# Section Heading Function
################################################################################
def print_section_heading(heading, mode = 'section'):
    """
    Prints a section heading with a specific format.
    Args:
        heading (str): The title of the section.
        mode (str): The mode of the heading, either 'section', 'subsection' or 'subsubsection'.
    """
    if mode == 'section':
        print("\n" + "#" * 80 + "\n" + heading + "\n" + "#" * 80)
    elif mode == 'subsection':
        print("\n" + "#" * 60 + "\n" + heading + "\n" + "#" * 60)
    elif mode == 'subsubsection':
        print("\n" + "#" * 40 + "\n" + heading + "\n" + "#" * 40)
    else:
        raise ValueError("Invalid mode. Use 'section', 'subsection' or 'subsubsection'.")