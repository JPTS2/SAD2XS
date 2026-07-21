"""
================================================================================
Shared SAD Lattice Fixtures for SAD Helper Tests
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import textwrap

################################################################################
# Transfer-line lattices
################################################################################
def write_minimal_transfer_lattice(tmp_path):
    """
    Write a minimal SAD transfer-line lattice: a single 1 m drift between a
    START and END marker. Returns (filename, line_name) for direct use as
    sad_helpers arguments after monkeypatch.chdir(tmp_path).
    """
    lattice_path = tmp_path / "test_lattice.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_DRIFT  = (L = 1.0);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_DRIFT END);
        """))

    return lattice_path.name, "TEST_LINE"


def write_minimal_bend_lattice(tmp_path):
    """
    Write a minimal SAD transfer-line lattice: a 1 m bend (ANGLE = 0.1 rad)
    between a START and END marker. The bend produces non-zero horizontal
    dispersion, used to test reverse_survey_horizontal sign-flip behaviour.
    Returns (filename, line_name) for direct use as sad_helpers arguments after
    monkeypatch.chdir(tmp_path).
    """
    lattice_path = tmp_path / "test_bend_lattice.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_BEND   = (L = 1.0 ANGLE = 0.1);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """))

    return lattice_path.name, "TEST_LINE"


def write_minimal_vertical_bend_lattice(tmp_path):
    """
    Write a minimal SAD transfer-line lattice: a 1 m bend (ANGLE = 0.1 rad,
    ROTATE = pi/2) between a START and END marker. The ROTATE = pi/2 makes
    this a vertical bend, producing non-zero vertical dispersion, used to
    test reverse_survey_vertical sign-flip behaviour (the plain horizontal
    bend from write_minimal_bend_lattice has zero vertical content, so it
    cannot exercise this flag).
    Returns (filename, line_name) for direct use as sad_helpers arguments after
    monkeypatch.chdir(tmp_path).
    """
    lattice_path = tmp_path / "test_vertical_bend_lattice.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        BEND        TEST_BEND   = (L = 1.0 ANGLE = 0.1 ROTATE = 1.570796);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE   = (START TEST_BEND END);
        """))

    return lattice_path.name, "TEST_LINE"


################################################################################
# Asymmetric closed ring lattice
################################################################################
def write_asymmetric_closed_ring(tmp_path):
    """
    Write a closed ring with deliberately asymmetric elements (bend E1 != E2
    with F1/FRINGE, a K0-only corrector with FB1 != FB2, two opposite-sign
    quads) plus a native SAD-reversed line (LINE REV = (-FWD)). Used to
    verify reverse_element_order=True against SAD's own native reversal
    independently of the reverse_element_order code path under test.

    Returns (filename, fwd_line_name, rev_line_name) for direct use as
    sad_helpers arguments after monkeypatch.chdir(tmp_path).
    """
    lattice_path = tmp_path / "test_asymmetric_ring.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        BEND    B1  = (L=2.0 ANGLE=0.15 E1=0.3 E2=0.7 F1=0.05 FRINGE=1);
        DRIFT   D1  = (L=1.0);
        BEND    C1  = (L=0.4 K0=0.03 FRINGE=1 FB1=0.025 FB2=0.010);
        DRIFT   D2  = (L=1.0);
        QUAD    Q1  = (L=0.3 K1=0.8);
        DRIFT   D3  = (L=1.0);
        QUAD    Q2  = (L=0.3 K1=-0.6);
        DRIFT   D4  = (L=1.0);

        MARK    START = ()
                END   = ();

        LINE    FWD = (START B1 D1 C1 D2 Q1 D3 Q2 D4 END);
        LINE    REV = (-FWD);
        """))

    return lattice_path.name, "FWD", "REV"


################################################################################
# FODO ring lattice
################################################################################
def write_fodo_ring(tmp_path):
    """
    Write a minimal closed 4-cell FODO ring (2π total bending, K1 = ±0.2)
    with an RF cavity. Each cell contributes π/2 of bending via two π/4 bends
    (L = ρ = 0.7854 m). The RF cavity (VOLT = 1.0E6, FREQ = 1.8E7) is
    required by emit_sad and is harmless for chromaticity_sad — chromaticity is
    a transverse optics quantity unaffected by the longitudinal cavity.
    Element parameters use SAD's whitespace-separated syntax.

    Returns (filename, line_name) for direct use as sad_helpers arguments after
    monkeypatch.chdir(tmp_path).
    """
    lattice_path = tmp_path / "test_ring.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        QUAD    QF  = (L = 0.3 K1 =  0.2);
        QUAD    QD  = (L = 0.3 K1 = -0.2);
        BEND    B   = (L = 0.7854 ANGLE = 0.7854);
        DRIFT   D   = (L = 0.5);
        CAVI    CAV = (VOLT = 1.0E6 FREQ = 1.8E7);
        MARK    IP  = ();

        LINE    CELL = (QF D B D QD D B D);
        LINE    RING = (IP CELL CELL CELL CELL CAV);
        """))

    return lattice_path.name, "RING"
