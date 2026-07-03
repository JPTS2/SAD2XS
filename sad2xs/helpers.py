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
import logging

import xtrack as xt

logger  = logging.getLogger(__name__)

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
def log_section_heading(heading, mode = 'section'):
    """
    Logs a section heading at INFO level with a specific format.
    Args:
        heading (str): The title of the section.
        mode (str): The mode of the heading, either 'section', 'subsection' or 'subsubsection'.
    """
    widths  = {'section': 80, 'subsection': 60, 'subsubsection': 40}
    if mode not in widths:
        raise ValueError("Invalid mode. Use 'section', 'subsection' or 'subsubsection'.")
    logger.info("\n" + f"#### {heading} ".ljust(widths[mode], "#"))
