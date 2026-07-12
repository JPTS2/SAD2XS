"""
================================================================================
Tests for sad2xs.xsuite_helpers.reference_energy
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-12
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import numpy as np
import pytest
import xtrack as xt

from sad2xs.xsuite_helpers import (
    install_reference_energy_updates,
    update_reference_energy_updates)

################################################################################
# Test Parameters
################################################################################
MASS_MEV     = 0.51099895000
MOMENTUM_GEV = 1.0

################################################################################
# Helpers
################################################################################
def _build_line(n_cavities = 2, voltage = 1.0E6, phase = np.pi / 2):
    """
    Build a line of alternating Drift/Cavity elements, all cavities sharing
    the given voltage/phase (a real, nonzero energy gain by default).
    """
    env = xt.Environment()
    env.particle_ref = xt.Particles(
        mass0 = MASS_MEV * 1.0E6,
        q0    = 1,
        p0c   = MOMENTUM_GEV * 1.0E9)

    components = []
    for i in range(n_cavities):
        env.new(f"d{i}", xt.Drift, length = 1.0)
        env.new(
            f"cav{i}", xt.Cavity,
            voltage = voltage, frequency = 4.0E8, length = 0.0,
            phase   = phase)
        components += [f"d{i}", f"cav{i}"]
    env.new("d_end", xt.Drift, length = 1.0)
    components.append("d_end")

    line = env.new_line(name = "test", components = components)
    line.particle_ref = env.particle_ref.copy()
    return line

################################################################################
# install_reference_energy_updates
################################################################################
def test_install_creates_one_update_pair_per_cavity():
    """
    One ReferenceEnergyIncrease/TimeDelay pair should be installed per
    logical cavity, immediately following it.
    """
    line = _build_line(n_cavities = 2)
    table = install_reference_energy_updates(line)

    assert list(table.name) == ["cav0", "cav1"]
    assert list(table.energy_update) == [
        "cav0_ref_energy_update", "cav1_ref_energy_update"]
    assert list(table.zeta_update) == [
        "cav0_ref_zeta_update", "cav1_ref_zeta_update"]

    for cavity_name in table.name:
        energy_name = f"{cavity_name}_ref_energy_update"
        zeta_name   = f"{cavity_name}_ref_zeta_update"
        assert isinstance(line[energy_name], xt.ReferenceEnergyIncrease)
        assert isinstance(line[zeta_name], xt.TimeDelay)

        energy_idx = line.element_names.index(energy_name)
        zeta_idx   = line.element_names.index(zeta_name)
        cavity_idx = line.element_names.index(cavity_name)
        assert energy_idx == cavity_idx + 1, (
            "The energy update should immediately follow its cavity.")
        assert zeta_idx == energy_idx + 1, (
            "The zeta update should immediately follow the energy update.")

def test_install_is_idempotent():
    """
    Calling install_reference_energy_updates twice should not duplicate
    the installed elements.
    """
    line = _build_line(n_cavities = 1)
    install_reference_energy_updates(line)
    n_elements_after_first = len(line.element_names)

    install_reference_energy_updates(line)
    assert len(line.element_names) == n_elements_after_first, (
        "A second install call should not add any further elements.")

def test_install_raises_without_any_cavities():
    """
    A line with no cavity elements at all should raise a clear error.
    """
    env = xt.Environment()
    env.particle_ref = xt.Particles(
        mass0 = MASS_MEV * 1.0E6, q0 = 1, p0c = MOMENTUM_GEV * 1.0E9)
    env.new("d0", xt.Drift, length = 1.0)
    line = env.new_line(name = "test", components = ["d0"])
    line.particle_ref = env.particle_ref.copy()

    with pytest.raises(ValueError, match = "No cavities found"):
        install_reference_energy_updates(line)

def test_install_raises_for_repeated_element_placements():
    """
    A cavity placed more than once from one shared element definition is
    reported with a `::N` suffix by the line's table, which cannot be used
    as a placement anchor -- install_reference_energy_updates should raise
    a clear, actionable error rather than fail deep inside line.insert.
    """
    env = xt.Environment()
    env.particle_ref = xt.Particles(
        mass0 = MASS_MEV * 1.0E6, q0 = 1, p0c = MOMENTUM_GEV * 1.0E9)
    env.new("d0", xt.Drift, length = 1.0)
    env.new("cav", xt.Cavity, voltage = 1.0E6, frequency = 4.0E8, length = 0.0)
    line = env.new_line(
        name = "test", components = ["d0", "cav", "d0", "cav", "d0"])
    line.particle_ref = env.particle_ref.copy()

    with pytest.raises(ValueError, match = "replace_all_repeated_elements"):
        install_reference_energy_updates(line)

    # The documented fix should resolve it.
    line.replace_all_repeated_elements()
    table = install_reference_energy_updates(line)
    assert len(table.name) == 2, (
        "Both cavity placements should be recognised as independent "
        "cavities once repeated elements are resolved.")

def _build_repeated_sliced_cavity_line():
    env = xt.Environment()
    env.particle_ref = xt.Particles(
        mass0 = MASS_MEV * 1.0E6, q0 = 1, p0c = MOMENTUM_GEV * 1.0E9)
    env.new("d0", xt.Drift, length = 1.0)
    env.new(
        "cav", xt.Cavity,
        voltage = 1.0E6, frequency = 4.0E8, length = 1.0, phase = np.pi / 2)
    line = env.new_line(
        name = "test", components = ["d0", "cav", "d0", "cav", "d0"])
    line.particle_ref = env.particle_ref.copy()
    return line

def test_install_raises_for_repeated_placement_of_sliced_cavity():
    """
    A cavity placed more than once AND sliced (thick, so it produces
    ThinSliceCavity/DriftSliceCavity rows) must still be caught. Slicing
    gives each slice a uniquely-numbered name that is not grouped by
    placement, so the repeat is no longer visible in the slice names
    themselves -- unlike the unsliced case above, this does not raise from
    a `::N` suffix on the cavity's own row. Covers both orderings that
    still leave the repeat unresolved by the time of slicing: no call to
    replace_all_repeated_elements() at all, and calling it only after
    slicing (too late -- the slices were already assigned by then).
    """
    line = _build_repeated_sliced_cavity_line()
    line.slice_thick_elements(
        slicing_strategies = [xt.Strategy(slicing = xt.Uniform(2))])
    with pytest.raises(ValueError, match = "replace_all_repeated_elements"):
        install_reference_energy_updates(line)

    line.replace_all_repeated_elements()
    with pytest.raises(ValueError, match = "replace_all_repeated_elements"):
        install_reference_energy_updates(line)

def test_install_succeeds_when_repeats_resolved_before_slicing():
    """
    Resolving repeats before slicing is the correct order: slicing then
    runs on two already-independent elements, so each placement's slices
    keep that placement's own disambiguated prefix and are correctly
    recognised as two separate logical cavities.
    """
    line = _build_repeated_sliced_cavity_line()
    line.replace_all_repeated_elements()
    line.slice_thick_elements(
        slicing_strategies = [xt.Strategy(slicing = xt.Uniform(2))])

    table = install_reference_energy_updates(line)
    assert len(table.name) == 2, (
        "Both cavity placements should be recognised as independent "
        "cavities when repeats are resolved before slicing.")

def test_install_raises_for_absolute_time_cavity():
    """
    Reference updates currently assume absolute_time=False; a cavity using
    absolute RF timing should raise NotImplementedError rather than
    silently producing an update that ignores it.
    """
    line = _build_line(n_cavities = 1)
    line["cav0"].absolute_time = True

    with pytest.raises(NotImplementedError, match = "absolute_time"):
        install_reference_energy_updates(line)

def test_install_raises_on_name_collision_with_wrong_type():
    """
    A pre-existing element occupying one of the reserved update-element
    names, but of the wrong type, should raise a clear error rather than
    silently being overwritten or silently reused.
    """
    line = _build_line(n_cavities = 1)
    line.env.new("cav0_ref_energy_update", xt.Drift, length = 1.0)

    with pytest.raises(ValueError, match = "already in use"):
        install_reference_energy_updates(line)

def test_install_recognises_sliced_thick_cavity_as_one_logical_cavity():
    """
    A thick cavity sliced into ThinSliceCavity/DriftSliceCavity elements
    should still be treated as one logical cavity, anchored at its exit
    marker, not once per slice.
    """
    env = xt.Environment()
    env.particle_ref = xt.Particles(
        mass0 = MASS_MEV * 1.0E6, q0 = 1, p0c = MOMENTUM_GEV * 1.0E9)
    env.new(
        "cav", xt.Cavity,
        voltage = 1.0E6, frequency = 4.0E8, length = 1.0, phase = np.pi / 2)
    line = env.new_line(name = "test", components = ["cav"])
    line.particle_ref = env.particle_ref.copy()
    line.slice_thick_elements(
        slicing_strategies = [xt.Strategy(slicing = xt.Uniform(3))])

    table = install_reference_energy_updates(line)
    assert list(table.name) == ["cav"], (
        "A sliced thick cavity should produce exactly one logical-cavity "
        "entry, not one per slice.")

    energy_idx = line.element_names.index("cav_ref_energy_update")
    exit_idx   = line.element_names.index("cav_exit")
    assert energy_idx == exit_idx + 1, (
        "The update pair should be anchored at the cavity's exit marker.")

################################################################################
# update_reference_energy_updates
################################################################################
def test_update_raises_without_install():
    """
    Calling update_reference_energy_updates before install should raise a
    clear error rather than failing on a missing element lookup.
    """
    line = _build_line(n_cavities = 1)

    with pytest.raises(ValueError, match = "install_reference_energy_updates"):
        update_reference_energy_updates(line)

def test_update_zeros_pilot_delta_and_zeta_after_every_cavity():
    """
    After update_reference_energy_updates, a freshly tracked on-momentum
    particle should have delta=zeta=0 immediately after every cavity, not
    just at the end of the line. Uses a nonzero-length cavity so shift_zeta
    is genuinely nonzero -- with length=0.0 (as in _build_line) it would be
    exactly 0 regardless of whether the TimeDelay is applied at all, which
    would not actually exercise it. `ele_stop` is exclusive in xtrack, so
    the check after cav0 must stop at the element following its zeta
    update, not at the zeta update element itself.
    """
    env = xt.Environment()
    env.particle_ref = xt.Particles(
        mass0 = MASS_MEV * 1.0E6, q0 = 1, p0c = MOMENTUM_GEV * 1.0E9)
    env.new("d0", xt.Drift, length = 1.0)
    env.new(
        "cav0", xt.Cavity,
        voltage = 1.0E6, frequency = 4.0E8, length = 1.0, phase = np.pi / 2)
    env.new("d1", xt.Drift, length = 1.0)
    env.new(
        "cav1", xt.Cavity,
        voltage = 2.0E6, frequency = 4.0E8, length = 1.0, phase = np.pi / 2)
    env.new("d_end", xt.Drift, length = 1.0)
    line = env.new_line(
        name = "test",
        components = ["d0", "cav0", "d1", "cav1", "d_end"])
    line.particle_ref = env.particle_ref.copy()

    install_reference_energy_updates(line)
    update_reference_energy_updates(line)
    assert line["cav0_ref_zeta_update"].shift_zeta != pytest.approx(0.0), (
        "This test needs a genuinely nonzero shift_zeta to exercise the "
        "TimeDelay element at all.")

    particle = line.build_particles(x = [0.0])
    line.track(particle, ele_stop = "d1")
    assert particle.delta[0] == pytest.approx(0.0, abs = 1E-12)
    assert particle.zeta[0]  == pytest.approx(0.0, abs = 1E-12)

    line.track(particle)
    assert particle.delta[0] == pytest.approx(0.0, abs = 1E-10)
    assert particle.zeta[0]  == pytest.approx(0.0, abs = 1E-10)

def test_update_reports_physical_delta_p0c_matching_energy_gain():
    """
    The configured Delta_p0c for each cavity should match the actual
    momentum gained from that cavity's voltage/phase, not merely be
    nonzero.
    """
    line = _build_line(n_cavities = 1, voltage = 1.0E6, phase = np.pi / 2)
    install_reference_energy_updates(line)
    table = update_reference_energy_updates(line)

    particle = line.build_particles(x = [0.0])
    line.track(particle, ele_stop = "cav0")
    p0c_before = float(particle.p0c[0])
    line.track(particle, ele_start = "cav0", ele_stop = "cav0_ref_energy_update")
    delta_p0c_expected = float(particle.p0c[0]) * float(particle.delta[0])

    assert table.Delta_p0c[0] == pytest.approx(delta_p0c_expected, rel = 1E-9)
    assert table.Delta_p0c[0] != pytest.approx(0.0), (
        "A cavity with a genuine energy gain should produce a nonzero "
        "Delta_p0c, not silently no-op.")

def test_update_raises_if_entrance_particle_not_on_reference():
    """
    verify=True should reject an entrance particle that isn't already at
    delta=zeta=0, since the whole scheme assumes the line starts on the
    reference trajectory.
    """
    line = _build_line(n_cavities = 1)
    install_reference_energy_updates(line)

    off_reference = line.particle_ref.copy()
    off_reference.delta = 0.01

    with pytest.raises(ValueError, match = "delta=zeta=0"):
        update_reference_energy_updates(line, particle = off_reference)

def test_update_can_be_recalled_after_voltage_change():
    """
    Calling update_reference_energy_updates again after a cavity's voltage
    changes should reconfigure the installed elements to the new values,
    not retain the stale ones from the previous call.
    """
    line = _build_line(n_cavities = 1, voltage = 1.0E6, phase = np.pi / 2)
    install_reference_energy_updates(line)
    table_before = update_reference_energy_updates(line)

    line["cav0"].voltage = 2.0E6
    table_after = update_reference_energy_updates(line)

    assert table_after.Delta_p0c[0] != pytest.approx(table_before.Delta_p0c[0]), (
        "Re-running update after a voltage change should recompute "
        "Delta_p0c, not keep the value from before the change.")
