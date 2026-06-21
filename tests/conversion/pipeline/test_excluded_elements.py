"""
================================================================================
Tests for the excluded_elements parameter of the SAD2XS conversion pipeline
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
import pytest
import sad2xs as s2x
import xtrack as xt

################################################################################
# No Exclusion
################################################################################
def test_pipeline_excluded_elements_none_leaves_elements_unchanged(write_lattice):
    """
    Passing excluded_elements=None should leave all elements in the converted line.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 END);
        """,
        filename = "excluded_elements_none.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        excluded_elements = None,
        _verbose          = False,
        _test_mode        = True)

    assert "d1" in line.element_names, (
        "Passing excluded_elements=None should leave 'd1' in the converted line.")
    assert "start" in line.element_names, (
        "Passing excluded_elements=None should leave 'start' in the converted line.")
    assert "end" in line.element_names, (
        "Passing excluded_elements=None should leave 'end' in the converted line.")


def test_pipeline_excluded_elements_empty_list_leaves_elements_unchanged(write_lattice):
    """
    Passing excluded_elements=[] should leave all elements in the converted line.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 END);
        """,
        filename = "excluded_elements_empty_list.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        excluded_elements = [],
        _verbose          = False,
        _test_mode        = True)

    assert "d1" in line.element_names, (
        "Passing excluded_elements=[] should leave 'd1' in the converted line.")
    assert "start" in line.element_names, (
        "Passing excluded_elements=[] should leave 'start' in the converted line.")
    assert "end" in line.element_names, (
        "Passing excluded_elements=[] should leave 'end' in the converted line.")


################################################################################
# Single Element Excluded
################################################################################
def test_pipeline_excluded_single_element_is_absent_from_line(write_lattice):
    """
    An element named in excluded_elements should not appear in the converted line.
    Element names are matched post-parse, so names must be lowercase.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 END);
        """,
        filename = "excluded_single_absent.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        excluded_elements = ["d1"],
        _verbose          = False,
        _test_mode        = True)

    assert "d1" not in line.element_names, (
        "Element 'd1' should be absent from the converted line after being "
        f"named in excluded_elements. Got: {line.element_names}.")


def test_pipeline_excluded_single_element_does_not_affect_other_elements(write_lattice):
    """
    Excluding one element should leave all other line elements unchanged.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0)
                    D2      = (L = 0.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 D2 END);
        """,
        filename = "excluded_single_others_unaffected.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        excluded_elements = ["d1"],
        _verbose          = False,
        _test_mode        = True)

    assert "d1" not in line.element_names, (
        "Element 'd1' should be absent after exclusion. "
        f"Got: {line.element_names}.")
    assert "d2" in line.element_names, (
        "Element 'd2' should remain in the converted line when only 'd1' is "
        f"excluded. Got: {line.element_names}.")
    assert "start" in line.element_names, (
        "Marker 'start' should remain in the converted line when only 'd1' is "
        f"excluded. Got: {line.element_names}.")
    assert "end" in line.element_names, (
        "Marker 'end' should remain in the converted line when only 'd1' is "
        f"excluded. Got: {line.element_names}.")


################################################################################
# Multiple Elements Excluded
################################################################################
def test_pipeline_excluded_multiple_elements_are_all_absent_from_line(write_lattice):
    """
    All elements named in excluded_elements should be absent from the converted
    line, while unlisted elements are unaffected.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);
        QUAD        Q1      = (L = 0.5 K1 = 0.1);
        DRIFT       D2      = (L = 0.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 Q1 D2 END);
        """,
        filename = "excluded_multiple_all_absent.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        excluded_elements = ["d1", "q1"],
        _verbose          = False,
        _test_mode        = True)

    assert "d1" not in line.element_names, (
        "Element 'd1' should be absent after exclusion. "
        f"Got: {line.element_names}.")
    assert "q1" not in line.element_names, (
        "Element 'q1' should be absent after exclusion. "
        f"Got: {line.element_names}.")
    assert "d2" in line.element_names, (
        "Element 'd2' should remain when only 'd1' and 'q1' are excluded. "
        f"Got: {line.element_names}.")
    assert "start" in line.element_names, (
        "Marker 'start' should remain when only 'd1' and 'q1' are excluded. "
        f"Got: {line.element_names}.")
    assert "end" in line.element_names, (
        "Marker 'end' should remain when only 'd1' and 'q1' are excluded. "
        f"Got: {line.element_names}.")


################################################################################
# Edge Cases
################################################################################
def test_pipeline_excluded_element_defined_but_not_in_line_raises_no_error(
        write_lattice):
    """
    Excluding an element that is defined in the SAD file but not referenced in
    any LINE should not raise an error.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);
        DRIFT       GHOST   = (L = 0.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 END);
        """,
        filename = "excluded_ghost_element.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        excluded_elements = ["ghost"],
        _verbose          = False,
        _test_mode        = True)

    assert isinstance(line, xt.Line), (
        "Excluding an element defined but not placed in any LINE should not "
        "raise an error — conversion should complete and return an xt.Line.")
    assert line.element_names == ["start", "d1", "end"], (
        "Excluding a ghost element should leave all placed elements intact. "
        f"Got: {line.element_names}.")


def test_pipeline_excluded_nonexistent_name_is_silently_ignored(write_lattice):
    """
    A name in excluded_elements that does not exist in the SAD file should be
    silently ignored — no error, and all elements remain in the converted line.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 END);
        """,
        filename = "excluded_nonexistent_ignored.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        excluded_elements = ["nonexistent"],
        _verbose          = False,
        _test_mode        = True)

    assert isinstance(line, xt.Line), (
        "A non-existent name in excluded_elements should be silently ignored "
        "and conversion should complete.")
    assert line.element_names == ["start", "d1", "end"], (
        "A non-existent excluded name should leave the converted line unchanged. "
        f"Got: {line.element_names}.")


################################################################################
# Auto-Reverse
################################################################################
def test_pipeline_excluded_forward_name_also_drops_reverse_form_from_line(
        write_lattice):
    """
    When a forward element name is excluded, its reverse form ('-name') should
    also be removed from the converted line. The exclusion stage auto-expands
    the list before filtering line components.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);
        DRIFT       D2      = (L = 0.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 -D1 D2 END);
        """,
        filename = "excluded_auto_reverse.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        output_directory  = "N/A",
        excluded_elements = ["d1"],
        _verbose          = False,
        _test_mode        = True)

    assert "d1" not in line.element_names, (
        "Forward element 'd1' should be absent after exclusion. "
        f"Got: {line.element_names}.")
    assert "-d1" not in line.element_names, (
        "Reverse form '-d1' should also be absent when 'd1' is excluded — "
        "the exclusion stage auto-expands to cover both forms. "
        f"Got: {line.element_names}.")
    assert "d2" in line.element_names, (
        "Unrelated element 'd2' should remain in the converted line. "
        f"Got: {line.element_names}.")
