"""
================================================================================
Tests for Dockerfile build contracts
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
from pathlib import Path

################################################################################
# Paths
################################################################################
REPO_ROOT       = Path(__file__).resolve().parents[2]
DOCKERFILE_PATH = REPO_ROOT / "Dockerfile"

################################################################################
# Helpers
################################################################################
def _builder_stage() -> str:
    """
    Return the Dockerfile text belonging to the builder stage.

    SAD is compiled in `builder`; `runtime` only receives the built tree. A
    package satisfying the build must therefore appear in the first stage,
    and finding it anywhere in the file would not prove that.
    """
    text   = DOCKERFILE_PATH.read_text(encoding = "utf-8")
    stages = text.split("FROM ")
    for stage in stages:
        if stage.startswith("ubuntu:24.04 AS builder"):
            return stage
    raise AssertionError("Dockerfile has no `FROM ubuntu:24.04 AS builder` stage.")

################################################################################
# Generated parser source
################################################################################
def test_builder_stage_installs_yacc():
    """
    The builder must install bison, which supplies yacc.

    Upstream SAD tracks both `src/calc.y` and the generated `src/calc.c`, and
    make's builtin `.y -> .c` rule fires whenever `calc.y` is the newer file.
    A shallow clone sets the two mtimes in write order, so whether the rule
    fires is a coin flip. Without yacc the build then dies at random, which
    reads as a fluke or as the fault of whichever branch was building.

    Layer caching hid this most of the time, so it only appeared on a cold
    cache. Nightly builds run cold far more often.
    """
    assert "bison" in _builder_stage(), (
        "The Dockerfile builder stage must install bison, so make can "
        "regenerate src/calc.c from src/calc.y when it decides to.")
