"""
================================================================================
Tests that a declared subline is never mistaken for a generated one
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-09-07
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import sad2xs as s2x

################################################################################
# Declared Sublines Using Former Generated-Name Shapes
################################################################################
# SAD2XS once named its invented lines "{name}_compound" and "{name}_reversed".
# Both are plausible names for a real subline, so a lattice declaring one was
# silently adopted in place of the generated line. The suffixes are now
# sentinels; these lattices check the declared lines are left alone.
def test_declared_compound_subline_is_not_adopted(write_lattice):
    """
    A declared subline named "X_COMPOUND" must not stand in for element "X".
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1          = (L = 1.0)
                    D2          = (L = 2.0);

        QUAD        Q1          = (L = 0.5 K1 = 0.1);

        MARK        START       = ()
                    END         = ();

        LINE        Q1_COMPOUND = (D2 D2);

        LINE        TEST_LINE   = (START Q1 D1 END);
        """,
        filename = "declared_compound_subline.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        line_name         = "TEST_LINE",
        output_directory  = "N/A",
        _verbose          = False,
        _test_mode        = True)

    assert list(line.element_names) == ["start", "q1", "d1", "end"], (
        "A declared \"Q1_COMPOUND\" subline should not be substituted for "
        f"\"q1\". Got: {list(line.element_names)}.")


def test_declared_reversed_subline_is_not_adopted(write_lattice):
    """
    A declared subline named "X_REVERSED" must not stand in for the reversal
    of subline "X".
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1          = (L = 1.0)
                    D2          = (L = 2.0);

        QUAD        Q1          = (L = 0.5 K1 = 0.1);

        MARK        START       = ()
                    END         = ();

        LINE        SUB         = (D1 Q1 D2);
        LINE        SUB_REVERSED = (D2 D2 D2);

        LINE        TEST_LINE   = (START -SUB END);
        """,
        filename = "declared_reversed_subline.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path  = str(lattice_path),
        line_name         = "TEST_LINE",
        output_directory  = "N/A",
        _verbose          = False,
        _test_mode        = True)

    assert list(line.element_names) == ["start", "d2", "q1", "d1", "end"], (
        "\"-SUB\" should be built from \"SUB\", not taken from the declared "
        f"\"SUB_REVERSED\" subline. Got: {list(line.element_names)}.")
