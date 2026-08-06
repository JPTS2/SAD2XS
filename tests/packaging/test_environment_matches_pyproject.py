"""
================================================================================
Tests that environment.yml and pyproject.toml declare the same dependencies
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-29
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import re
import tomllib
from pathlib import Path

import yaml
from packaging.requirements import Requirement
from packaging.version import Version

################################################################################
# Test Parameters
#
# Two files declare the same dependencies. environment.yml stays installable on
# its own, which is why the duplication is kept rather than removed, so these
# tests are what stop the two drifting apart.
################################################################################
REPO_ROOT   = Path(__file__).resolve().parents[2]
PYPROJECT   = REPO_ROOT / "pyproject.toml"
ENVIRONMENT = REPO_ROOT / "environment.yml"

# The `dev` extra aggregates the others by referring to the package itself.
SELF_NAME = "sad2xs"


################################################################################
# Helpers
################################################################################
def _canonical(name: str) -> str:
    """
    PEP 503 canonical form of a distribution name, for comparison across files.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def _floor(requirement: Requirement) -> Version | None:
    """
    Lowest version a requirement admits, or None when it sets no floor.
    """
    versions = [
        Version(spec.version) for spec in requirement.specifier
        if spec.operator in (">=", "==", "~=")]
    return max(versions) if versions else None


def _pyproject_requirements() -> dict[str, Requirement]:
    """
    Every dependency declared in `pyproject.toml`, core and extras alike.

    Returns
    -------
    dict
        Canonical distribution name to requirement.
    """
    data    = tomllib.loads(PYPROJECT.read_text())["project"]
    entries = list(data.get("dependencies", []))
    for extra in data.get("optional-dependencies", {}).values():
        entries.extend(extra)

    found = {}
    for entry in entries:
        requirement = Requirement(entry)
        if _canonical(requirement.name) == SELF_NAME:
            continue                        # the `dev` extra aggregating others
        found[_canonical(requirement.name)] = requirement
    return found


def _environment_requirements() -> dict[str, Requirement]:
    """
    Every pip requirement declared in `environment.yml`.

    Returns
    -------
    dict
        Canonical distribution name to requirement.
    """
    data  = yaml.safe_load(ENVIRONMENT.read_text())
    found = {}
    for entry in data.get("dependencies", []):
        if not isinstance(entry, dict) or "pip" not in entry:
            continue                        # a conda entry, not a pip one
        for item in entry["pip"]:
            requirement = Requirement(item)
            found[_canonical(requirement.name)] = requirement
    return found


################################################################################
# Coverage
################################################################################
def test_environment_declares_every_pyproject_dependency():
    """
    `environment.yml` installs everything `pyproject.toml` declares.

    Covers extras as well as core dependencies, because `environment.yml` is
    meant to produce a working development environment on its own. A new extra
    that never reaches it would leave the documented one-command setup short of
    a package the code imports.
    """
    missing = sorted(set(_pyproject_requirements()) - set(_environment_requirements()))

    assert not missing, (
        "environment.yml must declare every dependency in pyproject.toml. "
        f"Missing: {missing}")


def test_environment_declares_nothing_pyproject_omits():
    """
    `environment.yml` installs nothing `pyproject.toml` does not declare.

    An entry here and nowhere else is a dependency the published package never
    requires, so it works in a development environment and fails on install.
    """
    extra = sorted(set(_environment_requirements()) - set(_pyproject_requirements()))

    assert not extra, (
        "environment.yml declares packages absent from pyproject.toml. Add "
        f"them there or remove them here: {extra}")


################################################################################
# Version Agreement
################################################################################
def test_environment_floors_are_compatible_with_pyproject():
    """
    No `environment.yml` floor admits a version `pyproject.toml` forbids.

    A bare name beside a pinned requirement is the failure this catches: when
    `pyproject.toml` gained `xsuite>=0.57.0` for a corrected bend fringe
    formula, `environment.yml` still said `xsuite`, so the container could
    resolve an older release the tests do not pass against.
    """
    environment = _environment_requirements()
    violations  = []

    for name, requirement in sorted(_pyproject_requirements().items()):
        required = _floor(requirement)
        if required is None:
            continue

        declared = _floor(environment[name]) if name in environment else None
        if declared is None:
            violations.append(
                f"{name}: environment.yml sets no floor, pyproject.toml "
                f"requires >={required}")
        elif declared < required:
            violations.append(
                f"{name}: environment.yml allows {declared}, pyproject.toml "
                f"requires >={required}")

    assert not violations, (
        "environment.yml floors must not admit versions pyproject.toml "
        "forbids:\n" + "\n".join(f"  {line}" for line in violations))
