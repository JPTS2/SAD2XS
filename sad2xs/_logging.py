"""
================================================================================
Logging Configuration
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
import logging

################################################################################
# Package Logger
################################################################################
LOGGER  = logging.getLogger("sad2xs")

_LEVELS = {
    "debug":    logging.DEBUG,
    "info":     logging.INFO,
    "warning":  logging.WARNING,
    "error":    logging.ERROR}

################################################################################
# Formatter
################################################################################
class _SAD2XSFormatter(logging.Formatter):
    """
    Prefix warnings and errors so they stand out on the terminal.
    The INFO/DEBUG narrative is left unprefixed.
    """
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record, prefixing WARNING/ERROR levels only.

        Parameters
        ----------
        record : logging.LogRecord
            The log record to format.

        Returns
        -------
        str
            The formatted message: prefixed with "SAD2XS <LEVEL>:" for
            WARNING and above, otherwise the bare message.
        """
        if record.levelno >= logging.WARNING:
            return f"SAD2XS {record.levelname}: {record.getMessage()}"
        return record.getMessage()

################################################################################
# Default Handler Installation
################################################################################
def initialise_logging() -> None:
    """
    Attach the default stderr handler to the package logger.

    Called once at package import. By default only warnings and errors are
    shown; use set_log_level to change this. Users who configure the logging
    module themselves can remove or replace the handler on
    logging.getLogger("sad2xs").
    """
    if LOGGER.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(_SAD2XSFormatter())
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.WARNING)

################################################################################
# User Level Control
################################################################################
def set_log_level(level: str) -> None:
    """
    Set the SAD2XS terminal output level.

    Parameters
    ----------
    level : str
        One of "debug", "info", "warning", "error".
        "warning" (the default) keeps SAD2XS quiet except for warnings and
        errors. "info" adds the conversion progress narrative. "debug" adds
        per-element conversion detail and external SAD output.
    """
    if level.lower() not in _LEVELS:
        raise ValueError(
            f"Unknown log level '{level}'. Choose from {sorted(_LEVELS)}.")
    LOGGER.setLevel(_LEVELS[level.lower()])
