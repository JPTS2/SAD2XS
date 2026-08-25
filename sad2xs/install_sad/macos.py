"""
================================================================================
SAD Installation Script (macOS)
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
import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from ..helpers import log_section_heading
from .dispatch import require_platform

logger  = logging.getLogger(__name__)

################################################################################
# User Parameters
################################################################################
SAD_GIT_REPO_URL    = "https://github.com/KatsOide/SAD.git"

HEADER              = "macOS SAD Installation Script"

################################################################################
# Setup
################################################################################
HOME_DIR            = Path.home()
INSTALL_ROOT        = HOME_DIR / "bin" / "sad"
SRC_DIR             = INSTALL_ROOT / "src"
SAD_EXECUTABLE      = SRC_DIR / "bin" / "gs"
LAUNCHER_SCRIPT     = INSTALL_ROOT / "sad"

################################################################################
# Command Error class
################################################################################
class CommandError(RuntimeError):
    """
    Raised when a subprocess returns non-zero.

    Parameters
    ----------
    cmd : Iterable[str]
        Command that was run.
    returncode : int
        Return code from the command.
    log_path : Path, optional
        Path to the log file the command wrote to. Defaults to None.
    """
    def __init__(
            self,
            cmd:        Iterable[str],
            returncode: int,
            log_path:   Path | None = None) -> None:
        """
        Record the failed command, its exit status, and any log file.
        """
        self.cmd        = list(cmd)
        self.returncode = returncode
        self.log_path   = log_path

        msg = f"""Command failed ({returncode}): {" ".join(self.cmd)}"""
        if log_path:
            msg += f"\nLog: {log_path}"
        super().__init__(msg)

################################################################################
# Installation Functions
################################################################################

########################################
# Log Tail Reporting
########################################
def _log_tail(log_path: Path, n_lines: int = 120) -> None:
    """
    Log the last lines of a build log, best-effort.

    Called on build failure, where the cause is usually near the end of a
    log far too long to show whole.

    Parameters
    ----------
    log_path : Path
        Path to the log file.
    n_lines : int, optional
        Number of lines to show from the end of the log. Defaults to 120.
    """
    try:
        lines   = log_path.read_text(errors = "replace").splitlines()
    except OSError as error:
        logger.info(f"(could not read log) {log_path}: {error}")
        return

    tail    = lines[-n_lines:]
    logger.info("\n" + "#" * 80)
    logger.info(f"Last {len(tail)} lines of log: {log_path}")
    logger.info("#" * 80)
    for line in tail:
        logger.info(line)
    logger.info("#" * 80 + "\n")

########################################
# Run Shell Commands
########################################
def run(
        cmd:            list[str],
        cwd:            Path | str | None       = None,
        env:            dict[str, str] | None   = None,
        check:          bool                    = True,
        log_path:       Path | None             = None,
        stdin_devnull:  bool                    = False) -> subprocess.CompletedProcess | int:
    """
    Run a shell command.

    Parameters
    ----------
    cmd : list[str]
        Command and arguments to run.
    cwd : Path or str, optional
        Working directory to run the command in. Defaults to None.
    env : dict, optional
        Environment variables to use. Defaults to None.
    check : bool, optional
        If True, raise CommandError on a non-zero return code. Defaults to
        True.
    log_path : Path, optional
        If given, tee stdout/stderr to this file. Defaults to None.
    stdin_devnull : bool, optional
        If True, set stdin to /dev/null. Defaults to False.

    Returns
    -------
    subprocess.CompletedProcess or int
        The completed process, or the return code when `log_path` is given.

    Raises
    ------
    CommandError
        If `check` is True and the command returns non-zero.
    """
    logger.info(f"""▶ Running: {" ".join(cmd)}""")
    if cwd:
        logger.info(f"  cwd: {cwd}")

    stdin = subprocess.DEVNULL if stdin_devnull else None

    if log_path is None:
        process = subprocess.run(       # pylint: disable=subprocess-run-check
            cmd,
            cwd     = str(cwd) if cwd else None,
            env     = env,
            stdin   = stdin)
        if check and process.returncode != 0:
            raise CommandError(cmd, process.returncode)

        return process

    log_path.parent.mkdir(parents = True, exist_ok = True)
    with log_path.open("a") as log_file:
        log_file.write(f"""\n\n$ {" ".join(cmd)}\n""")
        log_file.flush()

        process = subprocess.Popen(     # pylint: disable=consider-using-with
            cmd,
            cwd     = str(cwd) if cwd else None,
            env     = env,
            text    = True,
            stdout  = subprocess.PIPE,
            stderr  = subprocess.STDOUT,
            stdin   = stdin,
            bufsize = 1)

        # The build's own output, passed through verbatim rather than logged:
        # it is another program's stdout, and flushing each line keeps it in
        # order with the logger's stderr when either is redirected.
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            log_file.write(line)
        returncode = process.wait()

    if check and returncode != 0:
        _log_tail(log_path)
        raise CommandError(cmd, returncode, log_path = log_path)
    return returncode

########################################
# Clean Conda Build Environment
########################################
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

    for variable in [
            "CPPFLAGS", "LDFLAGS", "LDFLAGS_LD",
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

    for variable in ("CC", "CXX", "FC", "AR", "RANLIB", "NM", "LD", "STRIP"):
        tool_path = Path(env[variable])
        if not tool_path.exists():
            sys.exit(f"Tool not found: {variable}={tool_path}")

    return env

########################################
# Ensure Xcode Command Line Tools
########################################
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

########################################
# Dependencies
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


def check_x11_headers() -> None:
    """
    Check for X11 headers, installing XQuartz if they are missing.
    """
    x11_header = Path("/opt/X11/include/X11/Xlib.h")
    if not x11_header.exists():
        logger.info("Missing: X11 headers")
        logger.info("Will install: xquartz")
        brew_install("xquartz", cask = True)


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
    ensure_brew_bin_exists("gfortran", "gcc")

    check_x11_headers()

########################################
# Write global launcher script
########################################
def write_launcher() -> None:
    """
    Write a global SAD launcher script to ~/bin/sad/sad.

    Notes
    -----
    1) If called with a file argument, runs in batch mode from the user's cwd
    2) If called without arguments, runs interactively from the SAD source dir
    """
    logger.info(f"Writing launcher script: {LAUNCHER_SCRIPT}")
    LAUNCHER_SCRIPT.write_text(f"""#!/bin/bash
SAD_DIR="{SRC_DIR}"
GS_EXEC="$SAD_DIR/bin/gs"
CALL_DIR="$(pwd)"

# If called with a file: run from the user's working directory (batch mode)
if [[ $# -gt 0 ]]; then
    SAD_INPUT="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$CALL_DIR/$1")"

    shift
    cd "$CALL_DIR" || exit 1
    exec "$GS_EXEC" "$SAD_INPUT" "$@"
else
    # No file: launch from SAD source dir (interactive mode)
    cd "$SAD_DIR" || exit 1
    exec "$GS_EXEC"
fi
""")
    LAUNCHER_SCRIPT.chmod(0o755)

########################################
# Append launcher to shell rc
########################################
def append_to_shell_rc() -> None:
    """
    Add the SAD bin directory to the user's shell rc file.
    """
    shell   = os.environ.get("SHELL", "")
    rc_file = None
    if "zsh" in shell:
        rc_file = Path.home() / ".zshrc"
    elif "bash" in shell:
        rc_file = Path.home() / ".bashrc"

    export_line = """export PATH="$HOME/bin/sad:$PATH"\n"""

    if rc_file and rc_file.exists():
        if any("bin/sad:$PATH" in line for line in rc_file.read_text().splitlines()):
            logger.info(f"PATH already present in {rc_file}")
        else:
            logger.info(f"Adding SAD to PATH in {rc_file}")
            with rc_file.open("a") as handle:
                handle.write("\n# Added by SAD installer\n")
                handle.write(export_line)
            logger.info(f"N.B. Must run: source {rc_file}")
    elif rc_file:
        logger.warning(f"{rc_file} not found")
        logger.info("Creating RC File and adding PATH to SAD")
        rc_file.write_text("# Created by SAD installer\n" + export_line)
        logger.info(f"N.B. Must run: source {rc_file}")
    else:
        logger.warning("Unknown shell")
        logger.info("Please manually add the following line to your shell config:")
        logger.info(export_line.strip())

################################################################################
# Main Installation Process
################################################################################
def install_sad_macos() -> None:
    """
    Build SAD from source on macOS.

    Notes
    -----
    1) Install dependencies
    2) Clean previous installation
    3) Create install directory
    4) Clone SAD repository
    5) Build SAD
    6) Write global launcher
    7) Append to shell rc file

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

    log_section_heading(HEADER, mode = "banner")

    log_section_heading("Installing Required Dependencies")
    ensure_xcode_clt()
    install_dependencies()

    if INSTALL_ROOT.exists():
        log_section_heading("Cleaning Previous Installation")
        logger.info(f"Previous installation found at {INSTALL_ROOT}")
        shutil.rmtree(INSTALL_ROOT)
        logger.info(f"Removed {INSTALL_ROOT}")

    log_section_heading("Creating Install Directory")
    SRC_DIR.mkdir(parents = True)
    logger.info(f"Install directory created at {INSTALL_ROOT}")

    log_section_heading("Creating Logging")
    log_dir = INSTALL_ROOT / "logs"
    log_dir.mkdir(parents = True, exist_ok = True)

    # Truncated so a failure tail cannot be read from an earlier run.
    build_log = log_dir / "build.log"
    build_log.write_text("")
    logger.info(f"Build log: {build_log}")

    log_section_heading("Cloning SAD Repository")
    run(
        ["git", "clone", SAD_GIT_REPO_URL, str(SRC_DIR)],
        log_path        = build_log,
        stdin_devnull   = True)

    log_section_heading("Building SAD")
    build_env = make_clean_build_env()

    run(
        ["make", "clean"],
        cwd             = SRC_DIR,
        env             = build_env,
        log_path        = build_log,
        stdin_devnull   = True,
        check           = False)
    run(
        ["make", "depend"],
        cwd             = SRC_DIR,
        env             = build_env,
        log_path        = build_log,
        stdin_devnull   = True)
    run(
        ["make", "exe"],
        cwd             = SRC_DIR,
        env             = build_env,
        log_path        = build_log,
        stdin_devnull   = True)

    logger.info("SAD build complete")

    if not SAD_EXECUTABLE.exists():
        sys.exit(f"SAD binary not found: {SAD_EXECUTABLE}")
    logger.info("SAD Binary found")

    log_section_heading("Writing global launcher")
    write_launcher()
    logger.info(f"Launcher script written to: {LAUNCHER_SCRIPT}")

    append_to_shell_rc()

    log_section_heading("SAD Installation Summary")
    logger.info("SAD installed successfully!")
    logger.info("Run:        sad sad_file.sad")
    logger.info(f"Source:     {SRC_DIR}")
    logger.info(f"Launcher:   {LAUNCHER_SCRIPT}")
    logger.info("#" * 80 + "\n")
