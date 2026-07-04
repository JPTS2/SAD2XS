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
from contextlib import contextmanager

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
        mode (str): 'banner' (80 wide, marks the major phases) or
            'section' (40 wide, marks each stage within a phase).
    """
    widths  = {'banner': 80, 'section': 40}
    if mode not in widths:
        raise ValueError("Invalid mode. Use 'banner' or 'section'.")
    bar     = "#" * widths[mode]
    logger.info("\n" + bar + "\n" + heading + "\n" + bar)

################################################################################
# Xtrack Progress Suppression
################################################################################
@contextmanager
def suppressed_xtrack_progress(active = True):
    """
    Temporarily replace xtrack's progress indicator with a passthrough, so
    quiet-mode conversions do not show progress bars from xtrack internals
    (e.g. line.replace_all_repeated_elements when reloading generated files).
    """
    if not active:
        yield
        return

    from xtrack import progress_indicator as xt_progress

    saved_cls       = xt_progress._config.default_indicator_cls
    saved_options   = xt_progress._config.default_options

    def _passthrough(iterable, **_kwargs):
        return iterable

    xt_progress.set_default_indicator(_passthrough)
    try:
        yield
    finally:
        xt_progress.set_default_indicator(saved_cls, **saved_options)
