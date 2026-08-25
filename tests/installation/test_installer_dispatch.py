"""
================================================================================
Tests for sad2xs.install_sad.dispatch
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
import pytest

from sad2xs.install_sad import dispatch

################################################################################
# Platform Guard
################################################################################
def test_require_platform_allows_the_macos_installer_on_macos(monkeypatch):
    """
    An installer running on the platform it supports should proceed.
    """
    monkeypatch.setattr(dispatch.sys, "platform", "darwin")

    dispatch.require_platform("darwin", "macOS")


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
# Install SAD
################################################################################
def test_install_sad_exits_when_no_installer_exists_for_the_platform(monkeypatch):
    """
    A platform with no installer should exit, naming those that have one.

    Without this the failure surfaces much later, as a missing package
    manager or a toolchain probe with no equivalent on that platform.
    """
    monkeypatch.setattr(dispatch.sys, "platform", "win32")

    with pytest.raises(SystemExit) as exc_info:
        dispatch.install_sad()

    message = str(exc_info.value)

    assert "win32" in message, (
        "The message should name the platform that was found.")
    assert "macOS" in message, (
        "The message should name the platforms that do have an installer.")
