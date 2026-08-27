"""
================================================================================
Tests for the macOS SAD installer helpers
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
import subprocess
from pathlib import Path

import pytest

from sad2xs.install_sad import macos as installer

################################################################################
# Homebrew Helpers
################################################################################
########################################
# Cask Installation
########################################
def test_brew_install_uses_cask_flag(monkeypatch):
    """
    Cask dependencies should be installed with `brew install --cask`.
    """
    commands = []

    def fake_run(cmd):
        commands.append(cmd)

    monkeypatch.setattr(installer, "run", fake_run)

    installer.brew_install("xquartz", cask = True)

    assert commands == [["brew", "install", "--cask", "xquartz"]]


########################################
# Prefix Lookup
########################################
def test_brew_prefix_installs_missing_formula_then_retries(monkeypatch):
    """
    brew_prefix(formula) should install a missing formula and retry lookup.
    """
    calls = []
    installed = []

    def fake_subprocess_run(cmd, text, stdout, stderr):
        calls.append(cmd)
        if len(calls) == 1:
            return subprocess.CompletedProcess(cmd, 1, stdout = "")
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout = "/opt/homebrew/opt/gcc\n")

    def fake_brew_install(formula):
        installed.append(formula)

    monkeypatch.setattr(installer.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(installer, "brew_install", fake_brew_install)

    assert installer.brew_prefix("gcc") == Path("/opt/homebrew/opt/gcc"), (
        "brew_prefix should return the prefix found on the retry.")
    assert installed == ["gcc"], (
        "brew_prefix should install the requested formula when prefix lookup "
        "fails.")
    assert calls == [
        ["brew", "--prefix", "gcc"],
        ["brew", "--prefix", "gcc"],
    ], "brew_prefix should retry prefix lookup after installation."


########################################
# Formula Executable Resolution
########################################
def test_ensure_brew_bin_exists_uses_executable_name(tmp_path, monkeypatch):
    """
    Homebrew binary checks should not duplicate the `bin` path component.
    """
    prefix  = tmp_path / "gcc"
    bin_dir = prefix / "bin"
    exe     = bin_dir / "gfortran"

    bin_dir.mkdir(parents = True)
    exe.touch()

    def fake_brew_prefix(formula):
        assert formula == "gcc"
        return prefix

    def fail_brew_install(formula):
        raise AssertionError(f"Unexpected install attempt for {formula}")

    monkeypatch.setattr(installer, "brew_prefix", fake_brew_prefix)
    monkeypatch.setattr(installer, "brew_install", fail_brew_install)

    assert installer.ensure_brew_bin_exists("gfortran", "gcc") == exe


########################################
# PATH Command Check
########################################
def test_ensure_command_exists_skips_install_when_command_available(monkeypatch):
    """
    ensure_command_exists should not install when the command is on PATH.
    """
    monkeypatch.setattr(installer.shutil, "which", lambda cmd: f"/usr/bin/{cmd}")

    def fail_brew_install(formula):
        raise AssertionError(f"Unexpected install attempt for {formula}")

    monkeypatch.setattr(installer, "brew_install", fail_brew_install)

    assert installer.ensure_command_exists("git", "git") is None


def test_ensure_command_exists_installs_missing_command(monkeypatch):
    """
    ensure_command_exists should install the formula when the command is missing.
    """
    which_results = iter([None, "/opt/homebrew/bin/nroff"])
    installed = []

    def fake_which(cmd):
        assert cmd == "nroff"
        return next(which_results)

    def fake_brew_install(formula):
        installed.append(formula)

    monkeypatch.setattr(installer.shutil, "which", fake_which)
    monkeypatch.setattr(installer, "brew_install", fake_brew_install)

    installer.ensure_command_exists("nroff", "groff")

    assert installed == ["groff"], (
        "ensure_command_exists should install the mapped formula when the "
        "command is missing.")


########################################
# X11 Headers
########################################
def test_check_x11_headers_installs_xquartz_when_headers_missing(monkeypatch):
    """
    Missing X11 headers should trigger xquartz cask installation.
    """
    installed = []
    header_present = iter([False, True])

    monkeypatch.setattr(
        installer.Path, "exists", lambda path: next(header_present))
    monkeypatch.setattr(
        installer,
        "brew_install",
        lambda pkg, cask = False: installed.append((pkg, cask)))

    installer.check_x11_headers()

    assert installed == [("xquartz", True)], (
        "Missing X11 headers should install the xquartz cask.")


def test_check_x11_headers_exits_when_the_cask_did_not_supply_them(monkeypatch):
    """
    XQuartz reporting success is not proof the headers arrived.

    The cask can install without placing headers until the user logs out
    and back in, and the build would otherwise fail much later with a
    missing Xlib.h and no explanation.
    """
    monkeypatch.setattr(installer.Path, "exists", lambda path: False)
    monkeypatch.setattr(installer, "brew_install", lambda pkg, cask = False: None)

    with pytest.raises(SystemExit) as exc_info:
        installer.check_x11_headers()

    assert "still missing after installing xquartz" in str(exc_info.value), (
        "The message should say the install did not supply the headers.")


########################################
# Dependency Order
########################################
def test_install_dependencies_checks_required_tools_in_order(monkeypatch):
    """
    install_dependencies should check Homebrew, required commands, gfortran,
    and X11 headers without performing installation work directly.
    """
    checked_commands = []
    checked_bins = []
    checked_x11 = []

    monkeypatch.setattr(installer.shutil, "which", lambda cmd: "/opt/homebrew/bin/brew")
    monkeypatch.setattr(
        installer,
        "ensure_command_exists",
        lambda cmd, formula: checked_commands.append((cmd, formula)))
    monkeypatch.setattr(
        installer,
        "ensure_brew_bin_exists",
        lambda exe, formula: checked_bins.append((exe, formula)))
    monkeypatch.setattr(
        installer,
        "check_x11_headers",
        lambda: checked_x11.append(True))

    installer.install_dependencies()

    assert checked_commands == [
        ("git", "git"),
        ("make", "make"),
        ("nroff", "groff"),
        ("bison", "bison"),
    ], "install_dependencies should check the expected command dependencies."
    assert checked_bins == [("gfortran", "gcc")], (
        "install_dependencies should require Homebrew gfortran from gcc.")
    assert checked_x11 == [True], (
        "install_dependencies should check X11 headers.")


################################################################################
# Build Environment
################################################################################
def test_make_clean_build_env_strips_conda_vars_and_sets_toolchain(
        tmp_path,
        monkeypatch):
    """
    make_clean_build_env should remove conda/build contamination and configure
    Homebrew plus Xcode toolchain paths.
    """
    tool_dir = tmp_path / "xcode"
    brew_root = tmp_path / "homebrew"
    gcc_prefix = brew_root / "opt" / "gcc"
    gcc_bin = gcc_prefix / "bin"
    tool_dir.mkdir()
    gcc_bin.mkdir(parents = True)

    tool_names = ["clang", "clang++", "ar", "ranlib", "nm", "strip", "ld"]
    for tool_name in tool_names:
        (tool_dir / tool_name).touch()
    (gcc_bin / "gfortran").touch()

    leaked = [
        "CONDA_PREFIX", "CC", "CMAKE_PREFIX_PATH",
        "CFLAGS", "CXXFLAGS", "FFLAGS", "FCFLAGS",
        "PKG_CONFIG_PATH", "CONDA_BUILD_SYSROOT", "LD_LIBRARY_PATH"]
    for variable in leaked:
        monkeypatch.setenv(variable, "/bad/conda")

    def fake_brew_prefix(formula = None):
        if formula == "gcc":
            return gcc_prefix
        return brew_root

    def fake_check_output(cmd, text):
        assert text is True
        if cmd == ["xcrun", "--show-sdk-path"]:
            return str(tmp_path / "sdk")
        lookup = {
            "clang":   tool_dir / "clang",
            "clang++": tool_dir / "clang++",
            "ar":      tool_dir / "ar",
            "ranlib":  tool_dir / "ranlib",
            "nm":      tool_dir / "nm",
            "strip":   tool_dir / "strip",
            "ld":      tool_dir / "ld",
        }
        return str(lookup[cmd[2]])

    monkeypatch.setattr(installer, "brew_prefix", fake_brew_prefix)
    monkeypatch.setattr(installer.subprocess, "check_output", fake_check_output)

    env = installer.make_clean_build_env()

    still_set = [v for v in leaked if v in env and env[v] == "/bad/conda"]
    assert not still_set, (
        f"An active conda environment must not reach the build, but "
        f"{still_set} survived. CFLAGS, CXXFLAGS and FFLAGS are exported by "
        f"an activated environment and were previously inherited.")
    assert env["PATH"].startswith(f"{brew_root}/bin:{brew_root}/sbin:"), (
        "make_clean_build_env should place Homebrew first on PATH.")
    assert env["FC"] == str(gcc_bin / "gfortran"), (
        "make_clean_build_env should use Homebrew gfortran.")
    assert env["CC"] == str(tool_dir / "clang"), (
        "make_clean_build_env should use the Xcode clang path.")


########################################
# Xcode Command Line Tools
########################################
def test_ensure_xcode_clt_passes_when_the_tools_are_configured(monkeypatch):
    """
    A configured toolchain should let the install proceed.
    """
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0))

    installer.ensure_xcode_clt()


def test_ensure_xcode_clt_exits_with_the_command_that_installs_them(monkeypatch):
    """
    Unconfigured Command Line Tools should exit naming the fix.

    Without them the failure appears much later as a missing xcrun, which
    says nothing about what the user has to do.
    """
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 1))

    with pytest.raises(SystemExit) as exc_info:
        installer.ensure_xcode_clt()

    assert "xcode-select --install" in str(exc_info.value), (
        "The message should give the exact command that fixes this.")


########################################
# Homebrew Absence
########################################
def test_brew_prefix_exits_when_homebrew_itself_is_missing(monkeypatch):
    """
    A missing Homebrew has no formula to install, so it cannot self-heal.
    """
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 1, stdout = ""))

    with pytest.raises(SystemExit) as exc_info:
        installer.brew_prefix()

    assert "Homebrew prefix" in str(exc_info.value), (
        "A missing Homebrew should be reported as such.")


def test_brew_prefix_gives_up_after_installing_a_formula_once(monkeypatch):
    """
    A formula that installs but still reports no prefix must not loop.
    """
    attempts = []

    def fake_run(cmd, **kwargs):
        attempts.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, stdout = "")

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(installer, "brew_install", lambda formula: None)

    with pytest.raises(SystemExit) as exc_info:
        installer.brew_prefix("gcc")

    assert len(attempts) == 2, (
        "The prefix lookup should be bounded at one reinstall.")
    assert "provided no prefix" in str(exc_info.value), (
        "The message should say the formula did not supply a prefix.")


def test_install_dependencies_exits_when_brew_is_not_installed(monkeypatch):
    """
    Homebrew is the only way this installer gets dependencies.
    """
    monkeypatch.setattr(installer.shutil, "which", lambda cmd: None)

    with pytest.raises(SystemExit) as exc_info:
        installer.install_dependencies()

    assert "brew.sh" in str(exc_info.value), (
        "The message should point at where to get Homebrew.")


########################################
# Toolchain Verification
########################################
def test_make_clean_build_env_exits_when_a_tool_path_does_not_exist(
        tmp_path,
        monkeypatch):
    """
    A toolchain variable pointing nowhere should fail before the build.

    xcrun can name a path that is not present, and the resulting build
    failure says nothing about which tool was missing.
    """
    monkeypatch.setattr(installer, "brew_prefix", lambda formula = None: tmp_path)
    monkeypatch.setattr(
        installer.subprocess,
        "check_output",
        lambda cmd, text: str(tmp_path / "absent_tool"))

    with pytest.raises(SystemExit) as exc_info:
        installer.make_clean_build_env()

    assert "Tool not found" in str(exc_info.value), (
        "The message should name the tool variable that failed to resolve.")


########################################
# Full Installation Sequence
########################################
def test_install_sad_macos_runs_every_stage_in_order(tmp_path, monkeypatch):
    """
    The install should check dependencies, fetch, build, verify, then link.

    Nothing else covers the function that performs the install, so a stage
    dropped or reordered would otherwise reach users unnoticed.
    """
    stages = []
    build_env = {"CC": "/usr/bin/clang"}

    monkeypatch.setattr(installer, "ensure_xcode_clt",
                        lambda: stages.append("xcode"))
    monkeypatch.setattr(installer, "install_dependencies",
                        lambda: stages.append("dependencies"))
    monkeypatch.setattr(installer, "clone_sad",
                        lambda config: stages.append("clone") or True)
    monkeypatch.setattr(installer, "make_clean_build_env",
                        lambda: build_env)
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

    config = installer.InstallConfig(
        prefix          = tmp_path / "share",
        bin_dir         = tmp_path / "bin",
        repo_url        = "https://example.invalid/SAD.git",
        branch          = "master",
        branch_explicit = False,
        reuse_clone     = False)

    installer.install_sad_macos(config)

    assert stages == [
        "xcode",
        "dependencies",
        "clone",
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
# Formula Without Its Executable
########################################
def test_ensure_brew_bin_exists_exits_when_the_formula_lacks_the_executable(
        tmp_path,
        monkeypatch):
    """
    A formula that installs but supplies no executable should exit.

    Homebrew reports success for the formula, so nothing else would catch
    a renamed or relocated binary.
    """
    monkeypatch.setattr(installer, "brew_prefix", lambda formula: tmp_path)
    monkeypatch.setattr(installer, "brew_install", lambda formula: None)

    with pytest.raises(SystemExit) as exc_info:
        installer.ensure_brew_bin_exists("gfortran", "gcc")

    assert "did not provide expected executable" in str(exc_info.value), (
        "The message should say the formula lacked the executable.")


########################################
# Command Still Missing After Install
########################################
def test_ensure_command_exists_exits_when_the_install_did_not_supply_it(
        monkeypatch):
    """
    A formula whose name does not match the command should exit.

    Homebrew returns success, so only a second PATH check catches it.
    """
    monkeypatch.setattr(installer.shutil, "which", lambda cmd: None)
    monkeypatch.setattr(installer, "brew_install", lambda formula: None)

    with pytest.raises(SystemExit) as exc_info:
        installer.ensure_command_exists("nroff", "groff")

    assert "still not found after installing groff" in str(exc_info.value), (
        "The message should name both the command and the formula.")
