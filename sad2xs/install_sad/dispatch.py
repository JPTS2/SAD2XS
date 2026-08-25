"""
================================================================================
SAD Installation Platform Dispatch
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-08-25
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import sys

from .._logging import set_log_level

################################################################################
# Platform Guard
################################################################################
def require_platform(prefix: str, name: str) -> None:
    """
    Exit unless the running platform is the one this installer supports.

    Called by each platform module for its own platform. Checking the
    specific platform rather than "some installer exists" is what stops the
    macOS installer running on Linux once Linux has an installer too.

    Parameters
    ----------
    prefix : str
        The `sys.platform` prefix this installer supports.
    name : str
        Platform name to use in the message.

    Raises
    ------
    SystemExit
        If the running platform is not the supported one.
    """
    if sys.platform.startswith(prefix):
        return

    sys.exit(
        f"This installer is for {name}, but sys.platform is "
        f"{sys.platform!r}. Run sad2xs-install-sad to get the right one.")

################################################################################
# Install SAD
################################################################################
def install_sad() -> None:
    """
    Build SAD from source for the running platform.

    Backs the `sad2xs-install-sad` console script, so it raises the package
    log level to info: the build narrative is the whole point of the
    command, and the package default shows warnings only.

    Raises
    ------
    SystemExit
        If no installer exists for the running platform.
    """
    set_log_level("info")

    # Imported per branch, never at module scope: each installer reaches for
    # tools that exist only on its own platform.
    if sys.platform.startswith("darwin"):
        from .macos import install_sad_macos     # pylint: disable=import-outside-toplevel
        install_sad_macos()
        return

    sys.exit(
        f"No SAD installer for sys.platform {sys.platform!r}. "
        f"Supported: macOS.")
