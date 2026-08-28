"""
================================================================================
SAD Installation Command Line and Platform Dispatch
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-08-27
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from .._logging import set_log_level
from ._helpers import (
    CommandError,
    InstallConfig,
    RollbackError,
    SAD_GIT_BRANCH,
    SAD_GIT_REPO_URL,
    default_bin_dir,
    default_prefix)

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
# Command Line
################################################################################
def parse_args_to_config(argv: list[str] | None = None) -> InstallConfig:
    """
    Turn command line arguments into an install configuration.

    Parameters
    ----------
    argv : list[str], optional
        Arguments to parse. Defaults to None, meaning `sys.argv[1:]`.

    Returns
    -------
    InstallConfig
        Configuration for the platform installer.

    Raises
    ------
    SystemExit
        If the arguments are invalid, or `--help` was requested. argparse
        exits directly in both cases.
    """
    prefix_default  = default_prefix()
    bin_dir_default = default_bin_dir()

    parser = argparse.ArgumentParser(
        prog        = "sad2xs-install-sad",
        description = "Build SAD from source and install a sad launcher.")

    ########################################
    # Install Locations
    ########################################
    parser.add_argument(
        "--prefix",
        type    = Path,
        default = prefix_default,
        help    = "directory for the SAD source tree and build logs "
                  f"(default: {prefix_default})")
    parser.add_argument(
        "--bin-dir",
        type    = Path,
        default = bin_dir_default,
        help    = f"directory for the sad launcher (default: {bin_dir_default})")

    ########################################
    # Source Selection
    ########################################
    parser.add_argument(
        "--repo-url",
        default = SAD_GIT_REPO_URL,
        help    = f"git URL to clone SAD from (default: {SAD_GIT_REPO_URL})")
    parser.add_argument(
        "--branch",
        # No argparse default: an explicitly named branch that is absent on
        # the remote is an error, while the default one falls back.
        default = None,
        help    = f"branch to clone (default: {SAD_GIT_BRANCH})")
    ########################################
    # Rebuild Behaviour
    ########################################
    parser.add_argument(
        "--reuse-clone",
        action  = "store_true",
        help    = "rebuild an existing source tree in place instead of "
                  "replacing it, which saves re-cloning on a slow or "
                  "quota-limited filesystem. The checkout must match "
                  "--repo-url and any explicit --branch, or the install is "
                  "refused. Note that an in-place rebuild can leave the tree "
                  "unusable if it fails part way; without this flag the "
                  "previous tree is held aside and put back if the new "
                  "build fails")

    args = parser.parse_args(argv)

    # InstallConfig normalises both directories, so nothing here has to.
    return InstallConfig(
        prefix          = args.prefix,
        bin_dir         = args.bin_dir,
        repo_url        = args.repo_url,
        branch          = args.branch or SAD_GIT_BRANCH,
        branch_explicit = args.branch is not None,
        reuse_clone     = args.reuse_clone)

################################################################################
# Entry Point
################################################################################

########################################
# Platform Installer Selection
########################################
def _platform_installer() -> Callable[[InstallConfig], None]:
    """
    Return the installer function for the running platform.

    Returns
    -------
    callable
        Takes an InstallConfig and performs the install.

    Raises
    ------
    SystemExit
        If no installer exists for the running platform.
    """
    # Imported per branch, never at module scope: each installer reaches for
    # tools that exist only on its own platform.
    if sys.platform.startswith("darwin"):
        from .macos import install_sad_macos     # pylint: disable=import-outside-toplevel
        return install_sad_macos

    if sys.platform.startswith("linux"):
        from .linux import install_sad_linux     # pylint: disable=import-outside-toplevel
        return install_sad_linux

    sys.exit(
        f"No SAD installer for sys.platform {sys.platform!r}. "
        f"Supported: macOS, Linux.")

########################################
# Install SAD
########################################
def install_sad(argv: list[str] | None = None) -> None:
    """
    Build SAD from source for the running platform.

    Backs the `sad2xs-install-sad` console script, so it raises the package
    log level to info: the build narrative is the whole point of the
    command, and the package default shows warnings only.

    Parameters
    ----------
    argv : list[str], optional
        Command line arguments. Defaults to None, meaning `sys.argv[1:]`.

    Raises
    ------
    SystemExit
        If no installer exists for the running platform, if a build step
        fails, or if argparse rejects the arguments.
    """
    config = parse_args_to_config(argv)
    set_log_level("info")

    installer = _platform_installer()

    try:
        installer(config)
    except (CommandError, RollbackError) as error:
        # run() has already reported the tail of the build log, so a
        # traceback into the command runner adds nothing actionable.
        sys.exit(str(error))
