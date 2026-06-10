"""
(Unofficial) SAD to XSuite Converter

Tests for SAD parser element expression handling.
"""

################################################################################
# Required Packages
################################################################################
import textwrap

import numpy as np
import pytest
import xtrack as xt

from sad2xs.config import Config
from sad2xs.converter._001_parser import parse_sad_file
from sad2xs.converter._003_expression_converter import convert_expressions
from sad2xs.converter._004_element_converter import convert_drifts

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
# Element Expressions
################################################################################
def test_element_parameters_accept_spaced_arithmetic_expressions(tmp_path):
    """
    Element values with spaced arithmetic should remain complete expressions.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        DL = 0.25;
        KBASE = 0.8;
        DK = 0.1;
        THETA = 0.02;

        DRIFT D_PLUS = (L = L0 + DL);
        DRIFT D_MINUS = (L = L0 - DL);
        QUAD Q_EXPR = (L = L0 + DL K1 = KBASE - DK ROTATE = 45 DEG);
        BEND B_EXPR = (L = 2 * L0 ANGLE = THETA / 2);
        """,
        filename = "element_spaced_expressions.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d_plus"]["l"] == "l0 + dl"
    assert parsed["elements"]["drift"]["d_minus"]["l"] == "l0 - dl"
    assert parsed["elements"]["quad"]["q_expr"]["l"] == "l0 + dl"
    assert parsed["elements"]["quad"]["q_expr"]["k1"] == "kbase - dk"
    assert parsed["elements"]["quad"]["q_expr"]["rotate"] == pytest.approx(
        np.pi / 4)
    assert parsed["elements"]["bend"]["b_expr"]["l"] == "2 * l0"
    assert parsed["elements"]["bend"]["b_expr"]["angle"] == "theta / 2"

def test_element_parameters_keep_compact_expressions_and_numeric_values(tmp_path):
    """
    Existing compact expressions and plain numeric parameters should be unchanged.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        DL = 0.25;
        KBASE = 0.8;
        DK = 0.1;

        DRIFT D_FLOAT = (L = 1.25);
        DRIFT D_COMPACT = (L = L0+DL);
        QUAD Q_FLOAT = (L = 2.0 K1 = 0.4);
        QUAD Q_COMPACT = (L = L0 K1 = KBASE-DK);
        """,
        filename = "element_compact_expressions.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d_float"]["l"] == pytest.approx(1.25)
    assert parsed["elements"]["drift"]["d_compact"]["l"] == "l0+dl"
    assert parsed["elements"]["quad"]["q_float"]["l"] == pytest.approx(2.0)
    assert parsed["elements"]["quad"]["q_float"]["k1"] == pytest.approx(0.4)
    assert parsed["elements"]["quad"]["q_compact"]["l"] == "l0"
    assert parsed["elements"]["quad"]["q_compact"]["k1"] == "kbase-dk"

def test_spaced_length_expression_can_be_evaluated_in_xsuite_environment(
        tmp_path):
    """
    Parsed spaced expressions should remain usable by Xsuite element creation.
    """
    lattice_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        L0 = 1.0;
        DL = 0.25;

        DRIFT D_EVAL = (L = L0 + DL);
        """,
        filename = "element_expression_evaluation.sad")

    config = Config(_verbose = False)
    parsed = parse_sad_file(str(lattice_path), config)

    environment = xt.Environment()
    convert_expressions(
        parsed_lattice_data = parsed,
        environment         = environment,
        config              = config)
    convert_drifts(
        parsed_elements = parsed["elements"],
        environment     = environment)

    assert environment["d_eval"].length == pytest.approx(1.25)
