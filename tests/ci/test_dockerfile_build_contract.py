"""
================================================================================
Tests for Dockerfile build contracts
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-10-29
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import re
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


def _run_instruction(stage: str, text: str) -> str:
    """
    Return the RUN instruction in a stage that contains `text`.

    Continuation lines are joined, so the result is the whole instruction:
    the unit Docker caches as one layer.
    """
    instructions = []
    for line in stage.splitlines():
        if instructions and instructions[-1].endswith("\\"):
            instructions[-1] = instructions[-1][:-1] + " " + line.strip()
        elif not line.startswith("#"):
            instructions.append(line.strip())
    for instruction in instructions:
        if instruction.startswith("RUN ") and text in instruction:
            return instruction
    raise AssertionError(f"Dockerfile builder stage has no RUN containing {text!r}.")

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

################################################################################
# Build check
################################################################################
def test_builder_stage_checks_the_sad_binary():
    """
    The builder must check that SAD linked `sad1.exe`, not only `bin/gs`.

    `bin/gs` is a wrapper script tracked in the SAD repository, so it exists
    whether or not the build produced a binary. Checking it cannot fail.

    The check must share the build's RUN instruction. HostArch names the arch
    after the kernel, and a cached build layer may come from a runner on
    another kernel than the one running the check.
    """
    stage = _builder_stage()
    assert "sad1.exe" in _run_instruction(stage, "make -s exe"), (
        "The Dockerfile builder stage must check that obj/<arch>/sad1.exe is "
        "executable in the same RUN instruction as `make exe`.")
    assert "test -x /opt/sad/src/bin/gs" not in stage, (
        "The Dockerfile builder stage must not treat `bin/gs` as proof of a "
        "successful build: it is a tracked script that always exists.")

################################################################################
# Architecture pin
################################################################################
def test_builder_stage_pins_the_sad_arch_in_gs():
    """
    The builder must pin `SAD_ARCH` in `bin/gs` to the arch it built for.

    `bin/gs` runs `bin/HostArch` at every start, and HostArch names the arch
    after the kernel major version. A container shares the host kernel, so an
    image built on a Linux 6 runner looks for `obj/AMD64-Linux7` on a Linux 7
    runner and finds nothing.

    The pin must share the build's RUN instruction. Otherwise a pin layer
    rerun over a build layer cached on another kernel records the wrong arch.
    """
    build = _run_instruction(_builder_stage(), "make -s exe")
    assert re.search(r"sed -i \"s\|\^SAD_ARCH=.*\" bin/gs", build), (
        "The Dockerfile builder stage must rewrite the `SAD_ARCH=` line of "
        "bin/gs in the same RUN instruction as `make exe`.")
