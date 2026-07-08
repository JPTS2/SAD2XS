"""
================================================================================
Tests for writer input-line preservation
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-08
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import xtrack as xt

import sad2xs as s2x
from sad2xs.config import Config

################################################################################
# Helpers
################################################################################
def _build_writer_preservation_line():
    """
    Build a line that exercises supported writer branches, including rotated
    bends and correctors with special explicit rotations.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Drift(length = 0.2),
            xt.Bend(
                length           = 1.0,
                angle            = 0.01,
                k1               = 0.002,
                edge_entry_angle = 0.001,
                edge_exit_angle  = -0.0015),
            xt.Bend(
                length           = 1.1,
                angle            = 0.011,
                edge_entry_angle = 0.0011,
                edge_exit_angle  = -0.0016,
                rot_s_rad        = np.pi),
            xt.Bend(
                length           = 1.2,
                angle            = 0.012,
                edge_entry_angle = 0.0012,
                edge_exit_angle  = -0.0017,
                rot_s_rad        = np.pi / 2),
            xt.Bend(
                length           = 1.3,
                angle            = 0.013,
                edge_entry_angle = 0.0013,
                edge_exit_angle  = -0.0018,
                rot_s_rad        = -np.pi / 2),
            xt.Bend(
                length           = 1.4,
                angle            = 0.014,
                edge_entry_angle = 0.0014,
                edge_exit_angle  = -0.0019,
                rot_s_rad        = np.pi / 4),
            xt.Bend(
                length           = 0.3,
                k0               = 1.0E-4,
                edge_entry_angle = 2.0E-4,
                edge_exit_angle  = -3.0E-4),
            xt.Bend(
                length           = 0.31,
                k0               = 1.1E-4,
                edge_entry_angle = 2.1E-4,
                edge_exit_angle  = -3.1E-4,
                rot_s_rad        = np.pi),
            xt.Bend(
                length           = 0.32,
                k0               = 1.2E-4,
                edge_entry_angle = 2.2E-4,
                edge_exit_angle  = -3.2E-4,
                rot_s_rad        = np.pi / 2),
            xt.Bend(
                length           = 0.33,
                k0               = 1.3E-4,
                edge_entry_angle = 2.3E-4,
                edge_exit_angle  = -3.3E-4,
                rot_s_rad        = -np.pi / 2),
            xt.Bend(
                length           = 0.34,
                k0               = 1.4E-4,
                edge_entry_angle = 2.4E-4,
                edge_exit_angle  = -3.4E-4,
                rot_s_rad        = np.pi / 4),
            xt.Quadrupole(length = 0.5, k1 = 0.2, k1s = -0.03),
            xt.Sextupole(length = 0.4, k2 = 0.3, k2s = -0.04),
            xt.Octupole(length = 0.3, k3 = 0.4, k3s = -0.05),
            xt.Multipole(
                length    = 0.2,
                knl       = [0.0, 0.1, 0.02],
                ksl       = [0.0, -0.03, 0.004],
                shift_x   = -1.0E-3,
                shift_y   = 2.0E-3,
                rot_s_rad = 0.1),
            xt.UniformSolenoid(length = 0.7, ks = 0.08),
            xt.Cavity(voltage = 3.0E6, frequency = 4.0E8, phase = np.pi + 0.5),
            xt.Translation(shift_x = 1.0E-3, shift_y = -2.0E-3),
            xt.TimeDelay(shift_zeta = 3.0E-3),
            xt.Rotation(rot_x_rad = 1.25),
            xt.Rotation(rot_y_rad = -1.25),
            xt.Rotation(rot_s_rad = 0.75),
            xt.LimitRect(min_x = -1.0, max_x = 2.0, min_y = -3.0, max_y = 4.0),
            xt.LimitEllipse(a = 1.0, b = 2.0),
            xt.Marker(),
        ],
        element_names = [
            "start",
            "d1",
            "hb1",
            "hb_pi",
            "vb1",
            "vb_minus_pi_over_2",
            "sb1",
            "hc1",
            "hc_pi",
            "vc1",
            "vc_minus_pi_over_2",
            "sc1",
            "q1",
            "s1",
            "o1",
            "m1",
            "sol1",
            "cav1",
            "shift1",
            "zshift1",
            "xrot1",
            "yrot1",
            "srot1",
            "rect1",
            "ellipse1",
            "end",
        ])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _normalise(value):
    if isinstance(value, dict):
        return tuple(sorted((key, _normalise(item)) for key, item in value.items()))
    if isinstance(value, np.ndarray):
        return tuple(_normalise(item) for item in value.tolist())
    if isinstance(value, (list, tuple)):
        return tuple(_normalise(item) for item in value)
    if hasattr(value, "item"):
        return value.item()

    return value


def _line_variable_snapshot(line, variable_name):
    try:
        value = line[variable_name]
    except KeyError:
        return (False, None)

    return (True, _normalise(value))


def _assert_lines_match(line_before, line_after):
    """
    Compare line content rather than object identity.
    """
    before_table = line_before.get_table(attr = True).to_pandas()
    after_table  = line_after.get_table(attr = True).to_pandas()

    before_table_snapshot = tuple(
        (row.name, row.element_type, float(row.s))
        for row in before_table[["name", "element_type", "s"]].itertuples(index = False))
    after_table_snapshot = tuple(
        (row.name, row.element_type, float(row.s))
        for row in after_table[["name", "element_type", "s"]].itertuples(index = False))

    assert tuple(line_after.element_names) == tuple(line_before.element_names)
    assert after_table_snapshot == before_table_snapshot

    for element_name in line_before.element_names:
        before_element = line_before[element_name]
        after_element  = line_after[element_name]
        assert type(after_element) is type(before_element)
        assert _normalise(after_element.to_dict()) == _normalise(before_element.to_dict())

    assert _normalise(line_after.particle_ref.to_dict()) == \
        _normalise(line_before.particle_ref.to_dict())

    for variable_name in ("p0c", "mass0", "q0", "fshift"):
        assert _line_variable_snapshot(line_after, variable_name) == \
            _line_variable_snapshot(line_before, variable_name)


def _output_dir(tmp_path):
    output_dir = tmp_path / "writer_output"
    output_dir.mkdir()
    return output_dir


def _write_lattice(line, output_dir, output_filename):
    s2x.write_lattice(
        line                    = line,
        output_filename         = output_filename,
        output_directory        = str(output_dir),
        output_header           = "Writer preservation test",
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    return output_dir / f"{output_filename}.py"


def _write_optics(line, output_dir, output_filename):
    s2x.write_optics(
        line              = line,
        output_filename   = output_filename,
        output_directory  = str(output_dir),
        output_header     = "Writer preservation test",
        config            = Config(_verbose = False))

    return output_dir / f"{output_filename}.py"

################################################################################
# Writer Input-Line Preservation Tests
################################################################################
def test_write_lattice_does_not_mutate_supported_line(tmp_path):
    """
    write_lattice should not change element fields, line order, table positions,
    particle_ref, or writer globals on the caller's input line.
    """
    line = _build_writer_preservation_line()
    line_before = line.copy()

    _write_lattice(line, _output_dir(tmp_path), "preservation_lattice")

    _assert_lines_match(line_before, line)


def test_write_optics_does_not_mutate_supported_line(tmp_path):
    """
    write_optics should not change element fields, line order, table positions,
    particle_ref, or writer globals on the caller's input line.
    """
    line = _build_writer_preservation_line()
    line_before = line.copy()

    _write_optics(line, _output_dir(tmp_path), "preservation_import_optics")

    _assert_lines_match(line_before, line)


def test_write_lattice_twice_from_same_line_is_identical(tmp_path):
    """
    A second write from the same input line should produce the same lattice file
    as the first write.
    """
    line = _build_writer_preservation_line()
    output_dir = _output_dir(tmp_path)

    first_path = _write_lattice(line, output_dir, "first")
    second_path = _write_lattice(line, output_dir, "second")

    assert second_path.read_text(encoding = "utf-8") == first_path.read_text(encoding = "utf-8")
