"""
================================================================================
Tests for sad2xs.sad_helpers.survey sad
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
import numpy as np
import pytest

from tests.support.lattices import write_minimal_bend_lattice, write_minimal_transfer_lattice
from sad2xs.sad_helpers import survey_sad
from sad2xs.sad_helpers.survey import generate_survey_print_function

################################################################################
# Helpers
################################################################################
def _run_survey(tmp_path, monkeypatch, **kwargs):
    """
    Write the minimal drift transfer-line lattice, change to its directory,
    and run survey_sad with closed=False, wall_time=30. Extra keyword
    arguments are forwarded to survey_sad to allow per-test flag overrides
    (e.g. reverse_element_order=True).
    """
    filename, line_name = write_minimal_transfer_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    return survey_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        closed           = False,
        wall_time        = 30,
        **kwargs)


def _run_survey_on_bend_lattice(tmp_path, monkeypatch, **kwargs):
    """
    Write the minimal bend transfer-line lattice, change to its directory, and
    run survey_sad with closed=False, wall_time=30. Extra keyword arguments are
    forwarded to survey_sad.
    """
    filename, line_name = write_minimal_bend_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    return survey_sad(
        lattice_filepath = filename,
        line_name        = line_name,
        closed           = False,
        wall_time        = 30,
        **kwargs)


################################################################################
# Command Generation Tests (SAD not required)
################################################################################
def test_generate_survey_print_function_returns_string():
    """
    generate_survey_print_function should return a non-empty string containing
    the SAD macro definition.
    """
    result = generate_survey_print_function()

    assert isinstance(result, str), (
        "generate_survey_print_function should return a str. "
        f"Got: {type(result).__name__}.")
    assert len(result) > 0, (
        "generate_survey_print_function should return a non-empty string.")


def test_generate_survey_print_function_defines_save_survey_file():
    """
    The returned string should define a SAD function named SaveSurveyFile that
    accepts a filename argument. This function is called inside survey_sad to
    write the survey output.
    """
    result = generate_survey_print_function()

    assert "SaveSurveyFile[filename_]" in result, (
        "generate_survey_print_function should define 'SaveSurveyFile[filename_]'. "
        f"Got: {result[:200]!r}.")


def test_generate_survey_print_function_includes_position_columns():
    """
    The macro string should include the SAD global position column names that
    are consumed by survey_sad: GX, GY, GZ. These map to xtrack's Z, X, Y
    coordinates respectively.
    """
    result = generate_survey_print_function()

    for column in ("GX", "GY", "GZ"):
        assert column in result, (
            f"generate_survey_print_function should include column '{column}'. "
            f"Got: {result[:200]!r}.")


def test_generate_survey_print_function_includes_rotation_columns():
    """
    The macro string should include the SAD rotation column names that are
    consumed by survey_sad: GCHI1, GCHI2, GCHI3. These map to xtrack's theta,
    phi, psi angles respectively.
    """
    result = generate_survey_print_function()

    for column in ("GCHI1", "GCHI2", "GCHI3"):
        assert column in result, (
            f"generate_survey_print_function should include column '{column}'. "
            f"Got: {result[:200]!r}.")


################################################################################
# survey_sad Smoke Tests (SAD required)
################################################################################
def test_survey_sad_runs_minimal_transfer_line_and_returns_survey_table(
        tmp_path,
        monkeypatch):
    """
    survey_sad should run SAD on a minimal transfer-line lattice and return a
    survey table for the requested line.
    """
    sv = _run_survey(tmp_path, monkeypatch)

    assert "START" in sv.name, (
        "survey_sad should return a table containing the START marker.")
    assert "END" in sv.name, (
        "survey_sad should return a table containing the END marker.")
    assert sv["s", "END"] == pytest.approx(1.0), (
        "survey_sad should preserve the minimal lattice length in the returned "
        "survey table.")


def test_survey_sad_returns_table_with_expected_columns(tmp_path, monkeypatch):
    """
    The SurveyTable returned by survey_sad should contain all standard survey
    columns: s, l, X, Y, Z, theta, phi, psi, name, element_type.
    """
    sv = _run_survey(tmp_path, monkeypatch)

    for column in ("s", "l", "X", "Y", "Z", "theta", "phi", "psi",
                   "name", "element_type"):
        assert column in sv.keys(), (
            f"survey_sad should return a table with column '{column}'.")


def test_survey_sad_elements_are_sorted_by_s_position(tmp_path, monkeypatch):
    """
    survey_sad should return elements sorted by s-position (ascending). The
    function calls np.argsort internally; this test confirms that contract is
    met on real SAD output.
    """
    sv       = _run_survey(tmp_path, monkeypatch)
    s_values = list(sv.s)

    assert s_values == sorted(s_values), (
        "survey_sad should return elements sorted by s-position (ascending). "
        f"Got s values: {s_values}.")


def test_survey_sad_s_at_start_is_zero(tmp_path, monkeypatch):
    """
    The START marker should always be at s = 0 in a transfer-line survey. This
    is a geometric identity independent of lattice physics.
    """
    sv = _run_survey(tmp_path, monkeypatch)

    assert sv["s", "START"] == pytest.approx(0.0), (
        "START marker should be at s = 0 in a transfer-line survey. "
        f"Got: s = {sv['s', 'START']}.")


def test_survey_sad_no_nan_in_standard_columns(tmp_path, monkeypatch):
    """
    All standard survey columns should be finite (no NaN or Inf) on valid SAD
    output. A NaN indicates a parsing failure or column mis-mapping in our
    wrapper, not a SAD physics error.
    """
    sv = _run_survey(tmp_path, monkeypatch)

    for column in ("s", "l", "X", "Y", "Z", "theta", "phi", "psi"):
        values = np.asarray(getattr(sv, column))
        assert np.all(np.isfinite(values)), (
            f"Column '{column}' should contain only finite values. "
            f"Got: {values}.")


def test_survey_sad_straight_lattice_has_zero_horizontal_displacement(
        tmp_path,
        monkeypatch):
    """
    A straight drift-only lattice should have X = 0 everywhere. The X column
    is mapped from SAD's -GY (horizontal transverse displacement). A non-zero
    value would indicate a column mis-mapping or a coordinate frame error.
    """
    sv = _run_survey(tmp_path, monkeypatch)

    assert np.allclose(np.asarray(sv.X), 0.0, atol = 1E-12), (
        "Horizontal displacement X should be 0 everywhere in a straight "
        f"lattice. Got X: {list(sv.X)}.")


def test_survey_sad_z_position_is_lattice_length_at_end_for_straight_lattice(
        tmp_path,
        monkeypatch):
    """
    For a straight 1 m drift lattice, the Z coordinate at END should be
    approximately 1.0 m. Z is mapped from SAD's +GX (longitudinal coordinate).
    This test validates the Z = +GX column mapping and sign: a wrong column or
    a sign error (Z = -GX) would produce Z = 0 or Z = -1.0 at END.
    """
    sv = _run_survey(tmp_path, monkeypatch)

    assert sv["Z", "END"] == pytest.approx(1.0), (
        "Z at END should equal the lattice length (1.0 m) for a straight "
        f"drift lattice. Got: Z = {sv['Z', 'END']}.")


def test_survey_sad_element_length_is_preserved(tmp_path, monkeypatch):
    """
    The l column (element arc length, from SAD's L field) should equal the
    declared element length: 1.0 m for TEST_DRIFT and 0.0 m for the START and
    END markers. This confirms the L column is parsed and stored correctly.
    """
    sv    = _run_survey(tmp_path, monkeypatch)
    names = list(sv.name)
    l_arr = np.asarray(sv.l)

    assert l_arr[names.index("TEST_DRIFT")] == pytest.approx(1.0), (
        "Element length l for TEST_DRIFT should be 1.0 m. "
        f"Got: {l_arr[names.index('TEST_DRIFT')]}.")
    assert l_arr[names.index("START")] == pytest.approx(0.0), (
        "Element length l for START (a marker) should be 0.0 m. "
        f"Got: {l_arr[names.index('START')]}.")
    assert l_arr[names.index("END")] == pytest.approx(0.0), (
        "Element length l for END (a marker) should be 0.0 m. "
        f"Got: {l_arr[names.index('END')]}.")


def test_survey_sad_maps_known_element_types(tmp_path, monkeypatch):
    """
    survey_sad should translate SAD element type strings to their xtrack
    equivalents: MARK → 'Marker', DRIFT → 'Drift'. An unknown type maps to
    'Unknown'.
    """
    sv     = _run_survey(tmp_path, monkeypatch)
    names  = list(sv.name)
    etypes = list(sv.element_type)

    assert etypes[names.index("START")] == "Marker", (
        "SAD MARK elements should map to element_type 'Marker'. "
        f"Got: {etypes[names.index('START')]}.")
    assert etypes[names.index("END")] == "Marker", (
        "SAD MARK elements should map to element_type 'Marker'. "
        f"Got: {etypes[names.index('END')]}.")
    assert etypes[names.index("TEST_DRIFT")] == "Drift", (
        "SAD DRIFT elements should map to element_type 'Drift'. "
        f"Got: {etypes[names.index('TEST_DRIFT')]}.")


def test_survey_sad_reverse_element_order_flips_s_axis(
        tmp_path,
        monkeypatch):
    """
    With reverse_element_order=True the s-values should be reflected about the
    midpoint so that START moves to s = total_length and END moves to s = 0.
    The row order in the table (and X, Y, Z values) is unchanged — only the
    s-axis is flipped.
    """
    sv_forward  = _run_survey(tmp_path, monkeypatch, reverse_element_order = False)
    sv_reversed = _run_survey(tmp_path, monkeypatch, reverse_element_order = True)

    total_length = float(sv_forward["s", "END"])
    names        = list(sv_reversed.name)
    s_reversed   = np.asarray(sv_reversed.s)

    assert s_reversed[names.index("END")] == pytest.approx(0.0), (
        "With reverse_element_order=True, END should be at s = 0. "
        f"Got s at END: {s_reversed[names.index('END')]}.")
    assert s_reversed[names.index("START")] == pytest.approx(total_length), (
        "With reverse_element_order=True, START should be at s = total_length. "
        f"Got s at START: {s_reversed[names.index('START')]}; "
        f"expected: {total_length}.")


def test_survey_sad_reverse_survey_horizontal_flips_x_plane_coordinates(
        tmp_path,
        monkeypatch):
    """
    reverse_survey_horizontal=True should negate X, theta, and psi everywhere
    (the x-plane geometry is reflected), leaving Y, Z, and phi unchanged. The
    test requires a lattice with a non-zero bend angle so that X != 0 and the
    sign-flip is meaningful.
    """
    sv_forward  = _run_survey_on_bend_lattice(
        tmp_path, monkeypatch, reverse_survey_horizontal = False)
    sv_reversed = _run_survey_on_bend_lattice(
        tmp_path, monkeypatch, reverse_survey_horizontal = True)

    X_fwd = np.asarray(sv_forward.X)
    X_rev = np.asarray(sv_reversed.X)

    assert not np.allclose(X_fwd, 0.0, atol = 1E-6), (
        "The bend lattice should produce non-zero X so that the sign-flip "
        f"can be verified. Got X_forward: {list(X_fwd)}.")
    assert np.allclose(X_rev, -X_fwd, atol = 1E-12), (
        "reverse_survey_horizontal=True should negate X everywhere. "
        f"X_forward: {list(X_fwd)}; X_reversed: {list(X_rev)}.")

    theta_fwd = np.asarray(sv_forward.theta)
    theta_rev = np.asarray(sv_reversed.theta)
    assert np.allclose(theta_rev, -theta_fwd, atol = 1E-12), (
        "reverse_survey_horizontal=True should negate theta everywhere. "
        f"theta_forward: {list(theta_fwd)}; theta_reversed: {list(theta_rev)}.")

    psi_fwd = np.asarray(sv_forward.psi)
    psi_rev = np.asarray(sv_reversed.psi)
    assert np.allclose(psi_rev, -psi_fwd, atol = 1E-12), (
        "reverse_survey_horizontal=True should negate psi everywhere. "
        f"psi_forward: {list(psi_fwd)}; psi_reversed: {list(psi_rev)}.")

    for column in ("Y", "Z", "phi"):
        fwd = np.asarray(getattr(sv_forward, column))
        rev = np.asarray(getattr(sv_reversed, column))
        assert np.allclose(rev, fwd, atol = 1E-12), (
            f"reverse_survey_horizontal=True should leave {column} unchanged. "
            f"{column}_forward: {list(fwd)}; {column}_reversed: {list(rev)}.")
