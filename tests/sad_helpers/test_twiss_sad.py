"""
================================================================================
Tests for sad2xs.sad_helpers.twiss
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
import numpy as np
import pytest

from tests.support.lattices import (
    write_asymmetric_closed_ring, write_minimal_bend_lattice,
    write_minimal_transfer_lattice, write_minimal_vertical_bend_lattice)
from sad2xs.sad_helpers import (
    compute_chromatic_functions,
    compute_second_order_dispersions,
    twiss_sad)
from sad2xs.sad_helpers.twiss import generate_twiss_print_function

################################################################################
# Helpers
################################################################################
def _run_twiss(tmp_path, monkeypatch, **kwargs):
    """
    Write the minimal drift transfer-line lattice, change to its directory,
    and run twiss_sad with closed=False, calc6d=False, wall_time=30. Extra
    keyword arguments are forwarded to twiss_sad to allow per-test flag
    overrides (e.g. reverse_element_order=True).
    """
    filename, line_name = write_minimal_transfer_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    return twiss_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        closed           = False,
        calc6d           = False,
        wall_time        = 30,
        **kwargs)


def _run_twiss_on_bend_lattice(tmp_path, monkeypatch, **kwargs):
    """
    Write the minimal bend transfer-line lattice, change to its directory, and
    run twiss_sad with closed=False, calc6d=False, wall_time=30. Extra keyword
    arguments are forwarded to twiss_sad.
    """
    filename, line_name = write_minimal_bend_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    return twiss_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        closed           = False,
        calc6d           = False,
        wall_time        = 30,
        **kwargs)


def _run_twiss_on_vertical_bend_lattice(tmp_path, monkeypatch, **kwargs):
    """
    Write the minimal vertical-bend transfer-line lattice, change to its
    directory, and run twiss_sad with closed=False, calc6d=False,
    wall_time=30. Extra keyword arguments are forwarded to twiss_sad.
    """
    filename, line_name = write_minimal_vertical_bend_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    return twiss_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        closed           = False,
        calc6d           = False,
        wall_time        = 30,
        **kwargs)


def _run_second_order_dispersions(tmp_path, monkeypatch):
    """
    Write the minimal drift transfer-line lattice and run
    compute_second_order_dispersions with closed=False, calc6d=False,
    wall_time=30.
    """
    filename, line_name = write_minimal_transfer_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    return compute_second_order_dispersions(
        lattice_filepath = filename,
        line_name        = line_name,
        closed           = False,
        calc6d           = False,
        wall_time        = 30)


def _run_chromatic_functions(tmp_path, monkeypatch):
    """
    Write the minimal drift transfer-line lattice and run
    compute_chromatic_functions with closed=False, calc6d=False, wall_time=30.
    """
    filename, line_name = write_minimal_transfer_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    return compute_chromatic_functions(
        lattice_filepath = filename,
        line_name        = line_name,
        closed           = False,
        calc6d           = False,
        wall_time        = 30)


################################################################################
# Command Generation Tests (SAD not required)
################################################################################
def test_generate_twiss_print_function_returns_string():
    """
    generate_twiss_print_function should return a non-empty string containing
    the SAD macro definition.
    """
    result = generate_twiss_print_function()

    assert isinstance(result, str), (
        "generate_twiss_print_function should return a str. "
        f"Got: {type(result).__name__}.")
    assert len(result) > 0, (
        "generate_twiss_print_function should return a non-empty string.")


def test_generate_twiss_print_function_defines_save_twiss_file():
    """
    The returned string should define a SAD function named SaveTwissFile that
    accepts a filename argument. This function is called inside twiss_sad to
    write the Twiss output.
    """
    result = generate_twiss_print_function()

    assert "SaveTwissFile[filename_]" in result, (
        "generate_twiss_print_function should define `SaveTwissFile[filename_]`. "
        f"Got: {result[:200]!r}.")


def test_generate_twiss_print_function_includes_optics_columns():
    """
    The macro string should include the Twiss column names that are consumed by
    twiss_sad when constructing the returned TwissTable: BETX, BETY, ALFX,
    ALFY, MUX, MUY.
    """
    result = generate_twiss_print_function()

    for column in ("BETX", "BETY", "ALFX", "ALFY", "MUX", "MUY"):
        assert column in result, (
            f"generate_twiss_print_function should include column `{column}`. "
            f"Got: {result[:200]!r}.")


def test_generate_twiss_print_function_includes_dispersion_and_coupling_columns():
    """
    The macro string should include the dispersion columns (DX, DY, DPX, DPY)
    and the coupling columns (R1, R2, R3, R4) used by twiss_sad.
    """
    result = generate_twiss_print_function()

    for column in ("DX", "DY", "DPX", "DPY", "R1", "R2", "R3", "R4"):
        assert column in result, (
            f"generate_twiss_print_function should include column `{column}`. "
            f"Got: {result[:200]!r}.")


################################################################################
# twiss_sad Smoke Tests (SAD required)
################################################################################
def test_twiss_sad_runs_minimal_transfer_line_and_returns_twiss_table(
        tmp_path,
        monkeypatch):
    """
    twiss_sad should run SAD on a minimal transfer-line lattice and return
    Twiss data for the requested line.
    """
    twiss = _run_twiss(tmp_path, monkeypatch)

    assert "START" in twiss.name, (
        "twiss_sad should return a Twiss table containing the START marker.")
    assert "END" in twiss.name, (
        "twiss_sad should return a Twiss table containing the END marker.")
    assert twiss["s", "END"] == pytest.approx(1.0), (
        "twiss_sad should preserve the minimal lattice length in the returned "
        "Twiss table.")


def test_twiss_sad_returns_table_with_expected_optics_columns(
        tmp_path,
        monkeypatch):
    """
    The TwissTable returned by twiss_sad should contain all standard optics
    columns: betx, bety, alfx, alfy, mux, muy, dx, dy, dpx, dpy.
    """
    twiss = _run_twiss(tmp_path, monkeypatch)

    for column in ("betx", "bety", "alfx", "alfy", "mux", "muy",
                   "dx", "dy", "dpx", "dpy"):
        assert column in twiss.keys(), (
            f"twiss_sad should return a table with column `{column}`.")


def test_twiss_sad_elements_are_sorted_by_s_position(tmp_path, monkeypatch):
    """
    twiss_sad should return elements sorted by s-position (ascending). The
    function calls np.argsort internally; this test confirms that contract is
    met on real SAD output.
    """
    twiss    = _run_twiss(tmp_path, monkeypatch)
    s_values = list(twiss.s)

    assert s_values == sorted(s_values), (
        "twiss_sad should return elements sorted by s-position (ascending). "
        f"Got s values: {s_values}.")


def test_twiss_sad_s_at_start_is_zero(tmp_path, monkeypatch):
    """
    The START marker should always be at s = 0 in a transfer-line Twiss. This
    is a geometric identity independent of lattice physics.
    """
    twiss = _run_twiss(tmp_path, monkeypatch)

    assert twiss["s", "START"] == pytest.approx(0.0), (
        "START marker should be at s = 0 in a transfer-line Twiss. "
        f"""Got: s = {twiss["s", "START"]}.""")


def test_twiss_sad_no_nan_in_standard_columns(tmp_path, monkeypatch):
    """
    All standard Twiss columns should be finite (no NaN or Inf) on valid SAD
    output. A NaN indicates a parsing failure or column mis-mapping in our
    wrapper, not a SAD physics error.
    """
    twiss = _run_twiss(tmp_path, monkeypatch)

    for column in ("s", "betx", "bety", "alfx", "alfy",
                   "mux", "muy", "dx", "dy", "dpx", "dpy",
                   "x", "y", "px", "py"):
        values = np.asarray(getattr(twiss, column))
        assert np.all(np.isfinite(values)), (
            f"Column `{column}` should contain only finite values. "
            f"Got: {values}.")


def test_twiss_sad_beta_functions_are_positive(tmp_path, monkeypatch):
    """
    Beta functions are positive definite by definition. A zero or negative
    value indicates a mis-mapped column or a sign error in a reversal
    transformation.
    """
    twiss = _run_twiss(tmp_path, monkeypatch)

    assert np.all(np.asarray(twiss.betx) > 0), (
        "betx should be positive everywhere. "
        f"Got betx: {list(twiss.betx)}.")
    assert np.all(np.asarray(twiss.bety) > 0), (
        "bety should be positive everywhere. "
        f"Got bety: {list(twiss.bety)}.")


def test_twiss_sad_orbit_is_zero_for_straight_lattice(tmp_path, monkeypatch):
    """
    A straight drift-only lattice with no orbit correction should have x = 0
    and y = 0 at all elements. A non-zero orbit here would indicate a
    column transposition or a parsing error.
    """
    twiss = _run_twiss(tmp_path, monkeypatch)

    assert np.allclose(twiss.x, 0.0, atol = 1E-12), (
        "Orbit x should be 0 everywhere in a straight lattice. "
        f"Got x: {list(twiss.x)}.")
    assert np.allclose(twiss.y, 0.0, atol = 1E-12), (
        "Orbit y should be 0 everywhere in a straight lattice. "
        f"Got y: {list(twiss.y)}.")


def test_twiss_sad_dispersion_is_zero_for_drift_only_lattice(
        tmp_path,
        monkeypatch):
    """
    A lattice with no bending elements has zero dispersion everywhere. A
    non-zero dx/dy indicates a column mis-mapping in the TFS parser output.
    """
    twiss = _run_twiss(tmp_path, monkeypatch)

    assert np.allclose(twiss.dx, 0.0, atol = 1E-12), (
        "Dispersion dx should be 0 everywhere in a drift-only lattice. "
        f"Got dx: {list(twiss.dx)}.")
    assert np.allclose(twiss.dy, 0.0, atol = 1E-12), (
        "Dispersion dy should be 0 everywhere in a drift-only lattice. "
        f"Got dy: {list(twiss.dy)}.")


def test_twiss_sad_reverse_element_order_puts_end_before_start(
        tmp_path,
        monkeypatch):
    """
    With reverse_element_order=True the name array should be reversed so that
    END appears before START. This tests our transformation code, not SAD's
    physics.
    """
    twiss = _run_twiss(tmp_path, monkeypatch, reverse_element_order = True)
    names = list(twiss.name)

    assert "START" in names and "END" in names, (
        "Reversed table should still contain START and END. "
        f"Got names: {names}.")
    assert names.index("END") < names.index("START"), (
        "With reverse_element_order=True, END should appear before START. "
        f"Got names: {names}.")


def test_twiss_sad_reverse_element_order_matches_sad_native_reversed_line(
        tmp_path,
        monkeypatch):
    """
    twiss_sad's reverse_element_order matches SAD's own native line reversal
    row for row, not merely END before START.

    Compares against a REV line defined directly in the lattice file, an
    independent SAD calculation that does not use the reverse_element_order
    path. The ring is deliberately asymmetric. This catches row-mislabelling,
    where every row shifts by one element because SAD treats a row as its
    element's entrance.
    """
    filename, fwd_name, rev_name = write_asymmetric_closed_ring(tmp_path)
    monkeypatch.chdir(tmp_path)

    tw_native = twiss_sad(
        lattice_filepath = filename,
        line_name        = rev_name,
        closed           = True,
        calc6d           = False,
        wall_time        = 30)

    tw_reversed = twiss_sad(
        lattice_filepath      = filename,
        line_name             = fwd_name,
        closed                = True,
        calc6d                = False,
        reverse_element_order = True,
        wall_time             = 30)

    name_to_idx_native   = {n: i for i, n in enumerate(tw_native.name)}
    name_to_idx_reversed = {n: i for i, n in enumerate(tw_reversed.name)}

    assert set(name_to_idx_native) == set(name_to_idx_reversed), (
        "Expected the native REV line and reverse_element_order=True to "
        f"share exactly the same element names. Native: {list(tw_native.name)}, "
        f"reversed: {list(tw_reversed.name)}.")

    for column in ("betx", "bety", "alfx", "alfy", "mux", "muy", "dx", "dy"):
        for name in name_to_idx_native:
            native_val   = tw_native[column][name_to_idx_native[name]]
            reversed_val = tw_reversed[column][name_to_idx_reversed[name]]
            assert reversed_val == pytest.approx(native_val, abs = 1E-9), (
                f"twiss_sad(reverse_element_order=True) column `{column}` at "
                f"`{name}` should match SAD's native REV line exactly. "
                f"Native: {native_val}, reversed: {reversed_val}.")


def test_twiss_sad_reverse_survey_horizontal_flips_x_plane_dispersion(
        tmp_path,
        monkeypatch):
    """
    reverse_survey_horizontal=True should negate the horizontal dispersion (dx,
    dpx) everywhere, leaving dy/dpy unchanged. This transformation is applied
    in our wrapper code to handle lattices where the bend direction is reversed
    with respect to the SAD coordinate convention. The test requires a lattice
    with a non-zero bend angle so that dx != 0 at the END marker.
    """
    twiss_forward  = _run_twiss_on_bend_lattice(
        tmp_path, monkeypatch, reverse_survey_horizontal = False)
    twiss_reversed = _run_twiss_on_bend_lattice(
        tmp_path, monkeypatch, reverse_survey_horizontal = True)

    dx_forward  = np.asarray(twiss_forward.dx)
    dx_reversed = np.asarray(twiss_reversed.dx)

    assert not np.allclose(dx_forward, 0.0, atol = 1E-6), (
        "The bend lattice should produce non-zero dispersion dx so that the "
        f"sign-flip can be verified. Got dx_forward: {list(dx_forward)}.")
    assert np.allclose(dx_reversed, -dx_forward, atol = 1E-12), (
        "reverse_survey_horizontal=True should negate dx everywhere. "
        f"dx_forward: {list(dx_forward)}; dx_reversed: {list(dx_reversed)}.")

    dpx_forward  = np.asarray(twiss_forward.dpx)
    dpx_reversed = np.asarray(twiss_reversed.dpx)

    assert np.allclose(dpx_reversed, -dpx_forward, atol = 1E-12), (
        "reverse_survey_horizontal=True should negate dpx everywhere. "
        f"dpx_forward: {list(dpx_forward)}; dpx_reversed: {list(dpx_reversed)}.")


def test_twiss_sad_reverse_survey_vertical_flips_y_plane_dispersion(
        tmp_path,
        monkeypatch):
    """
    reverse_survey_vertical=True should negate the vertical dispersion (dy,
    dpy) everywhere, leaving dx/dpx unchanged. Requires a vertical bend
    (ROTATE = pi/2) so that dy != 0 at the END marker -- the plain
    horizontal bend lattice used for the horizontal test has zero vertical
    dispersion.
    """
    twiss_forward  = _run_twiss_on_vertical_bend_lattice(
        tmp_path, monkeypatch, reverse_survey_vertical = False)
    twiss_reversed = _run_twiss_on_vertical_bend_lattice(
        tmp_path, monkeypatch, reverse_survey_vertical = True)

    dy_forward  = np.asarray(twiss_forward.dy)
    dy_reversed = np.asarray(twiss_reversed.dy)

    assert not np.allclose(dy_forward, 0.0, atol = 1E-6), (
        "The vertical bend lattice should produce non-zero dispersion dy so "
        f"that the sign-flip can be verified. Got dy_forward: {list(dy_forward)}.")
    assert np.allclose(dy_reversed, -dy_forward, atol = 1E-12), (
        "reverse_survey_vertical=True should negate dy everywhere. "
        f"dy_forward: {list(dy_forward)}; dy_reversed: {list(dy_reversed)}.")

    dpy_forward  = np.asarray(twiss_forward.dpy)
    dpy_reversed = np.asarray(twiss_reversed.dpy)

    assert np.allclose(dpy_reversed, -dpy_forward, atol = 1E-12), (
        "reverse_survey_vertical=True should negate dpy everywhere. "
        f"dpy_forward: {list(dpy_forward)}; dpy_reversed: {list(dpy_reversed)}.")


def test_twiss_sad_trpt_carries_reference_momentum_through_acceleration(
        tmp_path,
        monkeypatch):
    """
    trpt=True should declare the line a transport line, carrying the
    nominal/reference momentum along with an accelerating element instead
    of holding it fixed at the line's initial MOMENTUM. Without it, delta
    at the end of a strongly-accelerating element is reported relative to
    the fixed initial momentum and is not close to zero; with it, the
    reference tracks the acceleration and delta is close to zero. See
    docs/reference/sad-behaviour.md for the underlying physics.
    """
    lattice = tmp_path / "trpt_probe.sad"
    lattice.write_text(
        "MOMENTUM = 0.05 GEV;\n"
        "MULT M1 = (L=1.0 VOLT=1.0e8 PHI=-1.5707963267948966 FREQ=2.856e9);\n"
        "MARK START = ()\n"
        "     END   = ();\n"
        "LINE TEST = (START M1 END);\n")
    monkeypatch.chdir(tmp_path)

    twiss_no_trpt = twiss_sad(
        lattice_filepath = lattice.name,
        line_name        = "TEST",
        closed           = False,
        calc6d           = True,
        rfsw             = True,
        trpt             = False,
        wall_time        = 30)
    twiss_trpt = twiss_sad(
        lattice_filepath = lattice.name,
        line_name        = "TEST",
        closed           = False,
        calc6d           = True,
        rfsw             = True,
        trpt             = True,
        wall_time        = 30)

    assert abs(twiss_no_trpt.delta[-1]) > 1.0, (
        "Without trpt, delta at the end of a strongly-accelerating element "
        "should be large relative to the fixed initial reference momentum. "
        f"Got delta: {twiss_no_trpt.delta[-1]}.")
    assert abs(twiss_trpt.delta[-1]) < 1E-6, (
        "With trpt=True, the reference momentum should track the "
        "acceleration, leaving a near-zero residual delta. "
        f"Got delta: {twiss_trpt.delta[-1]}.")


################################################################################
# compute_second_order_dispersions Smoke Tests (SAD required)
################################################################################
def test_compute_second_order_dispersions_adds_second_order_fields(
        tmp_path,
        monkeypatch):
    """
    compute_second_order_dispersions should augment the returned TwissTable
    with four second-order dispersion fields: ddx, ddpx, ddy, ddpy.
    """
    twiss = _run_second_order_dispersions(tmp_path, monkeypatch)

    for field in ("ddx", "ddpx", "ddy", "ddpy"):
        assert field in twiss.keys(), (
            f"compute_second_order_dispersions should add field `{field}` to "
            "the returned TwissTable.")


def test_compute_second_order_dispersions_fields_are_finite(
        tmp_path,
        monkeypatch):
    """
    All four second-order dispersion fields should be finite. A NaN or Inf
    indicates a failure in the finite-difference computation or in the
    underlying twiss_sad calls.
    """
    twiss = _run_second_order_dispersions(tmp_path, monkeypatch)

    for field in ("ddx", "ddpx", "ddy", "ddpy"):
        values = np.asarray(twiss[field])
        assert np.all(np.isfinite(values)), (
            f"compute_second_order_dispersions field `{field}` should be "
            f"finite everywhere. Got: {values}.")


def test_compute_second_order_dispersions_is_zero_for_drift_only_lattice(
        tmp_path,
        monkeypatch):
    """
    A drift-only lattice has no bends, so second-order dispersion is zero
    everywhere. This confirms the finite-difference formula produces the
    correct result for the trivial case.
    """
    twiss = _run_second_order_dispersions(tmp_path, monkeypatch)

    for field in ("ddx", "ddpx", "ddy", "ddpy"):
        values = np.asarray(twiss[field])
        assert np.allclose(values, 0.0, atol = 1E-9), (
            f"Second-order dispersion `{field}` should be 0 everywhere in a "
            f"drift-only lattice. Got: {values}.")


################################################################################
# compute_chromatic_functions Smoke Tests (SAD required)
################################################################################
def test_compute_chromatic_functions_adds_chromatic_fields(
        tmp_path,
        monkeypatch):
    """
    compute_chromatic_functions should augment the returned TwissTable with
    six chromatic function fields: bx_chrom, by_chrom, ax_chrom, ay_chrom,
    wx_chrom, wy_chrom.
    """
    twiss = _run_chromatic_functions(tmp_path, monkeypatch)

    for field in ("bx_chrom", "by_chrom", "ax_chrom", "ay_chrom",
                  "wx_chrom", "wy_chrom"):
        assert field in twiss.keys(), (
            f"compute_chromatic_functions should add field `{field}` to "
            "the returned TwissTable.")


def test_compute_chromatic_functions_fields_are_finite(tmp_path, monkeypatch):
    """
    All six chromatic function fields should be finite. A NaN or Inf indicates
    a failure in the central-difference computation or in the underlying
    twiss_sad calls.
    """
    twiss = _run_chromatic_functions(tmp_path, monkeypatch)

    for field in ("bx_chrom", "by_chrom", "ax_chrom", "ay_chrom",
                  "wx_chrom", "wy_chrom"):
        values = np.asarray(twiss[field])
        assert np.all(np.isfinite(values)), (
            f"compute_chromatic_functions field `{field}` should be finite "
            f"everywhere. Got: {values}.")


def test_compute_chromatic_functions_w_functions_are_nonnegative(
        tmp_path,
        monkeypatch):
    """
    wx_chrom and wy_chrom are computed as sqrt(ax_chrom**2 + bx_chrom**2) and
    sqrt(ay_chrom**2 + by_chrom**2). They are non-negative by construction.
    A negative value would indicate a sign error in our computation.
    """
    twiss = _run_chromatic_functions(tmp_path, monkeypatch)

    assert np.all(np.asarray(twiss["wx_chrom"]) >= 0), (
        "wx_chrom should be non-negative everywhere (computed as a norm). "
        f"""Got: {list(twiss["wx_chrom"])}.""")
    assert np.all(np.asarray(twiss["wy_chrom"]) >= 0), (
        "wy_chrom should be non-negative everywhere (computed as a norm). "
        f"""Got: {list(twiss["wy_chrom"])}.""")
