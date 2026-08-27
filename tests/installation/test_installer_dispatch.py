"""
================================================================================
Tests for sad2xs.install_sad.dispatch
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
from pathlib import Path

import pytest

from sad2xs.install_sad import dispatch, macos
from sad2xs.install_sad._helpers import CommandError

################################################################################
# Platform Guard
################################################################################
########################################
# Supported Platform
########################################
def test_require_platform_allows_the_macos_installer_on_macos(monkeypatch):
    """
    An installer running on the platform it supports should proceed.
    """
    monkeypatch.setattr(dispatch.sys, "platform", "darwin")

    dispatch.require_platform("darwin", "macOS")


########################################
# Wrong Platform
########################################
def test_require_platform_exits_when_the_macos_installer_runs_on_linux(monkeypatch):
    """
    An installer run directly on the wrong platform should exit, naming the
    command that picks the right one.

    Linux specifically, because Linux has an installer of its own: a check
    for "some installer exists" would pass there and run the macOS one.
    """
    monkeypatch.setattr(dispatch.sys, "platform", "linux")

    with pytest.raises(SystemExit) as exc_info:
        dispatch.require_platform("darwin", "macOS")

    assert "sad2xs-install-sad" in str(exc_info.value), (
        "The message should name the command that picks the right installer.")

################################################################################
# Command Line
################################################################################
########################################
# Default Locations
########################################
def test_the_command_line_defaults_to_the_xdg_locations():
    """
    With no arguments the install should land in the XDG directories.
    """
    config = dispatch.parse_args_to_config([])

    assert config.prefix  == Path.home() / ".local" / "share" / "sad2xs", (
        "The source tree should default to the XDG data directory.")
    assert config.bin_dir == Path.home() / ".local" / "bin", (
        "The launcher should default to the directory distribution profiles "
        "already add to PATH.")
    assert config.reuse_clone is False, (
        "A rerun should replace the source tree unless asked not to.")
    assert config.branch_explicit is False, (
        "A defaulted branch should be marked as not user-supplied, so an "
        "upstream rename falls back instead of failing.")


########################################
# Prefix Redirection
########################################
def test_prefix_redirects_the_whole_install():
    """
    A single --prefix should move the source tree and the build logs.

    This is what makes an install off a slow or quota-limited home
    directory possible, which is the LXPlus case.
    """
    config = dispatch.parse_args_to_config(["--prefix", "/scratch/sad"])

    assert config.src_dir   == Path("/scratch/sad/src"), (
        "--prefix should move the source tree.")
    assert config.log_dir   == Path("/scratch/sad/logs"), (
        "--prefix should move the build logs with it.")
    assert config.bin_dir   == Path.home() / ".local" / "bin", (
        "--prefix should not move the launcher, which has its own flag.")


########################################
# User Relative Paths
########################################
def test_a_user_relative_prefix_is_expanded():
    """
    A ~ in a path should be expanded rather than taken literally.
    """
    config = dispatch.parse_args_to_config(["--prefix", "~/sad"])

    assert config.prefix == Path.home() / "sad", (
        "A tilde reaching the filesystem would create a directory named '~'.")

################################################################################
# Install SAD
################################################################################
def test_install_sad_exits_when_no_installer_exists_for_the_platform(monkeypatch):
    """
    A platform with no installer should exit, naming those that have one.

    Without this the failure surfaces much later, as a missing package
    manager or a toolchain probe with no equivalent on that platform.
    """
    monkeypatch.setattr(dispatch.sys, "platform", "win32")
    monkeypatch.setattr(dispatch, "set_log_level", lambda level: None)

    with pytest.raises(SystemExit) as exc_info:
        dispatch.install_sad([])

    message = str(exc_info.value)

    assert "win32" in message, (
        "The message should name the platform that was found.")
    assert "macOS" in message, (
        "The message should name the platforms that do have an installer.")


########################################
# Supported Platform Dispatch
########################################
def test_install_sad_hands_the_parsed_config_to_the_macos_installer(monkeypatch):
    """
    On macOS the command should reach the macOS installer, with the config.

    Nothing else covers the branch that actually installs, so a dispatch
    that never called an installer, or dropped the parsed arguments, would
    otherwise only show up when a user ran it.
    """
    received = []

    monkeypatch.setattr(dispatch.sys, "platform", "darwin")
    monkeypatch.setattr(dispatch, "set_log_level", lambda level: None)
    monkeypatch.setattr(
        macos,
        "install_sad_macos",
        lambda config: received.append(config))

    dispatch.install_sad(["--branch", "a-test-branch", "--reuse-clone"])

    assert len(received) == 1, (
        "macOS should reach the macOS installer exactly once.")
    assert received[0].branch == "a-test-branch", (
        "The installer should receive the parsed command line, not defaults.")
    assert received[0].reuse_clone is True, (
        "Flags should survive the trip through dispatch.")


########################################
# Build Failure Reporting
########################################
def test_install_sad_reports_a_failed_build_without_a_traceback(monkeypatch):
    """
    A failed build step should exit with its message, not a stack trace.

    run() has already reported the tail of the build log, so a traceback
    into the command runner shows the user nothing they can act on.
    """
    def failing_installer(config):
        raise CommandError(["make", "exe"], 2, log_path = "/tmp/build.log")

    monkeypatch.setattr(dispatch.sys, "platform", "darwin")
    monkeypatch.setattr(dispatch, "set_log_level", lambda level: None)
    monkeypatch.setattr(macos, "install_sad_macos", failing_installer)

    with pytest.raises(SystemExit) as exc_info:
        dispatch.install_sad([])

    message = str(exc_info.value)

    assert "make exe" in message, (
        "The exit message should name the build step that failed.")
    assert "/tmp/build.log" in message, (
        "The exit message should point at the build log.")


########################################
# Explicit Branch Selection
########################################
def test_a_named_branch_is_marked_as_explicitly_requested():
    """
    A branch given on the command line should be distinguishable.

    An absent explicit branch is an error, while an absent default one
    falls back to the remote default, so the two cannot be conflated.
    """
    config = dispatch.parse_args_to_config(["--branch", "feature-x"])

    assert config.branch == "feature-x", (
        "The requested branch should be carried through.")
    assert config.branch_explicit is True, (
        "A branch named by the user should be marked explicit.")
