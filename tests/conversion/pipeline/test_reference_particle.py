"""
================================================================================
Tests for the reference particle set by the SAD2XS conversion pipeline
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-27
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import sad2xs as s2x
import xtrack as xt

################################################################################
# Default Field Values
################################################################################
def test_pipeline_reference_particle_p0c_matches_sad_momentum(write_lattice):
    """
    The reference particle p0c should match the SAD MOMENTUM value.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "ref_particle_p0c_default.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.particle_ref.p0c[0] == pytest.approx(1.0E9), (
        "Reference particle p0c should match SAD MOMENTUM = 1.0 GEV = 1.0E9 eV. "
        f"Got: {line.particle_ref.p0c[0]}.")


def test_pipeline_reference_particle_mass0_defaults_to_electron_mass(write_lattice):
    """
    When MASS is absent from the SAD file, the reference particle mass0 should
    default to the electron mass.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "ref_particle_mass0_default.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.particle_ref.mass0 == pytest.approx(xt.ELECTRON_MASS_EV), (
        "Reference particle mass0 should default to the electron mass when "
        f"MASS is absent from the SAD file. Got: {line.particle_ref.mass0}.")


def test_pipeline_reference_particle_q0_defaults_to_positive_one(write_lattice):
    """
    When CHARGE is absent from the SAD file, the reference particle q0 should
    default to +1.0.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "ref_particle_q0_default.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.particle_ref.q0 == pytest.approx(1.0), (
        "Reference particle q0 should default to +1.0 when CHARGE is absent "
        f"from the SAD file. Got: {line.particle_ref.q0}.")


################################################################################
# Explicit SAD Globals
################################################################################
def test_pipeline_reference_particle_explicit_mass_is_preserved(write_lattice):
    """
    An explicit SAD MASS global should be reflected in the reference particle mass0.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        MASS        = 938.272 MEV;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "ref_particle_explicit_mass.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.particle_ref.mass0 == pytest.approx(938.272E6), (
        "Reference particle mass0 should match SAD MASS = 938.272 MEV = 938.272E6 eV. "
        f"Got: {line.particle_ref.mass0}.")


def test_pipeline_reference_particle_explicit_charge_is_ignored_with_warning(write_lattice):
    """
    SAD does not support non-positron CHARGE (confirmed by Oide, 2026-06-27).
    A SAD CHARGE != 1 must be silently ignored and a UserWarning emitted.
    The reference particle q0 should always be +1 regardless of the SAD value.
    Use reverse_charge=True in the converter to simulate electron/antiproton rings.
    """
    import warnings

    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        CHARGE      = -1.0;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "ref_particle_explicit_charge.sad")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path = str(lattice_path),
            output_directory = "N/A",
            _verbose         = False,
            _test_mode       = True)

    assert any(issubclass(w.category, UserWarning) and "CHARGE" in str(w.message)
               for w in caught), (
        "A UserWarning mentioning CHARGE should be emitted when CHARGE != 1 "
        "is found in the SAD file.")
    assert line.particle_ref.q0 == pytest.approx(1.0), (
        "SAD CHARGE = -1.0 must be ignored — q0 should be +1.0 (positron). "
        f"Got: {line.particle_ref.q0}.")


def test_pipeline_reference_particle_all_three_fields_set_simultaneously(write_lattice):
    """
    When MOMENTUM, MASS, and CHARGE are all set in the SAD file, all three
    reference particle fields should reflect the SAD values.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 3.0 GEV;
        MASS        = 938.272 MEV;
        CHARGE      = 1.0;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "ref_particle_all_three_fields.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.particle_ref.p0c[0] == pytest.approx(3.0E9), (
        "Reference particle p0c should match SAD MOMENTUM = 3.0 GEV = 3.0E9 eV. "
        f"Got: {line.particle_ref.p0c[0]}.")
    assert line.particle_ref.mass0 == pytest.approx(938.272E6), (
        "Reference particle mass0 should match SAD MASS = 938.272 MEV = 938.272E6 eV. "
        f"Got: {line.particle_ref.mass0}.")
    assert line.particle_ref.q0 == pytest.approx(1.0), (
        "Reference particle q0 should match SAD CHARGE = 1.0. "
        f"Got: {line.particle_ref.q0}.")


################################################################################
# Momentum Unit Propagation
################################################################################
@pytest.mark.parametrize(
    "unit, momentum_value, expected_p0c",
    [
        ("MEV", "100.0 MEV", 100.0E6),
        ("GEV", "1.0 GEV",   1.0E9),
    ])
def test_pipeline_reference_particle_p0c_respects_momentum_unit(
        write_lattice,
        unit,
        momentum_value,
        expected_p0c):
    """
    The SAD MOMENTUM unit should be converted correctly to p0c in eV on the
    reference particle.
    """
    lattice_path = write_lattice(
        f"""\
        MOMENTUM    = {momentum_value};

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = f"ref_particle_momentum_unit_{unit.lower()}.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.particle_ref.p0c[0] == pytest.approx(expected_p0c), (
        f"Reference particle p0c should be {expected_p0c} eV for SAD MOMENTUM "
        f"= {momentum_value}. Got: {line.particle_ref.p0c[0]}.")


################################################################################
# Config Overrides
################################################################################
def test_pipeline_reference_particle_config_p0c_overrides_sad_momentum(write_lattice):
    """
    A Config ref_particle_p0c override should take precedence over the SAD
    MOMENTUM global.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "ref_particle_config_p0c_override.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True,
        ref_particle_p0c = 2.0E9)

    assert line.particle_ref.p0c[0] == pytest.approx(2.0E9), (
        "Reference particle p0c should reflect the Config override of 2.0E9 eV, "
        "not the SAD MOMENTUM of 1.0 GEV = 1.0E9 eV. "
        f"Got: {line.particle_ref.p0c[0]}.")


def test_pipeline_reference_particle_config_mass0_overrides_sad_mass(write_lattice):
    """
    A Config ref_particle_mass0 override should take precedence over the SAD
    MASS global.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        MASS        = 938.272 MEV;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "ref_particle_config_mass0_override.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path   = str(lattice_path),
        output_directory   = "N/A",
        _verbose           = False,
        _test_mode         = True,
        ref_particle_mass0 = xt.ELECTRON_MASS_EV)

    assert line.particle_ref.mass0 == pytest.approx(xt.ELECTRON_MASS_EV), (
        "Reference particle mass0 should reflect the Config override of the "
        f"electron mass ({xt.ELECTRON_MASS_EV} eV), not the SAD MASS of "
        f"938.272 MEV. Got: {line.particle_ref.mass0}.")


def test_pipeline_reference_particle_config_q0_overrides_sad_charge(write_lattice):
    """
    A Config ref_particle_q0 override should take precedence over the SAD
    CHARGE global.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        CHARGE      = 1.0;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "ref_particle_config_q0_override.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True,
        ref_particle_q0  = -1.0)

    assert line.particle_ref.q0 == pytest.approx(-1.0), (
        "Reference particle q0 should reflect the Config override of -1.0, "
        "not the SAD CHARGE of +1.0. "
        f"Got: {line.particle_ref.q0}.")
