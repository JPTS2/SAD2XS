"""
================================================================================
Tests for the macOS SAD installer helpers
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

from sad2xs.install_sad import macos as installer

################################################################################
# Test Helpers
################################################################################
def make_config() -> installer.InstallConfig:
    """
    Build a config that no test is allowed to reach.

    Returns
    -------
    InstallConfig
        A config for a prefix the dependency gate stops short of.
    """
    return installer.InstallConfig(
        prefix          = Path("/nonexistent/sad2xs"),
        bin_dir         = Path("/nonexistent/bin"),
        repo_url        = "https://example.invalid/sad.git",
        branch          = "main",
        branch_explicit = False,
        reuse_clone     = False)

################################################################################
# Dependency Probes
################################################################################
########################################
# Homebrew Prefix Lookup
########################################
def test_brew_prefix_returns_none_when_the_formula_is_absent(monkeypatch):
    """
    A failed prefix lookup should report absence, never install anything.
    """
    commands = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, stdout = "")

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    assert installer.brew_prefix("gcc") is None, (
        "An absent formula should give no prefix.")
    assert commands == [["brew", "--prefix", "gcc"]], (
        "brew_prefix should probe once and never retry after an install.")


def test_brew_prefix_returns_none_when_homebrew_cannot_be_run(monkeypatch):
    """
    An absent brew executable should report absence, not raise.
    """
    def fake_run(cmd, **kwargs):
        raise OSError("no brew")

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    assert installer.brew_prefix() is None, (
        "An unrunnable brew should give no prefix.")


########################################
# Xcode Command Line Tools
########################################
def test_check_xcode_clt_passes_when_the_tools_are_configured(monkeypatch):
    """
    A configured toolchain should report nothing missing.
    """
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0))

    assert installer.check_xcode_clt() is None, (
        "Configured Command Line Tools are not a missing dependency.")


def test_check_xcode_clt_reports_the_command_that_installs_them(monkeypatch):
    """
    Unconfigured Command Line Tools should be reported naming the fix.

    Without them the failure appears much later as a missing xcrun, which
    says nothing about what the user has to do.
    """
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 1))

    missing = installer.check_xcode_clt()

    assert missing is not None, (
        "Unconfigured Command Line Tools should be reported.")
    assert missing.command == "xcode-select --install", (
        "The report should give the exact command that fixes this.")


########################################
# Build PATH
########################################
def test_build_path_puts_homebrew_ahead_of_the_system_directories():
    """
    The build PATH should be Homebrew then macOS, and nothing else.
    """
    assert installer.build_path(Path("/opt/homebrew")) == (
        "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/bin:/bin:/usr/sbin:/sbin"), (
        "The build PATH should carry Homebrew ahead of the system directories.")


def test_build_path_falls_back_to_the_system_directories_without_homebrew():
    """
    An absent Homebrew should leave only the macOS system directories.
    """
    assert installer.build_path(None) == installer.SYSTEM_PATH, (
        "Without Homebrew the build PATH is the system directories alone.")


def test_the_audit_and_the_build_use_the_same_path(tmp_path, monkeypatch):
    """
    The PATH the audit probes must be the PATH the build receives.

    A command found on a different PATH can pass the audit and then vanish
    once the build starts.
    """
    brew_root = tmp_path / "homebrew"
    (brew_root / "bin").mkdir(parents = True)
    (brew_root / "bin" / "gfortran").touch()
    probed = []

    monkeypatch.setattr(installer, "check_xcode_clt", lambda: None)
    monkeypatch.setattr(installer, "check_x11_headers", lambda: None)
    monkeypatch.setattr(installer, "brew_prefix", lambda formula = None: brew_root)
    monkeypatch.setattr(installer, "check_brew_bin",
                        lambda exe, formula, reason: None)

    def fake_which(cmd, path = None):
        if path is not None:
            probed.append(path)
        return f"/usr/bin/{cmd}"

    monkeypatch.setattr(installer.shutil, "which", fake_which)

    installer.audit_dependencies()

    monkeypatch.setattr(
        installer.subprocess,
        "check_output",
        lambda cmd, text: "/usr/bin/true")

    env = installer.make_clean_build_env()

    assert probed, "The audit should probe build commands on an explicit PATH."
    assert set(probed) == {env["PATH"]}, (
        "Every build-time probe must use the PATH the build receives.")


########################################
# PATH Command Check
########################################
def test_check_command_passes_when_the_command_is_on_path(monkeypatch):
    """
    A command already on PATH should report nothing missing.
    """
    monkeypatch.setattr(
        installer.shutil, "which", lambda cmd, path = None: "/usr/bin/git")

    assert installer.check_command("git", "why", "remedy") is None, (
        "A command on PATH is not a missing dependency.")


def test_check_command_reports_the_remedy_for_a_missing_command(monkeypatch):
    """
    A missing command should be reported with its manual command.
    """
    monkeypatch.setattr(
        installer.shutil, "which", lambda cmd, path = None: None)

    missing = installer.check_command("nroff", "why", "brew install groff")

    assert missing is not None, "A missing command should be reported."
    assert missing.name == "nroff", (
        "The report should name the command the user looked for.")
    assert missing.command == "brew install groff", (
        "The report should give the command that provides it.")


def test_check_command_searches_only_the_path_it_is_given(tmp_path):
    """
    An explicit PATH should be searched instead of the caller's.
    """
    real_dir = tmp_path / "real"
    empty_dir = tmp_path / "empty"
    real_dir.mkdir()
    empty_dir.mkdir()
    tool = real_dir / "toolname"
    tool.touch()
    tool.chmod(0o755)

    assert installer.check_command(
        "toolname", "why", "remedy", path = str(real_dir)) is None, (
        "A command on the given PATH should be accepted.")
    assert installer.check_command(
        "toolname", "why", "remedy", path = str(empty_dir)) is not None, (
        "A command absent from the given PATH should be reported.")


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
    brew_root = tmp_path / "homebrew"
    (brew_root / "bin").mkdir(parents = True)
    conda_bin.mkdir(parents = True)

    for name in ("make", "yacc", "nroff", "brew", "git"):
        tool = conda_bin / name
        tool.touch()
        tool.chmod(0o755)

    monkeypatch.setattr(installer, "check_xcode_clt", lambda: None)
    monkeypatch.setattr(installer, "check_x11_headers", lambda: None)
    monkeypatch.setattr(installer, "check_brew_bin",
                        lambda exe, formula, reason: None)
    monkeypatch.setattr(installer, "brew_prefix",
                        lambda formula = None: brew_root)
    monkeypatch.setattr(installer, "SYSTEM_PATH", str(tmp_path / "empty"))
    monkeypatch.setenv("PATH", str(conda_bin))

    names = [dependency.name for dependency in installer.audit_dependencies()]

    assert names == ["make", "yacc", "nroff"], (
        "A build command supplied only by conda must be reported missing.")


def test_a_build_command_on_the_sanitised_path_is_accepted(
        tmp_path,
        monkeypatch):
    """
    A command the sanitised PATH supplies should pass the build audit.

    This is the converse of the conda case, and proves the probe is not
    simply rejecting everything.
    """
    caller_bin = tmp_path / "caller"
    brew_root = tmp_path / "homebrew"
    (brew_root / "bin").mkdir(parents = True)
    caller_bin.mkdir()

    for name in ("brew", "git"):
        tool = caller_bin / name
        tool.touch()
        tool.chmod(0o755)
    for name in ("make", "yacc", "nroff"):
        tool = brew_root / "bin" / name
        tool.touch()
        tool.chmod(0o755)

    monkeypatch.setattr(installer, "check_xcode_clt", lambda: None)
    monkeypatch.setattr(installer, "check_x11_headers", lambda: None)
    monkeypatch.setattr(installer, "check_brew_bin",
                        lambda exe, formula, reason: None)
    monkeypatch.setattr(installer, "brew_prefix",
                        lambda formula = None: brew_root)
    monkeypatch.setattr(installer, "SYSTEM_PATH", str(tmp_path / "empty"))
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
    caller_bin.mkdir()
    git = caller_bin / "git"
    git.touch()
    git.chmod(0o755)

    monkeypatch.setattr(installer, "check_xcode_clt", lambda: None)
    monkeypatch.setattr(installer, "check_x11_headers", lambda: None)
    monkeypatch.setattr(installer, "check_brew_bin",
                        lambda exe, formula, reason: None)
    monkeypatch.setattr(installer, "brew_prefix",
                        lambda formula = None: tmp_path / "homebrew")
    monkeypatch.setenv("PATH", str(caller_bin))

    names = [dependency.name for dependency in installer.audit_dependencies()]

    assert "git" not in names, (
        "git on the caller's PATH should satisfy the clone dependency.")


########################################
# Formula Executable Check
########################################
def test_check_brew_bin_passes_when_the_formula_provides_it(tmp_path, monkeypatch):
    """
    A present, runnable formula executable should report nothing missing.
    """
    prefix = tmp_path / "gcc"
    (prefix / "bin").mkdir(parents = True)
    gfortran = prefix / "bin" / "gfortran"
    gfortran.touch()
    gfortran.chmod(0o755)

    monkeypatch.setattr(installer, "brew_prefix", lambda formula = None: prefix)

    assert installer.check_brew_bin("gfortran", "gcc", "why") is None, (
        "A runnable executable is not a missing dependency.")


def test_check_brew_bin_reports_an_executable_that_cannot_be_run(
        tmp_path,
        monkeypatch):
    """
    A present but non-executable file should be reported missing.

    An interrupted install can leave the file behind without its
    permissions, and the build would then fail with a bare exec error.
    """
    prefix = tmp_path / "gcc"
    (prefix / "bin").mkdir(parents = True)
    gfortran = prefix / "bin" / "gfortran"
    gfortran.touch()
    gfortran.chmod(0o644)

    monkeypatch.setattr(installer, "brew_prefix", lambda formula = None: prefix)

    assert installer.check_brew_bin("gfortran", "gcc", "why") is not None, (
        "A file that cannot be run is not a satisfied dependency.")


def test_check_brew_bin_reports_a_formula_that_is_not_installed(
        tmp_path,
        monkeypatch):
    """
    A prefix for an uninstalled formula should still report it missing.

    Homebrew answers with a prefix for any formula it knows, installed or
    not, so the prefix alone proves nothing.
    """
    monkeypatch.setattr(
        installer, "brew_prefix", lambda formula = None: tmp_path / "absent")

    missing = installer.check_brew_bin("gfortran", "gcc", "why")

    assert missing is not None, "An uninstalled formula should be reported."
    assert missing.command == "brew install gcc", (
        "The report should give the formula that provides gfortran.")


def test_check_brew_bin_reports_an_absent_formula(monkeypatch):
    """
    A formula with no prefix should be reported, not installed.
    """
    monkeypatch.setattr(installer, "brew_prefix", lambda formula = None: None)

    missing = installer.check_brew_bin("gfortran", "gcc", "why")

    assert missing is not None, "An absent formula should be reported."
    assert missing.command == "brew install gcc", (
        "The report should give the formula that provides gfortran.")


########################################
# X11 Headers
########################################
def test_check_x11_headers_reports_the_cask_when_headers_are_missing(monkeypatch):
    """
    Missing X11 headers should be reported, never installed.
    """
    monkeypatch.setattr(installer.Path, "exists", lambda self: False)

    missing = installer.check_x11_headers()

    assert missing is not None, "Absent X11 headers should be reported."
    assert missing.command == "brew install --cask xquartz", (
        "The report should give the cask that provides the headers.")


def test_check_x11_headers_passes_when_the_header_is_present(monkeypatch):
    """
    Present X11 headers should report nothing missing.
    """
    monkeypatch.setattr(installer.Path, "exists", lambda self: True)

    assert installer.check_x11_headers() is None, (
        "A present header is not a missing dependency.")


################################################################################
# Dependency Audit
################################################################################
########################################
# Complete Environment
########################################
def test_audit_dependencies_reports_nothing_when_everything_is_present(
        monkeypatch):
    """
    A complete dependency set should produce an empty report.
    """
    monkeypatch.setattr(installer, "check_xcode_clt", lambda: None)
    monkeypatch.setattr(
        installer.shutil,
        "which",
        lambda cmd, path = None: f"/usr/bin/{cmd}")
    monkeypatch.setattr(installer, "brew_prefix",
                        lambda formula = None: Path("/opt/homebrew"))
    monkeypatch.setattr(
        installer,
        "check_brew_bin",
        lambda exe, formula, reason: None)
    monkeypatch.setattr(installer, "check_x11_headers", lambda: None)

    assert installer.audit_dependencies() == [], (
        "A complete environment should report nothing missing.")


########################################
# Missing Homebrew
########################################
def test_audit_dependencies_reports_homebrew_without_probing_its_formulae(
        monkeypatch):
    """
    An absent Homebrew should be reported without a formula probe.

    Every formula probe goes through brew, so running them anyway would
    bury the one real problem under formulae the user cannot check.
    """
    monkeypatch.setattr(installer, "check_xcode_clt", lambda: None)
    monkeypatch.setattr(installer, "check_x11_headers", lambda: None)

    def refuse(exe, formula, reason):
        raise AssertionError("Formula probes must not run without Homebrew.")

    monkeypatch.setattr(installer, "check_brew_bin", refuse)
    monkeypatch.setattr(
        installer.shutil,
        "which",
        lambda cmd, path = None: None if cmd == "brew" else f"/usr/bin/{cmd}")

    names = [dependency.name for dependency in installer.audit_dependencies()]

    assert names == ["brew"], (
        "A missing Homebrew should be the only reported dependency.")


########################################
# Accumulated Report
########################################
def test_audit_dependencies_reports_every_miss_together(monkeypatch):
    """
    Several missing dependencies should be reported in one pass.

    Reporting one at a time would make the user rerun the installer once
    per missing package.
    """
    monkeypatch.setattr(
        installer,
        "check_xcode_clt",
        lambda: installer.MissingDependency("clt", "why", "xcode-select --install"))
    monkeypatch.setattr(installer, "brew_prefix",
                        lambda formula = None: Path("/opt/homebrew"))
    monkeypatch.setattr(
        installer.shutil,
        "which",
        lambda cmd, path = None:
            None if cmd in ("yacc", "nroff") else f"/usr/bin/{cmd}")
    monkeypatch.setattr(
        installer,
        "check_brew_bin",
        lambda exe, formula, reason:
            installer.MissingDependency(exe, reason, f"brew install {formula}"))
    monkeypatch.setattr(
        installer,
        "check_x11_headers",
        lambda: installer.MissingDependency(
            "Xlib.h", "why", "brew install --cask xquartz"))

    names = [dependency.name for dependency in installer.audit_dependencies()]

    assert names == ["clt", "yacc", "nroff", "gfortran", "Xlib.h"], (
        "Every missing dependency should appear in a single report.")


################################################################################
# Dependency Gate
################################################################################
########################################
# Complete Environment
########################################
def test_require_dependencies_returns_when_nothing_is_missing(monkeypatch):
    """
    A complete dependency set should let the install proceed.
    """
    monkeypatch.setattr(installer, "audit_dependencies", lambda: [])

    assert installer.require_dependencies() is None, (
        "A complete environment should not stop the install.")


########################################
# Missing Dependencies
########################################
def test_require_dependencies_exits_listing_every_manual_command(monkeypatch):
    """
    Missing dependencies should exit non-zero naming each manual command.
    """
    monkeypatch.setattr(
        installer,
        "audit_dependencies",
        lambda: [
            installer.MissingDependency(
                "bison", "Needed to generate SAD's parser sources.",
                "brew install bison"),
            installer.MissingDependency(
                "/opt/X11/include/X11/Xlib.h", "Needed to build SAD against X11.",
                "brew install --cask xquartz")])

    with pytest.raises(SystemExit) as exc_info:
        installer.require_dependencies()

    message = str(exc_info.value)

    assert "brew install bison" in message, (
        "The exit should give the command for each missing dependency.")
    assert "brew install --cask xquartz" in message, (
        "The exit should give the cask command for missing X11 headers.")
    assert "never uses sudo" in message, (
        "The exit should state that SAD2XS never uses sudo.")


########################################
# Installation Order
########################################
def test_install_sad_macos_stops_before_cloning_when_dependencies_are_missing(
        monkeypatch):
    """
    A missing dependency should stop the install before SAD is fetched.

    Cloning first would leave a half-installed tree behind that the user
    never asked for.
    """
    cloned = []

    monkeypatch.setattr(installer, "require_platform", lambda *args: None)
    monkeypatch.setattr(
        installer,
        "require_dependencies",
        lambda: sys.exit("missing"))
    monkeypatch.setattr(
        installer,
        "clone_sad",
        lambda config: cloned.append(config))

    with pytest.raises(SystemExit):
        installer.install_sad_macos(make_config())

    assert cloned == [], (
        "clone_sad should not run when a dependency is missing.")


########################################
# Non-Mutating Policy
########################################
def test_the_macos_installer_has_no_package_installation_path():
    """
    No installer source line may name a package-manager install command.

    The installer is only allowed to report what is missing. Executing a
    package manager would ask the user for a password for work they never
    authorised.
    """
    source = Path(installer.__file__).read_text(encoding = "utf-8")

    # Docstrings and messages quote the manual commands on purpose, so only
    # what the interpreter would actually execute is inspected.
    code = "".join(
        token.string for token in tokenize.generate_tokens(
            io.StringIO(source).readline)
        if token.type not in (
            tokenize.STRING,
            tokenize.COMMENT,
            tokenize.FSTRING_MIDDLE))

    for phrase in (
            "sudo", "brew install", "apt install", "apt-get install",
            "dnf install", "yum install"):
        assert phrase not in code, (
            f"The installer must never execute {phrase!r}.")


def test_the_macos_installer_never_runs_an_install_subcommand():
    """
    No subprocess the installer launches may carry an install subcommand.

    The literal-phrase check cannot see a command split across list
    elements, which is how the removed automatic installation built it.
    """
    source = Path(installer.__file__).read_text(encoding = "utf-8")

    runners = {"run", "check_output", "check_call", "call", "Popen", "system"}
    forbidden = ("sudo", "install", "apt", "apt-get", "dnf", "yum")

    offenders = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue

        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(
            func, "id", "")
        if name not in runners:
            continue

        for argument in ast.walk(node):
            if not (isinstance(argument, ast.Constant)
                    and isinstance(argument.value, str)):
                continue
            # A shell string carries the whole command in one constant,
            # while a list carries each word in its own.
            words = set(argument.value.split()) | {argument.value}
            for word in forbidden:
                if word in words:
                    offenders.append((name, argument.value))

    assert offenders == [], (
        f"No launched command may include an install subcommand: {offenders}")


################################################################################
# Toolchain Verification
################################################################################
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


def test_make_clean_build_env_exits_when_homebrew_has_no_prefix(monkeypatch):
    """
    An unusable Homebrew should fail naming the prefix, not crash later.
    """
    monkeypatch.setattr(installer, "brew_prefix", lambda formula = None: None)

    with pytest.raises(SystemExit) as exc_info:
        installer.make_clean_build_env()

    assert "Homebrew prefix" in str(exc_info.value), (
        "The message should name the lookup that failed.")


################################################################################
# Full Installation Sequence
################################################################################
def test_install_sad_macos_runs_every_stage_in_order(tmp_path, monkeypatch):
    """
    The install should check dependencies, fetch, build, verify, then link.

    Nothing else covers the function that performs the install, so a stage
    dropped or reordered would otherwise reach users unnoticed.
    """
    stages = []
    build_env = {"CC": "/usr/bin/clang"}

    monkeypatch.setattr(installer, "require_dependencies",
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
