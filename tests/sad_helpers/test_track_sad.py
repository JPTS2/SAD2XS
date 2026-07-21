"""
================================================================================
Tests for sad2xs.sad_helpers.track sad
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
import textwrap

import numpy as np
import pytest

from tests.support.lattices import write_minimal_transfer_lattice
from sad2xs.sad_helpers import track_sad

################################################################################
# Helpers
################################################################################
_N_TURNS_SMOKE = 10


def _zero_particles(n):
    """
    Return n on-axis particles with all phase-space coordinates zero.
    """
    return (
        np.zeros(n),  # x
        np.zeros(n),  # px
        np.zeros(n),  # y
        np.zeros(n),  # py
        np.zeros(n),  # zeta
        np.zeros(n),  # delta
    )


def _write_minimal_marker_lattice(tmp_path):
    """
    Write a minimal SAD lattice consisting of only two markers (START, END) with
    no physical elements between them. Returns (filename, line_name) for direct
    use as track_sad arguments after monkeypatch.chdir(tmp_path).
    """
    lattice_path = tmp_path / "test_marker_lattice.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START END);
        """))

    return lattice_path.name, "TEST_LINE"


def _run_track(tmp_path, monkeypatch, n_particles = 1, n_turns = _N_TURNS_SMOKE,
               with_progress = False, **kwargs):
    """
    Write the minimal transfer-line lattice, change to its directory, and run
    track_sad for n_particles on-axis particles. with_progress defaults to
    False so that the simple batch tracking path is used (avoids the streaming
    Popen code path and the with_progress/n_turns batch-size interaction).
    Extra keyword arguments are forwarded to track_sad.
    """
    filename, line_name = write_minimal_transfer_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    x, px, y, py, zeta, delta = _zero_particles(n_particles)

    return track_sad(
        lattice_filepath    = filename,
        line_name           = line_name,
        x_init              = x,
        px_init             = px,
        y_init              = y,
        py_init             = py,
        zeta_init           = zeta,
        delta_init          = delta,
        n_turns             = n_turns,
        rfsw                = False,
        rad                 = False,
        with_progress       = with_progress,
        wall_time           = 60,
        **kwargs)


################################################################################
# Input Validation Tests (SAD not required)
################################################################################
def test_track_sad_raises_if_x_init_not_ndarray():
    """
    track_sad asserts that x_init is a numpy ndarray. Passing a list should
    raise an AssertionError immediately, before any subprocess call.
    """
    with pytest.raises(AssertionError, match = "x_init must be a numpy array"):
        track_sad(
            lattice_filepath = "dummy.sad",
            line_name        = "LINE",
            x_init           = [0.0],
            px_init          = np.zeros(1),
            y_init           = np.zeros(1),
            py_init          = np.zeros(1),
            zeta_init        = np.zeros(1),
            delta_init       = np.zeros(1),
            n_turns          = 1)


def test_track_sad_raises_if_arrays_have_mismatched_shapes():
    """
    All six phase-space arrays must have the same shape. Passing arrays with
    different lengths should raise an AssertionError immediately.
    """
    with pytest.raises(AssertionError):
        track_sad(
            lattice_filepath = "dummy.sad",
            line_name        = "LINE",
            x_init           = np.zeros(2),
            px_init          = np.zeros(3),
            y_init           = np.zeros(2),
            py_init          = np.zeros(2),
            zeta_init        = np.zeros(2),
            delta_init       = np.zeros(2),
            n_turns          = 1)


def test_track_sad_raises_if_n_particles_is_zero():
    """
    Passing arrays with zero length should raise an AssertionError because
    n_particles must be greater than zero.
    """
    with pytest.raises(AssertionError):
        track_sad(
            lattice_filepath = "dummy.sad",
            line_name        = "LINE",
            x_init           = np.zeros(0),
            px_init          = np.zeros(0),
            y_init           = np.zeros(0),
            py_init          = np.zeros(0),
            zeta_init        = np.zeros(0),
            delta_init       = np.zeros(0),
            n_turns          = 1)


def test_track_sad_raises_if_too_many_particles():
    """
    Passing more than 1 million particles should raise an AssertionError because
    track_sad enforces a 1-million stack-size limit before launching the subprocess.
    """
    n = int(1E6) + 1
    with pytest.raises(AssertionError):
        track_sad(
            lattice_filepath = "dummy.sad",
            line_name        = "LINE",
            x_init           = np.zeros(n),
            px_init          = np.zeros(n),
            y_init           = np.zeros(n),
            py_init          = np.zeros(n),
            zeta_init        = np.zeros(n),
            delta_init       = np.zeros(n),
            n_turns          = 1)


################################################################################
# track_sad Smoke Tests (SAD required)
################################################################################
def test_track_sad_runs_and_returns_dict(tmp_path, monkeypatch):
    """
    track_sad should run SAD on a minimal transfer-line lattice and return a
    dict without raising an exception.
    """
    result = _run_track(tmp_path, monkeypatch)

    assert isinstance(result, dict), (
        f"track_sad should return a dict. Got: {type(result).__name__}.")


def test_track_sad_returns_expected_keys(tmp_path, monkeypatch):
    """
    The dict returned by track_sad should contain all seven expected keys:
    x, px, y, py, zeta, delta, state.
    """
    result = _run_track(tmp_path, monkeypatch)

    for key in ("x", "px", "y", "py", "zeta", "delta", "state"):
        assert key in result, (
            f"track_sad result should contain key `{key}`. "
            f"Got keys: {list(result.keys())}.")


def test_track_sad_output_shape_matches_n_particles(tmp_path, monkeypatch):
    """
    Without turn_by_turn_monitor, each output array should have shape
    (n_particles,). This confirms that the reshape step uses the correct
    particle count.
    """
    n = 3
    result = _run_track(tmp_path, monkeypatch, n_particles = n)

    for key in ("x", "px", "y", "py", "zeta", "delta", "state"):
        assert result[key].shape == (n,), (
            f"track_sad result[`{key}`] should have shape ({n},). "
            f"Got: {result[key].shape}.")


def test_track_sad_turn_by_turn_shape_matches_particles_and_turns(
        tmp_path,
        monkeypatch):
    """
    With turn_by_turn_monitor=True, each output array should have shape
    (n_particles, n_turns + 1): one column for the initial state plus one per
    tracked turn.
    """
    n_p = 2
    n_t = _N_TURNS_SMOKE
    result = _run_track(
        tmp_path, monkeypatch,
        n_particles         = n_p,
        n_turns             = n_t,
        turn_by_turn_monitor = True)

    for key in ("x", "px", "y", "py", "zeta", "delta", "state"):
        assert result[key].shape == (n_p, n_t + 1), (
            f"With turn_by_turn_monitor=True, result[`{key}`] should have "
            f"shape ({n_p}, {n_t + 1}). Got: {result[key].shape}.")


def test_track_sad_on_axis_particle_stays_on_axis_in_drift(
        tmp_path,
        monkeypatch):
    """
    An on-axis particle (all initial conditions zero) tracked through a
    straight drift should retain x = px = y = py = delta = 0 throughout.
    This is a geometric identity: a drift does not deflect or shift an
    on-axis particle.
    """
    result = _run_track(
        tmp_path, monkeypatch,
        n_particles         = 1,
        n_turns             = 1,
        turn_by_turn_monitor = True)

    for coord in ("x", "px", "y", "py", "zeta", "delta"):
        assert np.allclose(result[coord][0], 0.0, atol = 1E-12), (
            f"On-axis particle should have {coord} = 0 at every turn through a "
            f"drift. Got: {result[coord][0]}.")


def test_track_sad_surviving_particles_have_state_one(tmp_path, monkeypatch):
    """
    Particles that survive tracking through a short drift should have state = 1
    (alive). SAD's `alive` flag is 1 for surviving particles and 0 for lost
    ones.
    """
    result = _run_track(tmp_path, monkeypatch, n_particles = 5)

    assert np.all(result["state"] == 1), (
        "All particles should be alive (state = 1) after tracking through a "
        f"""short drift. Got states: {result["state"]}.""")


def test_track_sad_marker_only_line_is_identity(tmp_path, monkeypatch):
    """
    A lattice consisting of only two markers (START END) with no physical
    elements is the identity map. The four transverse coordinates and delta
    should be unchanged after one pass. SAD does not track zeta for transfer
    lines without RF, so zeta is excluded from this check.
    """
    filename, line_name = _write_minimal_marker_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    x0      = np.array([1E-3])
    px0     = np.array([2E-4])
    y0      = np.array([-5E-4])
    py0     = np.array([3E-4])
    zeta0   = np.array([1E-2])
    delta0  = np.array([1E-4])

    result = track_sad(
        lattice_filepath    = filename,
        line_name           = line_name,
        x_init              = x0,
        px_init             = px0,
        y_init              = y0,
        py_init             = py0,
        zeta_init           = zeta0,
        delta_init          = delta0,
        n_turns             = 1,
        rfsw                = False,
        rad                 = False,
        with_progress       = False,
        wall_time           = 60)

    for coord, init in (
            ("x", x0), ("px", px0), ("y", y0), ("py", py0), ("delta", delta0)):
        assert result[coord] == pytest.approx(init, abs = 1E-12), (
            f"Marker-only line should leave {coord} unchanged. "
            f"Expected: {init}, got: {result[coord]}.")


def test_track_sad_drift_applies_correct_transverse_map(tmp_path, monkeypatch):
    """
    For a particle with x0=0, px0=1e-3 tracked through a 1 m drift, the
    analytic result is x_final = x0 + px0 × L = 1e-3 m and px_final = px0.
    This confirms the coordinate convention and the SAD ↔ Xtrack translation.
    """
    filename, line_name = write_minimal_transfer_lattice(tmp_path)
    monkeypatch.chdir(tmp_path)

    px0 = 1E-3

    result = track_sad(
        lattice_filepath    = filename,
        line_name           = line_name,
        x_init              = np.array([0.0]),
        px_init             = np.array([px0]),
        y_init              = np.zeros(1),
        py_init             = np.zeros(1),
        zeta_init           = np.zeros(1),
        delta_init          = np.zeros(1),
        n_turns             = 1,
        rfsw                = False,
        rad                 = False,
        with_progress       = False,
        wall_time           = 60)

    assert result["x"][0] == pytest.approx(px0 * 1.0, abs = 1E-9), (
        f"After a 1 m drift with px0 = {px0}, x should be px0 × L = {px0 * 1.0} m. "
        f"""Got: {result["x"][0]}.""")
    assert result["px"][0] == pytest.approx(px0, abs = 1E-12), (
        f"""After a drift, px should be unchanged. Expected {px0}, got: {result["px"][0]}.""")
