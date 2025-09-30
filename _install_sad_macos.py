"""
SAD Installation Script
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       30-07-2025
"""

################################################################################
# Required Packages
################################################################################
import os
import subprocess
from pathlib import Path
import shutil
import sys

################################################################################
# User Parameters
################################################################################
SAD_GIT_REPO_URL    = "https://github.com/KatsOide/SAD.git"

HEADER              = "MacOS SAD Installation Script"
AUTHOR              = "JPT Salvesen"
CONTACT_EMAIL       = "john.salvesen@cern.ch"
VERSION             = "0.1.0"
DATE                = "30/07/2025"

################################################################################
# Setup
################################################################################
HOME_DIR            = Path.home()
INSTALL_ROOT        = HOME_DIR / "bin" / "sad"
SRC_DIR             = INSTALL_ROOT / "src"
SAD_EXECUTABLE      = SRC_DIR / "bin" / "gs"
LAUNCHER_SCRIPT     = INSTALL_ROOT / "sad"

BREW_PACKAGES       = {
    "git":          "git",
    "make":         "make",
    "gfortran":     "gcc",      # gfortran is part of gcc
    "nroff":        "groff",    # for manpage generation
    "X11/Xlib.h":   "xquartz"}  # for X11 headers

################################################################################
# Installation Functions
################################################################################

########################################
# Run shell commands
########################################
def run(cmd, cwd = None, check = True):
    print(f"▶ Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd = cwd)
    if check and result.returncode != 0:
        sys.exit(f"Command failed: {' '.join(cmd)}")

########################################
# Install with Homebrew
########################################
def brew_install(pkg):
    print(f"Installing with Homebrew: {pkg}")
    run(["brew", "install", pkg])

########################################
# Check for required dependencies
########################################
def check_dependency(cmd, brew_pkg):
    if shutil.which(cmd) is None:   
        print(f"Missing: command {cmd}")
        print(f"Will install: {brew_pkg}")
        brew_install(brew_pkg)

def check_x11_headers():
    x11_header = Path("/opt/X11/include/X11/Xlib.h")
    if not x11_header.exists():
        print("Missing: X11 headers")
        print("Will install: xquartz")
        brew_install("xquartz")

########################################
# Install required dependencies
########################################
def install_dependencies():
    print("Checking for required dependencies")
    for check_cmd, brew_pkg in BREW_PACKAGES.items():
        if check_cmd == "X11/Xlib.h":
            check_x11_headers()
        else:
            check_dependency(check_cmd, brew_pkg)

########################################
# Write global launcher script
########################################
def write_launcher():
    print(f"Writing launcher script: {LAUNCHER_SCRIPT}")
    LAUNCHER_SCRIPT.write_text(f"""#!/bin/bash
SAD_DIR="{SRC_DIR}"
GS_EXEC="$SAD_DIR/bin/gs"
CALL_DIR="$(pwd)"

# If called with a file: run from the user's working directory (batch mode)
if [[ $# -gt 0 ]]; then
    SAD_INPUT="$(realpath "$CALL_DIR/$1")"
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
    # Clone SAD Repository
    ########################################
    print("#" * 40 + "\n" + "Cloning SAD Repository" + "\n" + "#" * 40)
    run(["git", "clone", SAD_GIT_REPO_URL, str(SRC_DIR)])

    ########################################
    # Patching SAD Configuration
    ########################################
    print("#" * 40 + "\n" + "Patching SAD config for local installation" + "\n" + "#" * 40)
    print("For local installation, using only the first 70 lines of sad.conf")
    # Original Makefile.unx and sad.conf files designed for legacy Unix
    # KEK's installation instructions say:
    #   "Use only the first 70 lines of sad.conf for building SAD locally."

    sad_conf        = SRC_DIR / "sad.conf"
    patched_conf    = SRC_DIR / "sad.conf.new"
    with sad_conf.open() as f_in, patched_conf.open("w") as f_out:
        for i, line in enumerate(f_in):
            if i < 70:
                f_out.write(line)
            else:
                break
    sad_conf.unlink()
    patched_conf.rename(sad_conf)

    ########################################
    # Build SAD
    ########################################
    print("#" * 40 + "\n" + "Building SAD" + "\n" + "#" * 40)
    run(["make", "depend"], cwd = SRC_DIR)
    run(["make", "-s", "exe"], cwd = SRC_DIR)
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
    print(f"Run:        sad sad_file.sad")
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
