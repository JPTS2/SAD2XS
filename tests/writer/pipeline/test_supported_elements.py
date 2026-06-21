"""
================================================================================
Tests for writer supported element policy
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
import xtrack as xt

import sad2xs as s2x
from sad2xs.config import Config

################################################################################
# Helpers
################################################################################
def _build_single_element_line(element, name):
    """
    Wrap a single element between start and end markers and attach an electron
    particle reference.
    """
    line = xt.Line(
        elements      = [xt.Marker(), element, xt.Marker()],
        element_names = ["start", name, "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    return line


def _write_only(line, tmp_path, filename):
    """
    Write lattice and optics files without reloading. Returns the output
    directory so callers can assert on file existence.
    """
    output_dir = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = filename,
        output_directory        = str(output_dir),
        output_header           = "Supported elements test",
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = f"{filename}_import_optics",
        output_directory  = str(output_dir),
        output_header     = "Supported elements test",
        config            = Config(_verbose = False))

    return output_dir


def _assert_file_exists_and_is_executable(output_dir, filename):
    """
    Assert that output_dir/filename.py exists and that calling it in a fresh
    Xsuite environment registers a line named 'line'. Calling each generated
    file verifies that the writer output is syntactically valid Python and
    that the element serialisation produces a loadable lattice.
    """
    output_path = output_dir / f"{filename}.py"

    assert output_path.exists(), (
        f"write_lattice should create the output file at {output_path}.")

    env = xt.Environment()
    env.call(str(output_path))

    assert "line" in env.lines, (
        f"Calling {output_path.name} should register a line named 'line' in "
        "the Xsuite environment. This fails if the serialised element is "
        "syntactically invalid or produces an unloadable lattice.")


################################################################################
# Supported Element Policy Tests
################################################################################
def test_supported_elements_writer_handles_drift(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.Drift element.
    """
    line       = _build_single_element_line(xt.Drift(length = 1.0), "d1")
    output_dir = _write_only(line, tmp_path, "drift")

    _assert_file_exists_and_is_executable(output_dir, "drift")


def test_supported_elements_writer_handles_bend(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.Bend element classified as a dipole bend (angle set,
    h != 0).
    """
    line       = _build_single_element_line(xt.Bend(length = 0.5, angle = 0.1), "b1")
    output_dir = _write_only(line, tmp_path, "bend")

    _assert_file_exists_and_is_executable(output_dir, "bend")


def test_supported_elements_writer_handles_corrector(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.Bend element classified as a corrector (k0 set explicitly,
    h == 0).
    """
    line       = _build_single_element_line(xt.Bend(length = 0.3, k0 = 1.0E-4), "c1")
    output_dir = _write_only(line, tmp_path, "corrector")

    _assert_file_exists_and_is_executable(output_dir, "corrector")


def test_supported_elements_writer_handles_quadrupole(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.Quadrupole element.
    """
    line       = _build_single_element_line(xt.Quadrupole(length = 0.5, k1 = 0.2), "q1")
    output_dir = _write_only(line, tmp_path, "quadrupole")

    _assert_file_exists_and_is_executable(output_dir, "quadrupole")


def test_supported_elements_writer_handles_sextupole(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.Sextupole element.
    """
    line       = _build_single_element_line(xt.Sextupole(length = 0.4, k2 = 0.3), "s1")
    output_dir = _write_only(line, tmp_path, "sextupole")

    _assert_file_exists_and_is_executable(output_dir, "sextupole")


def test_supported_elements_writer_handles_octupole(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.Octupole element.
    """
    line       = _build_single_element_line(xt.Octupole(length = 0.3, k3 = 0.4), "o1")
    output_dir = _write_only(line, tmp_path, "octupole")

    _assert_file_exists_and_is_executable(output_dir, "octupole")


def test_supported_elements_writer_handles_multipole(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.Multipole element.
    """
    line = _build_single_element_line(
        xt.Multipole(knl = [0.0, 0.1], ksl = [0.0, -0.05]), "m1")
    output_dir = _write_only(line, tmp_path, "multipole")

    _assert_file_exists_and_is_executable(output_dir, "multipole")


def test_supported_elements_writer_handles_solenoid(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.UniformSolenoid element.
    """
    line       = _build_single_element_line(xt.UniformSolenoid(length = 0.7, ks = 0.08), "sol1")
    output_dir = _write_only(line, tmp_path, "solenoid")

    _assert_file_exists_and_is_executable(output_dir, "solenoid")


def test_supported_elements_writer_handles_cavity(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.Cavity element.
    """
    line = _build_single_element_line(
        xt.Cavity(voltage = 3.0E6, frequency = 4.0E8, lag = 5.0), "cav1")
    output_dir = _write_only(line, tmp_path, "cavity")

    _assert_file_exists_and_is_executable(output_dir, "cavity")


def test_supported_elements_writer_handles_translation(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.Translation element.
    """
    line       = _build_single_element_line(xt.Translation(shift_x = 1.0E-3, shift_y = -2.0E-3), "shift1")
    output_dir = _write_only(line, tmp_path, "translation")

    _assert_file_exists_and_is_executable(output_dir, "translation")


def test_supported_elements_writer_handles_timedelay(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.TimeDelay element.
    """
    line       = _build_single_element_line(xt.TimeDelay(shift_zeta = 3.0E-3), "zshift1")
    output_dir = _write_only(line, tmp_path, "timedelay")

    _assert_file_exists_and_is_executable(output_dir, "timedelay")


def test_supported_elements_writer_handles_rotation(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.Rotation element.
    """
    line       = _build_single_element_line(xt.Rotation(rot_y_rad = 1.25), "rot1")
    output_dir = _write_only(line, tmp_path, "rotation")

    _assert_file_exists_and_is_executable(output_dir, "rotation")


def test_supported_elements_writer_handles_limit_rect(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.LimitRect element.
    """
    line = _build_single_element_line(
        xt.LimitRect(min_x = -1.0, max_x = 2.0, min_y = -3.0, max_y = 4.0), "rect1")
    output_dir = _write_only(line, tmp_path, "limit_rect")

    _assert_file_exists_and_is_executable(output_dir, "limit_rect")


def test_supported_elements_writer_handles_limit_ellipse(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains an xt.LimitEllipse element.
    """
    line       = _build_single_element_line(xt.LimitEllipse(a = 1.0, b = 2.0), "ellipse1")
    output_dir = _write_only(line, tmp_path, "limit_ellipse")

    _assert_file_exists_and_is_executable(output_dir, "limit_ellipse")


def test_supported_elements_writer_handles_marker(tmp_path):
    """
    write_lattice should produce an executable lattice file when the line
    contains only xt.Marker elements.
    """
    line       = _build_single_element_line(xt.Marker(), "mk1")
    output_dir = _write_only(line, tmp_path, "marker")

    _assert_file_exists_and_is_executable(output_dir, "marker")
