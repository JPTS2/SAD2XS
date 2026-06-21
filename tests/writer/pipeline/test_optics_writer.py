"""
================================================================================
Tests for the write_optics entry point
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


def _build_optics_line(element, name):
    """
    Wrap a single Xsuite element between start and end markers and attach an
    electron particle reference. Used to build single-element lines for optics
    writer content tests.
    """
    line = xt.Line(
        elements      = [xt.Marker(), element, xt.Marker()],
        element_names = ["start", name, "end"])

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


def _optics_content(element, name, tmp_path):
    """
    Write a single-element optics line and return the text content of the
    generated optics file.
    """
    line = _build_optics_line(element, name)
    _, optics_path = _write_optics_only(line, tmp_path, "test_optics")
    return optics_path.read_text(encoding = "utf-8")


################################################################################
# write_optics Core Tests
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


################################################################################
# Quadrupole Optics Tests
################################################################################
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


def test_optics_writer_writes_k1s_variable_for_skew_quadrupole(tmp_path):
    """
    For a quadrupole with k1=0 and k1s != 0, write_optics should write a
    'k1s_{name}' variable and suppress 'k1_{name}'.
    """
    content = _optics_content(
        xt.Quadrupole(length = 0.5, k1 = 0.0, k1s = -0.05), "q1", tmp_path)

    assert "k1s_q1" in content, (
        "write_optics should write 'k1s_q1' for a quadrupole with k1s = -0.05. "
        f"File content: {content!r}.")
    assert "k1_q1" not in content, (
        "write_optics should not write 'k1_q1' when k1 = 0. "
        f"File content: {content!r}.")


################################################################################
# Bend Optics Tests
################################################################################
def test_optics_writer_writes_k0_variable_for_nonzero_bend(tmp_path):
    """
    For a bend with angle != 0 (h != 0), write_optics should write a
    'k0_{element_name}' variable to the optics file.
    """
    content = _optics_content(
        xt.Bend(length = 1.0, angle = 0.1), "b1", tmp_path)

    assert "k0_b1" in content, (
        "write_optics should write 'k0_b1' for a bend with angle = 0.1. "
        f"File content: {content!r}.")


################################################################################
# Corrector Optics Tests
################################################################################
def test_optics_writer_writes_k0_variable_for_nonzero_corrector(tmp_path):
    """
    For a corrector (Bend with h=0 and k0 != 0), write_optics should write a
    'k0_{element_name}' variable to the optics file.
    """
    content = _optics_content(
        xt.Bend(length = 0.3, k0 = 1.0E-4), "c1", tmp_path)

    assert "k0_c1" in content, (
        "write_optics should write 'k0_c1' for a corrector with k0 = 1e-4. "
        f"File content: {content!r}.")


def test_optics_writer_does_not_write_k0_for_zero_strength_corrector(tmp_path):
    """
    For a corrector with k0 == 0, write_optics should not write a 'k0_{name}'
    variable. Zero corrector strengths are suppressed in the optics file.
    """
    content = _optics_content(
        xt.Bend(length = 0.3, k0 = 0.0), "c1", tmp_path)

    assert "k0_c1" not in content, (
        "write_optics should not write 'k0_c1' for a corrector with k0 = 0. "
        f"File content: {content!r}.")


################################################################################
# Sextupole Optics Tests
################################################################################
def test_optics_writer_writes_k2_variable_for_nonzero_sextupole(tmp_path):
    """
    For a sextupole with k2 != 0, write_optics should write a 'k2_{name}'
    variable to the optics file.
    """
    content = _optics_content(
        xt.Sextupole(length = 0.4, k2 = 0.3), "s1", tmp_path)

    assert "k2_s1" in content, (
        "write_optics should write 'k2_s1' for a sextupole with k2 = 0.3. "
        f"File content: {content!r}.")


def test_optics_writer_does_not_write_k2_for_zero_strength_sextupole(tmp_path):
    """
    For a sextupole with k2 == 0, write_optics should not write a 'k2_{name}'
    variable. Zero sextupole strengths are suppressed in the optics file.
    """
    content = _optics_content(
        xt.Sextupole(length = 0.4, k2 = 0.0), "s1", tmp_path)

    assert "k2_s1" not in content, (
        "write_optics should not write 'k2_s1' for a sextupole with k2 = 0. "
        f"File content: {content!r}.")


def test_optics_writer_writes_k2s_variable_for_skew_sextupole(tmp_path):
    """
    For a sextupole with k2=0 and k2s != 0, write_optics should write
    'k2s_{name}' and suppress 'k2_{name}'.
    """
    content = _optics_content(
        xt.Sextupole(length = 0.4, k2 = 0.0, k2s = -0.04), "s1", tmp_path)

    assert "k2s_s1" in content, (
        "write_optics should write 'k2s_s1' for a sextupole with k2s = -0.04. "
        f"File content: {content!r}.")
    assert "k2_s1" not in content, (
        "write_optics should not write 'k2_s1' when k2 = 0. "
        f"File content: {content!r}.")


################################################################################
# Octupole Optics Tests
################################################################################
def test_optics_writer_writes_k3_variable_for_nonzero_octupole(tmp_path):
    """
    For an octupole with k3 != 0, write_optics should write a 'k3_{name}'
    variable to the optics file.
    """
    content = _optics_content(
        xt.Octupole(length = 0.3, k3 = 0.4), "o1", tmp_path)

    assert "k3_o1" in content, (
        "write_optics should write 'k3_o1' for an octupole with k3 = 0.4. "
        f"File content: {content!r}.")


def test_optics_writer_does_not_write_k3_for_zero_strength_octupole(tmp_path):
    """
    For an octupole with k3 == 0, write_optics should not write a 'k3_{name}'
    variable. Zero octupole strengths are suppressed in the optics file.
    """
    content = _optics_content(
        xt.Octupole(length = 0.3, k3 = 0.0), "o1", tmp_path)

    assert "k3_o1" not in content, (
        "write_optics should not write 'k3_o1' for an octupole with k3 = 0. "
        f"File content: {content!r}.")


def test_optics_writer_writes_k3s_variable_for_skew_octupole(tmp_path):
    """
    For an octupole with k3=0 and k3s != 0, write_optics should write
    'k3s_{name}' and suppress 'k3_{name}'.
    """
    content = _optics_content(
        xt.Octupole(length = 0.3, k3 = 0.0, k3s = -0.05), "o1", tmp_path)

    assert "k3s_o1" in content, (
        "write_optics should write 'k3s_o1' for an octupole with k3s = -0.05. "
        f"File content: {content!r}.")
    assert "k3_o1" not in content, (
        "write_optics should not write 'k3_o1' when k3 = 0. "
        f"File content: {content!r}.")


################################################################################
# Cavity Optics Tests
################################################################################
def test_optics_writer_writes_freq_volt_lag_variables_for_cavity(tmp_path):
    """
    For a cavity, write_optics should always write all three optics variables:
    'freq_{name}', 'volt_{name}', and 'lag_{name}'. Cavity parameters are
    never suppressed even when they take default values.
    """
    content = _optics_content(
        xt.Cavity(voltage = 3.0E6, frequency = 4.0E8, lag = 5.0), "cav1", tmp_path)

    for var in ("freq_cav1", "volt_cav1", "lag_cav1"):
        assert var in content, (
            f"write_optics should write '{var}' to the optics file for a "
            f"cavity. File content: {content!r}.")


################################################################################
# Translation Optics Tests
################################################################################
def test_optics_writer_writes_dx_and_dy_for_nonzero_translation(tmp_path):
    """
    For a Translation with both shift_x != 0 and shift_y != 0, write_optics
    should write 'dx_{name}' and 'dy_{name}' to the optics file.
    """
    content = _optics_content(
        xt.Translation(shift_x = 1.0E-3, shift_y = -2.0E-3), "shift1", tmp_path)

    assert "dx_shift1" in content, (
        "write_optics should write 'dx_shift1' for a Translation with shift_x = 1e-3. "
        f"File content: {content!r}.")
    assert "dy_shift1" in content, (
        "write_optics should write 'dy_shift1' for a Translation with shift_y = -2e-3. "
        f"File content: {content!r}.")


def test_optics_writer_does_not_write_dx_for_zero_shift_x_translation(tmp_path):
    """
    For a Translation with shift_x=0, write_optics should suppress 'dx_{name}'
    while still writing 'dy_{name}' when shift_y != 0.
    """
    content = _optics_content(
        xt.Translation(shift_x = 0.0, shift_y = -2.0E-3), "shift1", tmp_path)

    assert "dx_shift1" not in content, (
        "write_optics should not write 'dx_shift1' when shift_x = 0. "
        f"File content: {content!r}.")
    assert "dy_shift1" in content, (
        "write_optics should still write 'dy_shift1' when shift_y = -2e-3. "
        f"File content: {content!r}.")


################################################################################
# TimeDelay Optics Tests
################################################################################
def test_optics_writer_writes_dz_for_nonzero_timedelay(tmp_path):
    """
    For a TimeDelay with shift_zeta != 0, write_optics should write a
    'dz_{name}' variable to the optics file.
    """
    content = _optics_content(
        xt.TimeDelay(shift_zeta = 3.0E-3), "zshift1", tmp_path)

    assert "dz_zshift1" in content, (
        "write_optics should write 'dz_zshift1' for a TimeDelay with "
        f"shift_zeta = 3e-3. File content: {content!r}.")


################################################################################
# Rotation Optics Tests
################################################################################
def test_optics_writer_writes_chi2_for_nonzero_xrotation(tmp_path):
    """
    For an XRotation with angle != 0, write_optics should write a
    'chi2_{name}' variable to the optics file.
    """
    content = _optics_content(
        xt.XRotation(angle = 1.25), "xrot1", tmp_path)

    assert "chi2_xrot1" in content, (
        "write_optics should write 'chi2_xrot1' for an XRotation with "
        f"angle = 1.25. File content: {content!r}.")


def test_optics_writer_writes_chi1_for_nonzero_yrotation(tmp_path):
    """
    For a YRotation with angle != 0, write_optics should write a
    'chi1_{name}' variable to the optics file.
    """
    content = _optics_content(
        xt.YRotation(angle = -1.25), "yrot1", tmp_path)

    assert "chi1_yrot1" in content, (
        "write_optics should write 'chi1_yrot1' for a YRotation with "
        f"angle = -1.25. File content: {content!r}.")


def test_optics_writer_writes_chi3_for_nonzero_srotation(tmp_path):
    """
    For an SRotation with angle != 0, write_optics should write a
    'chi3_{name}' variable to the optics file.
    """
    content = _optics_content(
        xt.SRotation(angle = 0.75), "srot1", tmp_path)

    assert "chi3_srot1" in content, (
        "write_optics should write 'chi3_srot1' for an SRotation with "
        f"angle = 0.75. File content: {content!r}.")
