"""
================================================================================
Package Initialisation
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-20
================================================================================
"""

################################################################################
# Required Packages
################################################################################
import importlib
from types import ModuleType

################################################################################
# Logging (default: warnings and errors only)
################################################################################
from ._logging import initialise_logging, set_log_level
initialise_logging()

################################################################################
# Main conversion function
################################################################################
from .main import convert_sad_to_xsuite

################################################################################
# Lattice and Optics writers
################################################################################
from .converter._009_write_lattice import write_lattice
from .converter._010_write_optics import write_optics

################################################################################
# Xsuite Helpers Functions
################################################################################
# No optionaldependencies, so eager import.
from . import xsuite_helpers

################################################################################
# SAD Helpers Functions
################################################################################
# Has optional dependencies, so lazy import (PEP 562).
def __getattr__(name: str) -> ModuleType:
    """
    Lazily import `sad_helpers` on first access (PEP 562).

    `sad_helpers` depends on a working SAD executable and is not required
    for the core converter, so it is only imported the first time
    ``sad2xs.sad_helpers`` is accessed rather than eagerly at package
    import time.

    Parameters
    ----------
    name : str
        Attribute name being accessed on the `sad2xs` package.

    Returns
    -------
    module
        The imported `sad_helpers` submodule.

    Raises
    ------
    AttributeError
        If `name` is not `"sad_helpers"`.
    """
    if name == "sad_helpers":
        module = importlib.import_module(".sad_helpers", __name__)
        globals()["sad_helpers"] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
