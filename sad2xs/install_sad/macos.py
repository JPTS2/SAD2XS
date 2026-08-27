"""
================================================================================
SAD Installation Script (macOS)
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-08-28
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..helpers import log_section_heading
from ._helpers import (
    InstallConfig,
    clone_sad,
    report_path_setup,
    make_sad,
    run,
    verify_executable,
    write_launcher)
from .dispatch import require_platform

logger  = logging.getLogger(__name__)

################################################################################
# Xcode Command Line Tools
################################################################################
def ensure_xcode_clt() -> None:
    """
    Ensure that the Xcode Command Line Tools are installed.

    Raises
    ------
    SystemExit
        If the Command Line Tools are not configured.
    """
    process = subprocess.run(           # pylint: disable=subprocess-run-check
        ["xcode-select", "-p"],
        stdout  = subprocess.DEVNULL,
        stderr  = subprocess.DEVNULL)
    if process.returncode != 0:
        sys.exit(
            "Xcode Command Line Tools not configured. Run: xcode-select --install")

################################################################################
# Homebrew
################################################################################
########################################
# Brew Install
########################################
def brew_install(
        pkg:    str,
        cask:   bool    = False) -> None:
    """
    Install a package using Homebrew.

    Parameters
    ----------
    pkg : str
        Name of the Homebrew package to install.
    cask : bool, optional
        If True, install as a cask rather than a formula. Defaults to False.
    """
    logger.info(f"Installing with Homebrew: {pkg}")
    cmd = ["brew", "install"]
    if cask:
        cmd.append("--cask")
    cmd.append(pkg)
    run(cmd)


########################################
# Brew Prefix Lookup
########################################
def brew_prefix(formula: str | None = None) -> Path:
    """
    Return the Homebrew prefix, installing a missing formula once.

    Parameters
    ----------
    formula : str, optional
        If given, return the prefix for this formula rather than for
        Homebrew itself. Defaults to None.

    Returns
    -------
    Path
        The Homebrew prefix.

    Raises
    ------
    SystemExit
        If the prefix cannot be found, or the formula still provides no
        prefix after being installed.
    """
    cmd = ["brew", "--prefix"]
    if formula is not None:
        cmd.append(formula)

    # Bounded at one install: a formula that reports success but still has no
    # prefix would otherwise retry forever.
    for attempt in range(2):
        process = subprocess.run(       # pylint: disable=subprocess-run-check
            cmd,
            text    = True,
            stdout  = subprocess.PIPE,
            stderr  = subprocess.DEVNULL)

        if process.returncode == 0:
            return Path(process.stdout.strip())
        if formula is None:
            sys.exit("Homebrew prefix could not be found.")
        if attempt == 0:
            brew_install(formula)

    sys.exit(f"Homebrew formula {formula} provided no prefix after installation.")


########################################
# Formula Executable Check
########################################
def ensure_brew_bin_exists(
        exe:        str,
        formula:    str) -> Path:
    """
    Ensure that a Homebrew formula provides a given executable.

    Parameters
    ----------
    exe : str
        Executable name under the formula `bin` directory.
    formula : str
        Name of the Homebrew package to install if the executable is missing.

    Returns
    -------
    Path
        Path to the executable.

    Raises
    ------
    SystemExit
        If the formula does not provide the executable once installed.
    """
    exe_path = brew_prefix(formula) / "bin" / exe
    if not exe_path.exists():
        brew_install(formula)
        exe_path = brew_prefix(formula) / "bin" / exe
    if not exe_path.exists():
        sys.exit(
            f"Homebrew formula {formula} did not provide expected executable: "
            f"{exe_path}")
    return exe_path


########################################
# PATH Command Check
########################################
def ensure_command_exists(
        cmd:        str,
        formula:    str) -> None:
    """
    Ensure that a command is available on PATH, installing a formula if missing.

    Parameters
    ----------
    cmd : str
        Command to search for.
    formula : str
        Homebrew formula to install if the command is missing.

    Raises
    ------
    SystemExit
        If the command is still missing once the formula is installed.
    """
    if shutil.which(cmd) is not None:
        return

    logger.info(f"Missing: command {cmd}")
    logger.info(f"Will install: {formula}")
    brew_install(formula)

    if shutil.which(cmd) is None:
        sys.exit(f"Command still not found after installing {formula}: {cmd}")


########################################
# X11 Headers
########################################
def check_x11_headers() -> None:
    """
    Check for X11 headers, installing XQuartz if they are missing.

    Raises
    ------
    SystemExit
        If the header is still absent after installing XQuartz. The cask
        reports success without placing the headers when XQuartz needs a
        login to finish setting up.
    """
    x11_header = Path("/opt/X11/include/X11/Xlib.h")
    if x11_header.exists():
        return

    logger.info("Missing: X11 headers")
    logger.info("Will install: xquartz")
    brew_install("xquartz", cask = True)

    if not x11_header.exists():
        sys.exit(
            f"X11 headers still missing after installing xquartz: "
            f"{x11_header}. Log out and back in, then rerun.")


########################################
# Dependency Installation
########################################
def install_dependencies() -> None:
    """
    Install the dependencies the SAD build needs, using Homebrew.

    Raises
    ------
    SystemExit
        If Homebrew itself is not installed.
    """
    logger.info("Checking for required dependencies (brew-based)")
    if shutil.which("brew") is None:
        sys.exit("Homebrew (brew) not found. Install it from brew.sh then rerun.")

    ensure_command_exists("git", "git")
    ensure_command_exists("make", "make")
    ensure_command_exists("nroff", "groff")
    ensure_command_exists("bison", "bison")
    ensure_brew_bin_exists("gfortran", "gcc")

    check_x11_headers()

################################################################################
# Build Environment
################################################################################
def make_clean_build_env() -> dict[str, str]:
    """
    Build an environment that compiles SAD with the Xcode toolchain.

    A conda environment exports compiler and linker variables that point at
    its own toolchain. SAD picks those up and fails to link against the
    system frameworks, so they are stripped rather than overridden.

    Returns
    -------
    dict
        Environment variables for the SAD build.

    Raises
    ------
    SystemExit
        If any resolved toolchain executable does not exist.
    """
    env = os.environ.copy()

    ########################################
    # Strip Inherited Toolchain Settings
    ########################################
    for variable in [
            "CFLAGS", "CXXFLAGS", "FFLAGS", "FCFLAGS",
            "CPPFLAGS", "LDFLAGS", "LDFLAGS_LD",
            "PKG_CONFIG_PATH", "CONDA_BUILD_SYSROOT", "LD_LIBRARY_PATH",
            "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH",
            "DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH",
            "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "CONDA_SHLVL",
            "CONDA_TOOLCHAIN_HOST", "CONDA_TOOLCHAIN_BUILD",
            "_CONDA_PYTHON_SYSCONFIGDATA_NAME",
            "CC", "CXX", "FC", "F77", "F90",
            "AR", "AS", "LD", "NM", "RANLIB", "STRIP",
            "CMAKE_ARGS", "CMAKE_PREFIX_PATH",
            "CONDA_BUILD", "PREFIX", "BUILD_PREFIX",
            "HOST", "BUILD", "TARGET"]:
        env.pop(variable, None)

    ########################################
    # Point At The Xcode Toolchain
    ########################################
    brew_root = brew_prefix()

    env["PATH"]     = f"{brew_root}/bin:{brew_root}/sbin:/usr/bin:/bin:/usr/sbin:/sbin"
    env["SDKROOT"]  = subprocess.check_output(
        ["xcrun", "--show-sdk-path"], text = True).strip()

    for variable, tool in (
            ("CC",       "clang"),
            ("CXX",      "clang++"),
            ("AR",       "ar"),
            ("RANLIB",   "ranlib"),
            ("NM",       "nm"),
            ("STRIP",    "strip"),
            ("LD",       "ld")):
        env[variable] = subprocess.check_output(
            ["xcrun", "--find", tool], text = True).strip()

    # Apple's toolchain ships no Fortran compiler, so SAD's Fortran sources
    # need Homebrew's gfortran.
    env["FC"]       = str(brew_prefix("gcc") / "bin" / "gfortran")

    # macOS ships no ftp(1), which SAD's makefile would otherwise reach for.
    env["FETCH"]    = "curl -L --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 300 -O"

    ########################################
    # Confirm Every Tool Resolves
    ########################################
    for variable in ("CC", "CXX", "FC", "AR", "RANLIB", "NM", "LD", "STRIP"):
        tool_path = Path(env[variable])
        if not tool_path.exists():
            sys.exit(f"Tool not found: {variable}={tool_path}")

    return env

################################################################################
# Main Installation Process
################################################################################
def install_sad_macos(config: InstallConfig) -> None:
    """
    Build SAD from source on macOS.

    Parameters
    ----------
    config : InstallConfig
        Where to build and install, and which source to use.

    Raises
    ------
    SystemExit
        If the running platform is not macOS, or a required tool or the
        built SAD binary is missing.
    CommandError
        If the clone or a build step returns non-zero.
    """
    # Without this, the failure elsewhere is an unexplained "brew not found"
    # or a FileNotFoundError from xcrun, which has no Linux equivalent.
    require_platform("darwin", "macOS")

    log_section_heading("macOS SAD Installation", mode = "banner")

    log_section_heading("Installing Required Dependencies")
    ensure_xcode_clt()
    install_dependencies()

    log_section_heading("Fetching SAD Source")
    reused_tree = clone_sad(config)

    log_section_heading("Building SAD")
    make_sad(config, make_clean_build_env(), reused_tree)
    verify_executable(config)

    log_section_heading("Installing Launcher")
    write_launcher(config)
    report_path_setup(config)

    log_section_heading("SAD Installation Summary")
    logger.info("SAD installed successfully!")
    logger.info("Run:        sad sad_file.sad")
    logger.info(f"Source:     {config.src_dir}")
    logger.info(f"Launcher:   {config.launcher}")
    logger.info("#" * 80 + "\n")
