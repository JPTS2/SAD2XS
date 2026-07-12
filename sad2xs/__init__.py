"""
(Unofficial) SAD to XSuite Converter: Initialization
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-12
"""

################################################################################
# Required Packages
################################################################################
import importlib

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
def __getattr__(name):
    if name == "sad_helpers":
        module = importlib.import_module(".sad_helpers", __name__)
        globals()["sad_helpers"] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
