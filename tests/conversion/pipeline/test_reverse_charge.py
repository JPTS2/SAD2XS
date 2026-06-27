"""
================================================================================
Tests for the reverse_charge parameter of the SAD2XS conversion pipeline
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
import warnings

import pytest
import sad2xs as s2x
import xtrack as xt

################################################################################
# Helpers
################################################################################
_POSITRON_MARK_LATTICE = """\
MOMENTUM    = 1.0 GEV;

MARK        START   = ()
            END     = ();

LINE        TEST_LINE = (START END);
"""

_PROTON_MASS_LATTICE = """\
MOMENTUM    = 2.0 GEV;
MASS        = 938.272 MEV;

MARK        START   = ()
            END     = ();

LINE        TEST_LINE = (START END);
"""


def _convert(write_lattice, text, filename, **kwargs):
    path = write_lattice(text, filename=filename)
    return s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True,
        **kwargs)


################################################################################
# Default behaviour — no reverse_charge
################################################################################
def test_pipeline_reverse_charge_false_leaves_q0_unchanged(write_lattice):
    """
    Without reverse_charge, the reference particle should be a positron
    (SAD default): q0 = +1.
    """
    line = _convert(write_lattice, _POSITRON_MARK_LATTICE,
                    filename="rc_false.sad")

    assert line.particle_ref.q0 == pytest.approx(1.0), (
        f"Default q0 should be +1.0. Got: {line.particle_ref.q0}.")


################################################################################
# Charge reversal — q0 sign
################################################################################
def test_pipeline_reverse_charge_negates_positive_q0(write_lattice):
    """
    reverse_charge=True on a positron lattice should produce q0 = -1 (electron).
    """
    line = _convert(write_lattice, _POSITRON_MARK_LATTICE,
                    filename="rc_pos.sad", reverse_charge=True)

    assert line.particle_ref.q0 == pytest.approx(-1.0), (
        f"reverse_charge=True should give q0 = -1.0. Got: {line.particle_ref.q0}.")


def test_pipeline_reverse_charge_does_not_affect_p0c_or_mass0(write_lattice):
    """
    reverse_charge=True should only flip the charge sign. p0c and mass0 must
    be unaffected.
    """
    line = _convert(write_lattice, _PROTON_MASS_LATTICE,
                    filename="rc_isolation.sad", reverse_charge=True)

    assert line.particle_ref.q0 == pytest.approx(-1.0), (
        f"reverse_charge=True should give q0 = -1.0. Got: {line.particle_ref.q0}.")
    assert line.particle_ref.p0c[0] == pytest.approx(2.0e9), (
        f"p0c should be unaffected. Got: {line.particle_ref.p0c[0]}.")
    assert line.particle_ref.mass0 == pytest.approx(938.272e6), (
        f"mass0 should be unaffected. Got: {line.particle_ref.mass0}.")


################################################################################
# SAD CHARGE global — warning and ignore
################################################################################
def test_pipeline_charge_warning_emitted_for_non_unity_charge(write_lattice):
    """
    A SAD lattice with CHARGE != 1 should emit a UserWarning explaining that
    SAD ignores this setting. The value must NOT be used as q0.
    """
    lattice = """\
MOMENTUM    = 1.0 GEV;
CHARGE      = -1.0;

MARK        START   = ()
            END     = ();

LINE        TEST_LINE = (START END);
"""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = _convert(write_lattice, lattice, filename="rc_charge_warn.sad")

    assert any(issubclass(w.category, UserWarning) and "CHARGE" in str(w.message)
               for w in caught), (
        "A UserWarning mentioning CHARGE should be emitted when CHARGE != 1 "
        "is found in the SAD file.")

    assert line.particle_ref.q0 == pytest.approx(1.0), (
        "SAD CHARGE global must be ignored — q0 should remain +1.0 (positron). "
        f"Got: {line.particle_ref.q0}.")


################################################################################
# Species-string API — correct species selected from MASS
################################################################################
def test_pipeline_default_species_is_positron(write_lattice):
    """
    With no MASS specified, the reference particle should be a positron:
    q0 = +1, mass0 = electron mass.
    """
    line = _convert(write_lattice, _POSITRON_MARK_LATTICE,
                    filename="rc_species_pos.sad")

    assert line.particle_ref.q0 == pytest.approx(1.0)
    assert line.particle_ref.mass0 == pytest.approx(xt.ELECTRON_MASS_EV, rel=1e-3)


def test_pipeline_proton_mass_gives_proton_species(write_lattice):
    """
    With MASS = proton mass, the reference particle should be a proton:
    q0 = +1, mass0 = proton mass.
    """
    line = _convert(write_lattice, _PROTON_MASS_LATTICE,
                    filename="rc_species_proton.sad")

    assert line.particle_ref.q0 == pytest.approx(1.0)
    assert line.particle_ref.mass0 == pytest.approx(xt.PROTON_MASS_EV, rel=1e-3)


def test_pipeline_reverse_charge_positron_gives_electron(write_lattice):
    """
    reverse_charge=True on a positron lattice should produce an electron:
    q0 = -1, mass0 = electron mass.
    """
    line = _convert(write_lattice, _POSITRON_MARK_LATTICE,
                    filename="rc_to_electron.sad", reverse_charge=True)

    assert line.particle_ref.q0 == pytest.approx(-1.0)
    assert line.particle_ref.mass0 == pytest.approx(xt.ELECTRON_MASS_EV, rel=1e-3)


def test_pipeline_reverse_charge_proton_gives_antiproton(write_lattice):
    """
    reverse_charge=True on a proton-mass lattice should produce an antiproton:
    q0 = -1, mass0 = proton mass.
    """
    line = _convert(write_lattice, _PROTON_MASS_LATTICE,
                    filename="rc_to_antiproton.sad", reverse_charge=True)

    assert line.particle_ref.q0 == pytest.approx(-1.0)
    assert line.particle_ref.mass0 == pytest.approx(xt.PROTON_MASS_EV, rel=1e-3)
