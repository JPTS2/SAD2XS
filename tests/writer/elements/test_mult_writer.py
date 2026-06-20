"""
================================================================================
Tests for multipole element writer serialisation
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-20
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
def _write_and_load(line, tmp_path):
    """
    Write a line using the public SAD2XS writer entry points, reload it in a
    clean Xsuite environment, and return the environment and reloaded line.

    The environment is returned so tests can verify that multipole knl/ksl
    strengths are NOT written as live optics variables — unlike quadrupole k1,
    multipole strengths are baked into the lattice file as literal arrays.
    """
    output_dir = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = "Multipole writer test",
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = "test_lattice_import_optics",
        output_directory  = str(output_dir),
        output_header     = "Multipole writer test",
        config            = Config(_verbose = False))

    env = xt.Environment()
    env.call(str(output_dir / "test_lattice.py"))
    env.call(str(output_dir / "test_lattice_import_optics.py"))

    return env, env.lines["line"]


def _writer_roundtrip(line, tmp_path):
    """
    Write and reload a line. Returns the reloaded line only.
    """
    _, reloaded_line = _write_and_load(line, tmp_path)
    return reloaded_line


def _build_mult_line(
        length    = 0.1,
        knl       = None,
        ksl       = None,
        shift_x   = 0.0,
        shift_y   = 0.0,
        rot_s_rad = 0.0):
    """
    Build a minimal single-multipole Xsuite line with a reference particle.
    knl and ksl are the primary content of xt.Multipole; all other keyword
    arguments map to standard misalignment fields.
    """
    mult_kwargs = dict(
        length    = length,
        shift_x   = shift_x,
        shift_y   = shift_y,
        rot_s_rad = rot_s_rad)

    if knl is not None:
        mult_kwargs["knl"] = knl
    if ksl is not None:
        mult_kwargs["ksl"] = ksl

    line = xt.Line(
        elements      = [xt.Marker(), xt.Multipole(**mult_kwargs), xt.Marker()],
        element_names = ["start", "m1", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    return line


################################################################################
# Basic Serialisation
################################################################################
########################################
# Element Type and Name
########################################
def test_mult_writer_reloads_as_xsuite_multipole(tmp_path):
    """
    A written multipole element should reload as an xt.Multipole in a clean
    Xsuite environment.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["m1"], xt.Multipole), (
        "Written multipole element 'm1' should reload as xt.Multipole. "
        f"Got: {type(reloaded_line['m1']).__name__}.")


def test_mult_writer_preserves_element_name(tmp_path):
    """
    A written multipole element should appear under its original name in the
    reloaded line.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert "m1" in list(reloaded_line.element_names), (
        "Reloaded line should contain multipole element 'm1'. "
        f"Got: {list(reloaded_line.element_names)}.")


########################################
# Element Order
########################################
def test_mult_writer_preserves_element_order(tmp_path):
    """
    Multiple multipole and marker elements should appear in the same order
    after a write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Multipole(knl = [0.0, 0.5]),
            xt.Marker(),
            xt.Multipole(knl = [0.0, -0.5]),
            xt.Marker(),
        ],
        element_names = ["start", "mf", "mid", "md", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    assert list(reloaded_line.element_names) == list(line.element_names), (
        "Writer roundtrip should preserve element names and order. "
        f"Original: {list(line.element_names)}; "
        f"Reloaded: {list(reloaded_line.element_names)}.")


################################################################################
# Field Preservation
################################################################################
########################################
# Length
########################################
def test_mult_writer_preserves_length(tmp_path):
    """
    A multipole element's length should be preserved through a write and
    reload cycle.
    """
    original_line = _build_mult_line(length = 0.15, knl = [0.0, 0.5])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].length == pytest.approx(0.15), (
        "Writer roundtrip should preserve multipole length. "
        f"Original: 0.15, reloaded: {reloaded_line['m1'].length}.")


########################################
# Unpowered Multipole (Simple Path)
########################################
def test_mult_writer_preserves_zero_multipole(tmp_path):
    """
    A fully unpowered multipole with all-zero knl and ksl should survive a
    write and reload cycle. This exercises the writer's simple (unpowered) path
    which writes only env.new(name='m1', parent='mult_base') with no strength
    arguments.
    """
    original_line = _build_mult_line()
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert isinstance(reloaded_line["m1"], xt.Multipole), (
        "Unpowered multipole should reload as xt.Multipole. "
        f"Got: {type(reloaded_line['m1']).__name__}.")
    assert np.all(np.asarray(reloaded_line["m1"].knl) == pytest.approx(0.0)), (
        "Unpowered multipole should have all-zero knl after roundtrip. "
        f"Reloaded knl: {np.asarray(reloaded_line['m1'].knl).tolist()}.")


########################################
# Normal Multipole Components (knl)
########################################
def test_mult_writer_preserves_dipole_knl_component(tmp_path):
    """
    A thin dipole kick (knl[0] != 0) should be preserved through a write and
    reload cycle. knl values are written as literal arrays in the lattice file,
    not as optics expression variables.
    """
    original_line = _build_mult_line(knl = [1.5E-3])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["m1"].knl)[0] == pytest.approx(1.5E-3), (
        "Writer roundtrip should preserve multipole dipole component knl[0]. "
        f"Original: 1.5E-3, reloaded: {np.asarray(reloaded_line['m1'].knl)[0]}.")


def test_mult_writer_preserves_quadrupole_knl_component(tmp_path):
    """
    An integrated quadrupole kick (knl[1] != 0) should be preserved through a
    write and reload cycle.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["m1"].knl)[1] == pytest.approx(0.5), (
        "Writer roundtrip should preserve multipole quadrupole component knl[1]. "
        f"Original: 0.5, reloaded: {np.asarray(reloaded_line['m1'].knl)[1]}.")


def test_mult_writer_preserves_sextupole_knl_component(tmp_path):
    """
    An integrated sextupole kick (knl[2] != 0) should be preserved through a
    write and reload cycle.
    """
    original_line = _build_mult_line(knl = [0.0, 0.0, 2.0])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["m1"].knl)[2] == pytest.approx(2.0), (
        "Writer roundtrip should preserve multipole sextupole component knl[2]. "
        f"Original: 2.0, reloaded: {np.asarray(reloaded_line['m1'].knl)[2]}.")


def test_mult_writer_preserves_multiple_knl_components_simultaneously(tmp_path):
    """
    A multipole with several simultaneous non-zero knl components should
    preserve all of them through a write and reload cycle. The get_knl_string
    helper truncates trailing zeros and writes values at 24-decimal precision.
    """
    original_knl = [1.5E-3, 0.5, 2.0, 10.0]
    original_line = _build_mult_line(knl = original_knl)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    reloaded_knl = np.asarray(reloaded_line["m1"].knl)

    for i, expected in enumerate(original_knl):
        assert reloaded_knl[i] == pytest.approx(expected), (
            f"Writer roundtrip should preserve multipole knl[{i}]. "
            f"Original: {expected}, reloaded: {reloaded_knl[i]}.")


########################################
# Skew Multipole Components (ksl)
########################################
def test_mult_writer_preserves_dipole_ksl_component(tmp_path):
    """
    A skew dipole kick (ksl[0] != 0) should be preserved through a write and
    reload cycle. ksl values are written as literal arrays, not optics variables.
    """
    original_line = _build_mult_line(ksl = [0.8E-3])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["m1"].ksl)[0] == pytest.approx(0.8E-3), (
        "Writer roundtrip should preserve multipole skew dipole component ksl[0]. "
        f"Original: 0.8E-3, reloaded: {np.asarray(reloaded_line['m1'].ksl)[0]}.")


def test_mult_writer_preserves_sextupole_ksl_component(tmp_path):
    """
    An integrated skew sextupole kick (ksl[2] != 0) should be preserved
    through a write and reload cycle.
    """
    original_line = _build_mult_line(ksl = [0.0, 0.0, -1.5])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["m1"].ksl)[2] == pytest.approx(-1.5), (
        "Writer roundtrip should preserve multipole skew sextupole component ksl[2]. "
        f"Original: -1.5, reloaded: {np.asarray(reloaded_line['m1'].ksl)[2]}.")


def test_mult_writer_preserves_knl_and_ksl_simultaneously(tmp_path):
    """
    A multipole with both knl and ksl non-zero should preserve both through a
    write and reload cycle.
    """
    original_line = _build_mult_line(
        knl = [0.0, 0.5, 2.0],
        ksl = [0.0, 0.1, -0.8])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    reloaded_knl = np.asarray(reloaded_line["m1"].knl)
    reloaded_ksl = np.asarray(reloaded_line["m1"].ksl)

    assert reloaded_knl[1] == pytest.approx(0.5), (
        "Writer roundtrip should preserve knl[1] when ksl is also non-zero. "
        f"Original: 0.5, reloaded: {reloaded_knl[1]}.")
    assert reloaded_knl[2] == pytest.approx(2.0), (
        "Writer roundtrip should preserve knl[2] when ksl is also non-zero. "
        f"Original: 2.0, reloaded: {reloaded_knl[2]}.")
    assert reloaded_ksl[1] == pytest.approx(0.1), (
        "Writer roundtrip should preserve ksl[1] when knl is also non-zero. "
        f"Original: 0.1, reloaded: {reloaded_ksl[1]}.")
    assert reloaded_ksl[2] == pytest.approx(-0.8), (
        "Writer roundtrip should preserve ksl[2] when knl is also non-zero. "
        f"Original: -0.8, reloaded: {reloaded_ksl[2]}.")


########################################
# Precision
########################################
def test_mult_writer_knl_preserved_at_full_double_precision(tmp_path):
    """
    A knl value with many significant digits should survive a write and reload
    cycle at full double precision. The writer uses get_knl_string which formats
    values at 24 decimal places in scientific notation.
    """
    k1l_precise = 1.23456789012345678E-4
    original_line = _build_mult_line(knl = [0.0, k1l_precise])
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["m1"].knl)[1] == pytest.approx(
            k1l_precise, rel = 1E-15), (
        "Writer roundtrip should preserve multipole knl at full double precision. "
        f"Original: {k1l_precise!r}, "
        f"reloaded: {np.asarray(reloaded_line['m1'].knl)[1]!r}.")


########################################
# Strengths Not Written as Optics Variables
########################################
def test_mult_writer_knl_is_not_written_as_optics_variable(tmp_path):
    """
    Unlike quadrupole k1 or sextupole k2, multipole knl values are NOT written
    as live optics expression variables. They are baked into the lattice file as
    literal arrays. The Xsuite environment should therefore have no 'knl_m1'
    variable after reload.

    This is a deliberate writer design choice: multipoles carry thin-element
    combined-function kicks that are fully specified in the lattice file, not
    tunable strengths that benefit from a named optics variable.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5])
    env, _ = _write_and_load(line = original_line, tmp_path = tmp_path)

    with pytest.raises(KeyError):
        _ = env["knl_m1"]


################################################################################
# Misalignments via Hardcoded Values
################################################################################
# shift_x, shift_y, and rot_s_rad are written as literal numeric strings in
# the lattice file, identical to the mechanism used for quads, sexts, and octs.
########################################
# Horizontal Offset
########################################
def test_mult_writer_preserves_positive_shift_x(tmp_path):
    """
    A positive horizontal offset shift_x should be preserved through a write
    and reload cycle.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5], shift_x = 1.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve positive multipole shift_x. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['m1'].shift_x}.")


def test_mult_writer_preserves_negative_shift_x(tmp_path):
    """
    A negative horizontal offset shift_x should be preserved through a write
    and reload cycle.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5], shift_x = -1.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].shift_x == pytest.approx(-1.5E-3), (
        "Writer roundtrip should preserve negative multipole shift_x. "
        f"Original: -1.5E-3, reloaded: {reloaded_line['m1'].shift_x}.")


def test_mult_writer_preserves_shift_x_in_scientific_notation(tmp_path):
    """
    A very small shift_x value requiring scientific notation should survive a
    write and reload cycle.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5], shift_x = 4.56789012E-6)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].shift_x == pytest.approx(4.56789012E-6), (
        "Writer roundtrip should preserve a shift_x value in scientific notation. "
        f"Original: 4.56789012E-6, reloaded: {reloaded_line['m1'].shift_x}.")


########################################
# Vertical Offset
########################################
def test_mult_writer_preserves_positive_shift_y(tmp_path):
    """
    A positive vertical offset shift_y should be preserved through a write and
    reload cycle.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5], shift_y = 2.0E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].shift_y == pytest.approx(2.0E-3), (
        "Writer roundtrip should preserve positive multipole shift_y. "
        f"Original: 2.0E-3, reloaded: {reloaded_line['m1'].shift_y}.")


def test_mult_writer_preserves_negative_shift_y(tmp_path):
    """
    A negative vertical offset shift_y should be preserved through a write and
    reload cycle.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5], shift_y = -2.5E-3)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].shift_y == pytest.approx(-2.5E-3), (
        "Writer roundtrip should preserve negative multipole shift_y. "
        f"Original: -2.5E-3, reloaded: {reloaded_line['m1'].shift_y}.")


def test_mult_writer_preserves_shift_y_in_scientific_notation(tmp_path):
    """
    A very small shift_y value requiring scientific notation should survive a
    write and reload cycle.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5], shift_y = -7.65432109E-7)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].shift_y == pytest.approx(-7.65432109E-7), (
        "Writer roundtrip should preserve a shift_y value in scientific notation. "
        f"Original: -7.65432109E-7, reloaded: {reloaded_line['m1'].shift_y}.")


########################################
# In-Plane Rotation
########################################
def test_mult_writer_preserves_positive_rot_s_rad(tmp_path):
    """
    A positive in-plane rotation rot_s_rad should be preserved through a write
    and reload cycle.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5], rot_s_rad = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve positive multipole rot_s_rad. "
        f"Original: 0.05, reloaded: {reloaded_line['m1'].rot_s_rad}.")


def test_mult_writer_preserves_negative_rot_s_rad(tmp_path):
    """
    A negative in-plane rotation rot_s_rad should be preserved through a write
    and reload cycle.
    """
    original_line = _build_mult_line(knl = [0.0, 0.5], rot_s_rad = -0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].rot_s_rad == pytest.approx(-0.05), (
        "Writer roundtrip should preserve negative multipole rot_s_rad. "
        f"Original: -0.05, reloaded: {reloaded_line['m1'].rot_s_rad}.")


########################################
# All Misalignments Simultaneously
########################################
def test_mult_writer_preserves_all_misalignments_simultaneously(tmp_path):
    """
    A multipole with shift_x, shift_y, and rot_s_rad all non-zero but all-zero
    knl and ksl should preserve all three misalignment fields through a write
    and reload cycle. This exercises the complex path triggered by non-zero
    offsets even when the multipole carries no kick.
    """
    original_line = _build_mult_line(
        shift_x   = 1.0E-3,
        shift_y   = -2.0E-3,
        rot_s_rad = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    assert reloaded_line["m1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve shift_x alongside other misalignments. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['m1'].shift_x}.")
    assert reloaded_line["m1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve shift_y alongside other misalignments. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['m1'].shift_y}.")
    assert reloaded_line["m1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve rot_s_rad alongside other misalignments. "
        f"Original: 0.05, reloaded: {reloaded_line['m1'].rot_s_rad}.")


########################################
# Strengths with Misalignments
########################################
def test_mult_writer_preserves_knl_with_all_misalignments(tmp_path):
    """
    A multipole with knl, shift_x, shift_y, and rot_s_rad all non-zero should
    preserve all fields through a write and reload cycle.
    """
    original_line = _build_mult_line(
        knl       = [0.0, 0.5, 2.0],
        shift_x   = 1.0E-3,
        shift_y   = -2.0E-3,
        rot_s_rad = 0.05)
    reloaded_line = _writer_roundtrip(line = original_line, tmp_path = tmp_path)

    reloaded_knl = np.asarray(reloaded_line["m1"].knl)

    assert reloaded_knl[1] == pytest.approx(0.5), (
        "Writer roundtrip should preserve knl[1] alongside misalignments. "
        f"Original: 0.5, reloaded: {reloaded_knl[1]}.")
    assert reloaded_line["m1"].shift_x == pytest.approx(1.0E-3), (
        "Writer roundtrip should preserve shift_x alongside knl. "
        f"Original: 1.0E-3, reloaded: {reloaded_line['m1'].shift_x}.")
    assert reloaded_line["m1"].shift_y == pytest.approx(-2.0E-3), (
        "Writer roundtrip should preserve shift_y alongside knl. "
        f"Original: -2.0E-3, reloaded: {reloaded_line['m1'].shift_y}.")
    assert reloaded_line["m1"].rot_s_rad == pytest.approx(0.05), (
        "Writer roundtrip should preserve rot_s_rad alongside knl. "
        f"Original: 0.05, reloaded: {reloaded_line['m1'].rot_s_rad}.")


################################################################################
# Multi-Element Behaviour
################################################################################
########################################
# Multiple Multipoles
########################################
def test_mult_writer_preserves_multiple_multipoles_independently(tmp_path):
    """
    Multiple multipole elements with different knl arrays should each preserve
    their individual values through a single write and reload cycle.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Multipole(knl = [0.0, 0.5]),
            xt.Multipole(knl = [0.0, -0.5]),
            xt.Multipole(knl = [1.5E-3, 0.0, 2.0]),
            xt.Marker(),
        ],
        element_names = ["start", "mq", "mqd", "mcf", "end"])

    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = -1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    reloaded_line = _writer_roundtrip(line = line, tmp_path = tmp_path)

    assert np.asarray(reloaded_line["mq"].knl)[1] == pytest.approx(0.5), (
        "Writer roundtrip should preserve knl[1] for 'mq'. "
        f"Original: 0.5, reloaded: {np.asarray(reloaded_line['mq'].knl)[1]}.")
    assert np.asarray(reloaded_line["mqd"].knl)[1] == pytest.approx(-0.5), (
        "Writer roundtrip should preserve knl[1] for 'mqd'. "
        f"Original: -0.5, reloaded: {np.asarray(reloaded_line['mqd'].knl)[1]}.")
    assert np.asarray(reloaded_line["mcf"].knl)[0] == pytest.approx(1.5E-3), (
        "Writer roundtrip should preserve knl[0] for combined-function 'mcf'. "
        f"Original: 1.5E-3, reloaded: {np.asarray(reloaded_line['mcf'].knl)[0]}.")
    assert np.asarray(reloaded_line["mcf"].knl)[2] == pytest.approx(2.0), (
        "Writer roundtrip should preserve knl[2] for combined-function 'mcf'. "
        f"Original: 2.0, reloaded: {np.asarray(reloaded_line['mcf'].knl)[2]}.")
