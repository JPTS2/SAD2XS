"""
================================================================================
SAD Installation Script (Linux)
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
import glob
import logging
import os
import shutil
import sys
from pathlib import Path

from ..helpers import log_section_heading
from ._helpers import (
    InstallConfig,
    MissingDependency,
    check_command,
    clone_sad,
    report_path_setup,
    make_sad,
    strip_inherited_build_settings,
    verify_executable,
    write_launcher)
from ._helpers import require_dependencies as _require_dependencies
from .dispatch import require_platform

logger  = logging.getLogger(__name__)

# SAD is built against the system toolchain, so the build sees only the
# distribution's own directories.
SYSTEM_PATH = "/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin"

# KEK's installation instructions say to use only the first 70 lines of
# sad.conf when building locally. The rest targets legacy Unix systems.
SAD_CONF_LINES = 70

################################################################################
# Distribution Detection
################################################################################
########################################
# Package Families
########################################
# Only ever used to name packages in a printed suggestion. Nothing here
# decides what the installer does, and nothing here is executed.
PACKAGE_NAMES = {
    "debian": {
        "gcc":          "build-essential",
        "g++":          "build-essential",
        "gfortran":     "gfortran",
        "pkg-config":   "pkg-config",
        "nroff":        "groff",
        "yacc":         "bison",
        "x11":          "libx11-dev"},
    "rhel": {
        "gcc":          "gcc",
        "g++":          "gcc-c++",
        "gfortran":     "gcc-gfortran",
        "pkg-config":   "pkgconf-pkg-config",
        "nroff":        "groff-base",
        # Debian's bison provides yacc; the RHEL family's does not, and
        # ships only /usr/bin/bison. byacc is what supplies yacc there.
        "yacc":         "byacc",
        "x11":          "libX11-devel"}}

# Named so the report can say which distribution the package names are for.
FAMILY_NAMES = {
    "debian":   "Debian/Ubuntu",
    "rhel":     "RHEL family"}


########################################
# Distribution Family
########################################
def distro_family(os_release: Path = Path("/etc/os-release")) -> str | None:
    """
    Identify the packaging family of the running distribution.

    Parameters
    ----------
    os_release : Path, optional
        The file to read. Defaults to `/etc/os-release`.

    Returns
    -------
    str or None
        "debian", "rhel", or None when the family is not recognised.
    """
    try:
        text = os_release.read_text(encoding = "utf-8", errors = "replace")
    except OSError:
        return None

    identifiers: list[str] = []
    for line in text.splitlines():
        key, _, value = line.partition("=")
        if key.strip() in ("ID", "ID_LIKE"):
            identifiers.extend(value.strip().strip('"\'').split())

    for identifier in identifiers:
        if identifier in ("debian", "ubuntu"):
            return "debian"
        if identifier in ("rhel", "fedora", "centos", "almalinux", "rocky"):
            return "rhel"
    return None


########################################
# Package Suggestion
########################################
def package_suggestion(
        logical:    str,
        family:     str | None) -> str:
    """
    Describe how to provide a dependency.

    Parameters
    ----------
    logical : str
        Dependency name used by `PACKAGE_NAMES`.
    family : str or None
        Packaging family, as `distro_family` returns.

    Returns
    -------
    str
        The package to install, named for the detected distribution, or a
        plain instruction when its package names are unknown.

    Notes
    -----
    No command is printed. Installing a system package needs privileges
    SAD2XS never asks for, so naming the package leaves how it is installed
    to the user and their administrator.
    """
    if family is None:
        return f"your distribution's package providing {logical}"

    package = PACKAGE_NAMES[family].get(logical, logical)
    return f"the {FAMILY_NAMES[family]} package {package}"

################################################################################
# Dependency Reporting
################################################################################
########################################
# Build PATH
########################################
def build_path() -> str:
    """
    Build the PATH the SAD build runs with.

    Returns
    -------
    str
        The distribution's own directories, and nothing else.
    """
    return SYSTEM_PATH


########################################
# X11 Headers
########################################
def check_x11_headers(family: str | None) -> MissingDependency | None:
    """
    Check for the X11 headers SAD links against.

    Parameters
    ----------
    family : str or None
        Packaging family, as `distro_family` returns.

    Returns
    -------
    MissingDependency or None
        A report when the header is absent.

    Notes
    -----
    Multiarch distributions place the header under a triplet directory, so
    both locations count.
    """
    if Path("/usr/include/X11/Xlib.h").exists():
        return None
    if glob.glob("/usr/include/*/X11/Xlib.h"):
        return None

    return MissingDependency(
        "X11/Xlib.h",
        "Needed to build SAD against X11.",
        package_suggestion("x11", family))


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
    family  = distro_family()
    missing = []

    ########################################
    # Clone Dependencies
    ########################################
    # The clone runs in the caller's environment, not the build's, so git is
    # probed the way the clone will actually find it.
    git = check_command(
        "git",
        "Needed to clone the SAD source.",
        package_suggestion("git", family))
    if git is not None:
        missing.append(git)

    ########################################
    # Build Dependencies
    ########################################
    # Probing the caller's PATH would accept a conda-only command that
    # vanishes once the build replaces PATH with this same value.
    sanitised_path = build_path()

    for cmd, reason in (
            ("make",
             "Needed to run SAD's build."),
            ("gcc",
             "Needed to compile SAD's C sources and link the binary."),
            ("g++",
             "Needed to compile SAD's C++ sources under extensions/."),
            ("gfortran",
             "Needed to compile SAD's Fortran sources, which are most of SAD."),
            ("pkg-config",
             "Needed to locate the X11 headers while SAD configures."),
            ("nroff",
             "Needed to format SAD's libtai man pages during the build."),
            ("patch",
             "Needed to patch SAD's bundled libtai sources during the build."),
            ("yacc",
             "Needed to regenerate src/calc.c from src/calc.y.")):
        found = check_command(
            cmd,
            reason,
            package_suggestion(cmd, family),
            path = sanitised_path)
        if found is not None:
            missing.append(found)

    ########################################
    # X11 Headers
    ########################################
    headers = check_x11_headers(family)
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
    family = distro_family()
    logger.info(
        f"Checking for required dependencies "
        f"({family or 'unrecognised'} package names)")
    _require_dependencies(
        audit_dependencies(),
        footer = (
            "Install these through your system's normal package mechanism, "
            "or ask whoever administers this machine to install them. "
            "Then rerun sad2xs-install-sad."))

################################################################################
# Build Environment
################################################################################
########################################
# Conda Toolchain Rejection
########################################
# A conda compiler builds SAD against that environment's libraries, so the
# binary stops working the moment the environment is deactivated.
CONDA_MARKERS = ("conda", "mamba", "miniforge")


def make_clean_build_env() -> dict[str, str]:
    """
    Build an environment that compiles SAD with the system toolchain.

    Returns
    -------
    dict
        Environment variables for the SAD build.

    Raises
    ------
    SystemExit
        If a required compiler cannot be found on the build PATH, or
        resolves into a conda environment.
    """
    env = strip_inherited_build_settings()

    ########################################
    # Pin The System Toolchain
    ########################################
    env["PATH"] = build_path()

    # gcc is not a substitute for g++: SAD's build system carries a distinct
    # CXX, and the .cc sources under extensions/ need a real C++ driver.
    for variable, tool in (
            ("CC",  "gcc"),
            ("CXX", "g++"),
            ("FC",  "gfortran")):
        resolved = shutil.which(tool, path = env["PATH"])
        if resolved is None:
            sys.exit(
                f"Compiler not found on the build PATH: {variable} ({tool})")
        env[variable] = resolved

    ########################################
    # Refuse A Conda Toolchain
    ########################################
    for variable in ("CC", "CXX", "FC"):
        if any(marker in env[variable] for marker in CONDA_MARKERS):
            sys.exit(
                f"{variable}={env[variable]} lives in a conda environment. "
                f"SAD must be built with the system toolchain.")

    return env

################################################################################
# Source Preparation
################################################################################
def _expected_sad_conf(original: Path) -> str:
    """
    Build the sad.conf the build needs, from the preserved original.

    Parameters
    ----------
    original : Path
        The untruncated file kept beside sad.conf.

    Returns
    -------
    str
        The first lines of the original, as SAD_CONF_LINES sets.
    """
    text = original.read_text(encoding = "utf-8", errors = "replace")
    return "".join(text.splitlines(keepends = True)[:SAD_CONF_LINES])


def _write_atomically(path: Path, text: str) -> None:
    """
    Replace a file in one step, so it is never half-written.

    An interrupted write would otherwise leave a truncated sad.conf that
    looks finished, and the next run would build from it.

    Parameters
    ----------
    path : Path
        File to replace.
    text : str
        Contents to write.
    """
    staging = path.with_name(f"{path.name}.sad2xs-tmp")
    staging.write_text(text, encoding = "utf-8")
    os.replace(staging, path)


def truncate_sad_conf(config: InstallConfig) -> None:
    """
    Cut sad.conf down to the lines KEK's instructions call for.

    The remainder of the file targets legacy Unix systems and stops the
    build on a current distribution.

    The untruncated file is preserved first, and each write lands in one
    step. An interrupted run therefore always leaves a readable original,
    and the next run finishes the job from it.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.

    Raises
    ------
    SystemExit
        If the cloned tree has no sad.conf to work from.
    """
    sad_conf = config.src_dir / "sad.conf"
    original = config.src_dir / "sad.conf.orig"

    ########################################
    # Reused Or Interrupted Tree
    ########################################
    # The backup existing is not proof the replacement finished, so the
    # file is compared against what the original says it should be.
    if original.exists():
        expected = _expected_sad_conf(original)
        if (sad_conf.exists()
                and sad_conf.read_text(
                    encoding = "utf-8", errors = "replace") == expected):
            logger.info("sad.conf already truncated")
            return

        logger.info("Completing an interrupted sad.conf truncation")
        _write_atomically(sad_conf, expected)
        return

    ########################################
    # Fresh Tree
    ########################################
    if not sad_conf.exists():
        sys.exit(f"Cloned tree has no sad.conf: {sad_conf}")

    _write_atomically(
        original,
        sad_conf.read_text(encoding = "utf-8", errors = "replace"))
    _write_atomically(sad_conf, _expected_sad_conf(original))

    logger.info(
        f"Truncated sad.conf to {SAD_CONF_LINES} lines "
        f"(original kept as {original.name})")

################################################################################
# Main Installation Process
################################################################################
def install_sad_linux(config: InstallConfig) -> None:
    """
    Build SAD from source on Linux.

    Parameters
    ----------
    config : InstallConfig
        Where to build and install, and which source to use.

    Raises
    ------
    SystemExit
        If the running platform is not Linux, or a required tool or the
        built SAD binary is missing.
    CommandError
        If the clone or a build step returns non-zero.
    """
    # Without this, the failure elsewhere is an unexplained missing compiler
    # or an /etc/os-release that does not exist.
    require_platform("linux", "Linux")

    log_section_heading("Linux SAD Installation", mode = "banner")

    log_section_heading("Checking Required Dependencies")
    require_dependencies()

    log_section_heading("Fetching SAD Source")
    reused_tree = clone_sad(config)
    truncate_sad_conf(config)

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
