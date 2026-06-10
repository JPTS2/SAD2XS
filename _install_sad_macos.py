"""
SAD Installation Script
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       02-01-2026
"""

################################################################################
# Required Packages
################################################################################
import os
import subprocess
from pathlib import Path
import shutil
import sys
from typing import Iterable, Optional

################################################################################
# User Parameters
################################################################################
SAD_GIT_REPO_URL    = "https://github.com/KatsOide/SAD.git"

HEADER              = "MacOS SAD Installation Script"
AUTHOR              = "J.P.T. Salvesen"
CONTACT_EMAIL       = "john.salvesen@cern.ch"
VERSION             = "0.2.0"
DATE                = "10/06/2026"

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
    --------------------------------
    cmd : list[str]
        Command that was run
    returncode : int
        Return code from the command
    log_path : Path, optional
        Path to log file (if any)
    --------------------------------
    """
    def __init__(
            self,
            cmd:        Iterable[str],
            returncode: int,
            log_path:   Optional[Path]  = None):
        self.cmd        = list(cmd)
        self.returncode = returncode
        self.log_path   = log_path

        msg = f"Command failed ({returncode}): {' '.join(self.cmd)}"
        if log_path:
            msg += f"\nLog: {log_path}"
        super().__init__(msg)

################################################################################
# Installation Functions
################################################################################

########################################
# Run shell commands
########################################
def _print_log_tail(log_path: Path, n: int = 120) -> None:
    """
    Print the last n lines of a log file (best-effort)
    --------------------------------
    log_path : Path
        Path to the log file
    n : int, default=120
        Number of lines to print from the end of the log
    --------------------------------
    """
    try:
        txt     = log_path.read_text(errors="replace")
        lines   = txt.splitlines()
        tail    = lines[-n:] if len(lines) > n else lines
        print("\n" + "#" * 80)
        print(f"Last {len(tail)} lines of log: {log_path}")
        print("#" * 80)
        for line in tail:
            print(line)
        print("#" * 80 + "\n")
    except FileNotFoundError:
        print(f"(log missing) {log_path}")
    except Exception as e:
        print(f"(could not read log) {log_path}: {e}")

########################################
# Run shell commands
########################################
def run(
        cmd,
        cwd             = None,
        env             = None,
        check           = True,
        log_path        = None,
        stdin_devnull   = False):
    """
    Run a shell command
    --------------------------------
    cmd : list[str]
        Command and arguments to run
    cwd : Path or str, optional
        Working directory to run the command in
    env : dict, optional
        Environment variables to use
    check : bool, default=True
        If True, raise CommandError on non-zero return code
    log_path : Path, optional
        If given, log stdout/stderr to this file
    stdin_devnull : bool, default=False
        If True, set stdin to /dev/null
    --------------------------------
    Returns:
    subprocess.CompletedProcess if log_path is None, else return code (int)
    --------------------------------
    """
    print(f"▶ Running: {' '.join(cmd)}")
    if cwd:
        print(f"  cwd: {cwd}")

    stdin = subprocess.DEVNULL if stdin_devnull else None

    if log_path is None:
        p = subprocess.run(             # pylint: disable=subprocess-run-check
            cmd,
            cwd     = str(cwd) if cwd else None,
            env     = env,
            stdin   = stdin)
        if check and p.returncode != 0:
            raise CommandError(cmd, p.returncode)

        return p

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(f"\n\n$ {' '.join(cmd)}\n")
        f.flush()

        proc = subprocess.Popen(
            cmd,
            cwd     = str(cwd) if cwd else None,
            env     = env,
            text    = True,
            stdout  = subprocess.PIPE,
            stderr  = subprocess.STDOUT,
            stdin   = stdin,
            bufsize = 1)
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            f.write(line)
        rc = proc.wait()

    if check and rc != 0:
        _print_log_tail(log_path, n = 120)
        raise CommandError(cmd, rc, log_path = log_path)
    return rc

########################################
# Clean Conda Build Environment
########################################
def make_clean_build_env() -> dict[str, str]:
    """
    Make a clean build environment for building SAD on MacOS
    Remove conda-related environment variables
    Force use of Xcode toolchain.
    """
    env = os.environ.copy()

    # Remove conda contamination + common build poisoning vars
    for k in [
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
        env.pop(k, None)

    brew_root = brew_prefix()

    # Use a deterministic PATH: Homebrew first, then system
    env["PATH"]     = f"{brew_root}/bin:{brew_root}/sbin:/usr/bin:/bin:/usr/sbin:/sbin"

    # Force Xcode/CLT toolchain
    env["SDKROOT"]  = subprocess.check_output(
        ["xcrun", "--show-sdk-path"], text = True).strip()
    env["CC"]       = subprocess.check_output(
        ["xcrun", "--find", "clang"], text = True).strip()
    env["CXX"]      = subprocess.check_output(
        ["xcrun", "--find", "clang++"], text = True).strip()
    env["AR"]       = subprocess.check_output(
        ["xcrun", "--find", "ar"], text = True).strip()
    env["RANLIB"]   = subprocess.check_output(
        ["xcrun", "--find", "ranlib"], text = True).strip()
    env["NM"]       = subprocess.check_output(
        ["xcrun", "--find", "nm"], text = True).strip()
    env["STRIP"]    = subprocess.check_output(
        ["xcrun", "--find", "strip"], text = True).strip()
    env["LD"]       = subprocess.check_output(
        ["xcrun", "--find", "ld"], text = True).strip()

    # Force Homebrew gfortran (change if you use MacPorts)
    gcc_prefix      = brew_prefix("gcc")
    env["FC"]       = str(Path(gcc_prefix) / "bin" / "gfortran")

    # Optional: prevent any ftp-like downloader + make downloads reliable
    env["FETCH"]    = "curl -L --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 300 -O"

    for k in ("CC", "CXX", "FC", "AR", "RANLIB", "NM", "LD", "STRIP"):
        p   = Path(env[k])
        if not p.exists():
            sys.exit(f"Tool not found: {k}={p}")

    return env

########################################
# Ensure Xcode Command Line Tools
########################################
def ensure_xcode_clt():
    """
    Ensure that Xcode Command Line Tools are installed
    --------------------------------
    """
    p   = subprocess.run(             # pylint: disable=subprocess-run-check
        ["xcode-select", "-p"],
        stdout  = subprocess.DEVNULL,
        stderr  = subprocess.DEVNULL)
    if p.returncode != 0:
        sys.exit(
            "Xcode Command Line Tools not configured. Run: xcode-select --install")

########################################
# Dependencies
########################################
def brew_install(
        pkg:    str,
        cask:   bool    = False):
    """
    Install a package using Homebrew
    --------------------------------
    pkg : str
        Name of the Homebrew package to install
    --------------------------------

    """
    print(f"Installing with Homebrew: {pkg}")
    cmd = ["brew", "install"]
    if cask:
        cmd.append("--cask")
    cmd.append(pkg)
    run(cmd)

def brew_prefix(formula: str | None = None) -> Path:
    """
    Return the Homebrew prefix.
    --------------------------------
    formula : str, optional
        If given, return the prefix for a formula.
    --------------------------------
    """
    cmd = ["brew", "--prefix"]
    if formula is not None:
        cmd.append(formula)

    p = subprocess.run(             # pylint: disable=subprocess-run-check
        cmd,
        text    = True,
        stdout  = subprocess.PIPE,
        stderr  = subprocess.DEVNULL)

    if p.returncode != 0:
        if formula is None:
            sys.exit("Homebrew prefix could not be found.")
        brew_install(formula)
        return brew_prefix(formula)

    return Path(p.stdout.strip())

def ensure_brew_bin_exists(
        exe:        str,
        formula:    str) -> Path:
    """
    Ensure that a given binary exists from Homebrew
    Install the package if not.
    --------------------------------
    exe : str
        Executable name under the formula `bin` directory.
    formula : str
        Name of the Homebrew package to install if missing
    --------------------------------
    """
    prefix  = brew_prefix(formula)
    p       = Path(prefix) / "bin" / exe
    if not p.exists():
        brew_install(formula)
        prefix  = brew_prefix(formula)
        p       = Path(prefix) / "bin" / exe
    if not p.exists():
        sys.exit(f"Homebrew formula {formula} did not provide expected executable: {p}")
    return p

def ensure_command_exists(
        cmd:        str,
        formula:    str):
    """
    Ensure that a command is available on PATH, installing a formula if missing.
    --------------------------------
    cmd : str
        Command to search for.
    formula : str
        Homebrew formula to install if the command is missing.
    --------------------------------
    """
    if shutil.which(cmd) is not None:
        return

    print(f"Missing: command {cmd}")
    print(f"Will install: {formula}")
    brew_install(formula)

    if shutil.which(cmd) is None:
        sys.exit(f"Command still not found after installing {formula}: {cmd}")

def check_x11_headers():
    """
    Check for X11 headers, install xquartz if missing
    --------------------------------
    """
    x11_header = Path("/opt/X11/include/X11/Xlib.h")
    if not x11_header.exists():
        print("Missing: X11 headers")
        print("Will install: xquartz")
        brew_install("xquartz", cask = True)

def install_dependencies():
    """
    Install required dependencies using Homebrew
    --------------------------------
    """
    print("Checking for required dependencies (brew-based)")
    # Ensure brew itself exists
    if shutil.which("brew") is None:
        sys.exit("Homebrew (brew) not found. Install it from brew.sh then rerun.")

    # These are used explicitly later
    ensure_command_exists("git", "git")
    ensure_command_exists("make", "make")
    ensure_command_exists("nroff", "groff")
    ensure_brew_bin_exists("gfortran", "gcc")

    # X11 headers
    check_x11_headers()

########################################
# Write global launcher script
########################################
def write_launcher():
    """
    Write a global SAD launcher script to ~/bin/sad/sad
    --------------------------------
    1) If called with a file argument, runs in batch mode from the user's cwd
    2) If called without arguments, runs interactively from the SAD source dir
    --------------------------------
    """
    print(f"Writing launcher script: {LAUNCHER_SCRIPT}")
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
def append_to_shell_rc():
    """
    Append SAD bin directory to user's shell rc file
    --------------------------------
    """
    shell   = os.environ.get("SHELL", "")
    rc_file = None
    if "zsh" in shell:
        rc_file = Path.home() / ".zshrc"
    elif "bash" in shell:
        rc_file = Path.home() / ".bashrc"

    export_line = 'export PATH="$HOME/bin/sad:$PATH"\n'

    if rc_file and rc_file.exists():
        with rc_file.open("r") as f:
            lines   = f.readlines()
        if any("bin/sad:$PATH" in line for line in lines):
            print(f"PATH already present in {rc_file}")
        else:
            print(f"Adding SAD to PATH in {rc_file}")
            with rc_file.open("a") as f:
                f.write("\n# Added by SAD installer\n")
                f.write(export_line)
            print(f"N.B. Must run: source {rc_file}")
    elif rc_file:
        print(f"Warning: {rc_file} not found")
        print("Creating RC File and adding PATH to SAD")
        with rc_file.open("w") as f:
            f.write("# Created by SAD installer\n")
            f.write(export_line)
        print(f"N.B. Must run: source {rc_file}")
    else:
        print("Warning: Unknown shell")
        print("Please manually add the following line to your shell config:")
        print(export_line.strip())

################################################################################
# Main Installation Process
################################################################################
def main():
    """
    Main SAD installation process
    --------------------------------
    1) Install dependencies
    2) Clean previous installation
    3) Create install directory
    4) Clone SAD repository
    5) Build SAD
    6) Write global launcher
    7) Append to shell rc file
    --------------------------------
    """

    ########################################
    # Header
    ########################################
    print("#" * 80)
    print(f"{HEADER}")
    print("#" * 80)
    print(f"Author:     {AUTHOR}")
    print(f"Contact:    {CONTACT_EMAIL}")
    print(f"Version:    {VERSION}")
    print(f"Date:       {DATE}")
    print("#" * 80 + "\n")

    ########################################
    # Install Dependencies
    ########################################
    print("#" * 40 + "\n" + "Installing Required Dependencies" + "\n" + "#" * 40)
    ensure_xcode_clt()
    install_dependencies()

    ########################################
    # Clean Previous Installation
    ########################################
    if INSTALL_ROOT.exists():
        print("#" * 40 + "\n" + "Cleaning Previous Installation" + "\n" + "#" * 40)
        print(f"Previous installation found at {INSTALL_ROOT}")
        shutil.rmtree(INSTALL_ROOT)
        print(f"Removed {INSTALL_ROOT}")

    ########################################
    # Create Install Directory
    ########################################
    print("#" * 40 + "\n" + "Creating Install Directory" + "\n" + "#" * 40)
    SRC_DIR.mkdir(parents = True)
    print(f"Install directory created at {INSTALL_ROOT}")

    ########################################
    # Create Logging
    ########################################
    print("#" * 40 + "\n" + "Creating Logging" + "\n" + "#" * 40)
    LOG_DIR = INSTALL_ROOT / "logs"
    LOG_DIR.mkdir(parents = True, exist_ok = True)

    build_log = LOG_DIR / "build.log"
    # Start fresh each run (optional)
    build_log.write_text("")
    print(f"Build log: {build_log}")

    ########################################
    # Clone SAD Repository
    ########################################
    print("#" * 40 + "\n" + "Cloning SAD Repository" + "\n" + "#" * 40)
    run(
        ["git", "clone", SAD_GIT_REPO_URL, str(SRC_DIR)],
        log_path        = build_log,
        stdin_devnull   = True)

    ########################################
    # Build SAD
    ########################################
    print("#" * 40 + "\n" + "Building SAD" + "\n" + "#" * 40)

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

    print("SAD build complete")

    # Test SAD Installation
    if not SAD_EXECUTABLE.exists():
        sys.exit(f"SAD binary not found: {SAD_EXECUTABLE}")
    else:
        print("SAD Binary found")

    ########################################
    # Write global launcher
    ########################################
    print("#" * 40 + "\n" + "Writing global launcher" + "\n" + "#" * 40)
    write_launcher()
    print(f"Launcher script written to: {LAUNCHER_SCRIPT}")

    append_to_shell_rc()
    print("Added SAD to PATH in shell configuration file")

    ########################################
    # Summary Message
    ########################################
    print("#" * 40 + "\n" + "SAD Installation Summary" + "\n" + "#" * 40)
    print("SAD installed successfully!")
    print("Run:        sad sad_file.sad")
    print(f"Source:     {SRC_DIR}")
    print(f"Launcher:   {LAUNCHER_SCRIPT}")

    ########################################
    # Footer
    ########################################
    print("#" * 80 + "\n")

################################################################################
# Run the installer
################################################################################
if __name__ == "__main__":
    main()
