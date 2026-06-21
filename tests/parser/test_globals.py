"""
================================================================================
Tests for SAD parser global variable handling
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import xtrack as xt

from sad2xs.config import Config
from sad2xs.converter._001_parser import parse_sad_file

################################################################################
# Energy Units
################################################################################
@pytest.mark.parametrize(
    "unit, expected",
    [
        ("EV", 1.0),
        ("KEV", 1.0E3),
        ("MEV", 1.0E6),
        ("GEV", 1.0E9),
        ("TEV", 1.0E12),
        ("", 1.0),
    ])
def test_momentum_energy_units_parse_to_ev(write_lattice, unit, expected):
    """
    MOMENTUM values should parse supported energy units into eV.
    """
    lattice_path = write_lattice(
        f"""\
        MOMENTUM = 1.0 {unit};
        """,
        filename = f"globals_momentum_{unit.lower() or 'unitless'}.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["p0c"] == pytest.approx(expected), (
        f"MOMENTUM with unit '{unit or 'unitless'}' should parse to eV.")

@pytest.mark.parametrize(
    "unit, expected",
    [
        ("EV", 0.511),
        ("KEV", 0.511E3),
        ("MEV", 0.511E6),
        ("GEV", 0.511E9),
        ("TEV", 0.511E12),
        ("", 0.511),
    ])
def test_mass_energy_units_parse_to_ev(write_lattice, unit, expected):
    """
    MASS values should parse supported energy units into eV.
    """
    lattice_path = write_lattice(
        f"""\
        MOMENTUM = 1.0 GEV;
        MASS = 0.511 {unit};
        """,
        filename = f"globals_mass_{unit.lower() or 'unitless'}.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["mass0"] == pytest.approx(expected), (
        f"MASS with unit '{unit or 'unitless'}' should parse to eV.")

################################################################################
# Explicit Globals
################################################################################
def test_charge_and_fshift_parse_as_globals(write_lattice):
    """
    CHARGE and FSHIFT should parse into q0 and fshift globals.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        CHARGE = -1.0;
        FSHIFT = 0.01;
        """,
        filename = "globals_charge_fshift.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["q0"] == pytest.approx(-1.0), (
        "CHARGE should parse into q0.")
    assert parsed["globals"]["fshift"] == pytest.approx(0.01), (
        "FSHIFT should parse into fshift.")

def test_compact_lowercase_global_assignments_parse(write_lattice):
    """
    Compact lowercase global assignments should parse like spaced uppercase ones.
    """
    lattice_path = write_lattice(
        """\
        momentum=1.0gev;
        mass=0.511mev;
        charge=-1.0;
        fshift=0.01;
        """,
        filename = "globals_compact_lowercase.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["p0c"] == pytest.approx(1.0E9), (
        "Compact lowercase momentum should parse into p0c.")
    assert parsed["globals"]["mass0"] == pytest.approx(0.511E6), (
        "Compact lowercase mass should parse into mass0.")
    assert parsed["globals"]["q0"] == pytest.approx(-1.0), (
        "Compact lowercase charge should parse into q0.")
    assert parsed["globals"]["fshift"] == pytest.approx(0.01), (
        "Compact lowercase fshift should parse into fshift.")

################################################################################
# Defaults
################################################################################
def test_missing_mass_charge_and_fshift_use_defaults(write_lattice):
    """
    Missing optional globals should use documented parser defaults.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        """,
        filename = "globals_defaults.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["mass0"] == pytest.approx(xt.ELECTRON_MASS_EV), (
        "Missing MASS should default to the electron mass.")
    assert parsed["globals"]["q0"] == pytest.approx(+1.0), (
        "Missing CHARGE should default to +1.")
    assert parsed["globals"]["fshift"] == pytest.approx(0.0), (
        "Missing FSHIFT should default to 0.0.")

def test_missing_momentum_uses_config_fallback(write_lattice):
    """
    Config ref_particle_p0c should supply missing SAD momentum.
    """
    lattice_path = write_lattice(
        """\
        DRIFT D1 = (L = 1.0);
        LINE RING = (D1);
        """,
        filename = "globals_momentum_config_fallback.sad")

    parsed = parse_sad_file(
        str(lattice_path),
        Config(_verbose = False, ref_particle_p0c = 2.0E9))

    assert parsed["globals"]["p0c"] == pytest.approx(2.0E9), (
        "Config ref_particle_p0c should provide missing momentum.")

def test_missing_momentum_without_config_fallback_raises(write_lattice):
    """
    Missing SAD momentum should fail when no config fallback is provided.
    """
    lattice_path = write_lattice(
        """\
        DRIFT D1 = (L = 1.0);
        LINE RING = (D1);
        """,
        filename = "globals_missing_momentum_error.sad")

    with pytest.raises(ValueError, match = "No momentum"):
        parse_sad_file(str(lattice_path), Config(_verbose = False))

################################################################################
# Config Overrides
################################################################################
def test_config_ref_particle_values_override_sad_globals(write_lattice):
    """
    Explicit config reference-particle values should override SAD globals.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        MASS = 0.511 MEV;
        CHARGE = -1.0;
        """,
        filename = "globals_config_override.sad")

    parsed = parse_sad_file(
        str(lattice_path),
        Config(
            _verbose            = False,
            ref_particle_p0c    = 2.0E9,
            ref_particle_mass0  = 3.0E6,
            ref_particle_q0     = +1.0))

    assert parsed["globals"]["p0c"] == pytest.approx(2.0E9), (
        "Config ref_particle_p0c should override SAD MOMENTUM.")
    assert parsed["globals"]["mass0"] == pytest.approx(3.0E6), (
        "Config ref_particle_mass0 should override SAD MASS.")
    assert parsed["globals"]["q0"] == pytest.approx(+1.0), (
        "Config ref_particle_q0 should override SAD CHARGE.")

################################################################################
# Boundary With Deferred Expressions
################################################################################
def test_special_globals_are_not_duplicated_as_deferred_expressions(write_lattice):
    """
    Special global assignments should not also appear as deferred expressions.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        MASS = 0.511 MEV;
        CHARGE = -1.0;
        FSHIFT = 0.01;
        A = 1.0;
        """,
        filename = "globals_expression_boundary.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert set(parsed["expressions"]) == {"a"}, (
        "Only ordinary assignments should appear in deferred expressions.")

def test_global_name_prefix_collisions_remain_deferred_expressions(write_lattice):
    """
    Names starting with global keywords should not be parsed as special globals.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM_OFFSET = 1.0;
        MASS_SCALE = 2.0;
        CHARGE_STATE = -1.0;
        FSHIFT_VALUE = 0.01;
        MOMENTUM = 1.0 GEV;
        """,
        filename = "globals_prefix_collision.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["p0c"] == pytest.approx(1.0E9), (
        "Real MOMENTUM should still parse into p0c.")
    assert parsed["expressions"]["momentum_offset"] == pytest.approx(1.0), (
        "MOMENTUM_OFFSET should remain a deferred expression.")
    assert parsed["expressions"]["mass_scale"] == pytest.approx(2.0), (
        "MASS_SCALE should remain a deferred expression.")
    assert parsed["expressions"]["charge_state"] == pytest.approx(-1.0), (
        "CHARGE_STATE should remain a deferred expression.")
    assert parsed["expressions"]["fshift_value"] == pytest.approx(0.01), (
        "FSHIFT_VALUE should remain a deferred expression.")
