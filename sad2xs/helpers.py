"""
================================================================================
General Helper Functions
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-21
================================================================================
"""

################################################################################
# Required Packages
################################################################################
import logging
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Any

import xtrack as xt

logger  = logging.getLogger(__name__)

################################################################################
# Reference Particle Species
################################################################################
def species_from_mass_and_charge(mass0_ev: float, q0: float) -> str | None:
    """
    Map a reference particle's mass and charge to an xtrack species name.

    Matches `mass0_ev` against the electron and proton rest masses to
    within 0.1%, then uses the sign of `q0` to pick the particle vs.
    antiparticle.

    Parameters
    ----------
    mass0_ev : float
        Reference particle rest mass, in eV.
    q0 : float
        Reference particle charge, in units of the elementary charge.

    Returns
    -------
    str or None
        One of "electron", "positron", "proton", "antiproton", or None
        if `mass0_ev` does not match a recognised species.
    """
    if abs(mass0_ev - xt.ELECTRON_MASS_EV) / xt.ELECTRON_MASS_EV < 1e-3:
        return "electron" if q0 < 0 else "positron"
    if abs(mass0_ev - xt.PROTON_MASS_EV) / xt.PROTON_MASS_EV < 1e-3:
        return "antiproton" if q0 < 0 else "proton"
    return None

################################################################################
# Section Heading Function
################################################################################
def log_section_heading(heading: str, mode: str = "section") -> None:
    """
    Log a section heading at INFO level, framed by a horizontal rule.

    Parameters
    ----------
    heading : str
        The title of the section.
    mode : str, optional
        "banner" (80 characters wide, marks the major conversion phases)
        or "section" (40 characters wide, marks each stage within a
        phase). Defaults to "section".

    Raises
    ------
    ValueError
        If `mode` is not "banner" or "section".
    """
    widths  = {"banner": 80, "section": 40}
    if mode not in widths:
        raise ValueError("""Invalid mode. Use "banner" or "section".""")
    bar     = "#" * widths[mode]
    logger.info("\n" + bar + "\n" + heading + "\n" + bar)

################################################################################
# Xtrack Progress Suppression
################################################################################
@contextmanager
def suppressed_xtrack_progress(active: bool = True) -> Iterator[None]:
    """
    Temporarily replace xtrack's progress indicator with a passthrough.

    Prevents quiet-mode conversions from showing progress bars driven by
    xtrack internals (e.g. `Line.replace_all_repeated_elements` when
    reloading generated files), restoring xtrack's previous indicator
    once the context exits.

    Parameters
    ----------
    active : bool, optional
        If False, this is a no-op context manager (used when the caller
        already wants xtrack's normal progress indicator, e.g. verbose
        mode). Defaults to True.

    Yields
    ------
    None
        Control returns to the wrapped `with` block; nothing is yielded.
    """
    if not active:
        yield
        return

    from xtrack import progress_indicator as xt_progress

    saved_cls       = xt_progress._config.default_indicator_cls
    saved_options   = xt_progress._config.default_options

    def _passthrough(iterable: Iterable, **_kwargs: Any) -> Iterable:
        """
        Return `iterable` unchanged, discarding any progress-bar kwargs.

        Matches xtrack's progress-indicator factory signature
        (iterable, **kwargs -> iterable), so it can be installed via
        `set_default_indicator` as a no-op replacement.

        Parameters
        ----------
        iterable : iterable
            The iterable xtrack would otherwise wrap with a progress
            bar.
        **_kwargs
            Progress-indicator options (e.g. description, total),
            discarded.

        Returns
        -------
        iterable
            `iterable`, unchanged.
        """
        return iterable

    xt_progress.set_default_indicator(_passthrough)
    try:
        yield
    finally:
        xt_progress.set_default_indicator(saved_cls, **saved_options)
