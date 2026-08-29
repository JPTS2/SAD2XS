"""
================================================================================
Tests for Taylor map element writer serialisation
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-27
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import pytest
import xtrack as xt

from tests.support.writer_helpers import write_and_load as _shared_write_and_load

################################################################################
# Helpers
################################################################################
def _writer_roundtrip(line, tmp_path):
    """
    Write a line using the public SAD2XS writer entry points, reload it in a
    clean Xsuite environment, and return the reloaded line.
    """
    _, reloaded_line = _shared_write_and_load(
        line, tmp_path, output_header = "Taylor map writer test")
    return reloaded_line


def _build_first_order_map_line(length = 0.0, m0 = None, m1 = None, name = "m1"):
    """
    Build a minimal single-FirstOrderTaylorMap Xsuite line with a reference
    particle.
    """
    kwargs = dict(length = length)
    if m0 is not None:
        kwargs["m0"] = m0
    if m1 is not None:
        kwargs["m1"] = m1

    line = xt.Line(
        elements      = [xt.Marker(), xt.FirstOrderTaylorMap(**kwargs), xt.Marker()],
        element_names = ["start", name, "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


def _build_second_order_map_line(length = 0.0, k = None, R = None, T = None, name = "m1"):
    """
    Build a minimal single-SecondOrderTaylorMap Xsuite line with a reference
    particle.
    """
    kwargs = dict(length = length)
    if k is not None:
        kwargs["k"] = k
    if R is not None:
        kwargs["R"] = R
    if T is not None:
        kwargs["T"] = T

    line = xt.Line(
        elements      = [xt.Marker(), xt.SecondOrderTaylorMap(**kwargs), xt.Marker()],
        element_names = ["start", name, "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    return line


################################################################################
# FirstOrderTaylorMap
################################################################################
def test_first_order_taylor_map_writer_reloads_as_xsuite_first_order_taylor_map(tmp_path):
    """
    A written FirstOrderTaylorMap element should reload as an
    xt.FirstOrderTaylorMap in a clean Xsuite environment.
    """
    original_line = _build_first_order_map_line(m1 = np.eye(6) * 1.1)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["m1"], xt.FirstOrderTaylorMap), (
        "Written FirstOrderTaylorMap element `m1` should reload as "
        f"""xt.FirstOrderTaylorMap. Got: {type(reloaded_line["m1"]).__name__}.""")


def test_first_order_taylor_map_writer_preserves_element_name(tmp_path):
    """
    A written FirstOrderTaylorMap element should appear under its original
    name in the reloaded line.
    """
    original_line = _build_first_order_map_line(name = "fringe_in")
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "fringe_in" in list(reloaded_line.element_names), (
        "Reloaded line should contain FirstOrderTaylorMap element `fringe_in`. "
        f"Got: {list(reloaded_line.element_names)}.")


def test_first_order_taylor_map_writer_preserves_length(tmp_path):
    """
    A FirstOrderTaylorMap's length should be preserved through a write and
    reload cycle.
    """
    original_line = _build_first_order_map_line(length = 0.35)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].length == pytest.approx(0.35), (
        "Writer roundtrip should preserve FirstOrderTaylorMap length. "
        f"""Original: 0.35, reloaded: {reloaded_line["m1"].length}.""")


def test_first_order_taylor_map_writer_preserves_m0(tmp_path):
    """
    A FirstOrderTaylorMap's m0 (6-vector) should be preserved through a write
    and reload cycle.
    """
    m0 = np.array([1.0E-3, -2.0E-3, 3.0E-4, -4.0E-4, 5.0E-5, -6.0E-5])
    original_line = _build_first_order_map_line(m0 = m0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["m1"].m0).tolist() == pytest.approx(m0.tolist()), (
        "Writer roundtrip should preserve FirstOrderTaylorMap m0. "
        f"Original: {m0.tolist()}, reloaded: {np.asarray(reloaded_line['m1'].m0).tolist()}.")


def test_first_order_taylor_map_writer_preserves_m1(tmp_path):
    """
    A FirstOrderTaylorMap's m1 (6x6 matrix), including off-diagonal entries,
    should be preserved through a write and reload cycle.
    """
    m1 = np.eye(6)
    m1[0, 1] = 0.25
    m1[2, 3] = -0.5
    original_line = _build_first_order_map_line(m1 = m1)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    np.testing.assert_allclose(
        np.asarray(reloaded_line["m1"].m1), m1,
        err_msg = "Writer roundtrip should preserve FirstOrderTaylorMap m1, "
        "including off-diagonal entries.")


def test_first_order_taylor_map_writer_preserves_full_double_precision(tmp_path):
    """
    An m0 entry with many significant digits should survive a write and
    reload cycle at full double precision. The lattice file writes these
    coefficients to 24 decimal places, which exceeds the ~17 significant
    digits of IEEE 754 double precision.
    """
    precise = 0.12345678901234567E-3
    m0 = np.zeros(6)
    m0[0] = precise
    original_line = _build_first_order_map_line(m0 = m0)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].m0[0] == pytest.approx(precise, rel = 1E-15), (
        "Writer roundtrip should preserve m0 at full double precision. "
        f"""Original: {precise!r}, reloaded: {reloaded_line["m1"].m0[0]!r}.""")


################################################################################
# SecondOrderTaylorMap
################################################################################
def test_second_order_taylor_map_writer_reloads_as_xsuite_second_order_taylor_map(tmp_path):
    """
    A written SecondOrderTaylorMap element should reload as an
    xt.SecondOrderTaylorMap in a clean Xsuite environment.
    """
    original_line = _build_second_order_map_line(R = np.eye(6) * 1.1)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["m1"], xt.SecondOrderTaylorMap), (
        "Written SecondOrderTaylorMap element `m1` should reload as "
        f"""xt.SecondOrderTaylorMap. Got: {type(reloaded_line["m1"]).__name__}.""")


def test_second_order_taylor_map_writer_preserves_element_name(tmp_path):
    """
    A written SecondOrderTaylorMap element should appear under its original
    name in the reloaded line.
    """
    original_line = _build_second_order_map_line(name = "fringe_out")
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "fringe_out" in list(reloaded_line.element_names), (
        "Reloaded line should contain SecondOrderTaylorMap element "
        f"`fringe_out`. Got: {list(reloaded_line.element_names)}.")


def test_second_order_taylor_map_writer_preserves_length(tmp_path):
    """
    A SecondOrderTaylorMap's length should be preserved through a write and
    reload cycle.
    """
    original_line = _build_second_order_map_line(length = 0.6)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].length == pytest.approx(0.6), (
        "Writer roundtrip should preserve SecondOrderTaylorMap length. "
        f"""Original: 0.6, reloaded: {reloaded_line["m1"].length}.""")


def test_second_order_taylor_map_writer_preserves_k(tmp_path):
    """
    A SecondOrderTaylorMap's k (6-vector) should be preserved through a write
    and reload cycle.
    """
    k = np.array([1.0E-3, -2.0E-3, 3.0E-4, -4.0E-4, 5.0E-5, -6.0E-5])
    original_line = _build_second_order_map_line(k = k)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["m1"].k).tolist() == pytest.approx(k.tolist()), (
        "Writer roundtrip should preserve SecondOrderTaylorMap k. "
        f"Original: {k.tolist()}, reloaded: {np.asarray(reloaded_line['m1'].k).tolist()}.")


def test_second_order_taylor_map_writer_preserves_r(tmp_path):
    """
    A SecondOrderTaylorMap's R (6x6 matrix), including off-diagonal entries,
    should be preserved through a write and reload cycle.
    """
    R = np.eye(6)
    R[0, 1] = 0.006
    R[2, 3] = -0.006
    original_line = _build_second_order_map_line(R = R)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    np.testing.assert_allclose(
        np.asarray(reloaded_line["m1"].R), R,
        err_msg = "Writer roundtrip should preserve SecondOrderTaylorMap R, "
        "including off-diagonal entries.")


def test_second_order_taylor_map_writer_preserves_t(tmp_path):
    """
    A SecondOrderTaylorMap's T (6x6x6 tensor), including a genuinely non-zero
    off-diagonal entry, should be preserved through a write and reload cycle
    -- the shape that exercises _format_taylor_map_array's 3D recursion.
    """
    T = np.zeros((6, 6, 6))
    T[0, 0, 5] = T[0, 5, 0] = -1.5E-5
    T[4, 1, 1] = 3.0E-3
    original_line = _build_second_order_map_line(T = T)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    np.testing.assert_allclose(
        np.asarray(reloaded_line["m1"].T), T,
        err_msg = "Writer roundtrip should preserve SecondOrderTaylorMap T, "
        "including off-diagonal entries.")


def test_second_order_taylor_map_writer_preserves_full_double_precision(tmp_path):
    """
    A k entry with many significant digits should survive a write and reload
    cycle at full double precision.
    """
    precise = 0.12345678901234567E-3
    k = np.zeros(6)
    k[0] = precise
    original_line = _build_second_order_map_line(k = k)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].k[0] == pytest.approx(precise, rel = 1E-15), (
        "Writer roundtrip should preserve k at full double precision. "
        f"""Original: {precise!r}, reloaded: {reloaded_line["m1"].k[0]!r}.""")


################################################################################
# SAD Quad-Fringe Reversal Metadata
################################################################################
def test_second_order_taylor_map_writer_preserves_sad_quad_fringe_metadata_when_present(tmp_path):
    """
    The converter stashes plain (non-xofield) _sad_quad_fringe_a/b/theta
    attributes on a quad-fringe map. The reversal fix-up needs them, so they
    should survive a write and reload cycle.
    """
    original_line = _build_second_order_map_line()
    original_line["m1"]._sad_quad_fringe_a     = -3.125E-05
    original_line["m1"]._sad_quad_fringe_b     = 0.006
    original_line["m1"]._sad_quad_fringe_theta = 0.0

    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    element = reloaded_line["m1"]
    assert hasattr(element, "_sad_quad_fringe_a"), (
        "Reloaded SecondOrderTaylorMap should carry _sad_quad_fringe_a when "
        "the original element had it.")
    assert element._sad_quad_fringe_a == pytest.approx(-3.125E-05), (
        f"Reloaded _sad_quad_fringe_a should match the original. "
        f"Got: {element._sad_quad_fringe_a}.")
    assert element._sad_quad_fringe_b == pytest.approx(0.006), (
        f"Reloaded _sad_quad_fringe_b should match the original. "
        f"Got: {element._sad_quad_fringe_b}.")
    assert element._sad_quad_fringe_theta == pytest.approx(0.0), (
        f"Reloaded _sad_quad_fringe_theta should match the original. "
        f"Got: {element._sad_quad_fringe_theta}.")


def test_second_order_taylor_map_writer_omits_sad_quad_fringe_metadata_when_absent(tmp_path):
    """
    A plain SecondOrderTaylorMap not built via the quad-fringe path (no
    _sad_quad_fringe_a/b/theta attributes) should reload without them --
    the writer must not assume every SecondOrderTaylorMap is a quad fringe.
    """
    original_line = _build_second_order_map_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert not hasattr(reloaded_line["m1"], "_sad_quad_fringe_a"), (
        "Reloaded SecondOrderTaylorMap should not carry _sad_quad_fringe_a "
        "when the original element never had it.")


def test_sad_k1_fringe_writer_uses_compact_helper_without_post_assignment(tmp_path):
    """Recognised SAD fringe maps should be rebuilt semantically in one call."""
    line = _build_second_order_map_line()
    line["m1"]._sad_k1_fringe_a = -3.125E-05
    line["m1"]._sad_k1_fringe_b = 0.006
    line["m1"]._sad_k1_fringe_frame_rotation = 0.125

    output_dir = tmp_path / "compact_fringe_writer"
    output_dir.mkdir()
    import sad2xs as s2x
    from sad2xs.config import Config
    s2x.write_lattice(
        line = line, output_filename = "lattice",
        output_directory = str(output_dir), output_header = "test",
        offset_marker_locations = None,
        config = Config(_verbose = False))
    source = (output_dir / "lattice.py").read_text()

    assert source.count("def _new_sad_k1_fringe_map(") == 1
    assert "_new_sad_k1_fringe_map(" in source
    assert 'name = "m1"' in source
    assert "env.elements[" not in source
    assert source.count("prototype   = xt.SecondOrderTaylorMap") == 1

    env = xt.Environment()
    env.call(str(output_dir / "lattice.py"))
    reloaded = env["m1"]
    assert reloaded._sad_k1_fringe_a == pytest.approx(-3.125E-05)
    assert reloaded._sad_k1_fringe_b == pytest.approx(0.006)
    assert reloaded._sad_k1_fringe_frame_rotation == pytest.approx(0.125)
    from sad2xs.converter._000_fringe_helpers import (
        rotate_sad_k1_fringe_taylor_map, sad_k1_fringe_taylor_coeffs)
    expected_k, expected_R, expected_T = rotate_sad_k1_fringe_taylor_map(
        0.125, *sad_k1_fringe_taylor_coeffs(-3.125E-05, 0.006))
    np.testing.assert_allclose(reloaded.k, expected_k)
    np.testing.assert_allclose(reloaded.R, expected_R)
    np.testing.assert_allclose(reloaded.T, expected_T)


################################################################################
# Minus-Sign Root-Name Cleanup
################################################################################
def test_first_order_taylor_map_writer_strips_minus_sign_without_matching_root(tmp_path):
    """
    A FirstOrderTaylorMap named with a leading "-" and no non-minus sibling in
    the line should reload under the stripped (non-minus) name, matching
    Cavity's convention -- a direction-symmetric element gains nothing from
    keeping a reversal-only name.
    """
    original_line = _build_first_order_map_line(name = "-fringe_in")
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "fringe_in" in list(reloaded_line.element_names), (
        "A FirstOrderTaylorMap named '-fringe_in' with no 'fringe_in' sibling "
        "should reload under the stripped name 'fringe_in'. "
        f"Got: {list(reloaded_line.element_names)}.")
    assert "-fringe_in" not in list(reloaded_line.element_names), (
        "The minus-prefixed name should not survive when no non-minus "
        f"sibling exists. Got: {list(reloaded_line.element_names)}.")


def test_first_order_taylor_map_writer_keeps_minus_sign_with_matching_root(tmp_path):
    """
    When both "name" and "-name" FirstOrderTaylorMap elements exist in the
    same line, both are genuinely distinct maps and neither should be
    collapsed away.
    """
    m0_plus  = np.array([1.0, 0, 0, 0, 0, 0])
    m0_minus = np.array([-1.0, 0, 0, 0, 0, 0])

    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.FirstOrderTaylorMap(m0 = m0_plus),
            xt.FirstOrderTaylorMap(m0 = m0_minus),
            xt.Marker(),
        ],
        element_names = ["start", "fringe_in", "-fringe_in", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    assert "fringe_in" in list(reloaded_line.element_names), (
        "Both 'fringe_in' and '-fringe_in' should survive when both exist. "
        f"Got: {list(reloaded_line.element_names)}.")
    assert "-fringe_in" in list(reloaded_line.element_names), (
        "Both 'fringe_in' and '-fringe_in' should survive when both exist. "
        f"Got: {list(reloaded_line.element_names)}.")
    assert reloaded_line["fringe_in"].m0[0] == pytest.approx(1.0), (
        "The non-minus element's own m0 should be preserved independently.")
    assert reloaded_line["-fringe_in"].m0[0] == pytest.approx(-1.0), (
        "The minus-prefixed element's own m0 should be preserved independently.")


def test_second_order_taylor_map_writer_strips_minus_sign_without_matching_root(tmp_path):
    """
    A SecondOrderTaylorMap named with a leading "-" and no non-minus sibling
    in the line should reload under the stripped (non-minus) name, matching
    Cavity's convention -- a direction-symmetric element gains nothing from
    keeping a reversal-only name.
    """
    original_line = _build_second_order_map_line(name = "-fringe_in")
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "fringe_in" in list(reloaded_line.element_names), (
        "A SecondOrderTaylorMap named '-fringe_in' with no 'fringe_in' "
        "sibling should reload under the stripped name 'fringe_in'. "
        f"Got: {list(reloaded_line.element_names)}.")
    assert "-fringe_in" not in list(reloaded_line.element_names), (
        "The minus-prefixed name should not survive when no non-minus "
        f"sibling exists. Got: {list(reloaded_line.element_names)}.")


def test_second_order_taylor_map_writer_keeps_minus_sign_with_matching_root(tmp_path):
    """
    When both "name" and "-name" SecondOrderTaylorMap elements exist in the
    same line, both are genuinely distinct maps and neither should be
    collapsed away.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.SecondOrderTaylorMap(k = np.array([1.0, 0, 0, 0, 0, 0])),
            xt.SecondOrderTaylorMap(k = np.array([-1.0, 0, 0, 0, 0, 0])),
            xt.Marker(),
        ],
        element_names = ["start", "fringe_in", "-fringe_in", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    assert "fringe_in" in list(reloaded_line.element_names), (
        "Both 'fringe_in' and '-fringe_in' should survive when both exist. "
        f"Got: {list(reloaded_line.element_names)}.")
    assert "-fringe_in" in list(reloaded_line.element_names), (
        "Both 'fringe_in' and '-fringe_in' should survive when both exist. "
        f"Got: {list(reloaded_line.element_names)}.")
    assert reloaded_line["fringe_in"].k[0] == pytest.approx(1.0), (
        "The non-minus element's own k should be preserved independently.")
    assert reloaded_line["-fringe_in"].k[0] == pytest.approx(-1.0), (
        "The minus-prefixed element's own k should be preserved independently.")


################################################################################
# Multi-Element Behaviour
################################################################################
def test_taylor_maps_writer_preserves_multiple_maps_independently(tmp_path):
    """
    Multiple FirstOrderTaylorMap and SecondOrderTaylorMap elements in one
    line should each preserve their own coefficients independently through a
    single write and reload cycle.
    """
    m1 = np.eye(6)
    m1[0, 1] = 0.1
    k = np.zeros(6)
    k[0] = 0.2

    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.FirstOrderTaylorMap(m1 = m1),
            xt.SecondOrderTaylorMap(k = k),
            xt.Marker(),
        ],
        element_names = ["start", "first", "second", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    np.testing.assert_allclose(
        np.asarray(reloaded_line["first"].m1), m1,
        err_msg = "The FirstOrderTaylorMap's m1 should be preserved "
        "independently of the SecondOrderTaylorMap in the same line.")
    assert reloaded_line["second"].k[0] == pytest.approx(0.2), (
        "The SecondOrderTaylorMap's k should be preserved independently of "
        "the FirstOrderTaylorMap in the same line.")


def test_taylor_maps_writer_preserves_element_order(tmp_path):
    """
    Taylor map elements interleaved with markers should appear in the same
    order after a write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.SecondOrderTaylorMap(k = np.array([0.1, 0, 0, 0, 0, 0])),
            xt.Marker(),
            xt.SecondOrderTaylorMap(k = np.array([0.2, 0, 0, 0, 0, 0])),
            xt.Marker(),
        ],
        element_names = ["start", "fringe_in", "mid", "fringe_out", "end"])

    line.particle_ref = xt.Particles("electron", p0c = 1.0E9)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    assert list(reloaded_line.element_names) == list(line.element_names), (
        "Writer roundtrip should preserve Taylor map element names and order. "
        f"Original: {list(line.element_names)}; "
        f"Reloaded: {list(reloaded_line.element_names)}.")
