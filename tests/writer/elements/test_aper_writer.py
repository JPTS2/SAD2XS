"""
================================================================================
Tests for aperture element writer serialisation
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import xtrack as xt

from tests.support.writer_helpers import write_and_load as _shared_write_and_load

################################################################################
# Helpers
################################################################################
def _write_and_load(line, tmp_path):
    """
    Write a line using the public SAD2XS writer entry points, reload it in a
    clean Xsuite environment, and return the environment and reloaded line.

    The environment is returned so tests can verify that aperture dimensions
    (a, b, min_x, max_x, min_y, max_y) are written as live optics expression
    variables, bootstrapped to a safe non-zero placeholder in the lattice
    file and set to their real value by the optics file. shift_x and shift_y
    are written as bare literal numbers, not optics variables and not string
    expressions.

    This differs from magnets, where shift_x/shift_y are literal strings
    (not bare numbers) while k1/k2/k3 are optics expression variables.
    """
    return _shared_write_and_load(line, tmp_path, output_header = "Aperture writer test")


def _writer_roundtrip(line, tmp_path):
    """
    Write and reload a line. Returns the reloaded line only.
    """
    _, reloaded_line = _write_and_load(line, tmp_path)
    return reloaded_line


def _build_limitellipse_line(
        a       = 0.02,
        b       = 0.015,
        shift_x = 0.0,
        shift_y = 0.0):
    """
    Build a minimal single-LimitEllipse Xsuite line with a reference particle.
    a and b are the horizontal and vertical semi-axes in metres.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.LimitEllipse(
            a       = a,
            b       = b,
            shift_x = shift_x,
            shift_y = shift_y), xt.Marker()],
        element_names = ["start", "ap1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_limitrect_line(
        min_x   = -0.02,
        max_x   =  0.02,
        min_y   = -0.015,
        max_y   =  0.015,
        shift_x =  0.0,
        shift_y =  0.0):
    """
    Build a minimal single-LimitRect Xsuite line with a reference particle.
    min/max fields define the rectangular aperture boundaries in metres.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.LimitRect(
            min_x   = min_x,
            max_x   = max_x,
            min_y   = min_y,
            max_y   = max_y,
            shift_x = shift_x,
            shift_y = shift_y), xt.Marker()],
        element_names = ["start", "ap1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


################################################################################
# LimitEllipse
################################################################################
########################################
# Basic Serialisation
########################################
def test_aper_writer_limitellipse_reloads_as_xsuite_limitellipse(tmp_path):
    """
    A written LimitEllipse element should reload as an xt.LimitEllipse in a
    clean Xsuite environment.
    """
    original_line = _build_limitellipse_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["ap1"], xt.LimitEllipse), (
        "Written LimitEllipse element `ap1` should reload as xt.LimitEllipse. "
        f"""Got: {type(reloaded_line["ap1"]).__name__}.""")


def test_aper_writer_limitellipse_preserves_element_name(tmp_path):
    """
    A written LimitEllipse element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_limitellipse_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "ap1" in list(reloaded_line.element_names), (
        "Reloaded line should contain LimitEllipse element `ap1`. "
        f"Got: {list(reloaded_line.element_names)}.")


########################################
# Semi-Axes
########################################
def test_aper_writer_limitellipse_preserves_a(tmp_path):
    """
    The horizontal semi-axis a of a LimitEllipse should be preserved through a
    write and reload cycle. a is written as a bare literal number in the lattice
    file.
    """
    original_line = _build_limitellipse_line(a = 0.025)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].a == pytest.approx(0.025), (
        "Writer roundtrip should preserve LimitEllipse semi-axis a. "
        f"""Original: 0.025, reloaded: {reloaded_line["ap1"].a}.""")


def test_aper_writer_limitellipse_preserves_b(tmp_path):
    """
    The vertical semi-axis b of a LimitEllipse should be preserved through a
    write and reload cycle.
    """
    original_line = _build_limitellipse_line(b = 0.018)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].b == pytest.approx(0.018), (
        "Writer roundtrip should preserve LimitEllipse semi-axis b. "
        f"""Original: 0.018, reloaded: {reloaded_line["ap1"].b}.""")


def test_aper_writer_limitellipse_preserves_a_and_b_simultaneously(tmp_path):
    """
    Both semi-axes a and b of a LimitEllipse should be preserved independently
    through a write and reload cycle. An asymmetric aperture (a != b) exercises
    both fields at once.
    """
    original_line = _build_limitellipse_line(a = 0.025, b = 0.018)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].a == pytest.approx(0.025), (
        "Writer roundtrip should preserve LimitEllipse a alongside b. "
        f"""Original: 0.025, reloaded: {reloaded_line["ap1"].a}.""")
    assert reloaded_line["ap1"].b == pytest.approx(0.018), (
        "Writer roundtrip should preserve LimitEllipse b alongside a. "
        f"""Original: 0.018, reloaded: {reloaded_line["ap1"].b}.""")


########################################
# Offsets
########################################
def test_aper_writer_limitellipse_preserves_positive_shift_x(tmp_path):
    """
    A positive horizontal offset shift_x of a LimitEllipse should be preserved
    through a write and reload cycle. shift_x is written as a bare literal number
    (not a string expression as for magnets, not an optics variable).
    """
    original_line = _build_limitellipse_line(shift_x = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve positive LimitEllipse shift_x. "
        f"""Original: 1.0E-3, reloaded: {reloaded_line["ap1"].shift_x}.""")


def test_aper_writer_limitellipse_preserves_negative_shift_x(tmp_path):
    """
    A negative horizontal offset shift_x of a LimitEllipse should be preserved
    through a write and reload cycle.
    """
    original_line = _build_limitellipse_line(shift_x = -1.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].shift_x == pytest.approx(-1.5E-3), (
        "Writer roundtrip should preserve negative LimitEllipse shift_x. "
        f"""Original: -1.5E-3, reloaded: {reloaded_line["ap1"].shift_x}.""")


def test_aper_writer_limitellipse_preserves_positive_shift_y(tmp_path):
    """
    A positive vertical offset shift_y of a LimitEllipse should be preserved
    through a write and reload cycle.
    """
    original_line = _build_limitellipse_line(shift_y = 2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].shift_y == pytest.approx(2.0E-3), (
        "Writer roundtrip should preserve positive LimitEllipse shift_y. "
        f"""Original: 2.0E-3, reloaded: {reloaded_line["ap1"].shift_y}.""")


def test_aper_writer_limitellipse_preserves_negative_shift_y(tmp_path):
    """
    A negative vertical offset shift_y of a LimitEllipse should be preserved
    through a write and reload cycle.
    """
    original_line = _build_limitellipse_line(shift_y = -2.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].shift_y == pytest.approx(-2.5E-3), (
        "Writer roundtrip should preserve negative LimitEllipse shift_y. "
        f"""Original: -2.5E-3, reloaded: {reloaded_line["ap1"].shift_y}.""")


def test_aper_writer_limitellipse_preserves_all_fields_simultaneously(tmp_path):
    """
    A LimitEllipse with a, b, shift_x, and shift_y all non-zero should preserve
    all four fields through a write and reload cycle.
    """
    original_line = _build_limitellipse_line(
        a       = 0.025,
        b       = 0.018,
        shift_x = 1.0E-3,
        shift_y = -2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].a       == pytest.approx(0.025),  (
        f"""Writer roundtrip should preserve a. Reloaded: {reloaded_line["ap1"].a}.""")
    assert reloaded_line["ap1"].b       == pytest.approx(0.018),  (
        f"""Writer roundtrip should preserve b. Reloaded: {reloaded_line["ap1"].b}.""")
    assert reloaded_line["ap1"].shift_x == pytest.approx(1.0E-3), (
        f"""Writer roundtrip should preserve shift_x. Reloaded: {reloaded_line["ap1"].shift_x}.""")
    assert reloaded_line["ap1"].shift_y == pytest.approx(-2.0E-3),(
        f"""Writer roundtrip should preserve shift_y. Reloaded: {reloaded_line["ap1"].shift_y}.""")


########################################
# Optics Variables
########################################
def test_aper_writer_limitellipse_a_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the LimitEllipse semi-axis a should be
    accessible as named optics variable a_ap1 in the Xsuite environment.

    Aperture dimensions should be written as live optics variables, not fixed
    literal values in the lattice file.
    """
    original_line = _build_limitellipse_line(a = 0.025, b = 0.018)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["a_ap1"] == pytest.approx(0.025), (
        "Optics variable `a_ap1` should exist in the environment after reload "
        "and equal the original semi-axis a. "
        f"""Got: {env["a_ap1"]}.""")


def test_aper_writer_limitellipse_b_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the LimitEllipse semi-axis b should be
    accessible as named optics variable b_ap1 in the Xsuite environment.

    Aperture dimensions should be written as live optics variables, not fixed
    literal values in the lattice file.
    """
    original_line = _build_limitellipse_line(a = 0.025, b = 0.018)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["b_ap1"] == pytest.approx(0.018), (
        "Optics variable `b_ap1` should exist in the environment after reload "
        "and equal the original semi-axis b. "
        f"""Got: {env["b_ap1"]}.""")


def test_aper_writer_limitellipse_a_is_tunable_via_optics_variable(tmp_path):
    """
    The a_ap1 optics variable should remain live after reload: modifying it
    should immediately update the LimitEllipse semi-axis a in the line.

    Aperture dimensions should remain live after reload.
    """
    original_line = _build_limitellipse_line(a = 0.025, b = 0.018)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["a_ap1"] = 0.030

    assert reloaded_line["ap1"].a == pytest.approx(0.030), (
        "Modifying optics variable `a_ap1` should update the LimitEllipse a. "
        f"""Got: {reloaded_line["ap1"].a}.""")


########################################
# Multiple LimitEllipses
########################################
def test_aper_writer_preserves_multiple_limitellipses_independently(tmp_path):
    """
    Multiple LimitEllipse elements with different semi-axes should each preserve
    their individual values through a single write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.LimitEllipse(a = 0.025, b = 0.018),
            xt.LimitEllipse(a = 0.020, b = 0.015),
            xt.Marker(),
        ],
        element_names = ["start", "apa", "apb", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    assert reloaded_line["apa"].a == pytest.approx(0.025), (
        "Writer roundtrip should preserve a for `apa`. "
        f"""Original: 0.025, reloaded: {reloaded_line["apa"].a}.""")
    assert reloaded_line["apa"].b == pytest.approx(0.018), (
        "Writer roundtrip should preserve b for `apa`. "
        f"""Original: 0.018, reloaded: {reloaded_line["apa"].b}.""")
    assert reloaded_line["apb"].a == pytest.approx(0.020), (
        "Writer roundtrip should preserve a for `apb`. "
        f"""Original: 0.020, reloaded: {reloaded_line["apb"].a}.""")
    assert reloaded_line["apb"].b == pytest.approx(0.015), (
        "Writer roundtrip should preserve b for `apb`. "
        f"""Original: 0.015, reloaded: {reloaded_line["apb"].b}.""")


################################################################################
# LimitRect
################################################################################
########################################
# Basic Serialisation
########################################
def test_aper_writer_limitrect_reloads_as_xsuite_limitrect(tmp_path):
    """
    A written LimitRect element should reload as an xt.LimitRect in a clean
    Xsuite environment.
    """
    original_line = _build_limitrect_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["ap1"], xt.LimitRect), (
        "Written LimitRect element `ap1` should reload as xt.LimitRect. "
        f"""Got: {type(reloaded_line["ap1"]).__name__}.""")


def test_aper_writer_limitrect_preserves_element_name(tmp_path):
    """
    A written LimitRect element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_limitrect_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "ap1" in list(reloaded_line.element_names), (
        "Reloaded line should contain LimitRect element `ap1`. "
        f"Got: {list(reloaded_line.element_names)}.")


########################################
# Boundary Fields
########################################
def test_aper_writer_limitrect_preserves_horizontal_bounds(tmp_path):
    """
    The min_x and max_x bounds of a LimitRect should be preserved through a
    write and reload cycle.
    """
    original_line = _build_limitrect_line(min_x = -0.025, max_x = 0.025)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].min_x == pytest.approx(-0.025), (
        "Writer roundtrip should preserve LimitRect min_x. "
        f"""Original: -0.025, reloaded: {reloaded_line["ap1"].min_x}.""")
    assert reloaded_line["ap1"].max_x == pytest.approx( 0.025), (
        "Writer roundtrip should preserve LimitRect max_x. "
        f"""Original: 0.025, reloaded: {reloaded_line["ap1"].max_x}.""")


def test_aper_writer_limitrect_preserves_vertical_bounds(tmp_path):
    """
    The min_y and max_y bounds of a LimitRect should be preserved through a
    write and reload cycle.
    """
    original_line = _build_limitrect_line(min_y = -0.018, max_y = 0.018)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].min_y == pytest.approx(-0.018), (
        "Writer roundtrip should preserve LimitRect min_y. "
        f"""Original: -0.018, reloaded: {reloaded_line["ap1"].min_y}.""")
    assert reloaded_line["ap1"].max_y == pytest.approx( 0.018), (
        "Writer roundtrip should preserve LimitRect max_y. "
        f"""Original: 0.018, reloaded: {reloaded_line["ap1"].max_y}.""")


def test_aper_writer_limitrect_preserves_asymmetric_bounds(tmp_path):
    """
    A LimitRect with asymmetric bounds (min_x != -max_x, min_y != -max_y)
    should preserve all four boundaries independently through a write and
    reload cycle.
    """
    original_line = _build_limitrect_line(
        min_x = -0.015,
        max_x =  0.025,
        min_y = -0.010,
        max_y =  0.020)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].min_x == pytest.approx(-0.015), (
        "Writer roundtrip should preserve asymmetric min_x. "
        f"""Original: -0.015, reloaded: {reloaded_line["ap1"].min_x}.""")
    assert reloaded_line["ap1"].max_x == pytest.approx( 0.025), (
        "Writer roundtrip should preserve asymmetric max_x. "
        f"""Original: 0.025, reloaded: {reloaded_line["ap1"].max_x}.""")
    assert reloaded_line["ap1"].min_y == pytest.approx(-0.010), (
        "Writer roundtrip should preserve asymmetric min_y. "
        f"""Original: -0.010, reloaded: {reloaded_line["ap1"].min_y}.""")
    assert reloaded_line["ap1"].max_y == pytest.approx( 0.020), (
        "Writer roundtrip should preserve asymmetric max_y. "
        f"""Original: 0.020, reloaded: {reloaded_line["ap1"].max_y}.""")


########################################
# Offsets
########################################
def test_aper_writer_limitrect_preserves_positive_shift_x(tmp_path):
    """
    A positive horizontal offset shift_x of a LimitRect should be preserved
    through a write and reload cycle.
    """
    original_line = _build_limitrect_line(shift_x = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve positive LimitRect shift_x. "
        f"""Original: 1.0E-3, reloaded: {reloaded_line["ap1"].shift_x}.""")


def test_aper_writer_limitrect_preserves_negative_shift_y(tmp_path):
    """
    A negative vertical offset shift_y of a LimitRect should be preserved
    through a write and reload cycle.
    """
    original_line = _build_limitrect_line(shift_y = -2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve negative LimitRect shift_y. "
        f"""Original: -2.0E-3, reloaded: {reloaded_line["ap1"].shift_y}.""")


def test_aper_writer_limitrect_preserves_all_fields_simultaneously(tmp_path):
    """
    A LimitRect with all six fields set to non-zero values should preserve all
    of them through a write and reload cycle.
    """
    original_line = _build_limitrect_line(
        min_x   = -0.015,
        max_x   =  0.025,
        min_y   = -0.010,
        max_y   =  0.020,
        shift_x =  1.0E-3,
        shift_y = -2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].min_x   == pytest.approx(-0.015),  (
        f"""Writer roundtrip should preserve min_x. Reloaded: {reloaded_line["ap1"].min_x}.""")
    assert reloaded_line["ap1"].max_x   == pytest.approx( 0.025),  (
        f"""Writer roundtrip should preserve max_x. Reloaded: {reloaded_line["ap1"].max_x}.""")
    assert reloaded_line["ap1"].min_y   == pytest.approx(-0.010),  (
        f"""Writer roundtrip should preserve min_y. Reloaded: {reloaded_line["ap1"].min_y}.""")
    assert reloaded_line["ap1"].max_y   == pytest.approx( 0.020),  (
        f"""Writer roundtrip should preserve max_y. Reloaded: {reloaded_line["ap1"].max_y}.""")
    assert reloaded_line["ap1"].shift_x == pytest.approx( 1.0E-3), (
        f"""Writer roundtrip should preserve shift_x. Reloaded: {reloaded_line["ap1"].shift_x}.""")
    assert reloaded_line["ap1"].shift_y == pytest.approx(-2.0E-3), (
        f"""Writer roundtrip should preserve shift_y. Reloaded: {reloaded_line["ap1"].shift_y}.""")


########################################
# Optics Variables
########################################
def test_aper_writer_limitrect_min_x_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the LimitRect boundary min_x should be
    accessible as named optics variable min_x_ap1 in the Xsuite environment.

    Aperture boundaries should be written as live optics variables, not fixed
    literal values in the lattice file.
    """
    original_line = _build_limitrect_line(min_x = -0.025, max_x = 0.025)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["min_x_ap1"] == pytest.approx(-0.025), (
        "Optics variable `min_x_ap1` should exist in the environment after reload "
        "and equal the original min_x. "
        f"""Got: {env["min_x_ap1"]}.""")


def test_aper_writer_limitrect_max_x_is_accessible_as_optics_variable(tmp_path):
    """
    After writing and reloading, the LimitRect boundary max_x should be
    accessible as named optics variable max_x_ap1 in the Xsuite environment.

    Aperture boundaries should be written as live optics variables, not fixed
    literal values in the lattice file.
    """
    original_line = _build_limitrect_line(min_x = -0.025, max_x = 0.025)
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    assert env["max_x_ap1"] == pytest.approx(0.025), (
        "Optics variable `max_x_ap1` should exist in the environment after reload "
        "and equal the original max_x. "
        f"""Got: {env["max_x_ap1"]}.""")


def test_aper_writer_limitrect_min_x_is_tunable_via_optics_variable(tmp_path):
    """
    The min_x_ap1 optics variable should remain live after reload: modifying it
    should immediately update the LimitRect min_x in the line.

    Aperture boundaries should remain live after reload.
    """
    original_line = _build_limitrect_line(min_x = -0.025, max_x = 0.025)
    env, reloaded_line = _write_and_load(line = original_line, tmp_path = tmp_path)

    env["min_x_ap1"] = -0.030

    assert reloaded_line["ap1"].min_x == pytest.approx(-0.030), (
        "Modifying optics variable `min_x_ap1` should update the LimitRect min_x. "
        f"""Got: {reloaded_line["ap1"].min_x}.""")


########################################
# Multiple LimitRects
########################################
def test_aper_writer_preserves_multiple_limitrects_independently(tmp_path):
    """
    Multiple LimitRect elements with different boundaries should each preserve
    their individual values through a single write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.LimitRect(min_x = -0.025, max_x = 0.025, min_y = -0.018, max_y = 0.018),
            xt.LimitRect(min_x = -0.020, max_x = 0.020, min_y = -0.015, max_y = 0.015),
            xt.Marker(),
        ],
        element_names = ["start", "apa", "apb", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    assert reloaded_line["apa"].max_x == pytest.approx(0.025), (
        "Writer roundtrip should preserve max_x for `apa`. "
        f"""Original: 0.025, reloaded: {reloaded_line["apa"].max_x}.""")
    assert reloaded_line["apa"].max_y == pytest.approx(0.018), (
        "Writer roundtrip should preserve max_y for `apa`. "
        f"""Original: 0.018, reloaded: {reloaded_line["apa"].max_y}.""")
    assert reloaded_line["apb"].max_x == pytest.approx(0.020), (
        "Writer roundtrip should preserve max_x for `apb`. "
        f"""Original: 0.020, reloaded: {reloaded_line["apb"].max_x}.""")
    assert reloaded_line["apb"].max_y == pytest.approx(0.015), (
        "Writer roundtrip should preserve max_y for `apb`. "
        f"""Original: 0.015, reloaded: {reloaded_line["apb"].max_y}.""")


def _build_limitrectellipse_line(
        max_x   = 0.020,
        max_y   = 0.015,
        a       = 0.025,
        b       = 0.018,
        shift_x = 0.0,
        shift_y = 0.0):
    """
    Build a minimal single-LimitRectEllipse Xsuite line with a reference particle.
    """
    line = xt.Line(
        elements      = [xt.Marker(), xt.LimitRectEllipse(
            max_x   = max_x,
            max_y   = max_y,
            a       = a,
            b       = b,
            shift_x = shift_x,
            shift_y = shift_y), xt.Marker()],
        element_names = ["start", "ap1", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


################################################################################
# LimitRectEllipse
################################################################################
def test_aper_writer_limitrectellipse_reloads_as_xsuite_limitrectellipse(tmp_path):
    """
    A written LimitRectEllipse element should reload as xt.LimitRectEllipse.
    """
    original_line = _build_limitrectellipse_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["ap1"], xt.LimitRectEllipse), (
        "Written LimitRectEllipse element `ap1` should reload as xt.LimitRectEllipse. "
        f"""Got: {type(reloaded_line["ap1"]).__name__}.""")


def test_aper_writer_limitrectellipse_preserves_max_x(tmp_path):
    """
    The rectangular horizontal half-width max_x should be preserved through a
    write and reload cycle.
    """
    original_line = _build_limitrectellipse_line(max_x = 0.020)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].max_x == pytest.approx(0.020), (
        "Writer roundtrip should preserve LimitRectEllipse max_x. "
        f"""Original: 0.020, reloaded: {reloaded_line["ap1"].max_x}.""")


def test_aper_writer_limitrectellipse_preserves_max_y(tmp_path):
    """
    The rectangular vertical half-width max_y should be preserved through a
    write and reload cycle.
    """
    original_line = _build_limitrectellipse_line(max_y = 0.015)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].max_y == pytest.approx(0.015), (
        "Writer roundtrip should preserve LimitRectEllipse max_y. "
        f"""Original: 0.015, reloaded: {reloaded_line["ap1"].max_y}.""")


def test_aper_writer_limitrectellipse_preserves_a(tmp_path):
    """
    The ellipse horizontal semi-axis a should be preserved through a write and
    reload cycle.
    """
    original_line = _build_limitrectellipse_line(a = 0.025)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].a == pytest.approx(0.025), (
        "Writer roundtrip should preserve LimitRectEllipse a. "
        f"""Original: 0.025, reloaded: {reloaded_line["ap1"].a}.""")


def test_aper_writer_limitrectellipse_preserves_b(tmp_path):
    """
    The ellipse vertical semi-axis b should be preserved through a write and
    reload cycle.
    """
    original_line = _build_limitrectellipse_line(b = 0.018)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].b == pytest.approx(0.018), (
        "Writer roundtrip should preserve LimitRectEllipse b. "
        f"""Original: 0.018, reloaded: {reloaded_line["ap1"].b}.""")


def test_aper_writer_limitrectellipse_preserves_all_fields(tmp_path):
    """
    All four fields (max_x, max_y, a, b) should be preserved independently
    through a single write and reload cycle.
    """
    original_line = _build_limitrectellipse_line(
        max_x = 0.020, max_y = 0.015, a = 0.025, b = 0.018)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["ap1"].max_x == pytest.approx(0.020), (
        "Writer roundtrip should preserve LimitRectEllipse max_x.")
    assert reloaded_line["ap1"].max_y == pytest.approx(0.015), (
        "Writer roundtrip should preserve LimitRectEllipse max_y.")
    assert reloaded_line["ap1"].a     == pytest.approx(0.025), (
        "Writer roundtrip should preserve LimitRectEllipse a.")
    assert reloaded_line["ap1"].b     == pytest.approx(0.018), (
        "Writer roundtrip should preserve LimitRectEllipse b.")


################################################################################
# Mixed Aperture Types
################################################################################
########################################
# LimitEllipse and LimitRect in One Line
########################################
def test_aper_writer_preserves_limitellipse_and_limitrect_in_one_line(tmp_path):
    """
    A line containing both a LimitEllipse and a LimitRect should preserve each
    element's fields independently through a single write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.LimitEllipse(a = 0.025, b = 0.018),
            xt.LimitRect(min_x = -0.020, max_x = 0.020, min_y = -0.015, max_y = 0.015),
            xt.Marker(),
        ],
        element_names = ["start", "apell", "aprect", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["apell"], xt.LimitEllipse), (
        f"`apell` should reload as xt.LimitEllipse. "
        f"""Got: {type(reloaded_line["apell"]).__name__}.""")
    assert isinstance(reloaded_line["aprect"], xt.LimitRect), (
        f"`aprect` should reload as xt.LimitRect. "
        f"""Got: {type(reloaded_line["aprect"]).__name__}.""")

    assert reloaded_line["apell"].a    == pytest.approx(0.025), (
        f"Writer roundtrip should preserve LimitEllipse a. "
        f"""Original: 0.025, reloaded: {reloaded_line["apell"].a}.""")
    assert reloaded_line["apell"].b    == pytest.approx(0.018), (
        f"Writer roundtrip should preserve LimitEllipse b. "
        f"""Original: 0.018, reloaded: {reloaded_line["apell"].b}.""")
    assert reloaded_line["aprect"].max_x == pytest.approx(0.020), (
        f"Writer roundtrip should preserve LimitRect max_x. "
        f"""Original: 0.020, reloaded: {reloaded_line["aprect"].max_x}.""")
    assert reloaded_line["aprect"].max_y == pytest.approx(0.015), (
        f"Writer roundtrip should preserve LimitRect max_y. "
        f"""Original: 0.015, reloaded: {reloaded_line["aprect"].max_y}.""")
