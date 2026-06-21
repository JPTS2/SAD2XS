"""
================================================================================
Tests for SAD parser comment handling
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
import textwrap

from sad2xs.config import Config
from sad2xs.converter._001_parser import (
    load_and_clean_whitespace,
    parse_sad_file,
    strip_sad_comments)

################################################################################
# Comment Semicolons
################################################################################
def test_strip_sad_comments_removes_full_line_and_inline_comments():
    """
    Direct comment stripping should remove full-line and inline comments.
    """
    cleaned = strip_sad_comments(
        textwrap.dedent(
            """\
            ! full-line comment;
            DRIFT D1 = (L = 1.0); ! inline comment;
            LINE RING = (D1);
            """))

    assert "! full-line comment" not in cleaned, (
        "Full-line comments should be removed before section splitting.")
    assert "inline comment" not in cleaned, (
        "Inline comments should be removed before section splitting.")
    assert "DRIFT D1 = (L = 1.0);" in cleaned, (
        "Real SAD content before an inline comment should be preserved.")
    assert "LINE RING = (D1);" in cleaned, (
        "Real SAD content on later lines should be preserved.")

def test_strip_sad_comments_removes_comment_semicolons():
    """
    Semicolons inside stripped comments should not remain in parser input.
    """
    cleaned = strip_sad_comments(
        "DRIFT D1 = (L = 1.0); ! fake; sections; here;\n")

    assert cleaned.count(";") == 1, (
        "Only the real SAD section delimiter should remain after stripping "
        "comments.")

def test_comment_semicolons_do_not_create_sections(write_lattice):
    """
    Semicolons inside full-line or inline comments should not split sections.
    """
    lattice_path = write_lattice(
        """\
        ! full-line comment with ; and fake drift bad = (l = 9.0);
        MOMENTUM = 1.0 GEV; ! inline comment with ; and fake mass = 1.0 gev;

        DRIFT D1 = (L = 1.0); ! inline comment with ; and fake drift bad1 = (l = 9.0);
        ! another full-line comment; with several; semicolons;
        DRIFT D2 = (L = 2.0);
        LINE RING = (D1 D2); ! trailing comment; should be ignored
        """,
        filename = "commented_sections.sad")

    sections = [
        section.strip()
        for section in load_and_clean_whitespace(str(lattice_path))
        if section.strip()]

    assert len(sections) == 4
    assert all("fake" not in section for section in sections)
    assert all("comment" not in section for section in sections)

def test_parser_ignores_comment_semicolons(write_lattice):
    """
    Comment semicolons should not affect parsed globals, elements, or lines.
    """
    baseline_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = (L = 1.0);
        DRIFT D2 = (L = 2.0);
        LINE RING = (D1 D2);
        """,
        filename = "baseline.sad")
    commented_path = write_lattice(
        """\
        ! ignored full-line comment; including fake content;
        MOMENTUM = 1.0 GEV; ! ignored inline comment; including fake content;
        DRIFT D1 = (L = 1.0); ! ignored inline comment; fake drift bad = (l = 9.0);
        ! ignored full-line comment; including fake content;
        DRIFT D2 = (L = 2.0);
        LINE RING = (D1 D2); ! ignored trailing comment; fake line bad = (d1);
        """,
        filename = "commented.sad")

    config = Config(_verbose = False)

    baseline  = parse_sad_file(str(baseline_path), config)
    commented = parse_sad_file(str(commented_path), config)

    assert commented == baseline

################################################################################
# Comment Boundaries
################################################################################
def test_comment_only_file_creates_no_sections(write_lattice):
    """
    A file containing only comments should not create parsed SAD sections.
    """
    lattice_path = write_lattice(
        """\
        ! comment-only file;
        ! fake drift bad = (l = 9.0);
        """,
        filename = "comments_only.sad")

    sections = [
        section.strip()
        for section in load_and_clean_whitespace(str(lattice_path))
        if section.strip()]

    assert sections == [], (
        "Comment-only files should not produce non-empty SAD sections.")

def test_inline_comment_without_whitespace_is_removed(write_lattice):
    """
    Inline comments should be removed after the SAD section terminator.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = (L = 1.0);!inline comment; fake drift bad = (l = 9.0);
        LINE RING = (D1);
        """,
        filename = "inline_comment_no_space.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d1"]["l"] == 1.0, (
        "Inline comments after a section terminator should preserve preceding "
        "content.")
    assert "bad" not in parsed["elements"]["drift"], (
        "Inline comments after a section terminator should remove fake "
        "commented "
        "element definitions.")

def test_multiline_element_section_ignores_comment_content(write_lattice):
    """
    Comments inside multi-line element sections should not affect parsing.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = (L = 1.0) ! fake drift bad = (l = 9.0);
              D2 = (L = 2.0);
        LINE RING = (D1 D2);
        """,
        filename = "multiline_element_comments.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["elements"]["drift"]["d1"]["l"] == 1.0, (
        "Real element before an inline comment should be preserved.")
    assert parsed["elements"]["drift"]["d2"]["l"] == 2.0, (
        "Real element after a commented line segment should be preserved.")
    assert "bad" not in parsed["elements"]["drift"], (
        "Fake element definitions inside comments should be ignored.")

def test_multiple_elements_ignore_trailing_comment_content(write_lattice):
    """
    Comment text after a multi-element section should not add elements.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = (L = 1.0) D2 = (L = 2.0); ! fake drift d3 = (l = 3.0);
        LINE RING = (D1 D2);
        """,
        filename = "multiple_element_trailing_comment.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert set(parsed["elements"]["drift"]) == {"d1", "d2"}, (
        "Trailing comments should not add fake elements to a multi-element "
        "section.")
    assert parsed["elements"]["drift"]["d1"]["l"] == 1.0
    assert parsed["elements"]["drift"]["d2"]["l"] == 2.0

def test_commented_malformed_syntax_is_ignored(write_lattice):
    """
    Malformed SAD syntax inside comments should not raise parser errors.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV;
        ! DRIFT BAD = (L =);
        DRIFT D1 = (L = 1.0);
        LINE RING = (D1);
        """,
        filename = "commented_malformed_syntax.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert "bad" not in parsed["elements"]["drift"], (
        "Malformed element definitions inside comments should be ignored.")
    assert parsed["elements"]["drift"]["d1"]["l"] == 1.0, (
        "Valid elements following commented malformed syntax should parse.")

def test_inline_comment_after_global_does_not_override_defaults(write_lattice):
    """
    Fake globals inside inline comments should not alter parsed globals.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM = 1.0 GEV; ! MASS = 999.0 GEV; CHARGE = -1;
        DRIFT D1 = (L = 1.0);
        LINE RING = (D1);
        """,
        filename = "global_inline_comment.sad")

    parsed = parse_sad_file(str(lattice_path), Config(_verbose = False))

    assert parsed["globals"]["p0c"] == 1.0E9, (
        "Real momentum before an inline comment should be parsed.")
    assert parsed["globals"]["mass0"] != 999.0E9, (
        "Fake mass inside an inline comment should not override the default.")
    assert parsed["globals"]["q0"] == +1, (
        "Fake charge inside an inline comment should not override the default.")
