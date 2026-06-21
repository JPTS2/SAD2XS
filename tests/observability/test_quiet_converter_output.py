"""
================================================================================
Tests for SAD2XS converter quiet-mode output control
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

import sad2xs as s2x

################################################################################
# Helpers
################################################################################
def _write_minimal_lattice(tmp_path):
    """
    Write a minimal single-drift SAD lattice and return its path. Sufficient
    for the converter to run without invoking the SAD executable.
    """
    lattice_path = tmp_path / "observ_lattice.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        DRIFT       OBS_DRIFT   = (L = 1.0);

        MARK        START       = ()
                    END         = ();

        LINE        RING        = (START OBS_DRIFT END);
        """))
    return lattice_path


################################################################################
# Quiet mode — _verbose=False
################################################################################
def test_converter_produces_no_stdout_when_verbose_is_false(capsys, tmp_path):
    """
    With _verbose=False the converter should write nothing to stdout. Users who
    embed sad2xs in scripts or pipelines rely on quiet mode to prevent
    unintended output.
    """
    lattice_path = _write_minimal_lattice(tmp_path)

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _verbose         = False,
        _test_mode       = True)

    captured = capsys.readouterr()
    assert captured.out == "", (
        "convert_sad_to_xsuite with _verbose=False should produce no stdout. "
        f"Got: {captured.out!r}")


def test_converter_produces_no_stderr_when_verbose_is_false(capsys, tmp_path):
    """
    With _verbose=False the converter should write nothing to stderr either.
    """
    lattice_path = _write_minimal_lattice(tmp_path)

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _verbose         = False,
        _test_mode       = True)

    captured = capsys.readouterr()
    assert captured.err == "", (
        "convert_sad_to_xsuite with _verbose=False should produce no stderr. "
        f"Got: {captured.err!r}")


################################################################################
# Verbose mode — _verbose=True
################################################################################
def test_converter_produces_stdout_when_verbose_is_true(capsys, tmp_path):
    """
    With _verbose=True the converter should produce output to stdout. This test
    guards against a regression where verbose output is accidentally removed or
    silenced unconditionally.
    """
    lattice_path = _write_minimal_lattice(tmp_path)

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _verbose         = True,
        _test_mode       = True)

    captured = capsys.readouterr()
    assert len(captured.out) > 0, (
        "convert_sad_to_xsuite with _verbose=True should produce stdout output.")
