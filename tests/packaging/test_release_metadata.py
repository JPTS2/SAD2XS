"""
================================================================================
Tests for SAD2XS package release metadata
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import importlib.metadata
import re

################################################################################
# Module-level metadata fixture
################################################################################
_META     = importlib.metadata.metadata("sad2xs")
_REQUIRES = importlib.metadata.requires("sad2xs") or []

################################################################################
# Name
################################################################################
def test_release_metadata_package_name_is_a_non_empty_string():
    """
    The published package name should be a non-empty string. An empty or absent
    name breaks pip, PyPI, and any downstream tooling that resolves by name.
    """
    name = _META["Name"]
    assert isinstance(name, str) and len(name) > 0, (
        "Package `Name` metadata field should be a non-empty string.")


################################################################################
# Version
################################################################################
def test_release_metadata_version_follows_semver_format():
    """
    The package version should follow the MAJOR.MINOR.PATCH semver pattern.
    Non-conforming version strings break pip dependency resolution and PyPI
    upload validation.
    """
    version = _META["Version"]
    assert re.match(r"^\d+\.\d+\.\d+", version), (
        f"Package version `{version}` should follow MAJOR.MINOR.PATCH semver "
        "format.")


################################################################################
# Author
################################################################################
def test_release_metadata_author_field_is_a_non_empty_string():
    """
    The Author metadata field should be present and non-empty.
    """
    author = _META["Author"]
    assert isinstance(author, str) and len(author) > 0, (
        "Package `Author` metadata field should be a non-empty string.")


def test_release_metadata_author_email_contains_at_symbol():
    """
    The Author-email field should contain an `@` character, which is the
    minimal structural requirement for a valid email address.
    """
    email = _META["Author-email"]
    assert "@" in email, (
        f"Package `Author-email` field `{email}` should contain `@`.")


################################################################################
# License
################################################################################
def test_release_metadata_license_field_is_a_non_empty_string():
    """
    The License metadata field should be present and non-empty. An absent
    license blocks publication to PyPI and causes ambiguity for downstream
    users about redistribution rights.
    """
    license_field = _META["License"]
    assert isinstance(license_field, str) and len(license_field) > 0, (
        "Package `License` metadata field should be a non-empty string.")


################################################################################
# Dependencies
################################################################################
def test_release_metadata_xsuite_is_listed_as_a_dependency():
    """
    xsuite is a hard runtime dependency. Requiring the bundle ensures that pip
    installs mutually compatible Xtrack, Xobjects, and Xdeps versions.
    """
    assert any(req.startswith("xsuite>=") for req in _REQUIRES), (
        "Package install_requires should require a current coherent Xsuite "
        f"bundle. Current requires: {_REQUIRES}")


def test_release_metadata_numpy_is_listed_as_a_dependency():
    """
    numpy is a hard runtime dependency used throughout the converter and writer.
    It must appear in install_requires.
    """
    assert any("numpy" in req for req in _REQUIRES), (
        "Package install_requires should list `numpy`. "
        f"Current requires: {_REQUIRES}")


def test_release_metadata_tfs_is_an_optional_extra_not_a_hard_dependency():
    """
    tfs-pandas is only needed for sad2xs.sad_helpers, not the core converter.
    It must be declared as an extra, not an unconditional install_requires
    entry.
    """
    tfs_requires = [req for req in _REQUIRES if "tfs" in req]
    assert tfs_requires, (
        f"Expected a `tfs-pandas` entry in package metadata. Current "
        f"requires: {_REQUIRES}")
    assert all("extra ==" in req for req in tfs_requires), (
        "tfs-pandas should only be required under an extra, not "
        f"unconditionally. Current tfs requires: {tfs_requires}")
