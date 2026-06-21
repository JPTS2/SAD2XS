"""
================================================================================
Shared SAD Lattice Fixtures for SAD Helper Tests
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
    dispersion, used to test reverse_bend_direction sign-flip behaviour.
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
