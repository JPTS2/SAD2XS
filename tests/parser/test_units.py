"""
================================================================================
Tests for SAD parser unit handling
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-11
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import pytest

from sad2xs.config import Config
from sad2xs.converter._001_parser import ev_text_to_float, parse_sad_file

################################################################################
# Direct Energy Unit Conversion
################################################################################
@pytest.mark.parametrize(
    "value, expected",
    [
        ("1ev", 1.0),
        ("1kev", 1.0E3),
        ("1mev", 1.0E6),
        ("1gev", 1.0E9),
        ("1tev", 1.0E12),
        ("1.5mev", 1.5E6),
        ("1", 1.0),
    ])
def test_ev_text_to_float_converts_supported_units(value, expected):
    """
    Supported eV text units should convert to numeric eV values.
    """
    assert ev_text_to_float(value) == pytest.approx(expected), (
        f"Energy text '{value}' should convert to {expected} eV.")

def test_ev_text_to_float_returns_none_for_non_numeric_text():
    """
    Non-numeric text without a supported unit should not parse as energy.
    """
    assert ev_text_to_float("not_energy") is None, (
        "Non-numeric text without a supported unit should return None.")

################################################################################
# Energy Unit Parsing
################################################################################
def test_energy_units_parse_with_compact_and_spaced_formatting(write_lattice):
    """
    Energy units should parse with SAD-supported compact or spaced formatting.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0GEV;
        MASS = 0.511 MEV;
        """,
        filename = "units_energy_compact_and_spaced.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["p0c"] == pytest.approx(1.0E9), (
        "Compact MOMENTUM energy units should parse to eV.")
    assert parsed["globals"]["mass0"] == pytest.approx(0.511E6), (
        "Spaced MASS energy units should parse to eV.")

def test_energy_units_parse_case_insensitively(write_lattice):
    """
    Energy unit parsing should be case-insensitive after input normalisation.
    """
    lattice_path = write_lattice(
        """\
        Momentum = 1.0 GeV;
        Mass = 0.511 MeV;
        """,
        filename = "units_energy_case_insensitive.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["p0c"] == pytest.approx(1.0E9), (
        "Mixed-case MOMENTUM energy units should parse to eV.")
    assert parsed["globals"]["mass0"] == pytest.approx(0.511E6), (
        "Mixed-case MASS energy units should parse to eV.")

################################################################################
# Angle Unit Parsing
################################################################################
@pytest.mark.parametrize(
    "unit_text, expected",
    [
        ("45 DEG", np.pi / 4),
        ("45 deg", np.pi / 4),
        ("-30 DEG", -np.pi / 6),
    ])
def test_degree_angle_units_parse_to_radians(write_lattice, unit_text, expected):
    """
    SAD degree angle units should parse to radians.
    """
    lattice_path = write_lattice(
        f"""\
        MOMENTUM = 1.0 GEV;
        QUAD Q_ROT = (L = 1.0 ROTATE = {unit_text});
        """,
        filename = f"units_rotate_{unit_text.replace(' ', '_').lower()}.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["quad"]["q_rot"]["rotate"] == pytest.approx(
        expected), f"ROTATE = {unit_text} should parse to radians."

def test_radian_angle_units_parse_as_radians(write_lattice):
    """
    SAD RAD angle units should parse as numeric radians.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        QUAD Q_ROT = (L = 1.0 ROTATE = 0.1 RAD);
        """,
        filename = "units_rotate_rad.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["quad"]["q_rot"]["rotate"] == pytest.approx(
        0.1), "ROTATE values in RAD should parse as numeric radians."

def test_degree_units_parse_for_non_rotate_angle_fields(write_lattice):
    """
    SAD degree units should parse for other angular element parameters.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        BEND B_DEG = (L = 1.0 ANGLE = 45 DEG);
        """,
        filename = "units_bend_angle_degree.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["bend"]["b_deg"]["angle"] == pytest.approx(
        np.pi / 4), "BEND ANGLE values in DEG should parse to radians."
