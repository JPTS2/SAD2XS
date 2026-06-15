"""
================================================================================
Tests for the macOS SAD installer helpers
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-15
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import subprocess
from pathlib import Path

import pytest

import _install_sad_macos as installer

################################################################################
# Command Runner
################################################################################
def test_run_raises_command_error_on_nonzero_return_code(monkeypatch):
    """
    run should raise CommandError when a checked command returns non-zero.
    """
    def fake_subprocess_run(cmd, cwd = None, env = None, stdin = None):
        return subprocess.CompletedProcess(cmd, 7)

    monkeypatch.setattr(installer.subprocess, "run", fake_subprocess_run)

    with pytest.raises(installer.CommandError) as exc_info:
        installer.run(["sad-build-step"])

    assert exc_info.value.cmd == ["sad-build-step"], (
        "CommandError should report the command that failed.")
    assert exc_info.value.returncode == 7, (
        "CommandError should report the subprocess return code.")


def test_run_check_false_returns_completed_process_on_nonzero(monkeypatch):
    """
    run should return the CompletedProcess when check=False.
    """
    completed = subprocess.CompletedProcess(["sad-build-step"], 7)

    def fake_subprocess_run(cmd, cwd = None, env = None, stdin = None):
        assert cmd == ["sad-build-step"]
        return completed

    monkeypatch.setattr(installer.subprocess, "run", fake_subprocess_run)

    result = installer.run(["sad-build-step"], check = False)

    assert result is completed, (
        "run(check=False) should return the subprocess result without raising.")


################################################################################
# Homebrew Helpers
################################################################################
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

    assert installer.brew_prefix("gcc") == Path("/opt/homebrew/opt/gcc")
    assert installed == ["gcc"], (
        "brew_prefix should install the requested formula when prefix lookup "
        "fails.")
    assert calls == [
        ["brew", "--prefix", "gcc"],
        ["brew", "--prefix", "gcc"],
    ], "brew_prefix should retry prefix lookup after installation."


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


def test_check_x11_headers_installs_xquartz_when_headers_missing(monkeypatch):
    """
    Missing X11 headers should trigger xquartz cask installation.
    """
    installed = []

    def fake_exists(path):
        assert str(path) == "/opt/X11/include/X11/Xlib.h"
        return False

    def fake_brew_install(pkg, cask = False):
        installed.append((pkg, cask))

    monkeypatch.setattr(installer.Path, "exists", fake_exists)
    monkeypatch.setattr(installer, "brew_install", fake_brew_install)

    installer.check_x11_headers()

    assert installed == [("xquartz", True)], (
        "Missing X11 headers should install the xquartz cask.")


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

    monkeypatch.setenv("CONDA_PREFIX", "/bad/conda")
    monkeypatch.setenv("CC", "/bad/clang")
    monkeypatch.setenv("CMAKE_PREFIX_PATH", "/bad/cmake")

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

    assert "CONDA_PREFIX" not in env, (
        "make_clean_build_env should remove conda environment variables.")
    assert "CMAKE_PREFIX_PATH" not in env, (
        "make_clean_build_env should remove build-system contamination.")
    assert env["PATH"].startswith(f"{brew_root}/bin:{brew_root}/sbin:"), (
        "make_clean_build_env should place Homebrew first on PATH.")
    assert env["FC"] == str(gcc_bin / "gfortran"), (
        "make_clean_build_env should use Homebrew gfortran.")
    assert env["CC"] == str(tool_dir / "clang"), (
        "make_clean_build_env should use the Xcode clang path.")


################################################################################
# Launcher and Shell Integration
################################################################################
def test_write_launcher_writes_executable_launcher(tmp_path, monkeypatch):
    """
    write_launcher should create an executable script pointing at the SAD build.
    """
    src_dir = tmp_path / "src"
    launcher_path = tmp_path / "sad"

    monkeypatch.setattr(installer, "SRC_DIR", src_dir)
    monkeypatch.setattr(installer, "LAUNCHER_SCRIPT", launcher_path)

    installer.write_launcher()

    launcher_text = launcher_path.read_text()

    assert launcher_path.exists(), (
        "write_launcher should create the configured launcher script.")
    assert launcher_path.stat().st_mode & 0o111, (
        "write_launcher should make the launcher executable.")
    assert f'SAD_DIR="{src_dir}"' in launcher_text, (
        "Launcher should point at the configured SAD source directory.")
    assert 'GS_EXEC="$SAD_DIR/bin/gs"' in launcher_text, (
        "Launcher should execute SAD's gs binary.")


def test_append_to_shell_rc_does_not_duplicate_existing_path(
        tmp_path,
        monkeypatch):
    """
    append_to_shell_rc should not duplicate an existing SAD PATH entry.
    """
    rc_file = tmp_path / ".zshrc"
    rc_file.write_text('export PATH="$HOME/bin/sad:$PATH"\n')

    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr(installer.Path, "home", classmethod(lambda cls: tmp_path))

    installer.append_to_shell_rc()

    assert rc_file.read_text().count('export PATH="$HOME/bin/sad:$PATH"') == 1, (
        "append_to_shell_rc should not duplicate an existing SAD PATH entry.")


def test_append_to_shell_rc_creates_missing_shell_rc(
        tmp_path,
        monkeypatch):
    """
    append_to_shell_rc should create the shell rc file when it is missing.
    """
    rc_file = tmp_path / ".bashrc"

    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setattr(installer.Path, "home", classmethod(lambda cls: tmp_path))

    installer.append_to_shell_rc()

    assert rc_file.exists(), (
        "append_to_shell_rc should create a missing bash rc file.")
    assert 'export PATH="$HOME/bin/sad:$PATH"' in rc_file.read_text(), (
        "append_to_shell_rc should add SAD to PATH in the created rc file.")
