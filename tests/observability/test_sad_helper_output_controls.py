"""
================================================================================
Tests for SAD helper output behaviour
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================

sad_helpers functions have no _verbose or quiet-mode parameter. All helpers
print diagnostic lines (e.g. "Creating SAD Command") unconditionally on every
call. The signature tests below assert that _verbose is absent — they will
fail if a parameter is added without corresponding quiet/verbose coverage being
written, which is the intended forcing function. The baseline output tests
document that output is currently unconditional and guard against it being
silenced without a controlled replacement.
"""
################################################################################
# Required Packages
################################################################################
import inspect
import textwrap

from sad2xs.sad_helpers import (
    chromaticity_sad,
    emit_sad,
    rebuild_sad_lattice,
    survey_sad,
    track_sad,
    transfer_matrix_sad,
    twiss_sad)

################################################################################
# Helpers
################################################################################
def _write_minimal_transfer_lattice(tmp_path):
    """
    Write a minimal SAD transfer-line lattice. Returns (filename, line_name)
    for use as twiss_sad / survey_sad arguments after monkeypatch.chdir.
    """
    lattice_path = tmp_path / "observ_helper_lattice.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        DRIFT       OBS_DRIFT   = (L = 1.0);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START OBS_DRIFT END);
        """))
    return lattice_path.name, "TEST_LINE"


################################################################################
# Output suppression gap — signature checks
################################################################################
def test_twiss_sad_has_no_verbose_parameter():
    """
    twiss_sad currently accepts no _verbose parameter. This test documents the
    absence of output suppression in the SAD helper layer. When a _verbose (or
    equivalent) parameter is added to twiss_sad, this test should be replaced
    by tests that verify quiet and verbose behaviour separately.
    """
    sig = inspect.signature(twiss_sad)
    assert "_verbose" not in sig.parameters, (
        "twiss_sad should not yet have a '_verbose' parameter. If it does, "
        "replace this test with quiet-mode and verbose-mode coverage.")


def test_survey_sad_has_no_verbose_parameter():
    """
    survey_sad currently accepts no _verbose parameter, documenting the same
    output-suppression gap as twiss_sad.
    """
    sig = inspect.signature(survey_sad)
    assert "_verbose" not in sig.parameters, (
        "survey_sad should not yet have a '_verbose' parameter. If it does, "
        "replace this test with quiet-mode and verbose-mode coverage.")


def test_emit_sad_has_no_verbose_parameter():
    """
    emit_sad currently accepts no _verbose parameter.
    """
    sig = inspect.signature(emit_sad)
    assert "_verbose" not in sig.parameters, (
        "emit_sad should not yet have a '_verbose' parameter. If it does, "
        "replace this test with quiet-mode and verbose-mode coverage.")


def test_chromaticity_sad_has_no_verbose_parameter():
    """
    chromaticity_sad currently accepts no _verbose parameter.
    """
    sig = inspect.signature(chromaticity_sad)
    assert "_verbose" not in sig.parameters, (
        "chromaticity_sad should not yet have a '_verbose' parameter. If it "
        "does, replace this test with quiet-mode and verbose-mode coverage.")


def test_transfer_matrix_sad_has_no_verbose_parameter():
    """
    transfer_matrix_sad currently accepts no _verbose parameter.
    """
    sig = inspect.signature(transfer_matrix_sad)
    assert "_verbose" not in sig.parameters, (
        "transfer_matrix_sad should not yet have a '_verbose' parameter. If it "
        "does, replace this test with quiet-mode and verbose-mode coverage.")


def test_track_sad_has_no_verbose_parameter():
    """
    track_sad currently accepts no _verbose parameter.
    """
    sig = inspect.signature(track_sad)
    assert "_verbose" not in sig.parameters, (
        "track_sad should not yet have a '_verbose' parameter. If it does, "
        "replace this test with quiet-mode and verbose-mode coverage.")


def test_rebuild_sad_lattice_has_no_verbose_parameter():
    """
    rebuild_sad_lattice currently accepts no _verbose parameter.
    """
    sig = inspect.signature(rebuild_sad_lattice)
    assert "_verbose" not in sig.parameters, (
        "rebuild_sad_lattice should not yet have a '_verbose' parameter. If it "
        "does, replace this test with quiet-mode and verbose-mode coverage.")


################################################################################
# Unconditional output — current behaviour baseline
################################################################################
def test_twiss_sad_produces_stdout_output(monkeypatch, capsys, tmp_path):
    """
    twiss_sad unconditionally prints diagnostic lines (e.g. "Creating SAD
    Command") on every call. This test documents that baseline so a future
    change that accidentally silences all output is caught.
    """
    monkeypatch.chdir(tmp_path)
    filename, line_name = _write_minimal_transfer_lattice(tmp_path)

    twiss_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        closed           = False)

    captured = capsys.readouterr()
    assert len(captured.out) > 0, (
        "twiss_sad should produce stdout output. sad_helpers currently have no "
        "output suppression — if this fails, something has silenced all output "
        "without providing a controlled quiet mode.")


def test_survey_sad_produces_stdout_output(monkeypatch, capsys, tmp_path):
    """
    survey_sad unconditionally prints diagnostic lines on every call. Same
    baseline documentation as test_twiss_sad_produces_stdout_output.
    """
    monkeypatch.chdir(tmp_path)
    filename, line_name = _write_minimal_transfer_lattice(tmp_path)

    survey_sad(
        lattice_filepath = filename,
        line_name        = line_name)

    captured = capsys.readouterr()
    assert len(captured.out) > 0, (
        "survey_sad should produce stdout output. sad_helpers currently have no "
        "output suppression.")
