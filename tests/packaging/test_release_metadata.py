"""
================================================================================
Tests for SAD2XS package release metadata
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-27
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import importlib
import importlib.metadata
import pathlib
import re
import tomllib

################################################################################
# Module-level metadata fixture
################################################################################
_META     = importlib.metadata.metadata("sad2xs")
_REQUIRES = importlib.metadata.requires("sad2xs") or []

_PYPROJECT = tomllib.loads(
    (pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml").read_text())

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
def test_release_metadata_author_name_is_declared():
    """
    The author name should be present and non-empty. PEP 621 metadata carries
    the name inside `Author-email` as `Name <address>`, and emits no separate
    `Author` field, so the name is read from there.
    """
    author_email = _META["Author-email"]
    assert re.match(r"^\s*\S.*<[^>]+>\s*$", author_email or ""), (
        f"Package `Author-email` field `{author_email}` should declare an "
        "author name in `Name <address>` form.")


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
def test_release_metadata_license_expression_is_a_non_empty_string():
    """
    The license should be present and non-empty. An absent license blocks
    publication to PyPI and causes ambiguity for downstream users about
    redistribution rights. PEP 639 metadata declares it as a SPDX expression
    in `License-Expression` and emits no legacy `License` field.
    """
    license_field = _META["License-Expression"]
    assert isinstance(license_field, str) and len(license_field) > 0, (
        "Package `License-Expression` metadata field should be a non-empty "
        "SPDX license expression.")


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


def test_release_metadata_scipy_is_listed_as_a_dependency():
    """
    scipy is a hard runtime dependency. `sad2xs.converter` imports
    `scipy.constants` at module level, so a core conversion fails on import
    without it. Xsuite happens to pull scipy in today, but relying on a
    transitive dependency breaks as soon as Xsuite drops it.
    """
    assert any("scipy" in req for req in _REQUIRES), (
        "Package dependencies should list `scipy`. "
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


################################################################################
# Console Scripts
################################################################################
def test_release_metadata_console_scripts_resolve_to_real_callables():
    """
    Every `[project.scripts]` target should import and be callable.

    Nothing else executes these entry points, so a renamed or mistyped
    target ships a command that fails at the first invocation, and only for
    the user who runs it.
    """
    scripts = _PYPROJECT.get("project", {}).get("scripts", {})

    assert scripts, "The project should declare at least one console script."

    for name, target in scripts.items():
        module_path, _, attribute = target.partition(":")

        module = importlib.import_module(module_path)

        assert hasattr(module, attribute), (
            f"Console script {name} points at {target}, but {attribute} does "
            f"not exist in {module_path}.")
        assert callable(getattr(module, attribute)), (
            f"Console script {name} points at {target}, which is not callable.")
