"""
================================================================================
Tests for SAD parser element parameter handling
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
import textwrap

import numpy as np
import pytest

from sad2xs.config import Config
from sad2xs.converter._001_parser import parse_sad_file, split_element_parameters

################################################################################
# Helpers
################################################################################
def write_lattice(tmp_path, content, filename = "test_lattice.sad"):
    """
    Write a temporary SAD lattice file for parser tests.
    """
    lattice_path = tmp_path / filename
    lattice_path.write_text(textwrap.dedent(content))
    return lattice_path

################################################################################
# Direct Parameter Splitting
################################################################################
def test_split_element_parameters_accepts_basic_assignments():
    """
    The splitter should identify adjacent SAD parameter assignments.
    """
    parameters = split_element_parameters("l=1.0 k1=0.2")

    assert parameters == [("l", "1.0"), ("k1", "0.2")], (
        "Basic adjacent element assignments should split into name/value pairs.")

def test_split_element_parameters_preserves_spaced_expressions():
    """
    Spaces inside arithmetic expressions should remain part of the value.
    """
    parameters = split_element_parameters("l=l0 + dl k1=k0 - dk")

    assert parameters == [("l", "l0 + dl"), ("k1", "k0 - dk")], (
        "Spaced expressions should not be split at arithmetic whitespace.")

def test_split_element_parameters_empty_string_returns_empty_list():
    """
    Empty element parameter strings should produce no assignments.
    """
    assert split_element_parameters("") == [], (
        "Empty parameter strings should return an empty parameter list.")

def test_split_element_parameters_missing_value_raises_clear_error():
    """
    A parameter name followed by '=' should require a value.
    """
    with pytest.raises(ValueError, match = "Expected a value"):
        split_element_parameters("l=")

################################################################################
# Parser Scalar Parameters
################################################################################
def test_element_parameters_parse_numeric_and_string_values(tmp_path):
    """
    Parser output should preserve floats as floats and expressions as strings.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        DRIFT D_NUM = (L = 1.0);
        DRIFT D_EXPR = (L = L0);
        """,
        filename = "element_parameters_basic.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d_num"]["l"] == pytest.approx(1.0), (
        "Numeric drift length parameters should parse as floats.")
    assert parsed["elements"]["drift"]["d_expr"]["l"] == "l0", (
        "Symbolic drift length parameters should parse as lowercase strings.")

def test_element_parameters_parse_signed_values(tmp_path):
    """
    Signed numeric parameter values should preserve sign and magnitude.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D_PLUS = (L = +1.0);
        QUAD Q_NEG = (L = 0.5 K1 = -0.2);
        BEND B_NEG = (L = 1.0 ANGLE = -0.01);
        """,
        filename = "element_parameters_signed.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d_plus"]["l"] == pytest.approx(1.0), (
        "Explicitly positive numeric values should parse as positive floats.")
    assert parsed["elements"]["quad"]["q_neg"]["k1"] == pytest.approx(-0.2), (
        "Negative quadrupole strengths should parse as negative floats.")
    assert parsed["elements"]["bend"]["b_neg"]["angle"] == pytest.approx(
        -0.01), "Negative bend angles should parse as negative floats."

def test_multiple_elements_in_one_section_are_parsed(tmp_path):
    """
    Multiple element definitions in one SAD section should all be preserved.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = (L = 1.0) D2 = (L = 2.0);
        """,
        filename = "element_parameters_multiple_elements.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d1"]["l"] == pytest.approx(1.0), (
        "The first element in a multi-element section should parse.")
    assert parsed["elements"]["drift"]["d2"]["l"] == pytest.approx(2.0), (
        "The second element in a multi-element section should parse.")

def test_multiline_elements_with_comments_are_parsed(tmp_path):
    """
    Multi-line element sections with comments should preserve real elements.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = (L = 1.0) ! fake drift bad = (l = 9.0);
              D2 = (L = 2.0);
        """,
        filename = "element_parameters_multiline_comments.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert set(parsed["elements"]["drift"]) == {"d1", "d2"}, (
        "Comments inside multi-line element sections should not create fake "
        "elements or remove real elements.")
    assert parsed["elements"]["drift"]["d1"]["l"] == pytest.approx(1.0)
    assert parsed["elements"]["drift"]["d2"]["l"] == pytest.approx(2.0)

################################################################################
# Unit Handling
################################################################################
def test_element_parameters_convert_positive_degrees_to_radians(tmp_path):
    """
    SAD degree values should be converted to radians.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        QUAD Q_ROT = (L = 1.0 ROTATE = 45 DEG);
        """,
        filename = "element_parameters_positive_degrees.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["quad"]["q_rot"]["rotate"] == pytest.approx(
        np.pi / 4), "Positive degree values should convert to radians."

def test_element_parameters_convert_negative_degrees_to_radians(tmp_path):
    """
    Negative SAD degree values should preserve sign after conversion.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        SEXT S_ROT = (L = 1.0 K2 = 0.3 ROTATE = -30 DEG);
        """,
        filename = "element_parameters_negative_degrees.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["sext"]["s_rot"]["rotate"] == pytest.approx(
        -np.pi / 6), "Negative degree values should convert to radians."

################################################################################
# High-Order and List Parameters
################################################################################
def test_multipole_scalar_high_order_parameters_are_parsed(tmp_path):
    """
    Scalar multipole field parameters should parse without list syntax.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        MULT M1 = (K0 = 0.1 K1 = 0.2 K2 = 0.3 SK1 = -0.4);
        """,
        filename = "element_parameters_multipole_scalars.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["mult"]["m1"]["k0"] == pytest.approx(0.1)
    assert parsed["elements"]["mult"]["m1"]["k1"] == pytest.approx(0.2)
    assert parsed["elements"]["mult"]["m1"]["k2"] == pytest.approx(0.3)
    assert parsed["elements"]["mult"]["m1"]["sk1"] == pytest.approx(-0.4)

################################################################################
# Malformed Syntax
################################################################################
def test_malformed_element_missing_open_parenthesis_raises_clear_error(tmp_path):
    """
    Malformed element definitions should fail instead of parsing silently.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = L = 1.0);
        """,
        filename = "element_parameters_missing_open_parenthesis.sad")

    with pytest.raises(ValueError):
        parse_sad_file(str(lattice_path), Config(_verbose = False))

def test_malformed_element_missing_assignment_raises_clear_error(tmp_path):
    """
    Element parameters without assignment syntax should fail clearly.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = (L 1.0);
        """,
        filename = "element_parameters_missing_assignment.sad")

    with pytest.raises(ValueError, match = "Expected one or more"):
        parse_sad_file(str(lattice_path), Config(_verbose = False))
