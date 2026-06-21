"""
================================================================================
Tests for sad2xs.sad_helpers.rebuild lattice
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import textwrap

import pytest

from sad2xs.sad_helpers import rebuild_sad_lattice

################################################################################
# Helpers
################################################################################
def _write_minimal_transfer_lattice(tmp_path):
    """
    Write a minimal SAD transfer-line lattice consisting of a single 1 m drift
    between a START and END marker. Returns (filename, line_name) for direct
    use as rebuild_sad_lattice arguments after monkeypatch.chdir(tmp_path).
    """
    lattice_path = tmp_path / "test_lattice.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_DRIFT  = (L = 1.0);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT END);
        """))

    return lattice_path.name, "TEST_LINE"


def _run_rebuild(tmp_path, monkeypatch, **kwargs):
    """
    Write the minimal transfer-line lattice, change to its directory, and run
    rebuild_sad_lattice with wall_time=30. Extra keyword arguments are forwarded
    to rebuild_sad_lattice (e.g. output_filepath, additional_commands).
    """
    filename, line_name = _write_minimal_transfer_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    rebuild_sad_lattice(
        lattice_filepath = filename,
        line_name        = line_name,
        wall_time        = 30,
        **kwargs)

    return filename, line_name


################################################################################
# rebuild_sad_lattice Smoke Tests (SAD required)
################################################################################
def test_rebuild_sad_lattice_runs_without_error(tmp_path, monkeypatch):
    """
    rebuild_sad_lattice should run SAD on a minimal transfer-line lattice and
    return without raising an exception.
    """
    _run_rebuild(
        tmp_path, monkeypatch,
        output_filepath = "test_lattice_out.sad")


def test_rebuild_sad_lattice_creates_output_file(tmp_path, monkeypatch):
    """
    rebuild_sad_lattice should create the file at output_filepath. This
    confirms that the SAD WriteBeamLine command ran and that the output file
    path is passed correctly into the SAD command.
    """
    output = "test_lattice_out.sad"
    _run_rebuild(tmp_path, monkeypatch, output_filepath = output)

    assert (tmp_path / output).exists(), (
        f"rebuild_sad_lattice should create the output file '{output}'. "
        "File was not found after the function returned.")


def test_rebuild_sad_lattice_default_output_filepath_creates_rebuilt_file(
        tmp_path,
        monkeypatch):
    """
    With output_filepath=None, rebuild_sad_lattice should write to
    '{input}_rebuilt.sad' (replacing '.sad' with '_rebuilt.sad'). This
    confirms the default path logic is wired into the SAD command correctly.
    """
    _run_rebuild(tmp_path, monkeypatch, output_filepath = None)

    assert (tmp_path / "test_lattice_rebuilt.sad").exists(), (
        "rebuild_sad_lattice with output_filepath=None should create "
        "'test_lattice_rebuilt.sad'. File was not found after the function "
        "returned.")


def test_rebuild_sad_lattice_output_contains_momentum_declaration(
        tmp_path,
        monkeypatch):
    """
    The rebuilt lattice file should contain a MOMENTUM declaration. This is
    written by the SAD command via WriteString[of, "MOMENTUM = "//MOMENTUM//";"].
    Its absence indicates a SAD output format change or a command failure.
    """
    output = "test_lattice_out.sad"
    _run_rebuild(tmp_path, monkeypatch, output_filepath = output)

    content = (tmp_path / output).read_text()

    assert "MOMENTUM" in content, (
        "Rebuilt lattice file should contain a MOMENTUM declaration. "
        f"File content (first 500 chars): {content[:500]!r}.")


def test_rebuild_sad_lattice_output_contains_line_name(tmp_path, monkeypatch):
    """
    The rebuilt lattice file should contain the beamline name 'TEST_LINE', as
    written by WriteBeamLine with Name->{"TEST_LINE"}. Its absence indicates
    that WriteBeamLine did not execute or that the Name argument is not
    forwarded.
    """
    output = "test_lattice_out.sad"
    _run_rebuild(tmp_path, monkeypatch, output_filepath = output)

    content = (tmp_path / output).read_text()

    assert "TEST_LINE" in content, (
        "Rebuilt lattice file should contain the beamline name 'TEST_LINE'. "
        f"File content (first 500 chars): {content[:500]!r}.")


def test_rebuild_sad_lattice_additional_commands_accepted(tmp_path, monkeypatch):
    """
    rebuild_sad_lattice should accept a non-empty additional_commands string
    and run without error. The command is inserted verbatim into the SAD script
    before INS/CALC; this confirms the injection is syntactically valid.
    """
    _run_rebuild(
        tmp_path, monkeypatch,
        output_filepath     = "test_lattice_out.sad",
        additional_commands = "a = 1")
