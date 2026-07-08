"""
================================================================================
Tests for writer line roundtrip behaviour
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-24
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import pytest
import xtrack as xt

import sad2xs as s2x
from sad2xs.config import Config

################################################################################
# Helpers
################################################################################
def _writer_roundtrip(line, tmp_path):
    """
    Write a line with the public SAD2XS writer entry points and reload it in a
    clean Xsuite environment.
    """
    output_dir = tmp_path / "writer_roundtrip"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = "line_roundtrip",
        output_directory        = str(output_dir),
        output_header           = "Writer line roundtrip test",
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = "line_roundtrip_import_optics",
        output_directory  = str(output_dir),
        output_header     = "Writer line roundtrip test",
        config            = Config(_verbose = False))

    env = xt.Environment()
    env.call(str(output_dir / "line_roundtrip.py"))
    env.call(str(output_dir / "line_roundtrip_import_optics.py"))

    return env.lines["line"]


def _assert_scalar_field_preserved(original, reloaded, element_name, field_name):
    original_value = getattr(original[element_name], field_name)
    reloaded_value = getattr(reloaded[element_name], field_name)

    assert reloaded_value == pytest.approx(original_value), (
        f"Writer roundtrip should preserve {field_name} for element "
        f"'{element_name}'. Original: {original_value}, reloaded: "
        f"{reloaded_value}.")


def _assert_array_field_preserved(original, reloaded, element_name, field_name):
    original_value = np.asarray(getattr(original[element_name], field_name))
    reloaded_value = np.asarray(getattr(reloaded[element_name], field_name))

    n = max(len(original_value), len(reloaded_value))
    original_padded = np.zeros(n)
    reloaded_padded = np.zeros(n)
    original_padded[:len(original_value)] = original_value
    reloaded_padded[:len(reloaded_value)] = reloaded_value

    assert reloaded_padded.tolist() == pytest.approx(original_padded.tolist()), (
        f"Writer roundtrip should preserve {field_name} for element "
        f"'{element_name}'. Original: {original_value.tolist()}, reloaded: "
        f"{reloaded_value.tolist()}.")


def _assert_supported_fields_preserved(original, reloaded):
    expected_scalar_fields = {
        "d1":       ["length"],
        "b1":       [
            "length",
            "angle",
            "k1",
            "edge_entry_angle",
            "edge_exit_angle",
            "shift_x",
            "shift_y",
        ],
        "corr1":    ["length", "k0"],
        "q1":       ["length", "k1", "k1s"],
        "s1":       ["length", "k2", "k2s"],
        "o1":       ["length", "k3", "k3s"],
        "m1":       ["length", "shift_x", "shift_y", "rot_s_rad"],
        "sol1":     ["length", "ks"],
        "cav1":     ["voltage", "frequency", "phase"],
        "shift1":   ["shift_x", "shift_y"],
        "zshift1":  ["shift_zeta"],
        "xrot1":    ["rot_x_rad"],
        "yrot1":    ["rot_y_rad"],
        "srot1":    ["rot_s_rad"],
        "rect1":    ["min_x", "max_x", "min_y", "max_y"],
        "ellipse1": ["a", "b"],
    }

    for element_name, field_names in expected_scalar_fields.items():
        for field_name in field_names:
            _assert_scalar_field_preserved(
                original     = original,
                reloaded     = reloaded,
                element_name = element_name,
                field_name   = field_name)

    _assert_array_field_preserved(
        original     = original,
        reloaded     = reloaded,
        element_name = "m1",
        field_name   = "knl")
    _assert_array_field_preserved(
        original     = original,
        reloaded     = reloaded,
        element_name = "m1",
        field_name   = "ksl")


def _build_supported_writer_line():
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Drift(length = 1.0),
            xt.Bend(
                length           = 1.2,
                angle            = 0.024,
                k1               = 0.03,
                edge_entry_angle = 0.01,
                edge_exit_angle  = -0.02,
                shift_x          = 1.0E-3,
                shift_y          = -2.0E-3),
            xt.Bend(length = 0.3, k0 = 1.0E-4),
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
        ],
        element_names = [
            "mk1",
            "d1",
            "b1",
            "corr1",
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
        ])
    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line

################################################################################
# Writer Pipeline Roundtrip Tests
################################################################################
def test_writer_roundtrip_preserves_supported_line_contract(tmp_path):
    """
    The writer should roundtrip a directly constructed Xsuite line without
    relying on SAD2XS converter-owned state.
    """
    original_line = _build_supported_writer_line()

    reloaded_line = _writer_roundtrip(
        line     = original_line,
        tmp_path = tmp_path)

    assert list(reloaded_line.element_names) == list(original_line.element_names), (
        "Writer roundtrip should preserve element names and order. "
        f"Original: {list(original_line.element_names)}; reloaded: "
        f"{list(reloaded_line.element_names)}.")

    original_table = original_line.get_table()
    reloaded_table = reloaded_line.get_table()

    assert list(reloaded_table.element_type[:len(original_line.element_names)]) == (
        list(original_table.element_type[:len(original_line.element_names)])), (
        "Writer roundtrip should preserve element classes in line order.")

    assert reloaded_line.particle_ref is not None, (
        "Writer roundtrip should preserve the reference particle.")
    assert reloaded_line.particle_ref.p0c[0] == pytest.approx(
        original_line.particle_ref.p0c[0]), (
        "Writer roundtrip should preserve reference particle p0c.")
    assert reloaded_line.particle_ref.q0 == pytest.approx(
        original_line.particle_ref.q0), (
        "Writer roundtrip should preserve reference particle charge.")
    assert reloaded_line.particle_ref.mass0 == pytest.approx(
        original_line.particle_ref.mass0), (
        "Writer roundtrip should preserve reference particle mass.")

    _assert_supported_fields_preserved(
        original = original_line,
        reloaded = reloaded_line)
