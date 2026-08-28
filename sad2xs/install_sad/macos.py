"""
================================================================================
SAD Installation Script (macOS)
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
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..helpers import log_section_heading
from ._helpers import (
    InstallConfig,
    MissingDependency,
    install_sad_source,
    check_command,
    report_path_setup,
    strip_inherited_build_settings)
from ._helpers import require_dependencies as _require_dependencies
from .dispatch import require_platform

logger  = logging.getLogger(__name__)

# SAD is built against the platform toolchain, so the build sees only the
# macOS system directories and Homebrew.
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

# xcrun is the authority for paths inside the selected Xcode developer
# directory. Keeping the mapping here makes the audit and build environment
# resolve exactly the same toolchain.
XCODE_TOOLS = (
    ("CC",       "clang"),
    ("CXX",      "clang++"),
    ("AR",       "ar"),
    ("RANLIB",   "ranlib"),
    ("NM",       "nm"),
    ("STRIP",    "strip"),
    ("LD",       "ld"))


class XcodeToolchainError(RuntimeError):
    """Raised when the selected Xcode toolchain cannot be used."""

################################################################################
# Dependency Reporting
################################################################################
########################################
# Homebrew Prefix Lookup
########################################
def brew_prefix(formula: str | None = None) -> Path | None:
    """
    Look up a Homebrew prefix without changing the machine.

    A known formula reports a prefix whether or not it is installed, so a
    returned path is not proof that anything is there.

    Parameters
    ----------
    formula : str, optional
        If given, look up the prefix for this formula rather than for
        Homebrew itself. Defaults to None.

    Returns
    -------
    Path or None
        The prefix, or None when Homebrew reports none.
    """
    cmd = ["brew", "--prefix"]
    if formula is not None:
        cmd.append(formula)

    try:
        process = subprocess.run(       # pylint: disable=subprocess-run-check
            cmd,
            text    = True,
            stdout  = subprocess.PIPE,
            stderr  = subprocess.DEVNULL)
    except OSError:
        return None

    if process.returncode != 0:
        return None
    return Path(process.stdout.strip())


########################################
# Build PATH
########################################
def build_path(brew_root: Path | None) -> str:
    """
    Build the PATH the SAD build runs with.

    Parameters
    ----------
    brew_root : Path or None
        The Homebrew prefix, or None when Homebrew is absent.

    Returns
    -------
    str
        Homebrew ahead of the macOS system directories, and nothing else.
    """
    if brew_root is None:
        return SYSTEM_PATH
    return f"{brew_root}/bin:{brew_root}/sbin:{SYSTEM_PATH}"


########################################
# Xcode Command Line Tools
########################################
def resolve_xcode_toolchain() -> dict[str, str]:
    """
    Resolve the SDK and build tools from the selected Xcode installation.

    Returns
    -------
    dict
        SDKROOT and compiler-tool variables ready for the build environment.

    Raises
    ------
    XcodeToolchainError
        If xcrun cannot run, reports a failure, returns an empty path, or
        names a tool that is not executable.
    """
    commands = [("SDKROOT", ["xcrun", "--show-sdk-path"], False)]
    commands.extend(
        (variable, ["xcrun", "--find", tool], True)
        for variable, tool in XCODE_TOOLS)

    resolved = {}
    for variable, cmd, executable in commands:
        try:
            value = subprocess.check_output(
                cmd,
                text   = True,
                stderr = subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError) as error:
            raise XcodeToolchainError(
                f"{' '.join(cmd)} failed: {error}") from error

        if not value:
            raise XcodeToolchainError(
                f"{' '.join(cmd)} returned an empty path.")

        path = Path(value)
        if executable and not os.access(path, os.X_OK):
            raise XcodeToolchainError(
                f"{variable} resolved to a tool that is not executable: "
                f"{path}")
        if not executable and not path.exists():
            raise XcodeToolchainError(
                f"SDKROOT resolved to a path that does not exist: {path}")

        resolved[variable] = str(path)

    return resolved


def check_xcode_clt() -> MissingDependency | None:
    """
    Check that the selected Xcode Command Line Tools are usable.

    Returns
    -------
    MissingDependency or None
        A report when the tools are not configured.
    """
    report = MissingDependency(
        "Xcode Command Line Tools",
        "Needed for the clang toolchain, the macOS SDK, make, yacc, and git.",
        "Run xcode-select --install, or repair/select a working Xcode "
        "developer directory.")

    try:
        process = subprocess.run(       # pylint: disable=subprocess-run-check
            ["xcode-select", "-p"],
            stdout  = subprocess.DEVNULL,
            stderr  = subprocess.DEVNULL)
    except OSError:
        return report

    if process.returncode != 0:
        return report

    try:
        resolve_xcode_toolchain()
    except XcodeToolchainError:
        return report
    return None


########################################
# Formula Executable Check
########################################
def check_brew_bin(
        exe:        str,
        formula:    str,
        reason:     str) -> MissingDependency | None:
    """
    Check that a Homebrew formula provides a runnable executable.

    Existence alone is not enough: an interrupted install can leave a file
    behind that cannot be run.

    Parameters
    ----------
    exe : str
        Executable name under the formula `bin` directory.
    formula : str
        Homebrew formula that provides the executable.
    reason : str
        Why the SAD build needs the executable.

    Returns
    -------
    MissingDependency or None
        A report when the formula provides no runnable such executable.
    """
    prefix = brew_prefix(formula)
    if prefix is not None and os.access(prefix / "bin" / exe, os.X_OK):
        return None
    return MissingDependency(exe, reason, f"brew install {formula}")


########################################
# X11 Headers
########################################
def check_x11_headers() -> MissingDependency | None:
    """
    Check for the X11 headers XQuartz provides.

    Returns
    -------
    MissingDependency or None
        A report when the header is absent.
    """
    x11_header = Path("/opt/X11/include/X11/Xlib.h")
    if x11_header.exists():
        return None
    return MissingDependency(
        str(x11_header),
        "Needed to build SAD against X11.",
        "brew install --cask xquartz")


########################################
# Dependency Audit
########################################
def audit_dependencies() -> list[MissingDependency]:
    """
    Report every dependency the SAD installation needs but cannot find.

    Nothing here changes the machine. Every check is a read-only probe, so
    the whole set is reported at once rather than one rerun at a time.

    Returns
    -------
    list of MissingDependency
        Everything missing, in the order it is checked.
    """
    missing: list[MissingDependency] = []

    clt = check_xcode_clt()
    if clt is not None:
        missing.append(clt)

    ########################################
    # Clone Dependencies
    ########################################
    # The clone runs in the caller's environment, not the build's, so git is
    # probed the way the clone will actually find it.
    git = check_command(
        "git",
        "Needed to clone the SAD source.",
        "xcode-select --install")
    if git is not None:
        missing.append(git)

    ########################################
    # Build Dependencies
    ########################################
    # Probing the caller's PATH would accept a conda-only command that
    # vanishes once the build replaces PATH with this same value.
    brew_root = brew_prefix() if shutil.which("brew") is not None else None
    if brew_root is None:
        missing.append(MissingDependency(
            "brew",
            "Needed to provide gfortran, groff, and XQuartz.",
            "See https://brew.sh for the Homebrew installation command."))

    sanitised_path = build_path(brew_root)

    for cmd, reason, remedy in (
            ("make",
             "Needed to run SAD's build.",
             "xcode-select --install"),
            ("yacc",
             "Needed to generate SAD's parser from calc.y.",
             "xcode-select --install"),
            ("nroff",
             "Needed to format SAD's libtai man pages during the build.",
             "brew install groff")):
        found = check_command(cmd, reason, remedy, path = sanitised_path)
        if found is not None:
            missing.append(found)

    if brew_root is not None:
        gfortran = check_brew_bin(
            "gfortran",
            "gcc",
            "Needed to compile SAD's Fortran sources; Apple ships no Fortran compiler.")
        if gfortran is not None:
            missing.append(gfortran)

    ########################################
    # X11 Headers
    ########################################
    headers = check_x11_headers()
    if headers is not None:
        missing.append(headers)

    return missing


########################################
# Dependency Gate
########################################
def require_dependencies() -> None:
    """
    Report every missing dependency, and stop before touching SAD.

    Raises
    ------
    SystemExit
        If anything the SAD installation needs is missing.
    """
    logger.info("Checking for required dependencies")
    _require_dependencies(audit_dependencies())

################################################################################
# Build Environment
################################################################################
def make_clean_build_env() -> dict[str, str]:
    """
    Build an environment that compiles SAD with the Xcode toolchain.

    Returns
    -------
    dict
        Environment variables for the SAD build.

    Raises
    ------
    SystemExit
        If Homebrew or the selected Xcode toolchain cannot support the build.
    """
    env = strip_inherited_build_settings()

    ########################################
    # Point At The Xcode Toolchain
    ########################################
    brew_root = brew_prefix()
    if brew_root is None:
        sys.exit("Homebrew prefix could not be found.")

    env["PATH"] = build_path(brew_root)
    try:
        env.update(resolve_xcode_toolchain())
    except XcodeToolchainError as error:
        sys.exit(
            f"The selected Xcode Command Line Tools are unusable: {error}\n"
            f"Run xcode-select --install, or repair/select a working Xcode "
            f"developer directory, then rerun sad2xs-install-sad.")

    # Apple's toolchain ships no Fortran compiler, so SAD's Fortran sources
    # need Homebrew's gfortran.
    gcc_prefix = brew_prefix("gcc")
    if gcc_prefix is None:
        sys.exit("Homebrew formula gcc provided no prefix.")
    env["FC"]       = str(gcc_prefix / "bin" / "gfortran")

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

    log_section_heading("Checking Required Dependencies")
    require_dependencies()

    log_section_heading("Installing SAD")
    install_sad_source(config, make_clean_build_env())
    report_path_setup(config)

    log_section_heading("SAD Installation Summary")
    logger.info("SAD installed successfully!")
    logger.info("Run:        sad sad_file.sad")
    logger.info(f"Source:     {config.src_dir}")
    logger.info(f"Launcher:   {config.launcher}")
    logger.info("#" * 80 + "\n")
