"""
(Unofficial) SAD to XSuite Converter

Tests for SAD parser comment handling.
"""

################################################################################
# Required Packages
################################################################################
import textwrap

from sad2xs.config import Config
from sad2xs.converter._001_parser import load_and_clean_whitespace, parse_sad_file

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
# Comment Semicolons
################################################################################
def test_comment_semicolons_do_not_create_sections(tmp_path):
    """
    Semicolons inside full-line or inline comments should not split sections.
    """
    lattice_path = write_lattice(
        tmp_path,
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

def test_parser_ignores_comment_semicolons(tmp_path):
    """
    Comment semicolons should not affect parsed globals, elements, or lines.
    """
    baseline_path = write_lattice(
        tmp_path,
        """\
        MOMENTUM = 1.0 GEV;
        DRIFT D1 = (L = 1.0);
        DRIFT D2 = (L = 2.0);
        LINE RING = (D1 D2);
        """,
        filename = "baseline.sad")
    commented_path = write_lattice(
        tmp_path,
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
