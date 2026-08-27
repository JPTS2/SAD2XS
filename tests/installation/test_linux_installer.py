"""
================================================================================
Tests for the Linux SAD installer helpers
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
import ast
import io
import subprocess
import sys
import tokenize
from pathlib import Path

import pytest

from sad2xs.install_sad import linux as installer

################################################################################
# Test Helpers
################################################################################
def make_config(tmp_path: Path) -> installer.InstallConfig:
    """
    Build a config rooted under a temporary directory.

    Parameters
    ----------
    tmp_path : Path
        Directory to root the install under.

    Returns
    -------
    InstallConfig
        A config no test writes outside of.
    """
    return installer.InstallConfig(
        prefix          = tmp_path / "share",
        bin_dir         = tmp_path / "bin",
        repo_url        = "https://example.invalid/SAD.git",
        branch          = "master",
        branch_explicit = False,
        reuse_clone     = False)


def write_os_release(tmp_path: Path, text: str) -> Path:
    """
    Write an os-release file for the distribution probe.

    Parameters
    ----------
    tmp_path : Path
        Directory to write into.
    text : str
        File contents.

    Returns
    -------
    Path
        The written file.
    """
    path = tmp_path / "os-release"
    path.write_text(text, encoding = "utf-8")
    return path


def stub_toolchain(directory: Path, *names: str) -> None:
    """
    Create runnable stand-ins for build commands.

    Parameters
    ----------
    directory : Path
        Directory to create them in.
    *names : str
        Command names to create.
    """
    directory.mkdir(parents = True, exist_ok = True)
    for name in names:
        tool = directory / name
        tool.touch()
        tool.chmod(0o755)

################################################################################
# Distribution Detection
################################################################################
########################################
# Recognised Families
########################################
@pytest.mark.parametrize(
    ("os_release", "expected"),
    [
        ('ID=ubuntu\nID_LIKE=debian\n',              "debian"),
        ('ID=debian\n',                              "debian"),
        ('ID="almalinux"\nID_LIKE="rhel centos"\n',  "rhel"),
        ('ID=rocky\nID_LIKE="rhel centos fedora"\n', "rhel"),
        ('ID=fedora\n',                              "rhel"),
        ('ID=alpine\n',                              None),
    ])
def test_distro_family_maps_a_distribution_to_its_packaging_family(
        tmp_path,
        os_release,
        expected):
    """
    A distribution should map to the family whose package names apply.

    ID_LIKE is what makes a derivative work without naming every one.
    """
    assert installer.distro_family(
        write_os_release(tmp_path, os_release)) == expected, (
        f"{os_release!r} should resolve to family {expected!r}.")


########################################
# Unreadable os-release
########################################
def test_distro_family_is_unknown_when_os_release_cannot_be_read(tmp_path):
    """
    An absent os-release should give no family rather than raise.
    """
    assert installer.distro_family(tmp_path / "absent") is None, (
        "An unreadable os-release should leave the family unknown.")


################################################################################
# Package Suggestions
################################################################################
########################################
# Family Package Names
########################################
@pytest.mark.parametrize(
    ("logical", "family", "expected"),
    [
        ("gfortran",   "debian", "the Debian/Ubuntu package gfortran"),
        ("gfortran",   "rhel",   "the RHEL family package gcc-gfortran"),
        ("gcc",        "debian", "the Debian/Ubuntu package build-essential"),
        ("gcc",        "rhel",   "the RHEL family package gcc"),
        ("g++",        "debian", "the Debian/Ubuntu package build-essential"),
        ("g++",        "rhel",   "the RHEL family package gcc-c++"),
        ("nroff",      "debian", "the Debian/Ubuntu package groff"),
        ("nroff",      "rhel",   "the RHEL family package groff-base"),
        ("x11",        "debian", "the Debian/Ubuntu package libx11-dev"),
        ("x11",        "rhel",   "the RHEL family package libX11-devel"),
        ("pkg-config", "debian", "the Debian/Ubuntu package pkg-config"),
        ("pkg-config", "rhel",   "the RHEL family package pkgconf-pkg-config"),
        ("yacc",       "debian", "the Debian/Ubuntu package bison"),
        ("yacc",       "rhel",   "the RHEL family package byacc"),
    ])
def test_package_suggestion_names_the_package_for_the_family(
        logical,
        family,
        expected):
    """
    The same dependency should be named the way its distribution names it.
    """
    assert installer.package_suggestion(logical, family) == expected, (
        f"{logical} on {family} should be suggested as {expected!r}.")


########################################
# Unrecognised Distribution
########################################
def test_package_suggestion_falls_back_when_the_family_is_unknown():
    """
    An unrecognised distribution should get an instruction, not a guess.

    Naming a package that does not exist on that distribution is worse
    than saying which dependency to go and find.
    """
    suggestion = installer.package_suggestion("gfortran", None)

    assert "gfortran" in suggestion, (
        "The instruction should still name the dependency.")
    assert "Debian" not in suggestion and "RHEL" not in suggestion, (
        "An unknown distribution should not be given another distribution's "
        "package names.")


########################################
# Unchecked Dependencies
########################################
def test_package_suggestion_passes_through_a_name_it_has_no_mapping_for():
    """
    A dependency named the same everywhere needs no mapping.
    """
    assert installer.package_suggestion("git", "debian") == (
        "the Debian/Ubuntu package git"), (
        "An unmapped dependency should keep its own name.")


################################################################################
# Dependency Audit
################################################################################
########################################
# Sanitised PATH
########################################
def test_build_path_is_the_system_directories_alone():
    """
    The build PATH should carry the distribution's directories only.
    """
    assert installer.build_path() == (
        "/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin"), (
        "The build PATH should be the system directories, in order.")


def test_the_audit_and_the_build_use_the_same_path(tmp_path, monkeypatch):
    """
    The PATH the audit probes must be the PATH the build receives.

    A command found on a different PATH can pass the audit and then vanish
    once the build starts.
    """
    system_bin = tmp_path / "system"
    stub_toolchain(
        system_bin, "make", "gcc", "g++", "gfortran", "pkg-config", "nroff",
        "patch", "yacc")
    monkeypatch.setattr(installer, "SYSTEM_PATH", str(system_bin))

    probed = []
    real_which = installer.shutil.which

    def fake_which(cmd, path = None):
        if path is not None:
            probed.append(path)
        return real_which(cmd, path = path)

    monkeypatch.setattr(installer.shutil, "which", fake_which)
    monkeypatch.setattr(installer, "check_x11_headers", lambda family: None)

    installer.audit_dependencies()
    env = installer.make_clean_build_env()

    assert probed, "The audit should probe build commands on an explicit PATH."
    assert set(probed) == {env["PATH"]}, (
        "Every build-time probe must use the PATH the build receives.")


########################################
# Conda Contamination
########################################
def test_a_build_command_supplied_only_by_conda_is_reported_missing(
        tmp_path,
        monkeypatch):
    """
    A command that only conda supplies must not pass the build audit.

    The build strips conda from PATH, so accepting it here would let the
    install fail later with no explanation.
    """
    conda_bin = tmp_path / "conda" / "bin"
    stub_toolchain(
        conda_bin, "git", "make", "gcc", "g++", "gfortran", "pkg-config",
        "nroff", "patch", "yacc")

    monkeypatch.setattr(installer, "SYSTEM_PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(installer, "check_x11_headers", lambda family: None)
    monkeypatch.setattr(installer, "distro_family", lambda: "debian")
    monkeypatch.setenv("PATH", str(conda_bin))

    names = [dependency.name for dependency in installer.audit_dependencies()]

    assert names == [
        "make", "gcc", "g++", "gfortran", "pkg-config", "nroff", "patch",
        "yacc"], (
        "A build command supplied only by conda must be reported missing.")


def test_a_build_command_on_the_sanitised_path_is_accepted(
        tmp_path,
        monkeypatch):
    """
    A command the sanitised PATH supplies should pass the build audit.

    This is the converse of the conda case, and proves the probe is not
    simply rejecting everything.
    """
    system_bin = tmp_path / "system"
    caller_bin = tmp_path / "caller"
    stub_toolchain(
        system_bin, "make", "gcc", "g++", "gfortran", "pkg-config", "nroff",
        "patch", "yacc")
    stub_toolchain(caller_bin, "git")

    monkeypatch.setattr(installer, "SYSTEM_PATH", str(system_bin))
    monkeypatch.setattr(installer, "check_x11_headers", lambda family: None)
    monkeypatch.setattr(installer, "distro_family", lambda: "debian")
    monkeypatch.setenv("PATH", str(caller_bin))

    assert installer.audit_dependencies() == [], (
        "A command on the sanitised PATH should be accepted.")


########################################
# Clone Dependencies
########################################
def test_git_is_probed_on_the_callers_path(tmp_path, monkeypatch):
    """
    git should be found the way the clone will find it.

    The clone runs before the build and inherits the caller's environment,
    so probing it on the build PATH would report the wrong answer.
    """
    caller_bin = tmp_path / "caller"
    stub_toolchain(caller_bin, "git")

    monkeypatch.setattr(installer, "SYSTEM_PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(installer, "check_x11_headers", lambda family: None)
    monkeypatch.setattr(installer, "distro_family", lambda: "debian")
    monkeypatch.setenv("PATH", str(caller_bin))

    names = [dependency.name for dependency in installer.audit_dependencies()]

    assert "git" not in names, (
        "git on the caller's PATH should satisfy the clone dependency.")


########################################
# Accumulated Report
########################################
def test_the_audit_reports_every_miss_together(tmp_path, monkeypatch):
    """
    Several missing dependencies should be reported in one pass.

    Reporting one at a time would make the user rerun the installer once
    per missing package.
    """
    monkeypatch.setattr(installer, "SYSTEM_PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(installer, "distro_family", lambda: "rhel")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    missing = installer.audit_dependencies()
    names = [dependency.name for dependency in missing]

    assert names == [
        "git", "make", "gcc", "g++", "gfortran", "pkg-config", "nroff",
        "patch", "yacc", "X11/Xlib.h",
    ], "Every missing dependency should appear in a single report."
    assert all("RHEL family package" in item.remedy for item in missing), (
        "Every suggestion should name the detected distribution's package.")


########################################
# X11 Headers
########################################
def test_check_x11_headers_accepts_a_multiarch_header(tmp_path, monkeypatch):
    """
    A header under a triplet directory should count as present.

    Debian multiarch puts it there rather than directly under
    /usr/include, and rejecting that would report a false miss.
    """
    triplet = tmp_path / "usr" / "include" / "x86_64-linux-gnu" / "X11"
    triplet.mkdir(parents = True)
    (triplet / "Xlib.h").touch()

    monkeypatch.setattr(
        installer.glob,
        "glob",
        lambda pattern: [str(triplet / "Xlib.h")])
    monkeypatch.setattr(installer.Path, "exists", lambda self: False)

    assert installer.check_x11_headers("debian") is None, (
        "A multiarch X11 header should satisfy the check.")


def test_check_x11_headers_reports_the_package_when_absent(monkeypatch):
    """
    Absent X11 headers should be reported with the distribution's package.
    """
    monkeypatch.setattr(installer.glob, "glob", lambda pattern: [])
    monkeypatch.setattr(installer.Path, "exists", lambda self: False)

    missing = installer.check_x11_headers("rhel")

    assert missing is not None, "Absent X11 headers should be reported."
    assert missing.remedy == "the RHEL family package libX11-devel", (
        "The report should name the package for the detected family.")


################################################################################
# Build Environment
################################################################################
########################################
# Inherited Settings
########################################
def test_make_clean_build_env_strips_conda_settings_and_pins_the_toolchain(
        tmp_path,
        monkeypatch):
    """
    The build environment should drop conda settings and name the compilers.

    A conda environment exports flags that redirect the build at its own
    toolchain, and SAD then links against libraries that vanish when the
    environment is deactivated.
    """
    system_bin = tmp_path / "system"
    stub_toolchain(system_bin, "gcc", "g++", "gfortran")
    monkeypatch.setattr(installer, "SYSTEM_PATH", str(system_bin))

    for variable in (
            "CFLAGS", "CXXFLAGS", "FFLAGS", "CPPFLAGS", "LDFLAGS",
            "PKG_CONFIG_PATH", "LD_LIBRARY_PATH", "CPATH", "LIBRARY_PATH",
            "CONDA_PREFIX", "CONDA_BUILD_SYSROOT"):
        monkeypatch.setenv(variable, "/opt/conda/contamination")

    env = installer.make_clean_build_env()

    for variable in (
            "CFLAGS", "CXXFLAGS", "FFLAGS", "CPPFLAGS", "LDFLAGS",
            "PKG_CONFIG_PATH", "LD_LIBRARY_PATH", "CPATH", "LIBRARY_PATH",
            "CONDA_PREFIX", "CONDA_BUILD_SYSROOT"):
        assert variable not in env, (
            f"{variable} should not reach the SAD build.")

    assert env["PATH"] == str(system_bin), (
        "The build should run on the sanitised PATH.")
    assert env["CC"] == str(system_bin / "gcc"), (
        "CC should be the system compiler, named explicitly.")
    assert env["FC"] == str(system_bin / "gfortran"), (
        "FC should be the system Fortran compiler, named explicitly.")


########################################
# No Compiler Substitution
########################################
def test_make_clean_build_env_refuses_to_use_gcc_as_the_cxx_compiler(
        tmp_path,
        monkeypatch):
    """
    gcc must not stand in for g++.

    SAD's build system carries a distinct CXX, and the .cc sources under
    extensions/ need a real C++ driver. Falling back would build a subtly
    different SAD, or fail deep inside make.
    """
    system_bin = tmp_path / "system"
    stub_toolchain(system_bin, "gcc", "gfortran")
    monkeypatch.setattr(installer, "SYSTEM_PATH", str(system_bin))

    with pytest.raises(SystemExit) as exc_info:
        installer.make_clean_build_env()

    assert "CXX" in str(exc_info.value) and "g++" in str(exc_info.value), (
        "The message should name both the variable and the missing compiler.")


def test_the_audit_reports_a_missing_gxx(tmp_path, monkeypatch):
    """
    A machine with gcc but no g++ should be told which package supplies it.
    """
    system_bin = tmp_path / "system"
    caller_bin = tmp_path / "caller"
    stub_toolchain(
        system_bin, "make", "gcc", "gfortran", "pkg-config", "nroff", "patch",
        "yacc")
    stub_toolchain(caller_bin, "git")

    monkeypatch.setattr(installer, "SYSTEM_PATH", str(system_bin))
    monkeypatch.setattr(installer, "check_x11_headers", lambda family: None)
    monkeypatch.setattr(installer, "distro_family", lambda: "rhel")
    monkeypatch.setenv("PATH", str(caller_bin))

    missing = installer.audit_dependencies()

    assert [item.name for item in missing] == ["g++"], (
        "Only the absent C++ compiler should be reported.")
    assert missing[0].remedy == "the RHEL family package gcc-c++", (
        "RHEL supplies g++ from gcc-c++, not from gcc.")


########################################
# Missing Compiler
########################################
def test_make_clean_build_env_exits_when_a_compiler_is_absent(
        tmp_path,
        monkeypatch):
    """
    A compiler missing from the build PATH should fail naming the variable.
    """
    system_bin = tmp_path / "system"
    stub_toolchain(system_bin, "gcc", "g++")
    monkeypatch.setattr(installer, "SYSTEM_PATH", str(system_bin))

    with pytest.raises(SystemExit) as exc_info:
        installer.make_clean_build_env()

    assert "FC" in str(exc_info.value), (
        "The message should name the compiler variable that failed.")


########################################
# Conda Toolchain Rejection
########################################
@pytest.mark.parametrize("marker", ["conda", "mamba", "miniforge"])
def test_make_clean_build_env_refuses_a_conda_compiler(
        tmp_path,
        monkeypatch,
        marker):
    """
    A compiler inside a conda environment should be refused, not used.

    SAD built with one links against that environment's libraries and
    stops working the moment it is deactivated.
    """
    system_bin = tmp_path / f"{marker}-env" / "bin"
    stub_toolchain(system_bin, "gcc", "g++", "gfortran")
    monkeypatch.setattr(installer, "SYSTEM_PATH", str(system_bin))

    with pytest.raises(SystemExit) as exc_info:
        installer.make_clean_build_env()

    assert "system toolchain" in str(exc_info.value), (
        "The message should say the system toolchain is required.")


################################################################################
# Source Preparation
################################################################################
########################################
# sad.conf Truncation
########################################
def test_truncate_sad_conf_keeps_seventy_lines_and_the_original(tmp_path):
    """
    sad.conf should be cut to the lines KEK's instructions call for.

    The rest of the file targets legacy Unix and stops the build on a
    current distribution.
    """
    config = make_config(tmp_path)
    config.src_dir.mkdir(parents = True)
    lines = [f"line {n}\n" for n in range(1, 121)]
    (config.src_dir / "sad.conf").write_text("".join(lines), encoding = "utf-8")

    installer.truncate_sad_conf(config)

    kept = (config.src_dir / "sad.conf").read_text(encoding = "utf-8")
    original = (config.src_dir / "sad.conf.orig").read_text(encoding = "utf-8")

    assert kept.splitlines() == [f"line {n}" for n in range(1, 71)], (
        "sad.conf should keep exactly its first 70 lines.")
    assert original == "".join(lines), (
        "The untruncated file should be kept alongside it.")


def test_truncate_sad_conf_leaves_a_correctly_truncated_tree_alone(tmp_path):
    """
    A reused tree already prepared correctly should be left as it is.
    """
    config = make_config(tmp_path)
    config.src_dir.mkdir(parents = True)
    lines = [f"line {n}\n" for n in range(1, 121)]
    (config.src_dir / "sad.conf.orig").write_text(
        "".join(lines), encoding = "utf-8")
    (config.src_dir / "sad.conf").write_text(
        "".join(lines[:70]), encoding = "utf-8")

    installer.truncate_sad_conf(config)

    assert (config.src_dir / "sad.conf").read_text(
        encoding = "utf-8") == "".join(lines[:70]), (
        "A correctly prepared sad.conf should be left untouched.")


@pytest.mark.parametrize(
    ("state", "contents"),
    [
        ("untruncated", "".join(f"line {n}\n" for n in range(1, 121))),
        ("partial",     "".join(f"line {n}\n" for n in range(1, 34))),
        ("wrong",       "something else entirely\n"),
        ("absent",      None),
    ])
def test_truncate_sad_conf_repairs_an_interrupted_preparation(
        tmp_path,
        state,
        contents):
    """
    A backup with a sad.conf that does not match it should be repaired.

    An interruption between writing the backup and replacing sad.conf
    leaves exactly this state, and the backup existing is not proof the
    replacement ever finished.
    """
    config = make_config(tmp_path)
    config.src_dir.mkdir(parents = True)
    lines = [f"line {n}\n" for n in range(1, 121)]
    (config.src_dir / "sad.conf.orig").write_text(
        "".join(lines), encoding = "utf-8")
    if contents is not None:
        (config.src_dir / "sad.conf").write_text(contents, encoding = "utf-8")

    installer.truncate_sad_conf(config)

    assert (config.src_dir / "sad.conf").read_text(
        encoding = "utf-8") == "".join(lines[:70]), (
        f"A {state} sad.conf should be rebuilt from the preserved original.")
    assert (config.src_dir / "sad.conf.orig").read_text(
        encoding = "utf-8") == "".join(lines), (
        "The preserved original must never be rewritten.")


def test_truncate_sad_conf_leaves_no_staging_file_behind(tmp_path):
    """
    The atomic write should leave nothing beside the files it replaces.
    """
    config = make_config(tmp_path)
    config.src_dir.mkdir(parents = True)
    (config.src_dir / "sad.conf").write_text(
        "".join(f"line {n}\n" for n in range(1, 121)), encoding = "utf-8")

    installer.truncate_sad_conf(config)

    assert sorted(path.name for path in config.src_dir.iterdir()) == [
        "sad.conf", "sad.conf.orig"], (
        "No staging file should survive the preparation.")


def test_truncate_sad_conf_exits_when_the_tree_has_no_sad_conf(tmp_path):
    """
    A tree without sad.conf should fail here, not deep inside make.
    """
    config = make_config(tmp_path)
    config.src_dir.mkdir(parents = True)

    with pytest.raises(SystemExit) as exc_info:
        installer.truncate_sad_conf(config)

    assert "sad.conf" in str(exc_info.value), (
        "The message should name the file that was expected.")


################################################################################
# Installation Sequence
################################################################################
########################################
# Failure Ordering
########################################
def test_install_sad_linux_stops_before_cloning_when_dependencies_are_missing(
        tmp_path,
        monkeypatch):
    """
    A missing dependency should stop the install before SAD is fetched.

    Cloning first would leave a half-installed tree behind that the user
    never asked for.
    """
    cloned = []

    monkeypatch.setattr(installer, "require_platform", lambda *args: None)
    monkeypatch.setattr(installer, "require_dependencies",
                        lambda: sys.exit("missing"))
    monkeypatch.setattr(installer, "clone_sad",
                        lambda config: cloned.append(config))

    with pytest.raises(SystemExit):
        installer.install_sad_linux(make_config(tmp_path))

    assert cloned == [], (
        "clone_sad should not run when a dependency is missing.")


########################################
# Full Installation Sequence
########################################
def test_install_sad_linux_runs_every_stage_in_order(tmp_path, monkeypatch):
    """
    The install should check, fetch, prepare, build, verify, then link.

    Nothing else covers the function that performs the install, so a stage
    dropped or reordered would otherwise reach users unnoticed.
    """
    stages = []
    build_env = {"CC": "/usr/bin/gcc"}

    monkeypatch.setattr(installer, "require_platform", lambda *args: None)
    monkeypatch.setattr(installer, "require_dependencies",
                        lambda: stages.append("dependencies"))
    monkeypatch.setattr(installer, "clone_sad",
                        lambda config: stages.append("clone") or True)
    monkeypatch.setattr(installer, "truncate_sad_conf",
                        lambda config: stages.append("sad.conf"))
    monkeypatch.setattr(installer, "make_clean_build_env", lambda: build_env)
    monkeypatch.setattr(installer, "verify_executable",
                        lambda config: stages.append("verify"))
    monkeypatch.setattr(installer, "write_launcher",
                        lambda config: stages.append("launcher"))
    monkeypatch.setattr(installer, "report_path_setup",
                        lambda config: stages.append("path"))

    received = {}

    def fake_make_sad(config, env, reused_tree):
        stages.append("build")
        received["env"] = env
        received["reused_tree"] = reused_tree

    monkeypatch.setattr(installer, "make_sad", fake_make_sad)

    installer.install_sad_linux(make_config(tmp_path))

    assert stages == [
        "dependencies",
        "clone",
        "sad.conf",
        "build",
        "verify",
        "launcher",
        "path",
    ], "The install stages should run in dependency order."
    assert received["env"] is build_env, (
        "The build should run against the sanitised environment.")
    assert received["reused_tree"] is True, (
        "clone_sad's reuse answer should reach the build, which decides "
        "whether to clean first.")


########################################
# Launcher Execution
########################################
def test_the_linux_install_writes_a_launcher_that_runs(tmp_path, monkeypatch):
    """
    The launcher the Linux install writes should run as written.

    The shared writer quotes the source path, and a path with a space in
    it would otherwise produce a launcher bash cannot parse.
    """
    bash = installer.shutil.which("bash")
    if bash is None:
        pytest.skip("bash is needed to run the generated launcher")

    config = make_config(tmp_path / "a dir with spaces")
    config.src_dir.mkdir(parents = True)
    (config.src_dir / "bin").mkdir()
    gs = config.src_dir / "bin" / "gs"
    gs.write_text('#!/bin/sh\necho "gs ran"\n', encoding = "utf-8")
    gs.chmod(0o755)

    monkeypatch.setattr(installer, "require_platform", lambda *args: None)
    monkeypatch.setattr(installer, "require_dependencies", lambda: None)
    monkeypatch.setattr(installer, "clone_sad", lambda config: False)
    monkeypatch.setattr(installer, "truncate_sad_conf", lambda config: None)
    monkeypatch.setattr(installer, "make_clean_build_env", dict)
    monkeypatch.setattr(installer, "make_sad",
                        lambda config, env, reused_tree: None)

    installer.install_sad_linux(config)

    result = subprocess.run(
        [bash, str(config.launcher)],
        capture_output  = True,
        text            = True,
        check           = False)

    assert result.returncode == 0, (
        f"The generated launcher should run: {result.stderr}")
    assert "gs ran" in result.stdout, (
        "The launcher should execute the built SAD binary.")


################################################################################
# Reported Instructions
################################################################################
def test_the_dependency_report_names_packages_without_a_privileged_command(
        tmp_path,
        monkeypatch):
    """
    The report should name packages, never a command to run as root.

    Printing a sudo line invites the user to run one, and on a shared
    machine they may have no route to root at all.
    """
    monkeypatch.setattr(installer, "SYSTEM_PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(installer, "distro_family", lambda: "debian")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    with pytest.raises(SystemExit) as exc_info:
        installer.require_dependencies()

    message = str(exc_info.value)

    assert "the Debian/Ubuntu package build-essential" in message, (
        "The report should name the package for the detected distribution.")
    assert "administers this machine" in message, (
        "The report should offer a route for a user without root.")
    for forbidden in ("sudo apt", "sudo dnf", "apt-get install", "dnf install",
                      " -y"):
        assert forbidden not in message, (
            f"The report should not print {forbidden!r}.")
    assert "never installs system dependencies and never uses sudo" in message, (
        "The report should state that SAD2XS runs none of it.")


########################################
# Family-Specific Providers
########################################
def test_yacc_is_named_per_family_because_bison_does_not_supply_it_everywhere():
    """
    The package that provides yacc differs between families.

    Debian's bison installs a yacc alternative. The RHEL family's bison
    ships only /usr/bin/bison, and yacc comes from byacc, so recommending
    bison there would leave the next audit reporting yacc again.
    """
    assert installer.package_suggestion("yacc", "debian").endswith("bison"), (
        "Debian supplies yacc from bison.")
    assert installer.package_suggestion("yacc", "rhel").endswith("byacc"), (
        "The RHEL family supplies yacc from byacc, not bison.")
