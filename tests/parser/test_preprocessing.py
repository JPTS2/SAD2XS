"""
================================================================================
Tests for SAD parser preprocessing
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

from sad2xs.config import Config
from sad2xs.converter._001_parser import parse_sad_file

################################################################################
# SAD Command Filtering
################################################################################
def test_on_and_off_commands_are_removed_before_parsing(write_lattice):
    """
    SAD ON/OFF commands should not be treated as expressions or elements.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        ON RAD;
        OFF COD;
        DRIFT D1 = (L = 1.0);
        LINE RING = (D1);
        """,
        filename = "commands_on_off_removed.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d1"]["l"] == pytest.approx(1.0), (
        "Valid elements after ON/OFF commands should still be parsed.")
    assert parsed["lines"]["ring"] == ["d1"], (
        "Valid lines after ON/OFF commands should still be parsed.")
    assert "on rad" not in parsed["expressions"], (
        "ON commands should not be parsed as deferred expressions.")
    assert "off cod" not in parsed["expressions"], (
        "OFF commands should not be parsed as deferred expressions.")

def test_on_and_off_prefix_variable_names_are_not_removed(write_lattice):
    """
    SAD-valid names starting with ON/OFF should remain deferred expressions.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        ONVALUE = 1.0;
        OFFVALUE = 2.0;
        DRIFT D1 = (L = ONVALUE);
        DRIFT D2 = (L = OFFVALUE);
        LINE RING = (D1 D2);
        """,
        filename = "commands_on_off_prefix_variables.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["expressions"]["onvalue"] == pytest.approx(1.0), (
        "SAD-valid variable names beginning with ON should not be removed as "
        "ON commands.")
    assert parsed["expressions"]["offvalue"] == pytest.approx(2.0), (
        "SAD-valid variable names beginning with OFF should not be removed as "
        "OFF commands.")
    assert parsed["elements"]["drift"]["d1"]["l"] == "onvalue", (
        "Element expressions should preserve ON-prefixed variable names.")
    assert parsed["elements"]["drift"]["d2"]["l"] == "offvalue", (
        "Element expressions should preserve OFF-prefixed variable names.")

################################################################################
# Case Normalization
################################################################################
def test_parser_normalizes_names_commands_parameters_and_expressions(write_lattice):
    """
    SAD names should be normalized consistently to lowercase parser keys.
    """
    lattice_path = write_lattice(
        """\
        MoMeNtUm = 1.0 GeV;
        LBase = 1.5;
        DrIfT D_MiXeD = (L = LBase);
        LiNe RiNg = (D_MiXeD);
        """,
        filename = "case_normalization_mixed_case.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["p0c"] == pytest.approx(1.0E9), (
        "Mixed-case MOMENTUM should parse as the p0c global.")
    assert parsed["expressions"]["lbase"] == pytest.approx(1.5), (
        "Mixed-case deferred expression names should normalize to lowercase.")
    assert parsed["elements"]["drift"]["d_mixed"]["l"] == "lbase", (
        "Mixed-case element names, parameter names, and expression references "
        "should normalize to lowercase.")
    assert parsed["lines"]["ring"] == ["d_mixed"], (
        "Mixed-case line names and components should normalize to lowercase.")

################################################################################
# Whitespace Normalization
################################################################################
def test_tabs_blank_lines_and_indented_continuations_are_normalized(write_lattice):
    """
    Tabs, blank lines, and indented continuations should not change parsing.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM\t=\t1.0\tGEV;

        DRIFT\tD1\t=\t(L\t=\t1.0)
               D2\t=\t(L\t=\t2.0);

        LINE\tRING\t=\t(
            D1
            D2
        );
        """,
        filename = "whitespace_tabs_blank_lines.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["p0c"] == pytest.approx(1.0E9), (
        "Tabbed MOMENTUM assignment should parse.")
    assert parsed["elements"]["drift"]["d1"]["l"] == pytest.approx(1.0), (
        "First drift in a tabbed multiline section should parse.")
    assert parsed["elements"]["drift"]["d2"]["l"] == pytest.approx(2.0), (
        "Indented continuation drift should parse.")
    assert parsed["lines"]["ring"] == ["d1", "d2"], (
        "Multiline tabbed line components should preserve order.")
