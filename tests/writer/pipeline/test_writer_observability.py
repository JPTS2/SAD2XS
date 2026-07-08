"""
================================================================================
Tests for writer output reporting
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-04
================================================================================

The writer must never silently lose data: elements whose type it cannot
represent are dropped from the generated lattice, and that drop must be
warned about. At INFO level the writer reports what it wrote and where.
"""
################################################################################
# Required Packages
################################################################################
import logging

import xtrack as xt

import sad2xs as s2x
from sad2xs.config import Config

################################################################################
# Helpers
################################################################################
def _build_line(elements, element_names):
    """
    Build an Xsuite line with an electron reference particle.
    """
    line = xt.Line(elements = elements, element_names = element_names)

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _write_files(line, tmp_path):
    """
    Write lattice and optics files. Returns the output directory.
    """
    output_dir = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = "Writer observability test",
        offset_marker_locations = None,
        config                  = Config())

    s2x.write_optics(
        line              = line,
        output_filename   = "test_lattice_import_optics",
        output_directory  = str(output_dir),
        output_header     = "Writer observability test",
        config            = Config())

    return output_dir


################################################################################
# Dropped Element Warning
################################################################################
def test_writer_warns_for_unsupported_element_types(tmp_path, caplog):
    """
    An element whose type is not writer-supported is dropped from the
    generated lattice. That data loss must be warned about, naming the type,
    even at the default (quiet) level.
    """
    line = _build_line(
        elements      = [
            xt.Marker(),
            xt.Drift(length = 1.0),
            xt.RFMultipole(knl = [0.01], frequency = 1.0E6),
            xt.Marker()],
        element_names = ["start", "d1", "rfm", "end"])

    output_dir = _write_files(line, tmp_path)

    dropped_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "RFMultipole" in r.getMessage()]
    assert len(dropped_warnings) == 1, (
        "Dropping an unsupported element should warn exactly once, naming "
        f"the type. Got records: {[r.getMessage() for r in caplog.records]!r}")
    assert "1 element(s)" in dropped_warnings[0].getMessage(), (
        "The dropped-element warning should state how many elements were "
        f"omitted. Got: {dropped_warnings[0].getMessage()!r}")

    env = xt.Environment()
    env.call(str(output_dir / "test_lattice.py"))
    reloaded_line = env.lines["line"]

    assert "rfm" not in reloaded_line.element_names, (
        "The unsupported element should be absent from the written lattice.")


def test_writer_does_not_warn_when_all_elements_supported(tmp_path, caplog):
    """
    Writing a fully supported line emits no warnings. This also guards the
    table end-point sentinel: it has an empty element type and must not be
    reported as a dropped element.
    """
    line = _build_line(
        elements      = [xt.Marker(), xt.Drift(length = 1.0), xt.Marker()],
        element_names = ["start", "d1", "end"])

    _write_files(line, tmp_path)

    warnings = [
        r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings == [], (
        "Writing a fully supported line should not warn. "
        f"Got: {[r.getMessage() for r in warnings]!r}")


################################################################################
# Written File Reporting
################################################################################
def test_writer_reports_written_files_at_info_level(tmp_path, caplog):
    """
    At INFO level the writer reports the path of each generated file and the
    element count of the written lattice.
    """
    caplog.set_level(logging.INFO, logger = "sad2xs")

    line = _build_line(
        elements      = [xt.Marker(), xt.Drift(length = 1.0), xt.Marker()],
        element_names = ["start", "d1", "end"])

    _write_files(line, tmp_path)

    messages = [r.getMessage() for r in caplog.records]
    assert any("Lattice file written" in m and "3 elements" in m
               for m in messages), (
        f"Expected a lattice-file summary record. Got: {messages!r}")
    assert any("Optics file written" in m for m in messages), (
        f"Expected an optics-file summary record. Got: {messages!r}")
