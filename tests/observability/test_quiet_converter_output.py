"""
================================================================================
Tests for SAD2XS converter output control
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-04
================================================================================

Output policy: errors are raised, warnings are always shown, progress (INFO)
and detail (DEBUG) are opt-in via _verbose=True or sad2xs.set_log_level. A
clean conversion at the default level is completely silent.
"""
################################################################################
# Required Packages
################################################################################
import logging
import textwrap

import pytest

import sad2xs as s2x
from sad2xs._logging import _SAD2XSFormatter

################################################################################
# Helpers
################################################################################
def _write_fully_specified_lattice(tmp_path):
    """
    Write a SAD lattice that triggers no converter warnings: mass, momentum
    and charge are all defined, and the solenoid pair has DISFRIN=1. The
    solenoid pair and the offset marker matter: they drive the solenoid
    correction stages and the generated-file marker installation (including
    xtrack's replace_all_repeated_elements on reload), which historically
    leaked progress bars in quiet mode.
    """
    lattice_path = tmp_path / "observ_silent_lattice.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;
        MASS        = 0.51099895069 MEV;
        CHARGE      = -1;

        DRIFT       OBS_DRIFT   = (L = 1.0);
        SOL         SOL_IN      = (BZ = 0.1 BOUND = 1 GEO = 1 DISFRIN = 1)
                    SOL_OUT     = (BZ = 0.1 BOUND = 1 DISFRIN = 1);

        MARK        START       = ()
                    M_OFF       = (OFFSET = 0.5)
                    END         = ();

        LINE        RING        = (START SOL_IN M_OFF OBS_DRIFT SOL_OUT END);
        """))
    return lattice_path


def _write_minimal_lattice(tmp_path):
    """
    Write a minimal single-drift SAD lattice with no MASS or CHARGE globals,
    so the parser emits its default-assumption warnings.
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
# Quiet by default — full pipeline
################################################################################
def test_full_conversion_is_silent_by_default(capfd, tmp_path):
    """
    A warning-free conversion through the full pipeline (parser, converter,
    solenoid stages, writer, and reload of the generated files) must produce
    no terminal output at the default level. This covers the historical
    quiet-mode leaks: tqdm bars in the solenoid reference shift stage and
    xt.get_environment(verbose=True) in the generated files.
    """
    lattice_path = _write_fully_specified_lattice(tmp_path)
    output_dir   = tmp_path / "out"
    output_dir.mkdir()

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        line_name        = "RING")

    captured = capfd.readouterr()
    assert captured.out == "", (
        f"Default conversion should produce no stdout. Got: {captured.out!r}")
    assert captured.err == "", (
        f"Default conversion should produce no stderr. Got: {captured.err!r}")


def test_quiet_mode_emits_no_progress_records(caplog, tmp_path):
    """
    With the default level, no INFO or DEBUG log records are emitted.
    """
    lattice_path = _write_minimal_lattice(tmp_path)

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _test_mode       = True)

    progress_records = [
        r for r in caplog.records if r.levelno < logging.WARNING]
    assert progress_records == [], (
        "Default conversion should emit no progress/debug records. "
        f"Got: {[r.getMessage() for r in progress_records]!r}")


################################################################################
# Warnings survive quiet mode
################################################################################
def test_parser_warnings_visible_at_default_level(caplog, tmp_path):
    """
    A lattice with no MASS global makes the parser assume the electron mass.
    That assumption must be warned about even at the default (quiet) level.
    """
    lattice_path = _write_minimal_lattice(tmp_path)

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _test_mode       = True)

    mass_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "mass" in r.getMessage().lower()]
    assert len(mass_warnings) >= 1, (
        "The electron-mass assumption should be warned about in quiet mode. "
        f"Got records: {[r.getMessage() for r in caplog.records]!r}")


################################################################################
# Verbose mode — _verbose=True
################################################################################
def test_verbose_enables_progress_narrative(caplog, capsys, tmp_path):
    """
    _verbose=True raises the level to INFO and the conversion narrative is
    emitted as log records. Nothing is written to stdout: all diagnostics go
    through logging (to stderr), leaving stdout for user data.
    """
    lattice_path = _write_minimal_lattice(tmp_path)

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _verbose         = True,
        _test_mode       = True)

    info_records = [
        r for r in caplog.records if r.levelno == logging.INFO]
    assert info_records != [], (
        "_verbose=True should emit INFO progress records.")

    captured = capsys.readouterr()
    assert captured.out == "", (
        f"Diagnostics should never go to stdout. Got: {captured.out!r}")


################################################################################
# Debug level — set_log_level
################################################################################
def test_set_log_level_debug_enables_debug_records(caplog, tmp_path):
    """
    set_log_level("debug") exposes the per-element detail records.
    """
    lattice_path = _write_minimal_lattice(tmp_path)

    s2x.set_log_level("debug")
    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _test_mode       = True)

    debug_records = [
        r for r in caplog.records if r.levelno == logging.DEBUG]
    assert debug_records != [], (
        "set_log_level('debug') should emit DEBUG records.")


def test_set_log_level_rejects_unknown_level():
    """
    set_log_level validates its argument.
    """
    with pytest.raises(ValueError, match = "Unknown log level"):
        s2x.set_log_level("loud")


################################################################################
# Formatter contract
################################################################################
def test_formatter_prefixes_warnings_but_not_narrative():
    """
    Warnings and errors carry the "SAD2XS <LEVEL>:" prefix so they stand out;
    the INFO narrative is unprefixed, matching the historical print output.
    """
    formatter = _SAD2XSFormatter()

    def _record(level, message):
        return logging.LogRecord(
            name     = "sad2xs.test",
            level    = level,
            pathname = __file__,
            lineno   = 0,
            msg      = message,
            args     = None,
            exc_info = None)

    assert formatter.format(_record(logging.WARNING, "careful")) == \
        "SAD2XS WARNING: careful"
    assert formatter.format(_record(logging.ERROR, "broken")) == \
        "SAD2XS ERROR: broken"
    assert formatter.format(_record(logging.INFO, "progress")) == "progress"
    assert formatter.format(_record(logging.DEBUG, "detail")) == "detail"
