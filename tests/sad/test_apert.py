"""
================================================================================
SAD syntax assumptions: APERT element
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
import os

import numpy as np
import pytest

from sad2xs.sad_helpers import track_sad, twiss_sad

################################################################################
# Accepted parameters
# APERT supports multiple aperture shapes (ellipse, rect, rectellipse), each
# with their own parameter set. DX, DY, ROTATE are non-obvious.
################################################################################
ACCEPTED_PARAMS = [
    pytest.param("AX=0.05",                       id = "ax"),
    pytest.param("AY=0.03",                       id = "ay"),
    pytest.param("AX=0.05 AY=0.03 DX=0.001",       id = "dx"),
    pytest.param("AX=0.05 AY=0.03 DY=0.001",       id = "dy"),
    pytest.param("AX=0.05 AY=0.03 ROTATE=0.1",     id = "rotate"),
    pytest.param("DX1=-0.01 DX2=0.02",             id = "dx1_dx2"),
    pytest.param("DY1=-0.01 DY2=0.02",             id = "dy1_dy2"),
]

@pytest.mark.parametrize("params", ACCEPTED_PARAMS)
def test_apert_accepts(sad_accepts, params):
    """
    SAD's APERT element should accept AX/AY (ellipse), DX1-DY2
    (rectangle), and the DX/DY/ROTATE geometry parameters.
    """
    sad_accepts(
        f"APERT A1 = ({params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")

################################################################################
# Effect on Twiss
################################################################################
def test_apert_does_not_affect_twiss_betx(tmp_path):
    """
    An APERT with AX/AY/DX1-DY2 set should give the same Twiss betx as a
    bare APERT — apertures are transparent to the optics, only tracking
    can lose a particle on one.
    """
    def run(apert_params, name):
        lat = tmp_path / name
        lat.write_text(
            "MOMENTUM = 1.0 GEV;\n"
            f"APERT A1 = ({apert_params});\n"
            "DRIFT D = (L=1.0);\n"
            "MARK START = ()\n     END   = ();\n"
            "LINE TEST = (START D A1 D END);\n")
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            return twiss_sad(
                lattice_filepath    = lat.name,
                line_name           = "TEST",
                calc6d              = False,
                closed              = False,
                additional_commands = "")
        finally:
            os.chdir(cwd)

    tw_bare = run("AX=0.05 AY=0.05", "apert_bare_twiss.sad")
    tw_set  = run(
        "AX=0.05 AY=0.05 DX1=-0.03 DX2=0.03 DY1=-0.03 DY2=0.03",
        "apert_set_twiss.sad")
    assert tw_set["betx"][-1] == pytest.approx(tw_bare["betx"][-1]), (
        "An APERT with DX1-DY2 set should give the same Twiss betx as one "
        "without them.")

################################################################################
# Effect on tracking: grid-based ground truth
#
# These tests establish, against real SAD, the same analytic pass/fail
# formulas already trusted at the converter/Xsuite level
# (tests/conversion/elements/test_apert.py's _ellipse_alive / _rectangle_alive
# / _rotated_rectangle_alive) — confirming the model the converter assumes
# is correct, not just internally self-consistent within Xsuite.
#
# The DX1==DX2 degenerate-rectangle-bound case and the DX-recentres-both-
# terms case both match the SAD manual once read correctly (see their own
# docstrings). Only one sub-case remains a genuine, unresolved discrepancy:
# a missing ellipse axis (AX or AY entirely omitted) does not behave as
# "infinite" — see test_apert_missing_ellipse_axis_behavior. This is under
# active discussion with the SAD side.
################################################################################
def _track_apert_grid(tmp_path, name, apert_params, x_grid, y_grid):
    """
    Track a grid of particles (all other coordinates zero) through a single
    APERT element and return the alive mask (state == 1).
    """
    lat = tmp_path / name
    lat.write_text(
        "MOMENTUM = 1.0 GEV;\n"
        f"APERT A1 = ({apert_params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);\n")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = track_sad(
            lattice_filepath    = lat.name,
            line_name           = "TEST",
            x_init              = x_grid.copy(),
            px_init             = np.zeros_like(x_grid),
            y_init              = y_grid.copy(),
            py_init             = np.zeros_like(x_grid),
            zeta_init           = np.zeros_like(x_grid),
            delta_init          = np.zeros_like(x_grid),
            n_turns             = 1,
            rfsw                = False,
            with_progress       = False,
            wall_time           = 120)
    finally:
        os.chdir(cwd)
    return result["state"] == 1


def _ellipse_grid(a, b, shift_x = 0.0, shift_y = 0.0):
    """
    Deterministic ellipse-focused test particles (mirrors the converter-level helper).
    """
    angles = np.linspace(0.0, 2.0 * np.pi, 16, endpoint = False)
    radii = np.array([0.25, 0.75, 0.99, 1.01, 1.25])
    x_values, y_values = [], []
    for radius in radii:
        x_values.extend(shift_x + radius * a * np.cos(angles))
        y_values.extend(shift_y + radius * b * np.sin(angles))
    return np.array(x_values), np.array(y_values)

def _ellipse_alive(x_values, y_values, a, b, shift_x = 0.0, shift_y = 0.0):
    """
    Analytic ellipse alive mask (mirrors the converter-level helper).
    """
    x_local = x_values - shift_x
    y_local = y_values - shift_y
    return (x_local / a) ** 2 + (y_local / b) ** 2 < 1.0

def _rectangle_grid(min_x, max_x, min_y, max_y, shift_x = 0.0, shift_y = 0.0):
    """
    Deterministic rectangle-focused test particles (mirrors the converter-level helper).
    """
    x_edges = shift_x + np.array([
        1.25 * min_x, 1.01 * min_x, 0.99 * min_x, 0.0,
        0.99 * max_x, 1.01 * max_x, 1.25 * max_x])
    y_edges = shift_y + np.array([
        1.25 * min_y, 1.01 * min_y, 0.99 * min_y, 0.0,
        0.99 * max_y, 1.01 * max_y, 1.25 * max_y])
    xx, yy = np.meshgrid(x_edges, y_edges)
    return xx.ravel(), yy.ravel()

def _rectangle_alive(x_values, y_values, min_x, max_x, min_y, max_y,
                      shift_x = 0.0, shift_y = 0.0):
    """
    Analytic rectangle alive mask (mirrors the converter-level helper).
    """
    x_local = x_values - shift_x
    y_local = y_values - shift_y
    return (min_x < x_local) & (x_local < max_x) & (min_y < y_local) & (y_local < max_y)

def _rotated_rectangle_alive(x_values, y_values, min_x, max_x, min_y, max_y,
                              rotation, shift_x = 0.0, shift_y = 0.0):
    """
    Analytic rotated-rectangle alive mask (mirrors the converter-level helper).
    """
    x_shifted = x_values - shift_x
    y_shifted = y_values - shift_y
    x_local =  x_shifted * np.cos(rotation) + y_shifted * np.sin(rotation)
    y_local = -x_shifted * np.sin(rotation) + y_shifted * np.cos(rotation)
    return (min_x < x_local) & (x_local < max_x) & (min_y < y_local) & (y_local < max_y)


def test_apert_ellipse_grid_matches_analytic_boundary(tmp_path):
    """
    A pure elliptical APERT's pass/fail pattern over a grid should match the
    standard ellipse formula (x/AX)^2 + (y/AY)^2 < 1.
    """
    a, b = 0.02, 0.03
    x_grid, y_grid = _ellipse_grid(a, b)
    expected_alive = _ellipse_alive(x_grid, y_grid, a, b)
    alive = _track_apert_grid(
        tmp_path, "apert_ellipse_grid.sad", f"AX={a} AY={b}", x_grid, y_grid)
    assert np.array_equal(alive, expected_alive), (
        f"Ellipse grid mismatch. Mismatches: {np.count_nonzero(alive != expected_alive)}.\n"
        f"x: {x_grid}\ny: {y_grid}\nexpected: {expected_alive}\ngot: {alive}")


def test_apert_asymmetric_rectangle_grid_matches_analytic_boundary(tmp_path):
    """
    An asymmetric rectangular APERT (DX1 != -DX2) should match
    min(DX1,DX2) < x < max(DX1,DX2) exactly — this is the case that would
    catch a converter mapping DX1/DX2 onto a symmetric bound.
    """
    min_x, max_x, min_y, max_y = -0.005, 0.02, -0.01, 0.03
    x_grid, y_grid = _rectangle_grid(min_x, max_x, min_y, max_y)
    expected_alive = _rectangle_alive(x_grid, y_grid, min_x, max_x, min_y, max_y)
    alive = _track_apert_grid(
        tmp_path, "apert_rect_grid.sad",
        f"DX1={min_x} DX2={max_x} DY1={min_y} DY2={max_y}", x_grid, y_grid)
    assert np.array_equal(alive, expected_alive), (
        f"Asymmetric rectangle grid mismatch. "
        f"Mismatches: {np.count_nonzero(alive != expected_alive)}.\n"
        f"x: {x_grid}\ny: {y_grid}\nexpected: {expected_alive}\ngot: {alive}")


def test_apert_combined_rect_and_ellipse_grid_requires_both(tmp_path):
    """
    A combined rect+ellipse APERT should require BOTH conditions (AND
    logic): the pass/fail pattern should match the intersection of the two
    analytic masks, not either alone.
    """
    a, b = 0.02, 0.02
    min_x, max_x, min_y, max_y = -0.005, 0.03, -0.03, 0.005
    x_grid, y_grid = _rectangle_grid(min_x, max_x, min_y, max_y)
    expected_alive = (
        _rectangle_alive(x_grid, y_grid, min_x, max_x, min_y, max_y) &
        _ellipse_alive(x_grid, y_grid, a, b))
    alive = _track_apert_grid(
        tmp_path, "apert_combined_grid.sad",
        f"AX={a} AY={b} DX1={min_x} DX2={max_x} DY1={min_y} DY2={max_y}",
        x_grid, y_grid)
    assert np.array_equal(alive, expected_alive), (
        f"Combined rect+ellipse grid mismatch. "
        f"Mismatches: {np.count_nonzero(alive != expected_alive)}.\n"
        f"x: {x_grid}\ny: {y_grid}\nexpected: {expected_alive}\ngot: {alive}")


def test_apert_rotated_rectangle_grid_matches_analytic_boundary(tmp_path):
    """
    A rotated rectangular APERT's pass/fail pattern should match the
    standard rotation-matrix transform of the rectangle bound.
    """
    min_x, max_x, min_y, max_y = -0.03, 0.03, -0.005, 0.005
    rotation = np.pi / 6.0
    x_grid, y_grid = _rectangle_grid(min_x, max_x, min_y, max_y)
    expected_alive = _rotated_rectangle_alive(
        x_grid, y_grid, min_x, max_x, min_y, max_y, rotation)
    alive = _track_apert_grid(
        tmp_path, "apert_rotated_rect_grid.sad",
        f"DX1={min_x} DX2={max_x} DY1={min_y} DY2={max_y} ROTATE={-rotation}",
        x_grid, y_grid)
    assert np.array_equal(alive, expected_alive), (
        f"Rotated rectangle grid mismatch (SAD ROTATE = -rotation, matching "
        f"the sign convention verified elsewhere for magnet rot_s_rad). "
        f"Mismatches: {np.count_nonzero(alive != expected_alive)}.\n"
        f"x: {x_grid}\ny: {y_grid}\nexpected: {expected_alive}\ngot: {alive}")


def test_apert_offset_shifts_both_ellipse_and_rectangle(tmp_path):
    """
    A SAD APERT DX offset recentres both the ellipse and the rectangle.

    Tracks probes at x = 0.000, 0.009, 0.015 with DX1=-0.01, DX2=0.01,
    AX=AY=0.005, DX=0.01, and asserts which survive. The rectangle clause is
    min(DX1,DX2) < (x-DX) < max(DX1,DX2), equivalent to testing raw x against
    the shifted bound. A raw-x reading would wrongly reject x=0.015.
    """
    x0 = np.array([0.000, 0.009, 0.015])
    y0 = np.array([0.000, 0.000, 0.000])
    expected_alive = np.array([False, True, True])
    alive = _track_apert_grid(
        tmp_path, "apert_offset_grid.sad",
        "AX=0.005 AY=0.005 DX1=-0.01 DX2=0.01 DX=0.01", x0, y0)
    assert np.array_equal(alive, expected_alive), (
        f"DX should recentre both the ellipse and rectangle terms "
        f"(min(DX1,DX2) < x-DX < max(DX1,DX2)). "
        f"expected: {expected_alive}\ngot: {alive}")


def test_apert_missing_ellipse_axis_behavior(tmp_path):
    """
    OBSERVED BEHAVIOUR, not yet confirmed against the SAD manual: an APERT
    with only AX set (AY entirely omitted) currently rejects even a
    dead-centre (x=0, y=0) particle in this SAD build, contradicting the
    documented "absent axis = infinite" rule. This test pins the CURRENT
    behaviour, so a future fix, or a correction of this test if the manual is
    confirmed right, is a deliberate and visible change.
    """
    alive = _track_apert_grid(
        tmp_path, "apert_missing_axis.sad", "AX=0.01",
        np.array([0.0]), np.array([0.0]))
    assert alive[0] == False, (  # noqa: E712 (explicit for clarity against the disputed claim)
        "CURRENT (disputed) behaviour: a dead-centre particle is lost when "
        "only AX is set. If this starts failing, either SAD's behaviour "
        "changed or this has been fixed/clarified — update this test's "
        "expectation deliberately, don't just relax it.")


def test_apert_degenerate_rectangle_bound_behavior(tmp_path):
    """
    Per the SAD documentation, AX!=0 && AY!=0 with DX1==DX2 should fall back
    to an ellipse-only aperture (not a zero-width, always-reject rectangle).
    Confirmed with commas fixed: a particle inside the ellipse but at
    x != 0 survives despite DX1==DX2==0.
    """
    x0 = np.array([0.005, 0.020])
    y0 = np.array([0.000, 0.000])
    expected_alive = np.array([True, False])
    # x=0.005: literal rect bound (0 < x < 0) would reject this if taken at
    #   face value; the ellipse-only fallback allows it: (0.5)^2 = 0.25 < 1.
    # x=0.020: still outside the ellipse: (2.0)^2 = 4 > 1 -> lost regardless.
    alive = _track_apert_grid(
        tmp_path, "apert_degenerate_rect.sad",
        "AX=0.01 AY=0.01 DX1=0.0 DX2=0.0", x0, y0)
    assert np.array_equal(alive, expected_alive), (
        f"DX1==DX2 with AX,AY both nonzero should fall back to an "
        f"ellipse-only aperture. expected: {expected_alive}\ngot: {alive}")

################################################################################
# Rejected parameters
# APERT is a geometry element — it has no magnetic field parameters. See
# tests/sad/README.md's "Parameter matrix" for the full accepted/rejected
# table this parametrization transcribes.
################################################################################
REJECTED_PARAMS = [
    pytest.param("AX=0.05 AY=0.03 ANGLE=0.01", id = "angle"),
    pytest.param("AX=0.05 AY=0.03 K0=0.1",     id = "k0"),
    pytest.param("AX=0.05 AY=0.03 SK0=0.1",    id = "sk0"),
    pytest.param("AX=0.05 AY=0.03 K1=0.1",     id = "k1"),
    pytest.param("AX=0.05 AY=0.03 SK1=0.1",    id = "sk1"),
    pytest.param("AX=0.05 AY=0.03 K2=0.1",     id = "k2"),
    pytest.param("AX=0.05 AY=0.03 SK2=0.1",    id = "sk2"),
    pytest.param("AX=0.05 AY=0.03 K3=0.1",     id = "k3"),
    pytest.param("AX=0.05 AY=0.03 SK3=0.1",    id = "sk3"),
    pytest.param("AX=0.05 AY=0.03 K4=0.1",     id = "k4"),
    pytest.param("AX=0.05 AY=0.03 SK4=0.1",    id = "sk4"),
    pytest.param("AX=0.05 AY=0.03 BZ=0.1",     id = "bz"),
    pytest.param("AX=0.05 AY=0.03 HARM=1000",  id = "harm"),
    pytest.param("AX=0.05 AY=0.03 FREQ=400E6", id = "freq"),
    pytest.param("AX=0.05 AY=0.03 FRINGE=1",   id = "fringe"),
    pytest.param("AX=0.05 AY=0.03 DISFRIN=1",  id = "disfrin"),
    pytest.param("AX=0.05 AY=0.03 F1=0.1",     id = "f1"),
    pytest.param("AX=0.05 AY=0.03 F2=0.1",     id = "f2"),
    pytest.param("AX=0.05 AY=0.03 FB1=0.1",    id = "fb1"),
    pytest.param("AX=0.05 AY=0.03 FB2=0.1",    id = "fb2"),
    pytest.param("AX=0.05 AY=0.03 F1K1F=0.1",  id = "f1k1f"),
    pytest.param("AX=0.05 AY=0.03 F2K1F=0.1",  id = "f2k1f"),
    pytest.param("AX=0.05 AY=0.03 F1K1B=0.1",  id = "f1k1b"),
    pytest.param("AX=0.05 AY=0.03 F2K1B=0.1",  id = "f2k1b"),
]

@pytest.mark.parametrize("params", REJECTED_PARAMS)
def test_apert_rejects(sad_rejects, params):
    """
    SAD's APERT element is pure geometry and should reject every magnetic
    field, solenoid, RF, and fringe (FRINGE/DISFRIN/F1/F2/FB1/FB2/F1K1x)
    parameter.
    """
    sad_rejects(
        f"APERT A1 = ({params});\n"
        "MARK START = ()\n     END   = ();\n"
        "LINE TEST = (START A1 END);")
