"""
================================================================================
Tests for the write_lattice entry point
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import xtrack as xt

import sad2xs as s2x
from sad2xs.config import Config

################################################################################
# Helpers
################################################################################
def _build_minimal_line():
    """
    Build a minimal two-marker line with an electron particle reference.
    Sufficient to exercise the write_lattice entry point without pulling in
    element-specific writer behaviour.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Marker()],
        element_names = ["start", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_external_line_without_writer_globals():
    """
    Build a generic Xsuite line that has a particle reference but no SAD2XS
    writer globals in the line environment.
    """
    line = xt.Line(
        elements      = [
            xt.Marker(),
            xt.Drift(length = 1.5),
            xt.Quadrupole(length = 0.75, k1 = 0.2),
            xt.Marker()],
        element_names = ["start", "d1", "q1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _write_lattice_only(line, tmp_path, filename, header = "Lattice writer test"):
    """
    Call write_lattice and return (output_dir, output_path) so callers can
    inspect the created file directly.
    """
    output_dir  = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = filename,
        output_directory        = str(output_dir),
        output_header           = header,
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    return output_dir, output_dir / f"{filename}.py"


def _build_line_with_length():
    """
    Build a line containing a 2 m drift so that line.get_length() returns a
    positive value. Used by offset-marker tests where the generated code calls
    line.get_length() to compute the remaining length before insertion.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Drift(length = 2.0), xt.Marker()],
        element_names = ["start", "d1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


################################################################################
# write_lattice Tests
################################################################################
def test_lattice_writer_creates_output_file(tmp_path):
    """
    write_lattice should create a file at output_directory/output_filename.py.
    """
    line              = _build_minimal_line()
    _, output_path    = _write_lattice_only(line, tmp_path, "test_lattice")

    assert output_path.exists(), (
        f"write_lattice should create the output file at {output_path}.")


def test_lattice_writer_output_file_has_correct_name(tmp_path):
    """
    The created file should be named exactly output_filename.py. A different
    filename should not exist alongside it.
    """
    line              = _build_minimal_line()
    output_dir, _     = _write_lattice_only(line, tmp_path, "my_lattice")

    assert (output_dir / "my_lattice.py").exists(), (
        "write_lattice should create a file named `my_lattice.py` when "
        "output_filename=`my_lattice`.")
    assert not (output_dir / "my_lattice").exists(), (
        "write_lattice should not create a file without the .py extension.")


def test_lattice_writer_header_is_written_to_file(tmp_path):
    """
    The output_header string passed to write_lattice should appear verbatim in
    the body of the created lattice file.
    """
    header            = "My custom lattice header string"
    line              = _build_minimal_line()
    _, output_path    = _write_lattice_only(line, tmp_path, "test_lattice", header = header)

    content = output_path.read_text(encoding = "utf-8")
    assert header in content, (
        f"The output_header `{header}` should appear in the written lattice "
        f"file. File content starts with: {content[:200]!r}.")


def test_lattice_writer_output_is_executable_python(tmp_path):
    """
    The lattice file produced by write_lattice should be callable via
    env.call() in a clean Xsuite environment without raising an exception.
    """
    line              = _build_minimal_line()
    _, output_path    = _write_lattice_only(line, tmp_path, "test_lattice")

    env = xt.Environment()
    env.call(str(output_path))

    assert "line" in env.lines, (
        "Calling the lattice file should register a line named `line` in "
        "the Xsuite environment.")


def test_lattice_writer_does_not_mutate_input_line(tmp_path):
    """
    write_lattice should derive missing writer globals from particle_ref
    without adding those variables to the caller's input line.
    """
    line = _build_external_line_without_writer_globals()

    for variable_name in ("p0c", "mass0", "q0", "fshift"):
        with pytest.raises(KeyError):
            line[variable_name]

    _write_lattice_only(line, tmp_path, "external_line")

    for variable_name in ("p0c", "mass0", "q0", "fshift"):
        with pytest.raises(KeyError):
            line[variable_name]


def test_lattice_writer_output_uses_particle_ref_without_mutating_line(tmp_path):
    """
    A line without writer globals should still produce a lattice file with
    globals derived from particle_ref.
    """
    line = _build_external_line_without_writer_globals()
    p0c   = float(line.particle_ref.p0c[0])
    mass0 = float(line.particle_ref.mass0)
    q0    = float(line.particle_ref.q0)
    _, output_path = _write_lattice_only(line, tmp_path, "external_line")

    content = output_path.read_text(encoding = "utf-8")

    assert f"""env["p0c"]      = {p0c}""" in content
    assert f"""env["mass0"]    = {mass0}""" in content
    assert f"""env["q0"]       = {q0}""" in content
    assert """env["fshift"]   = 0.0""" in content
    for variable_name in ("p0c", "mass0", "q0", "fshift"):
        with pytest.raises(KeyError):
            line[variable_name]


################################################################################
# write_lattice Offset Marker Tests
################################################################################
def test_lattice_writer_offset_markers_section_is_written(tmp_path):
    """
    When offset_marker_locations is a non-empty dict, write_lattice should
    include a MARKER_POSITIONS block in the output file, with the marker name
    and s-position listed. This tests the branch at the end of write_lattice
    that is skipped when offset_marker_locations=None.
    """
    line        = _build_line_with_length()
    output_dir  = tmp_path / "writer_output"
    output_dir.mkdir()
    output_path = output_dir / "test_lattice.py"

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = "Offset marker content test",
        offset_marker_locations = {"obs0": [1.0]},
        config                  = Config(_verbose = False))

    content = output_path.read_text(encoding = "utf-8")
    assert "MARKER_POSITIONS" in content, (
        "write_lattice with a non-empty offset_marker_locations should write "
        "a MARKER_POSITIONS block. File content starts with: "
        f"{content[:300]!r}.")
    assert "obs0" in content, (
        "write_lattice should include the marker name `obs0` inside the "
        "MARKER_POSITIONS block.")


def test_lattice_writer_empty_offset_markers_omits_section(tmp_path):
    """
    When offset_marker_locations is an empty dict, the offset markers writer
    short-circuits and returns an empty string, so no MARKER_POSITIONS block
    should appear in the output file.
    """
    line        = _build_line_with_length()
    output_dir  = tmp_path / "writer_output"
    output_dir.mkdir()
    output_path = output_dir / "test_lattice.py"

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = "Empty offset marker test",
        offset_marker_locations = {},
        config                  = Config(_verbose = False))

    content = output_path.read_text(encoding = "utf-8")
    assert "MARKER_POSITIONS" not in content, (
        "write_lattice with an empty offset_marker_locations dict should not "
        "write a MARKER_POSITIONS block. File content starts with: "
        f"{content[:300]!r}.")


def test_lattice_writer_offset_markers_output_is_executable(tmp_path):
    """
    A lattice file written with a non-empty offset_marker_locations and
    _install_offset_markers=False (dict-only form, no insertion code) should
    be callable via env.call() without raising an exception. This confirms
    that the MARKER_POSITIONS dict is syntactically valid Python and that
    line.get_length() is callable in the generated file context.
    """
    line        = _build_line_with_length()
    output_dir  = tmp_path / "writer_output"
    output_dir.mkdir()
    output_path = output_dir / "test_lattice.py"

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = "Offset marker executable test",
        offset_marker_locations = {"obs0": [1.0]},
        config                  = Config(_verbose = False, _install_offset_markers = False))

    env = xt.Environment()
    env.call(str(output_path))

    assert "line" in env.lines, (
        "Calling a lattice file written with offset_marker_locations should "
        "still register `line` in the Xsuite environment.")
