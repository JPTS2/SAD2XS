"""
================================================================================
Tests for SAD APERT conversion
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-29
================================================================================
"""
################################################################################
# Required Packages
################################################################################
from pathlib import Path

import numpy as np
import pytest
import sad2xs as s2x
import xtrack as xt

from sad2xs.converter._004_element_converter import convert_apertures
from tests.support.diagnostics import diagnostic_report_path

################################################################################
# Diagnostic Helpers
################################################################################
APERT_ARTIFACT_CATEGORY = "conversion/elements/apert"

def _format_value(value):
    """
    Format values consistently for aperture diagnostic reports.
    """
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.12e}"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (bool, np.bool_)):
        return str(bool(value))
    return str(value)

def _markdown_table(headers, rows):
    """
    Build a simple Markdown table.
    """
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(_format_value(value) for value in row) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])

def _write_aperture_grid_report(
        report_path,
        title,
        aperture_description,
        x_grid,
        y_grid,
        expected_alive,
        xsuite_alive,
        parameters,
        raw_particle_id = None,
        raw_xsuite_alive = None,
        notes = None):
    """
    Write a Markdown report for failed aperture grid-loss comparisons.
    """
    mismatch = expected_alive != xsuite_alive
    mismatch_rows = [
        [
            idx,
            x_grid[idx],
            y_grid[idx],
            expected_alive[idx],
            xsuite_alive[idx],
        ]
        for idx in np.where(mismatch)[0]
    ]
    all_rows = [
        [
            idx,
            x_grid[idx],
            y_grid[idx],
            expected_alive[idx],
            xsuite_alive[idx],
        ]
        for idx in range(len(x_grid))
    ]
    raw_rows = []
    if raw_particle_id is not None and raw_xsuite_alive is not None:
        raw_rows = [
            [
                idx,
                raw_particle_id[idx],
                raw_xsuite_alive[idx],
            ]
            for idx in range(len(raw_particle_id))
        ]

    sections = [
        f"# {title}",
        "## Parameters\n\n" + _markdown_table(
            headers = ["name", "value"],
            rows = list(parameters.items())),
        "## Aperture Definition\n\n```text\n" + aperture_description.strip() + "\n```",
        "## Summary\n\n" + _markdown_table(
            headers = ["name", "value"],
            rows = [
                ["particles", len(x_grid)],
                ["mismatches", int(np.count_nonzero(mismatch))],
            ]),
        "## Mismatches\n\n" + _markdown_table(
            headers = ["i", "x", "y", "expected_alive", "xsuite_alive"],
            rows = mismatch_rows),
        "## Full Grid\n\n" + _markdown_table(
            headers = ["i", "x", "y", "expected_alive", "xsuite_alive"],
            rows = all_rows),
    ]
    if raw_rows:
        sections.append(
            "## Raw Xsuite Particle Order\n\n" + _markdown_table(
                headers = ["raw_i", "particle_id", "raw_xsuite_alive"],
                rows    = raw_rows))
    if notes:
        sections.append("## Notes\n\n" + "\n".join(f"- {note}" for note in notes))

    report_path = Path(report_path)
    report_path.parent.mkdir(parents = True, exist_ok = True)
    report_path.write_text("\n\n".join(sections) + "\n")
    return report_path

def _assert_aperture_grid_matches(
        test_name,
        aperture,
        aperture_description,
        x_grid,
        y_grid,
        expected_alive,
        parameters,
        notes = None):
    """
    Track a grid through one aperture and compare the alive mask.
    """
    _assert_apertures_grid_matches(
        test_name             = test_name,
        apertures             = [aperture],
        aperture_names        = ["test_apert"],
        aperture_description  = aperture_description,
        x_grid                = x_grid,
        y_grid                = y_grid,
        expected_alive        = expected_alive,
        parameters            = parameters,
        notes                 = notes)

def _assert_apertures_grid_matches(
        test_name,
        apertures,
        aperture_names,
        aperture_description,
        x_grid,
        y_grid,
        expected_alive,
        parameters,
        notes = None):
    """
    Track a grid through one or more consecutive (same-s) apertures and
    compare the AND of their alive masks, as SAD applies combined APERT
    conditions.
    """
    line = xt.Line(elements = apertures, element_names = aperture_names)
    particles = xt.Particles(
        "positron",
        p0c   = 1.0E9,
        x     = x_grid.copy(),
        px    = np.zeros_like(x_grid),
        y     = y_grid.copy(),
        py    = np.zeros_like(y_grid),
        zeta  = np.zeros_like(x_grid),
        delta = np.zeros_like(x_grid))
    line.track(particles, num_turns = 1)

    raw_particle_id = np.asarray(particles.particle_id, dtype = int)
    raw_xsuite_alive = np.asarray(particles.state > 0)
    xsuite_alive = np.empty_like(raw_xsuite_alive, dtype = bool)
    xsuite_alive[raw_particle_id] = raw_xsuite_alive

    if not np.array_equal(expected_alive, xsuite_alive):
        report_path = diagnostic_report_path(
            test_name  = test_name,
            category   = APERT_ARTIFACT_CATEGORY,
            parameters = parameters)
        _write_aperture_grid_report(
            report_path          = report_path,
            title                = f"{test_name} failure",
            aperture_description = aperture_description,
            x_grid               = x_grid,
            y_grid               = y_grid,
            expected_alive       = expected_alive,
            xsuite_alive         = xsuite_alive,
            parameters           = parameters,
            raw_particle_id      = raw_particle_id,
            raw_xsuite_alive     = raw_xsuite_alive,
            notes                = notes)
        pytest.fail(
            f"Converted aperture grid-loss mask should match expectation. "
            f"Mismatches: {np.count_nonzero(expected_alive != xsuite_alive)}. "
            f"Diagnostic report: {report_path}")

################################################################################
# Grid Helpers
################################################################################
def _ellipse_grid(a, b, shift_x = 0.0, shift_y = 0.0):
    """
    Return deterministic ellipse-focused test particles.
    """
    angles = np.linspace(0.0, 2.0 * np.pi, 16, endpoint = False)
    radii = np.array([0.25, 0.75, 0.99, 1.01, 1.25])
    x_values = []
    y_values = []
    for radius in radii:
        x_values.extend(shift_x + radius * a * np.cos(angles))
        y_values.extend(shift_y + radius * b * np.sin(angles))

    x_axis = shift_x + np.array([
        -1.25 * a,
        -1.01 * a,
        -0.99 * a,
        0.0,
        0.99 * a,
        1.01 * a,
        1.25 * a,
    ])
    y_axis = np.full_like(x_axis, shift_y)

    y_axis_values = shift_y + np.array([
        -1.25 * b,
        -1.01 * b,
        -0.99 * b,
        0.0,
        0.99 * b,
        1.01 * b,
        1.25 * b,
    ])
    x_axis_values = np.full_like(y_axis_values, shift_x)

    return (
        np.concatenate([np.array(x_values), x_axis, x_axis_values]),
        np.concatenate([np.array(y_values), y_axis, y_axis_values]),
    )

def _rectangle_grid(min_x, max_x, min_y, max_y, shift_x = 0.0, shift_y = 0.0):
    """
    Return deterministic rectangle-focused test particles.
    """
    x_edges = shift_x + np.array([
        1.25 * min_x,
        1.01 * min_x,
        0.99 * min_x,
        0.0,
        0.99 * max_x,
        1.01 * max_x,
        1.25 * max_x,
    ])
    y_edges = shift_y + np.array([
        1.25 * min_y,
        1.01 * min_y,
        0.99 * min_y,
        0.0,
        0.99 * max_y,
        1.01 * max_y,
        1.25 * max_y,
    ])

    xx, yy = np.meshgrid(x_edges, y_edges)
    core = np.linspace(-0.9, 0.9, 21)
    x_line = shift_x + min_x + (max_x - min_x) * (core + 1.0) / 2.0
    y_line = np.full_like(x_line, shift_y)
    y_line_2 = shift_y + min_y + (max_y - min_y) * (core + 1.0) / 2.0
    x_line_2 = np.full_like(y_line_2, shift_x)

    return (
        np.concatenate([xx.ravel(), x_line, x_line_2]),
        np.concatenate([yy.ravel(), y_line, y_line_2]),
    )

def _ellipse_alive(x_values, y_values, a, b, shift_x = 0.0, shift_y = 0.0):
    """
    Return the analytic SAD ellipse alive mask.
    """
    x_local = x_values - shift_x
    y_local = y_values - shift_y
    return (x_local / a) ** 2 + (y_local / b) ** 2 < 1.0

def _rectangle_alive(
        x_values,
        y_values,
        min_x,
        max_x,
        min_y,
        max_y,
        shift_x = 0.0,
        shift_y = 0.0):
    """
    Return the analytic SAD rectangle alive mask.
    """
    x_local = x_values - shift_x
    y_local = y_values - shift_y
    return (
        (min_x < x_local) &
        (x_local < max_x) &
        (min_y < y_local) &
        (y_local < max_y)
    )

def _rotated_rectangle_alive(
        x_values,
        y_values,
        min_x,
        max_x,
        min_y,
        max_y,
        rotation,
        shift_x = 0.0,
        shift_y = 0.0):
    """
    Return the analytic SAD rotated-rectangle alive mask.
    """
    x_shifted = x_values - shift_x
    y_shifted = y_values - shift_y
    x_local = x_shifted * np.cos(rotation) + y_shifted * np.sin(rotation)
    y_local = -x_shifted * np.sin(rotation) + y_shifted * np.cos(rotation)
    return (
        (min_x < x_local) &
        (x_local < max_x) &
        (min_y < y_local) &
        (y_local < max_y)
    )

################################################################################
# Basic Conversion and Smoke Tests
################################################################################
########################################
# Direct Converter Behaviour
########################################
def test_aper_converter_creates_xsuite_limitellipse(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Parsed SAD elliptical APERT elements should become Xsuite LimitEllipse.
    """
    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {"ax": 0.01, "ay": 0.02}),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitEllipse)

    assert aperture.a == pytest.approx(0.01), (
        "Converted elliptical APERT should preserve SAD AX.")
    assert aperture.b == pytest.approx(0.02), (
        "Converted elliptical APERT should preserve SAD AY.")

def test_aper_converter_creates_xsuite_limitrect(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Parsed SAD rectangular APERT elements should become Xsuite LimitRect.
    """
    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "dx1": -0.01,
                "dx2": 0.02,
                "dy1": -0.03,
                "dy2": 0.04,
            }),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitRect)

    assert aperture.min_x == pytest.approx(-0.01), (
        "Converted rectangular APERT should preserve SAD DX1 as min_x.")
    assert aperture.max_x == pytest.approx(0.02), (
        "Converted rectangular APERT should preserve SAD DX2 as max_x.")
    assert aperture.min_y == pytest.approx(-0.03), (
        "Converted rectangular APERT should preserve SAD DY1 as min_y.")
    assert aperture.max_y == pytest.approx(0.04), (
        "Converted rectangular APERT should preserve SAD DY2 as max_y.")

def test_aper_converter_creates_all_apertures(
        xsuite_environment,
        assert_environment_element):
    """
    Multiple parsed SAD APERT elements should all be converted.
    """
    parsed_elements = {
        "apert": {
            "ellipse": {"ax": 0.01, "ay": 0.02},
            "rect": {"dx1": -0.01, "dx2": 0.02, "dy1": -0.03, "dy2": 0.04},
        },
    }

    convert_apertures(
        parsed_elements = parsed_elements,
        environment     = xsuite_environment)

    assert set(xsuite_environment.element_dict) == {"ellipse", "rect"}, (
        "All parsed SAD APERT elements should be present in the environment.")
    assert_environment_element(
        environment  = xsuite_environment,
        element_name = "ellipse",
        element_type = xt.LimitEllipse)
    assert_environment_element(
        environment  = xsuite_environment,
        element_name = "rect",
        element_type = xt.LimitRect)

################################################################################
# Aperture Parameters and Offsets
################################################################################
########################################
# Defaults and Bounds Normalisation
########################################
@pytest.mark.parametrize(
    "element_variables, expected_a, expected_b",
    [
        ({"ax": 0.01}, 0.01, 1.0),
        ({"ay": 0.02}, 1.0, 0.02),
    ])
def test_aper_converter_uses_one_metre_fallback_for_missing_ellipse_axis(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables,
        expected_a,
        expected_b):
    """
    Partial SAD APERT ellipses should use the SAD2XS 1 m fallback axis.

    This test documents the current SAD2XS/Xsuite policy for omitted local
    ellipse axes. It does not assert native SAD zero-axis or global-aperture
    semantics, which need separate verification before being encoded.
    """
    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = element_variables),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitEllipse)

    assert aperture.a == pytest.approx(expected_a), (
        "Partial APERT ellipse definitions should use the documented SAD2XS "
        "fallback for missing AX.")
    assert aperture.b == pytest.approx(expected_b), (
        "Partial APERT ellipse definitions should use the documented SAD2XS "
        "fallback for missing AY.")

def test_aper_converter_sorts_rectangular_bounds(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    SAD rectangular APERT bounds should be order-independent.
    """
    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "dx1": 0.02,
                "dx2": -0.01,
                "dy1": 0.04,
                "dy2": -0.03,
            }),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitRect)

    assert aperture.min_x == pytest.approx(-0.01), (
        "Converted APERT should sort rectangular x-bounds.")
    assert aperture.max_x == pytest.approx(0.02), (
        "Converted APERT should sort rectangular x-bounds.")
    assert aperture.min_y == pytest.approx(-0.03), (
        "Converted APERT should sort rectangular y-bounds.")
    assert aperture.max_y == pytest.approx(0.04), (
        "Converted APERT should sort rectangular y-bounds.")

########################################
# Offsets
########################################
@pytest.mark.parametrize(
    "element_variables, element_type",
    [
        ({"ax": 0.01, "ay": 0.02, "dx": 0.001, "dy": -0.002}, xt.LimitEllipse),
        ({
            "dx1": -0.01,
            "dx2": 0.02,
            "dy1": -0.03,
            "dy2": 0.04,
            "dx": 0.001,
            "dy": -0.002,
        }, xt.LimitRect),
    ])
def test_aper_converter_preserves_offsets(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables,
        element_type):
    """
    SAD APERT DX/DY should map to Xsuite aperture shifts.
    """
    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = element_variables),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = element_type)

    assert aperture.shift_x == pytest.approx(0.001), (
        "Converted APERT should preserve SAD DX as Xsuite shift_x.")
    assert aperture.shift_y == pytest.approx(-0.002), (
        "Converted APERT should preserve SAD DY as Xsuite shift_y.")

########################################
# Rotations
########################################
def test_aper_converter_preserves_rectangle_rotation(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    SAD APERT ROTATE should map to Xsuite aperture rotation with the SAD->Xsuite
    sign convention rot_s_rad = -ROTATE (the same negation as magnets). A
    non-symmetric angle (pi/6) is used so the sign is unambiguous; the sign was
    validated against real SAD aperture tracking.
    """
    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "dx1": -0.01,
                "dx2": 0.01,
                "dy1": -0.02,
                "dy2": 0.02,
                "rotate": np.pi / 6.0,
            }),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitRect)

    assert aperture.rot_s_rad == pytest.approx(-np.pi / 6.0), (
        "Converted rectangular APERT should map SAD ROTATE to rot_s_rad = "
        "-ROTATE.")

########################################
# Combined Apertures
########################################
def test_aper_converter_preserves_combined_rectangular_and_elliptical_limits(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    SAD APERT supports the intersection of rectangular and elliptical limits.
    Provably symmetric bounds (DX1 == -DX2, DY1 == -DY2) collapse to a
    single xt.LimitRectEllipse.
    """
    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "ax": 0.02,
                "ay": 0.03,
                "dx1": -0.01,
                "dx2": 0.01,
                "dy1": -0.015,
                "dy2": 0.015,
            }),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitRectEllipse)

    assert aperture.max_x == pytest.approx(0.01), (
        "Combined APERT should preserve the rectangular horizontal limit.")
    assert aperture.max_y == pytest.approx(0.015), (
        "Combined APERT should preserve the rectangular vertical limit.")
    assert aperture.a == pytest.approx(0.02), (
        "Combined APERT should preserve the elliptical horizontal axis.")
    assert aperture.b == pytest.approx(0.03), (
        "Combined APERT should preserve the elliptical vertical axis.")
    assert "test_apert" not in xsuite_environment.lines, (
        "A provably-symmetric combined APERT should not be split into a "
        "sub-line.")

def test_aper_converter_splits_asymmetric_combined_limits_into_rect_and_ellipse(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    An off-centre rectangular window (DX1 != -DX2) can't be represented by a
    single xt.LimitRectEllipse, so the converter splits it into a
    LimitRect + LimitEllipse pair sharing the same shift/rotation (see
    tests/sad/test_apert.py::
    test_apert_combined_rect_and_ellipse_grid_requires_both for the real-SAD
    behaviour this mirrors).
    """
    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "ax": 0.02,
                "ay": 0.03,
                "dx1": -0.005,
                "dx2": 0.02,
                "dy1": -0.03,
                "dy2": 0.005,
                "dx": 0.001,
                "dy": -0.002,
                "rotate": np.pi / 6.0,
            }),
        environment = xsuite_environment)

    assert "test_apert" in xsuite_environment.lines, (
        "An asymmetric combined APERT should be built as a named sub-line.")
    assert xsuite_environment.lines["test_apert"].element_names == [
        "test_apert_rect", "test_apert_ellipse"], (
        "The sub-line should reference the split Rect and Ellipse, in order.")

    rect = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert_rect",
        element_type = xt.LimitRect)
    ellipse = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert_ellipse",
        element_type = xt.LimitEllipse)

    assert rect.min_x == pytest.approx(-0.005), "Rect should preserve DX1."
    assert rect.max_x == pytest.approx(0.02), "Rect should preserve DX2."
    assert rect.min_y == pytest.approx(-0.03), "Rect should preserve DY1."
    assert rect.max_y == pytest.approx(0.005), "Rect should preserve DY2."
    assert ellipse.a == pytest.approx(0.02), "Ellipse should preserve AX."
    assert ellipse.b == pytest.approx(0.03), "Ellipse should preserve AY."

    for aperture, label in [(rect, "rect"), (ellipse, "ellipse")]:
        assert aperture.shift_x == pytest.approx(0.001), (
            f"Split combined APERT {label} should share the DX shift.")
        assert aperture.shift_y == pytest.approx(-0.002), (
            f"Split combined APERT {label} should share the DY shift.")
        assert aperture.rot_s_rad == pytest.approx(-np.pi / 6.0), (
            f"Split combined APERT {label} should share the ROTATE rotation.")

def test_aper_converter_split_sub_line_flattens_into_parent_line(
        parsed_elements,
        xsuite_environment):
    """
    Referencing a split combined APERT's name as a component of another
    line (as convert_lines does for every SAD LINE) should transparently
    flatten it to its two constituent elements, at every occurrence.
    """
    xsuite_environment.new("d1", xt.Drift, length = 1.0)
    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "ax": 0.02, "ay": 0.03,
                "dx1": -0.005, "dx2": 0.02,
                "dy1": -0.03, "dy2": 0.005,
            }),
        environment = xsuite_environment)

    line = xsuite_environment.new_line(
        name       = "l",
        components = ["d1", "test_apert", "d1", "test_apert", "d1"])

    assert line.element_names == [
        "d1", "test_apert_rect", "test_apert_ellipse",
        "d1", "test_apert_rect", "test_apert_ellipse",
        "d1"], (
        "Every occurrence of the split aperture should flatten to its Rect "
        "and Ellipse components.")

@pytest.mark.parametrize(
    "element_variables",
    [
        {"ax": 0.01, "ay": 0.01, "dx1": 0.0, "dx2": 0.0,
         "dy1": -0.005, "dy2": 0.02},
    ])
def test_aper_converter_treats_degenerate_axis_as_unconstrained(
        parsed_elements,
        xsuite_environment,
        assert_environment_element,
        element_variables):
    """
    DX1 == DX2 leaves that axis unconstrained rather than zero-width (see
    tests/sad/test_apert.py::test_apert_degenerate_rectangle_bound_behavior).
    The y-axis stays asymmetric here, so this still splits into Rect + Ellipse.
    """
    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = element_variables),
        environment = xsuite_environment)

    assert xsuite_environment.lines["test_apert"].element_names == [
        "test_apert_rect", "test_apert_ellipse"]
    rect = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert_rect",
        element_type = xt.LimitRect)
    assert rect.min_x < -1.0E9 and rect.max_x > 1.0E9, (
        "A degenerate x-axis bound (DX1 == DX2) should leave x effectively "
        "unconstrained on the Rect, not zero-width.")
    assert rect.min_y == pytest.approx(-0.005)
    assert rect.max_y == pytest.approx(0.02)

def test_aper_converter_treats_fully_degenerate_rect_as_ellipse_only(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    When both rectangular axes are degenerate (DX1 == DX2 and DY1 == DY2),
    no rectangular constraint survives on either axis, so a single
    LimitEllipse is sufficient and no split is needed.
    """
    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "ax": 0.01, "ay": 0.02,
                "dx1": 0.0, "dx2": 0.0,
                "dy1": 3.0, "dy2": 3.0,
            }),
        environment = xsuite_environment)

    assert "test_apert" not in xsuite_environment.lines, (
        "A fully-degenerate rectangular bound should collapse to a single "
        "LimitEllipse, not a split sub-line.")
    ellipse = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitEllipse)
    assert ellipse.a == pytest.approx(0.01)
    assert ellipse.b == pytest.approx(0.02)

################################################################################
# Error Handling
################################################################################
########################################
# Invalid Definitions
########################################
def test_aper_converter_empty_definition_raises_clear_error(
        parsed_elements,
        xsuite_environment):
    """
    SAD APERT elements without aperture limits should fail clearly.
    """
    with pytest.raises(ValueError, match = "no valid definition"):
        convert_apertures(
            parsed_elements = parsed_elements(
                element_type      = "apert",
                element_name      = "test_apert",
                element_variables = {}),
            environment = xsuite_environment)

################################################################################
# Pipeline Behaviour
################################################################################
########################################
# Full Conversion
########################################
def test_aper_pipeline_preserves_names_order_and_ellipse_parameters(write_lattice):
    """
    Full conversion should preserve SAD APERT names, order, and ellipse limits.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_DRIFT  = (L = 1.0);
        APERT       TEST_APERT  = (AX = 0.01 AY = 0.02 DX = 0.001 DY = -0.002);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT TEST_APERT END);
        """,
        filename = "aper_pipeline_preserves_ellipse_parameters.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.element_names == ["start", "test_drift", "test_apert", "end"], (
        "Converted APERT line should preserve SAD element order and names.")
    assert isinstance(line["test_apert"], xt.LimitEllipse), (
        "Elliptical SAD APERT should remain an Xsuite LimitEllipse.")
    assert line["test_apert"].a == pytest.approx(0.01), (
        "Pipeline APERT conversion should preserve SAD AX.")
    assert line["test_apert"].b == pytest.approx(0.02), (
        "Pipeline APERT conversion should preserve SAD AY.")
    assert line["test_apert"].shift_x == pytest.approx(0.001), (
        "Pipeline APERT conversion should preserve SAD DX.")
    assert line["test_apert"].shift_y == pytest.approx(-0.002), (
        "Pipeline APERT conversion should preserve SAD DY.")

def test_aper_pipeline_preserves_names_order_and_rectangle_parameters(write_lattice):
    """
    Full conversion should preserve SAD APERT names, order, and rectangle limits.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_DRIFT  = (L = 1.0);
        APERT       TEST_APERT  = (
            DX1     = -0.01
            DX2     = 0.02
            DY1     = -0.03
            DY2     = 0.04
            DX      = 0.001
            DY      = -0.002
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT TEST_APERT END);
        """,
        filename = "aper_pipeline_preserves_rectangle_parameters.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.element_names == ["start", "test_drift", "test_apert", "end"], (
        "Converted APERT line should preserve SAD element order and names.")
    assert isinstance(line["test_apert"], xt.LimitRect), (
        "Rectangular SAD APERT should remain an Xsuite LimitRect.")
    assert line["test_apert"].min_x == pytest.approx(-0.01), (
        "Pipeline APERT conversion should preserve SAD DX1.")
    assert line["test_apert"].max_x == pytest.approx(0.02), (
        "Pipeline APERT conversion should preserve SAD DX2.")
    assert line["test_apert"].min_y == pytest.approx(-0.03), (
        "Pipeline APERT conversion should preserve SAD DY1.")
    assert line["test_apert"].max_y == pytest.approx(0.04), (
        "Pipeline APERT conversion should preserve SAD DY2.")

def test_aper_pipeline_preserves_rectangle_rotation(write_lattice):
    """
    Full conversion should preserve rectangular APERT ROTATE.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_DRIFT  = (L = 1.0);
        APERT       TEST_APERT  = (
            DX1     = -0.01
            DX2     = 0.01
            DY1     = -0.02
            DY2     = 0.02
            ROTATE  = 30 DEG
        );

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT TEST_APERT END);
        """,
        filename = "aper_pipeline_preserves_rectangle_rotation.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.element_names == ["start", "test_drift", "test_apert", "end"], (
        "Converted APERT line should preserve SAD element order and names.")
    assert isinstance(line["test_apert"], xt.LimitRect), (
        "Rectangular SAD APERT should remain an Xsuite LimitRect.")
    assert line["test_apert"].rot_s_rad == pytest.approx(-np.deg2rad(30.0)), (
        "Pipeline APERT conversion should map SAD ROTATE to rot_s_rad = -ROTATE.")

def test_aper_pipeline_can_install_apertures_as_markers(write_lattice):
    """
    User option `install_apertures_as_markers` should install APERT as Marker.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_DRIFT  = (L = 1.0);
        APERT       TEST_APERT  = (AX = 0.01 AY = 0.02);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT TEST_APERT END);
        """,
        filename = "aper_pipeline_can_install_apertures_as_markers.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path             = str(lattice_path),
        output_directory             = "N/A",
        install_apertures_as_markers = True,
        _verbose                     = False,
        _test_mode                   = True)

    assert line.element_names == ["start", "test_drift", "test_apert", "end"], (
        "Aperture-to-marker conversion should preserve line order and names.")
    assert isinstance(line["test_apert"], xt.Marker), (
        "install_apertures_as_markers should convert APERT to Xsuite Marker.")

################################################################################
# Particle-Loss Equivalence
################################################################################
########################################
# Analytic Grid-Loss Tests
########################################
def test_aper_limitellipse_grid_loss_matches_analytic_boundary(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    A converted elliptical APERT should lose the same particles as SAD's
    ellipse. The aperture is built by CONVERTING a SAD APERT definition (not
    hand-constructed) so the converter's AX/AY mapping is tested end-to-end.
    """
    a = 0.01
    b = 0.02
    x_grid, y_grid = _ellipse_grid(a = a, b = b)
    expected_alive = _ellipse_alive(x_grid, y_grid, a = a, b = b)

    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {"ax": a, "ay": b}),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitEllipse)

    _assert_aperture_grid_matches(
        test_name            = (
            "test_aper_limitellipse_grid_loss_matches_analytic_boundary"),
        aperture             = aperture,
        aperture_description = "APERT TEST_APERT = (AX = 0.01 AY = 0.02);",
        x_grid               = x_grid,
        y_grid               = y_grid,
        expected_alive       = expected_alive,
        parameters           = {"ax": a, "ay": b},
        notes                = [
            "Aperture built by converting a SAD APERT definition so the "
            "converter AX/AY mapping is tested end-to-end.",
            "The grid intentionally concentrates particles near the aperture "
            "boundary rather than at the centre.",
        ])

def test_aper_limitrect_grid_loss_matches_analytic_boundary(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    A converted rectangular APERT should lose the same particles as SAD's
    rectangle. The aperture is built by CONVERTING a SAD APERT definition (not
    hand-constructed) so the converter's DX1/DX2/DY1/DY2 mapping is tested
    end-to-end.
    """
    min_x = -0.01
    max_x = 0.02
    min_y = -0.03
    max_y = 0.04
    x_grid, y_grid = _rectangle_grid(
        min_x = min_x,
        max_x = max_x,
        min_y = min_y,
        max_y = max_y)
    expected_alive = _rectangle_alive(
        x_grid,
        y_grid,
        min_x = min_x,
        max_x = max_x,
        min_y = min_y,
        max_y = max_y)

    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "dx1": min_x,
                "dx2": max_x,
                "dy1": min_y,
                "dy2": max_y,
            }),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitRect)

    _assert_aperture_grid_matches(
        test_name            = (
            "test_aper_limitrect_grid_loss_matches_analytic_boundary"),
        aperture             = aperture,
        aperture_description = (
            "APERT TEST_APERT = "
            "(DX1 = -0.01 DX2 = 0.02 DY1 = -0.03 DY2 = 0.04);"),
        x_grid               = x_grid,
        y_grid               = y_grid,
        expected_alive       = expected_alive,
        parameters           = {
            "dx1": min_x,
            "dx2": max_x,
            "dy1": min_y,
            "dy2": max_y,
        },
        notes                = [
            "Aperture built by converting a SAD APERT definition so the "
            "converter DX1/DX2/DY1/DY2 mapping is tested end-to-end.",
            "The grid intentionally concentrates particles near all four "
            "aperture edges.",
        ])

def test_aper_offset_limitellipse_grid_loss_matches_analytic_boundary(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    An offset elliptical APERT should lose particles using SAD's shifted
    boundary. The aperture is built by CONVERTING a SAD APERT definition (not
    hand-constructed) so the converter's DX/DY -> shift_x/shift_y mapping is
    tested end-to-end.
    """
    a = 0.01
    b = 0.02
    shift_x = 0.001
    shift_y = -0.002
    x_grid, y_grid = _ellipse_grid(
        a       = a,
        b       = b,
        shift_x = shift_x,
        shift_y = shift_y)
    expected_alive = _ellipse_alive(
        x_grid,
        y_grid,
        a       = a,
        b       = b,
        shift_x = shift_x,
        shift_y = shift_y)

    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "ax": a,
                "ay": b,
                "dx": shift_x,
                "dy": shift_y,
            }),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitEllipse)

    _assert_aperture_grid_matches(
        test_name            = (
            "test_aper_offset_limitellipse_grid_loss_matches_analytic_boundary"),
        aperture             = aperture,
        aperture_description = (
            "APERT TEST_APERT = "
            "(AX = 0.01 AY = 0.02 DX = 0.001 DY = -0.002);"),
        x_grid               = x_grid,
        y_grid               = y_grid,
        expected_alive       = expected_alive,
        parameters           = {
            "ax": a,
            "ay": b,
            "dx": shift_x,
            "dy": shift_y,
        },
        notes                = [
            "Aperture built by converting a SAD APERT definition so the "
            "converter DX/DY -> shift_x/shift_y mapping is tested end-to-end.",
        ])

def test_aper_offset_limitrect_grid_loss_matches_analytic_boundary(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    An offset rectangular APERT should lose particles using SAD's shifted
    boundary. The aperture is built by CONVERTING a SAD APERT definition (not
    hand-constructed) so the converter's bounds and DX/DY -> shift_x/shift_y
    mapping are tested end-to-end.
    """
    min_x = -0.01
    max_x = 0.02
    min_y = -0.03
    max_y = 0.04
    shift_x = 0.001
    shift_y = -0.002
    x_grid, y_grid = _rectangle_grid(
        min_x   = min_x,
        max_x   = max_x,
        min_y   = min_y,
        max_y   = max_y,
        shift_x = shift_x,
        shift_y = shift_y)
    expected_alive = _rectangle_alive(
        x_grid,
        y_grid,
        min_x   = min_x,
        max_x   = max_x,
        min_y   = min_y,
        max_y   = max_y,
        shift_x = shift_x,
        shift_y = shift_y)

    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "dx1": min_x,
                "dx2": max_x,
                "dy1": min_y,
                "dy2": max_y,
                "dx": shift_x,
                "dy": shift_y,
            }),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitRect)

    _assert_aperture_grid_matches(
        test_name            = (
            "test_aper_offset_limitrect_grid_loss_matches_analytic_boundary"),
        aperture             = aperture,
        aperture_description = (
            "APERT TEST_APERT = "
            "(DX1 = -0.01 DX2 = 0.02 DY1 = -0.03 DY2 = 0.04 "
            "DX = 0.001 DY = -0.002);"),
        x_grid               = x_grid,
        y_grid               = y_grid,
        expected_alive       = expected_alive,
        parameters           = {
            "dx1": min_x,
            "dx2": max_x,
            "dy1": min_y,
            "dy2": max_y,
            "dx": shift_x,
            "dy": shift_y,
        },
        notes                = [
            "Aperture built by converting a SAD APERT definition so the "
            "converter bounds and DX/DY -> shift mapping are tested end-to-end.",
        ])

def test_aper_rotated_limitrect_grid_loss_matches_sad_boundary(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    A converted rotated rectangular APERT loses exactly the particles real SAD
    loses.

    The aperture is built by converting a SAD APERT definition rather than
    hand-constructed, so the converter's ROTATE handling is exercised end to
    end. A 30 deg angle with off-axis probes makes the sign unambiguous: SAD's
    ROTATE = R is a coordinate rotation by -R, so (0.012, 0.012) survives
    while (-0.012, 0.012) is lost.
    """
    min_x = -0.01
    max_x = 0.01
    min_y = -0.02
    max_y = 0.02
    rotation = np.deg2rad(30.0)

    x_grid, y_grid = _rectangle_grid(
        min_x = min_x,
        max_x = max_x,
        min_y = min_y,
        max_y = max_y)

    # Off-axis probes that distinguish +rotation from -rotation. Real SAD
    # tracking at ROTATE = 30 deg gives survival [1, 0, 0, 1] for these.
    sad_probe_x = np.array([0.012, -0.012,  0.012, -0.012])
    sad_probe_y = np.array([0.012,  0.012, -0.012, -0.012])
    x_grid = np.concatenate([x_grid, sad_probe_x])
    y_grid = np.concatenate([y_grid, sad_probe_y])

    # SAD APERT ROTATE = R corresponds to a coordinate rotation by -R.
    expected_alive = _rotated_rectangle_alive(
        x_grid,
        y_grid,
        min_x    = min_x,
        max_x    = max_x,
        min_y    = min_y,
        max_y    = max_y,
        rotation = -rotation)

    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "dx1": min_x,
                "dx2": max_x,
                "dy1": min_y,
                "dy2": max_y,
                "rotate": rotation,
            }),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitRect)

    _assert_aperture_grid_matches(
        test_name            = (
            "test_aper_rotated_limitrect_grid_loss_matches_sad_boundary"),
        aperture             = aperture,
        aperture_description = (
            "APERT TEST_APERT = "
            "(DX1 = -0.01 DX2 = 0.01 DY1 = -0.02 DY2 = 0.02 "
            "ROTATE = 30 DEG);"),
        x_grid               = x_grid,
        y_grid               = y_grid,
        expected_alive       = expected_alive,
        parameters           = {
            "dx1": min_x,
            "dx2": max_x,
            "dy1": min_y,
            "dy2": max_y,
            "rotate": rotation,
        },
        notes                = [
            "Aperture built by converting a SAD APERT definition so the "
            "converter ROTATE handling is tested end-to-end.",
            "Real SAD tracking at ROTATE = 30 deg matched the analytic model "
            "at -ROTATE; off-axis probes pin the rotation sign.",
        ])

def test_aper_limitrectellipse_grid_loss_matches_analytic_boundary(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Combined SAD APERT limits should use the ellipse/rectangle intersection. The
    aperture is built by CONVERTING a SAD APERT definition (not hand-constructed)
    so the converter's combined AX/AY + DX1/DX2/DY1/DY2 mapping is tested
    end-to-end.
    """
    a = 0.02
    b = 0.03
    max_x = 0.01
    max_y = 0.015
    x_grid, y_grid = _ellipse_grid(a = a, b = b)
    rect_x, rect_y = _rectangle_grid(
        min_x = -max_x,
        max_x = max_x,
        min_y = -max_y,
        max_y = max_y)
    x_grid = np.concatenate([x_grid, rect_x])
    y_grid = np.concatenate([y_grid, rect_y])
    expected_alive = (
        _ellipse_alive(x_grid, y_grid, a = a, b = b) &
        _rectangle_alive(
            x_grid,
            y_grid,
            min_x = -max_x,
            max_x = max_x,
            min_y = -max_y,
            max_y = max_y)
    )

    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "ax": a,
                "ay": b,
                "dx1": -max_x,
                "dx2": max_x,
                "dy1": -max_y,
                "dy2": max_y,
            }),
        environment = xsuite_environment)

    aperture = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert",
        element_type = xt.LimitRectEllipse)

    _assert_aperture_grid_matches(
        test_name            = (
            "test_aper_limitrectellipse_grid_loss_matches_analytic_boundary"),
        aperture             = aperture,
        aperture_description = (
            "APERT TEST_APERT = "
            "(AX = 0.02 AY = 0.03 DX1 = -0.01 DX2 = 0.01 "
            "DY1 = -0.015 DY2 = 0.015);"),
        x_grid               = x_grid,
        y_grid               = y_grid,
        expected_alive       = expected_alive,
        parameters           = {
            "ax": a,
            "ay": b,
            "dx1": -max_x,
            "dx2": max_x,
            "dy1": -max_y,
            "dy2": max_y,
        },
        notes                = [
            "Aperture built by converting a SAD APERT definition so the "
            "converter combined-limit mapping is tested end-to-end.",
            "SAD documentation defines APERT survival as the intersection of "
            "the ellipse and rectangle conditions.",
        ])


def test_aper_split_rect_and_ellipse_grid_loss_matches_analytic_boundary(
        parsed_elements,
        xsuite_environment,
        assert_environment_element):
    """
    Tracking through a split (asymmetric-window) combined APERT's Rect and
    Ellipse should match the intersection of both analytic masks, same as
    real SAD (see tests/sad/test_apert.py::
    test_apert_combined_rect_and_ellipse_grid_requires_both).
    """
    a, b = 0.02, 0.02
    min_x, max_x, min_y, max_y = -0.005, 0.03, -0.03, 0.005
    x_grid, y_grid = _rectangle_grid(min_x, max_x, min_y, max_y)
    expected_alive = (
        _rectangle_alive(x_grid, y_grid, min_x, max_x, min_y, max_y) &
        _ellipse_alive(x_grid, y_grid, a, b)
    )

    convert_apertures(
        parsed_elements = parsed_elements(
            element_type      = "apert",
            element_name      = "test_apert",
            element_variables = {
                "ax": a,
                "ay": b,
                "dx1": min_x,
                "dx2": max_x,
                "dy1": min_y,
                "dy2": max_y,
            }),
        environment = xsuite_environment)

    assert xsuite_environment.lines["test_apert"].element_names == [
        "test_apert_rect", "test_apert_ellipse"], (
        "This asymmetric combined APERT should have been split.")

    rect = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert_rect",
        element_type = xt.LimitRect)
    ellipse = assert_environment_element(
        environment  = xsuite_environment,
        element_name = "test_apert_ellipse",
        element_type = xt.LimitEllipse)

    _assert_apertures_grid_matches(
        test_name            = (
            "test_aper_split_rect_and_ellipse_grid_loss_matches_analytic_boundary"),
        apertures            = [rect, ellipse],
        aperture_names       = ["test_apert_rect", "test_apert_ellipse"],
        aperture_description = (
            "APERT TEST_APERT = "
            "(AX = 0.02 AY = 0.02 DX1 = -0.005 DX2 = 0.03 "
            "DY1 = -0.03 DY2 = 0.005);"),
        x_grid               = x_grid,
        y_grid               = y_grid,
        expected_alive       = expected_alive,
        parameters           = {
            "ax": a,
            "ay": b,
            "dx1": min_x,
            "dx2": max_x,
            "dy1": min_y,
            "dy2": max_y,
        },
        notes                = [
            "Aperture built by converting a SAD APERT definition, split "
            "into LimitRect + LimitEllipse inside a named sub-line, and "
            "tracked as a two-element line so the converter's split path "
            "is tested end-to-end.",
            "The rectangular window is deliberately asymmetric; a converter "
            "that forced it into a single symmetric LimitRectEllipse would "
            "fail this comparison.",
        ])
