"""
================================================================================
Tests for SAD helper output behaviour
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-20
================================================================================

See tests/observability/README.md ("test_sad_helper_output_controls.py") for
the single-mechanism design this file guards. Helper failures raise
RuntimeError with SAD's stdout/stderr embedded.
"""
################################################################################
# Required Packages
################################################################################
import inspect
import logging

import sad2xs  # noqa: F401  (installs the logging handler)
from tests.support.lattices import write_minimal_transfer_lattice
from sad2xs.sad_helpers import (
    chromaticity_sad,
    emit_sad,
    rebuild_sad_lattice,
    survey_sad,
    track_sad,
    transfer_matrix_sad,
    twiss_sad)

################################################################################
# Single output mechanism — signature checks
################################################################################
def test_twiss_sad_has_no_verbose_parameter():
    """
    Helper verbosity is controlled by sad2xs.set_log_level, not per-function
    parameters. A _verbose parameter on twiss_sad would mean a second,
    parallel output mechanism was introduced.
    """
    sig = inspect.signature(twiss_sad)
    assert "_verbose" not in sig.parameters, (
        "twiss_sad should not have a '_verbose' parameter: helper output is "
        "controlled by sad2xs.set_log_level.")


def test_survey_sad_has_no_verbose_parameter():
    """
    survey_sad output is controlled by sad2xs.set_log_level.
    """
    sig = inspect.signature(survey_sad)
    assert "_verbose" not in sig.parameters, (
        "survey_sad should not have a '_verbose' parameter: helper output is "
        "controlled by sad2xs.set_log_level.")


def test_emit_sad_has_no_verbose_parameter():
    """
    emit_sad output is controlled by sad2xs.set_log_level.
    """
    sig = inspect.signature(emit_sad)
    assert "_verbose" not in sig.parameters, (
        "emit_sad should not have a '_verbose' parameter: helper output is "
        "controlled by sad2xs.set_log_level.")


def test_chromaticity_sad_has_no_verbose_parameter():
    """
    chromaticity_sad output is controlled by sad2xs.set_log_level.
    """
    sig = inspect.signature(chromaticity_sad)
    assert "_verbose" not in sig.parameters, (
        "chromaticity_sad should not have a '_verbose' parameter: helper "
        "output is controlled by sad2xs.set_log_level.")


def test_transfer_matrix_sad_has_no_verbose_parameter():
    """
    transfer_matrix_sad output is controlled by sad2xs.set_log_level.
    """
    sig = inspect.signature(transfer_matrix_sad)
    assert "_verbose" not in sig.parameters, (
        "transfer_matrix_sad should not have a '_verbose' parameter: helper "
        "output is controlled by sad2xs.set_log_level.")


def test_track_sad_has_no_verbose_parameter():
    """
    track_sad output is controlled by sad2xs.set_log_level (the tqdm bar
    stays governed by with_progress).
    """
    sig = inspect.signature(track_sad)
    assert "_verbose" not in sig.parameters, (
        "track_sad should not have a '_verbose' parameter: helper output is "
        "controlled by sad2xs.set_log_level.")


def test_rebuild_sad_lattice_has_no_verbose_parameter():
    """
    rebuild_sad_lattice output is controlled by sad2xs.set_log_level.
    """
    sig = inspect.signature(rebuild_sad_lattice)
    assert "_verbose" not in sig.parameters, (
        "rebuild_sad_lattice should not have a '_verbose' parameter: helper "
        "output is controlled by sad2xs.set_log_level.")


################################################################################
# Quiet by default
################################################################################
def test_twiss_sad_is_silent_by_default(monkeypatch, capfd, tmp_path):
    """
    At the default level a successful twiss_sad call produces no terminal
    output at all.
    """
    monkeypatch.chdir(tmp_path)
    filename, line_name = write_minimal_transfer_lattice(tmp_path)

    twiss_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        closed           = False)

    captured = capfd.readouterr()
    assert captured.out == "", (
        f"twiss_sad should be silent by default. Got stdout: {captured.out!r}")
    assert captured.err == "", (
        f"twiss_sad should be silent by default. Got stderr: {captured.err!r}")


def test_survey_sad_is_silent_by_default(monkeypatch, capfd, tmp_path):
    """
    At the default level a successful survey_sad call produces no terminal
    output at all.
    """
    monkeypatch.chdir(tmp_path)
    filename, line_name = write_minimal_transfer_lattice(tmp_path)

    survey_sad(
        lattice_filepath = filename,
        line_name        = line_name)

    captured = capfd.readouterr()
    assert captured.out == "", (
        f"survey_sad should be silent by default. Got stdout: {captured.out!r}")
    assert captured.err == "", (
        f"survey_sad should be silent by default. Got stderr: {captured.err!r}")


################################################################################
# Debug narrative
################################################################################
def test_twiss_sad_logs_sad_output_at_debug_level(monkeypatch, caplog, tmp_path):
    """
    At debug level the helper narrative includes SAD's own terminal output,
    so degenerate-lattice diagnostics are recoverable without rerunning.
    """
    caplog.set_level(logging.DEBUG, logger = "sad2xs")
    monkeypatch.chdir(tmp_path)
    filename, line_name = write_minimal_transfer_lattice(tmp_path)

    twiss_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        closed           = False)

    messages = [r.getMessage() for r in caplog.records]
    assert any("Creating SAD command" in m for m in messages), (
        f"Expected the debug narrative. Got: {messages!r}")
    assert any("SAD twiss terminal output" in m for m in messages), (
        f"Expected SAD's terminal output in the debug records. "
        f"Got: {messages!r}")
