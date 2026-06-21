"""
================================================================================
Tests for the write_optics entry point
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
def _build_quad_line(k1 = 0.2):
    """
    Build a line containing a single quadrupole with the given k1 value,
    surrounded by start and end markers.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.Quadrupole(length = 0.5, k1 = k1), xt.Marker()],
        element_names = ["start", "q1", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    return line


def _write_optics_only(line, tmp_path, filename, header = "Optics writer test"):
    """
    Write both the lattice and optics files and return (output_dir,
    optics_path) so callers can inspect the optics file directly without
    performing a full environment reload.
    """
    output_dir   = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = filename,
        output_directory        = str(output_dir),
        output_header           = header,
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    optics_filename = f"{filename}_import_optics"

    s2x.write_optics(
        line              = line,
        output_filename   = optics_filename,
        output_directory  = str(output_dir),
        output_header     = header,
        config            = Config(_verbose = False))

    return output_dir, output_dir / f"{optics_filename}.py"


################################################################################
# write_optics Tests
################################################################################
def test_optics_writer_creates_output_file(tmp_path):
    """
    write_optics should create a file at output_directory/output_filename.py.
    """
    line              = _build_quad_line()
    _, optics_path    = _write_optics_only(line, tmp_path, "test_optics")

    assert optics_path.exists(), (
        f"write_optics should create the output file at {optics_path}.")


def test_optics_writer_header_is_written_to_file(tmp_path):
    """
    The output_header string passed to write_optics should appear verbatim in
    the body of the created optics file.
    """
    header            = "My custom optics header string"
    line              = _build_quad_line()
    _, optics_path    = _write_optics_only(line, tmp_path, "test_optics", header = header)

    content = optics_path.read_text(encoding = "utf-8")
    assert header in content, (
        f"The output_header '{header}' should appear in the written optics "
        f"file. File content starts with: {content[:200]!r}.")


def test_optics_writer_writes_k1_variable_for_nonzero_strength_quadrupole(tmp_path):
    """
    For a quadrupole with k1 != 0, write_optics should write a named optics
    variable 'k1_{element_name}' to the optics file.
    """
    line              = _build_quad_line(k1 = 0.2)
    _, optics_path    = _write_optics_only(line, tmp_path, "test_optics")

    content = optics_path.read_text(encoding = "utf-8")
    assert "k1_q1" in content, (
        "write_optics should write 'k1_q1' to the optics file for a "
        f"quadrupole with k1 = 0.2. File content: {content!r}.")


def test_optics_writer_does_not_write_k1_variable_for_zero_strength_quadrupole(tmp_path):
    """
    For a quadrupole with k1 == 0, write_optics should not write a 'k1_{name}'
    variable to the optics file. The variable is skipped; it resolves to 0 via
    the default_to_zero mechanism in the optics file header.
    """
    line              = _build_quad_line(k1 = 0.0)
    _, optics_path    = _write_optics_only(line, tmp_path, "test_optics")

    content = optics_path.read_text(encoding = "utf-8")
    assert "k1_q1" not in content, (
        "write_optics should not write 'k1_q1' for a quadrupole with k1 = 0. "
        f"Found it in file content: {content!r}.")


def test_optics_writer_output_is_executable_python(tmp_path):
    """
    The optics file produced by write_optics should be callable via env.call()
    after the corresponding lattice file has been loaded, without raising an
    exception.
    """
    line = _build_quad_line()

    output_dir, optics_path = _write_optics_only(line, tmp_path, "test_optics")
    lattice_path            = output_dir / "test_optics.py"

    env = xt.Environment()
    env.call(str(lattice_path))
    env.call(str(optics_path))

    assert env["k1_q1"] is not None, (
        "After calling the optics file, 'k1_q1' should be accessible in "
        "the Xsuite environment.")
