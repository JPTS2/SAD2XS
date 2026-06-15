"""
================================================================================
Tests for the reverse_charge parameter of the SAD2XS conversion pipeline
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
# Default Behaviour
################################################################################
def test_pipeline_reverse_charge_false_leaves_q0_unchanged(write_lattice):
    """
    When reverse_charge is not set, the reference particle q0 should reflect
    the SAD CHARGE global without modification.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        CHARGE      = 1.0;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "reverse_charge_false.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.particle_ref.q0 == pytest.approx(1.0), (
        "Reference particle q0 should remain +1.0 when reverse_charge is not "
        f"set. Got: {line.particle_ref.q0}.")


################################################################################
# Charge Reversal
################################################################################
def test_pipeline_reverse_charge_negates_positive_q0(write_lattice):
    """
    reverse_charge=True should negate a positive q0, producing a negative charge.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "reverse_charge_positive.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge   = True,
        _verbose         = False,
        _test_mode       = True)

    assert line.particle_ref.q0 == pytest.approx(-1.0), (
        "reverse_charge=True should negate the default q0 of +1.0 to -1.0. "
        f"Got: {line.particle_ref.q0}.")


def test_pipeline_reverse_charge_negates_negative_q0(write_lattice):
    """
    reverse_charge=True applied to an explicit negative SAD CHARGE should
    produce a positive q0.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        CHARGE      = -1.0;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "reverse_charge_negative.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge   = True,
        _verbose         = False,
        _test_mode       = True)

    assert line.particle_ref.q0 == pytest.approx(1.0), (
        "reverse_charge=True applied to SAD CHARGE = -1.0 should produce "
        f"q0 = +1.0. Got: {line.particle_ref.q0}.")


################################################################################
# Field Isolation
################################################################################
def test_pipeline_reverse_charge_does_not_affect_p0c_or_mass0(write_lattice):
    """
    reverse_charge=True should only negate q0. The p0c and mass0 fields of the
    reference particle should be unaffected.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 2.0 GEV;
        MASS        = 938.272 MEV;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "reverse_charge_field_isolation.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        reverse_charge   = True,
        _verbose         = False,
        _test_mode       = True)

    assert line.particle_ref.q0 == pytest.approx(-1.0), (
        "reverse_charge=True should negate q0 from +1.0 to -1.0. "
        f"Got: {line.particle_ref.q0}.")
    assert line.particle_ref.p0c[0] == pytest.approx(2.0E9), (
        "reverse_charge=True should not affect p0c. Expected 2.0E9 eV from "
        f"SAD MOMENTUM = 2.0 GEV. Got: {line.particle_ref.p0c[0]}.")
    assert line.particle_ref.mass0 == pytest.approx(938.272E6), (
        "reverse_charge=True should not affect mass0. Expected 938.272E6 eV "
        f"from SAD MASS = 938.272 MEV. Got: {line.particle_ref.mass0}.")
