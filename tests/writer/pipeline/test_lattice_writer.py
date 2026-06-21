"""
================================================================================
Tests for the write_lattice entry point
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
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

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

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
        "write_lattice should create a file named 'my_lattice.py' when "
        "output_filename='my_lattice'.")
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
        f"The output_header '{header}' should appear in the written lattice "
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
        "Calling the lattice file should register a line named 'line' in "
        "the Xsuite environment.")
