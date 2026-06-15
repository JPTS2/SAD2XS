"""
================================================================================
Tests for user multipole replacements in the SAD2XS conversion pipeline
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-15
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import sad2xs as s2x
import xtrack as xt

################################################################################
# No Replacement
################################################################################
def test_pipeline_mult_without_replacement_produces_multipole(write_lattice):
    """
    A SAD MULT element with no user replacement should produce an xt.Multipole.
    A combined (multi-order) MULT is used to ensure the default simplification
    path does not auto-promote the element to a single type.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MULT        MELE    = (L = 0.1 K0 = 0.001 K1 = 0.01);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START MELE END);
        """,
        filename = "mult_no_replacement.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path          = str(lattice_path),
        output_directory          = "N/A",
        user_multipole_replacements = None,
        _verbose                  = False,
        _test_mode                = True)

    assert isinstance(line["mele"], xt.Multipole), (
        "A combined SAD MULT with no user replacement should produce an "
        f"xt.Multipole. Got: {type(line['mele']).__name__}.")


################################################################################
# Type Replacement
################################################################################
@pytest.mark.parametrize(
    "replacement_type, sad_param, xsuite_type, xsuite_attr, expected_strength",
    [
        ("Quadrupole", "K1", xt.Quadrupole, "k1", 0.2),
        ("Sextupole",  "K2", xt.Sextupole,  "k2", 0.2),
        ("Octupole",   "K3", xt.Octupole,   "k3", 0.2),
        ("Bend",       "K0", xt.Bend,        "k0", 0.2),
    ])
def test_pipeline_mult_user_replacement_produces_correct_type_and_strength(
        write_lattice,
        replacement_type,
        sad_param,
        xsuite_type,
        xsuite_attr,
        expected_strength):
    """
    A MULT whose name matches a user replacement prefix should become the target
    Xsuite type, with integrated strength (KnL) divided by element length (L).
    L = 0.5, KnL = 0.1 → expected strength = 0.2.
    """
    lattice_path = write_lattice(
        f"""\
        MOMENTUM    = 1.0 GEV;

        MULT        MELE    = (L = 0.5 {sad_param} = 0.1);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START MELE END);
        """,
        filename = f"mult_replacement_{replacement_type.lower()}.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path            = str(lattice_path),
        output_directory            = "N/A",
        user_multipole_replacements = {"mele": replacement_type},
        _verbose                    = False,
        _test_mode                  = True)

    assert isinstance(line["mele"], xsuite_type), (
        f"SAD MULT with user replacement '{replacement_type}' should produce an "
        f"xt.{xsuite_type.__name__}. Got: {type(line['mele']).__name__}.")
    assert getattr(line["mele"], xsuite_attr) == pytest.approx(expected_strength), (
        f"Replacement {replacement_type} should divide KnL = 0.1 by L = 0.5 to "
        f"give {xsuite_attr} = {expected_strength}. "
        f"Got: {getattr(line['mele'], xsuite_attr)}.")


################################################################################
# Prefix Selectivity
################################################################################
def test_pipeline_mult_replacement_prefix_is_selective(write_lattice):
    """
    A user replacement key should only match MULT elements whose names start
    with that prefix. Elements with non-matching names should remain xt.Multipole.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MULT        MX1     = (L = 0.5 K1 = 0.1);
        MULT        MY1     = (L = 0.1 K0 = 0.001 K1 = 0.01);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START MX1 MY1 END);
        """,
        filename = "mult_replacement_prefix_selective.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path            = str(lattice_path),
        output_directory            = "N/A",
        user_multipole_replacements = {"mx": "Quadrupole"},
        _verbose                    = False,
        _test_mode                  = True)

    assert isinstance(line["mx1"], xt.Quadrupole), (
        "SAD MULT 'mx1' should be replaced with xt.Quadrupole because its name "
        f"starts with the prefix 'mx'. Got: {type(line['mx1']).__name__}.")
    assert isinstance(line["my1"], xt.Multipole), (
        "SAD MULT 'my1' should remain an xt.Multipole because its name does not "
        f"start with the prefix 'mx'. Got: {type(line['my1']).__name__}.")


################################################################################
# Multiple Replacement Keys
################################################################################
def test_pipeline_mult_multiple_replacement_keys_applied_independently(write_lattice):
    """
    Multiple user replacement keys should each be applied to their matching
    elements independently in a single conversion.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MULT        MX1     = (L = 0.5 K1 = 0.1);
        MULT        MY1     = (L = 0.5 K2 = 0.1);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START MX1 MY1 END);
        """,
        filename = "mult_replacement_multiple_keys.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path            = str(lattice_path),
        output_directory            = "N/A",
        user_multipole_replacements = {"mx": "Quadrupole", "my": "Sextupole"},
        _verbose                    = False,
        _test_mode                  = True)

    assert isinstance(line["mx1"], xt.Quadrupole), (
        "SAD MULT 'mx1' should become xt.Quadrupole via the 'mx' replacement key. "
        f"Got: {type(line['mx1']).__name__}.")
    assert isinstance(line["my1"], xt.Sextupole), (
        "SAD MULT 'my1' should become xt.Sextupole via the 'my' replacement key. "
        f"Got: {type(line['my1']).__name__}.")
    assert line["mx1"].k1 == pytest.approx(0.2), (
        "Quadrupole replacement should divide K1L = 0.1 by L = 0.5 to give "
        f"k1 = 0.2. Got: {line['mx1'].k1}.")
    assert line["my1"].k2 == pytest.approx(0.2), (
        "Sextupole replacement should divide K2L = 0.1 by L = 0.5 to give "
        f"k2 = 0.2. Got: {line['my1'].k2}.")


################################################################################
# Error Propagation
################################################################################
def test_pipeline_mult_thin_replacement_raises_value_error(write_lattice):
    """
    A thin SAD MULT element (no L parameter) matched by a user replacement key
    should raise a ValueError — integrated strengths cannot be divided by zero
    length to produce a physical thick element.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MULT        MELE    = (K1 = 0.01);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START MELE END);
        """,
        filename = "mult_replacement_thin_error.sad")

    with pytest.raises(ValueError, match = "Cannot replace thin SAD multipole"):
        s2x.convert_sad_to_xsuite(
            sad_lattice_path            = str(lattice_path),
            output_directory            = "N/A",
            user_multipole_replacements = {"mele": "Quadrupole"},
            _verbose                    = False,
            _test_mode                  = True)
