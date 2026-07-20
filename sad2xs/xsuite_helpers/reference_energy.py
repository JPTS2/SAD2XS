"""
================================================================================
Xsuite Helpers: Reference Energy
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-20
================================================================================
"""

################################################################################
# Required Packages
################################################################################
import re
from collections import Counter
from collections.abc import Sequence
from typing import Any

import xtrack as xt

import numpy as np

################################################################################
# Float from Xtrack
################################################################################
def _as_float(value: Any) -> float:
    """
    Return a Python float from a scalar on any Xobjects context.

    Parameters
    ----------
    value : Any
        A scalar value, possibly an Xobjects-context array element
        (anything with a `.get()` method) or a 0-d/1-element numpy
        array.

    Returns
    -------
    float
        `value` as a plain Python float.
    """
    if hasattr(value, "get"):
        value = value.get()
    return float(np.asarray(value))

################################################################################
# Find logical cavities and their placement anchors
################################################################################
def _find_cavity_anchors(
        line:           xt.Line,
        table_names:    list[str],
        element_types:  Sequence) -> dict[str, str]:
    """
    Return {cavity_name: anchor_name}, in lattice order, for every logical
    cavity found in a line's table rows (excluding the final "" row).

    Raises ValueError if no cavity is found, or if any cavity is a
    repeated placement of a shared element definition -- see
    `install_reference_energy_updates`'s docstring for what that means
    and why both possible orderings of resolving it are detected here.
    Three complementary signals catch it: an unsliced Cavity row's own
    table name carries the repeat directly ("cav::N"); a sliced
    cavity's entry/exit markers repeat in `line.element_names` (the
    slices themselves don't, so they can't be used); and, if repeats
    were resolved only after slicing, two distinct exit markers still
    collapse to the same base name once each one's own per-placement
    suffix is stripped.

    Parameters
    ----------
    line : xt.Line
        The line the table was built from.
    table_names : list of str
        Element names from `line.get_table()`, excluding the final
        synthetic row.
    element_types : sequence
        The corresponding `element_type` values from the same table.

    Returns
    -------
    dict
        `{cavity_name: anchor_name}`, in lattice order.

    Raises
    ------
    ValueError
        If no cavity is found, or if any cavity is a repeated
        placement of a shared element definition.
    """
    slice_types         = {
        "ThinSliceCavity",
        "ThickSliceCavity",
        "DriftSliceCavity"}
    element_name_counts = Counter(line.element_names)

    # Catches repeats resolved only after slicing (too late) -- see the
    # ordering note in install_reference_energy_updates's docstring.
    exit_marker_bases = Counter()
    for name, element_type in zip(table_names, element_types):
        if str(element_type) != "Marker":
            continue
        stripped = re.sub(r"(\.\d+|::\d+)$", "", name)
        if stripped.endswith("_exit"):
            exit_marker_bases[stripped.removesuffix("_exit")] += 1

    # anchors keeps one entry per parent cavity; dict order = lattice order.
    anchors = {}

    for name, element_type in zip(table_names, element_types):
        element_type = str(element_type)

        if element_type == "Cavity":
            cavity_name = name
        elif element_type in slice_types:
            cavity_name = name.removeprefix("drift_").split("..")[0]
        else:
            continue

        # Otherwise fails deep inside line.insert with an opaque error --
        # see this function's docstring for what each signal below detects.
        is_repeated = (
            "::" in cavity_name
            or element_name_counts[cavity_name] > 1
            or element_name_counts[f"{cavity_name}_entry"] > 1
            or element_name_counts[f"{cavity_name}_exit"] > 1
            or exit_marker_bases[cavity_name] > 1)
        if is_repeated:
            raise ValueError(
                f"Cavity {cavity_name!r} is a repeated placement of a "
                "shared element definition. Call "
                "line.replace_all_repeated_elements() to give every "
                "placement its own element before installing reference "
                "energy updates.")

        anchors[cavity_name] = name

    if not anchors:
        raise ValueError("No cavities found in the line.")
    return anchors

################################################################################
# Install reference energy updates at cavities
################################################################################
def install_reference_energy_updates(line: xt.Line, *, s_tol: float = 1E-6) -> xt.Table:
    """
    Insert one ReferenceEnergyIncrease and TimeDelay per logical cavity.

    Xsuite does not automatically carry the reference momentum along an
    accelerating line: a line whose cavities impart a real energy gain
    still reports the same p0c everywhere unless the reference is updated
    explicitly. This installs, immediately after every logical cavity, a
    zero-valued ReferenceEnergyIncrease and TimeDelay pair for
    update_reference_energy_updates to configure.

    A logical cavity is any element the line's table reports as one of
    "Cavity", "ThinSliceCavity", "ThickSliceCavity", or "DriftSliceCavity"
    (the element types produced by tracking or slicing an xt.Cavity,
    confirmed empirically against real Xsuite output). A thick cavity that
    has been sliced contributes several table rows for one logical cavity;
    these are collapsed into a single update pair anchored at the cavity's
    exit.

    Every cavity must be its own independent element -- call
    `line.replace_all_repeated_elements()` *before* slicing any thick
    cavities, if any cavity is placed more than once from one shared
    definition. Resolving repeats after slicing does not work: slicing
    gives each slice a uniquely-numbered name that is not grouped by
    placement, so the repeat is no longer visible in the slice names
    themselves. Both orderings are detected and raise a clear error rather
    than either failing inside `line.insert` or silently collapsing two
    cavities into one.

    Parameters
    ----------
    line : xt.Line
        The line to install updates into. Modified in place.
    s_tol : float, optional
        Tolerance passed to `line.insert` for the new elements.

    Returns
    -------
    xt.Table
        One row per logical cavity: name, s, and the names of the
        installed energy_update/zeta_update elements.

    Raises
    ------
    ValueError
        If no cavities are found, a cavity is a repeated placement of
        a shared element definition, or an element name collision is
        found.
    NotImplementedError
        If a cavity uses absolute RF timing (`absolute_time=True`).
    """

    ########################################
    # Find logical cavities
    ########################################
    table          = line.get_table()
    table_names    = [str(nn) for nn in table.name[:-1]]
    table_name_set = set(table_names)
    anchors        = _find_cavity_anchors(
        line, table_names, table.element_type[:-1])
    cavities       = list(anchors.keys())

    ########################################
    # Select insertion anchors
    ########################################
    for cavity_name in cavities:
        # Prefer the exit marker; fall back to the last slice found above.
        exit_marker = f"{cavity_name}_exit"
        if exit_marker in table_name_set:
            anchors[cavity_name] = exit_marker

    ########################################
    # Validate cavity RF timing mode
    ########################################
    for cavity_name in cavities:
        cavity = line.env.elements.get(cavity_name)
        if cavity is None:
            raise ValueError(
                f"Could not find cavity element {cavity_name!r} in the "
                "line's environment -- this is an internal error in "
                "install_reference_energy_updates, please report it.")
        if bool(cavity.absolute_time):
            raise NotImplementedError(
                "Reference updates currently require absolute_time=False; "
                f"{cavity_name!r} uses absolute RF timing.")

    ########################################
    # Create and place update elements
    ########################################
    insertions              = []
    existing_element_names  = set(line.element_names)

    for cavity_name in cavities:
        energy_name = f"{cavity_name}_ref_energy_update"
        zeta_name   = f"{cavity_name}_ref_zeta_update"

        energy  = line.env.elements.get(energy_name)
        zeta    = line.env.elements.get(zeta_name)

        # Deterministic names make this idempotent; wrong type still errors.
        if energy is not None and not isinstance(
                energy, xt.ReferenceEnergyIncrease):
            raise ValueError(f"Element name already in use: {energy_name!r}")
        if zeta is not None and not isinstance(zeta, xt.TimeDelay):
            raise ValueError(f"Element name already in use: {zeta_name!r}")

        if energy is None:
            line.env.new(
                energy_name,
                xt.ReferenceEnergyIncrease,
                Delta_p0c = 0)
        if zeta is None:
            line.env.new(
                zeta_name,
                xt.TimeDelay,
                shift_zeta = 0)

        if energy_name not in existing_element_names:
            insertions.append(line.env.place(
                energy_name,
                at          = 0,
                from_       = anchors[cavity_name],
                from_anchor = "end"))
        if zeta_name not in existing_element_names:
            insertions.append(line.env.place(
                zeta_name,
                at          = 0,
                from_       = energy_name,
                from_anchor = "end"))

    if insertions:
        line.insert(insertions, s_tol = s_tol)

    ########################################
    # Report installed elements
    ########################################
    table        = line.get_table()
    energy_names = [f"{cc}_ref_energy_update" for cc in cavities]

    return xt.Table({
        "name":             np.array(cavities),
        "s":                np.array([
            _as_float(table["s", nn]) for nn in energy_names]),
        "energy_update":    np.array(energy_names),
        "zeta_update":      np.array([
            f"{cc}_ref_zeta_update" for cc in cavities])})

################################################################################
# Update reference energy updates at cavities
################################################################################
def update_reference_energy_updates(
        line:       xt.Line,
        *,
        particle:   xt.Particles | None = None,
        verify:     bool                = True,
        atol:       float               = 1E-13) -> xt.Table:
    """
    Track the reference particle and recompute the installed updates.

    For each installed cavity, in lattice order: track a pilot copy of the
    reference particle up to the cavity, set the ReferenceEnergyIncrease so
    the pilot's delta becomes zero, then set the TimeDelay so its zeta
    becomes zero. Call again after any change to cavity voltage, phase, or
    frequency, or to line length/order upstream of an installed cavity.

    Parameters
    ----------
    line : xt.Line
        A line that has already had install_reference_energy_updates run
        on it. Modified in place.
    particle : xt.Particles or None, optional
        Reference particle to track. Defaults to `line.particle_ref`.
    verify : bool, optional
        If True, check delta=zeta=0 at the entrance and after every cavity,
        raising if either check fails.
    atol : float, optional
        Absolute tolerance used by the verify checks.

    Returns
    -------
    xt.Table
        One row per logical cavity: name, s, the configured Delta_p0c and
        zeta_shift, and the pilot's delta/zeta/p0c immediately before and
        after each cavity.

    Raises
    ------
    ValueError
        If no installed reference updates are found, an
        energy/zeta-update pair is missing its partner or misordered,
        or (when `verify` is True) the entrance particle does not have
        delta=zeta=0.
    RuntimeError
        If, after configuring a cavity's updates, the pilot's
        delta/zeta is not zero within `atol` (only checked when
        `verify` is True).
    """

    ########################################
    # Find and clear installed updates
    ########################################
    energy_names = [
        nn for nn in line.element_names
        if nn.endswith("_ref_energy_update")]

    if not energy_names:
        raise ValueError(
            "No reference updates found; call "
            "install_reference_energy_updates first.")

    for energy_name in energy_names:
        cavity_name = energy_name.removesuffix("_ref_energy_update")
        zeta_name   = f"{cavity_name}_ref_zeta_update"

        if zeta_name not in line.element_names:
            raise ValueError(f"Missing paired element {zeta_name!r}.")

        # Must clear old values first, or a stale one skews later cavities.
        line[energy_name].Delta_p0c  = 0
        line[zeta_name].shift_zeta   = 0

    ########################################
    # Prepare pilot particle
    ########################################
    if line.tracker is None:
        line.build_tracker()

    if particle is None:
        particle = line.particle_ref
    if particle is None:
        raise ValueError("The line needs a reference particle.")

    pilot = particle.copy(_context = line._context)

    if verify and (
            abs(_as_float(pilot.delta[0])) > atol
            or abs(_as_float(pilot.zeta[0])) > atol):
        raise ValueError(
            "The entrance particle must have delta=zeta=0 when verify=True.")

    ########################################
    # Configure updates in lattice order
    ########################################
    rows          = []
    ele_start     = 0
    table         = line.get_table()

    # Safe even with unrelated repeated elements: energy/zeta names are unique.
    element_index = {name: i for i, name in enumerate(line.element_names)}

    for energy_name in energy_names:
        cavity_name  = energy_name.removesuffix("_ref_energy_update")
        zeta_name    = f"{cavity_name}_ref_zeta_update"
        energy_idx   = element_index[energy_name]
        zeta_idx     = element_index[zeta_name]

        if zeta_idx != energy_idx + 1:
            raise ValueError(
                f"{zeta_name!r} must immediately follow {energy_name!r}.")

        # Pilot now reflects the cavity's and all prior elements' effect.
        line.track(
            pilot,
            ele_start   = ele_start,
            ele_stop    = energy_idx)

        p0c_before   = _as_float(pilot.p0c[0])
        delta_before = _as_float(pilot.delta[0])
        zeta_before  = _as_float(pilot.zeta[0])

        # Preserves physical momentum, so this zeroes the pilot's delta.
        line[energy_name].Delta_p0c = p0c_before * delta_before
        line.track(
            pilot,
            ele_start   = energy_idx,
            ele_stop    = energy_idx + 1)

        # Rebases downstream zeta to the newly established reference.
        line[zeta_name].shift_zeta = _as_float(pilot.zeta[0])
        line.track(
            pilot,
            ele_start   = zeta_idx,
            ele_stop    = zeta_idx + 1)

        delta_after = _as_float(pilot.delta[0])
        zeta_after  = _as_float(pilot.zeta[0])

        if verify and (
                abs(delta_after) > atol or abs(zeta_after) > atol):
            raise RuntimeError(
                f"Reference reset failed after {cavity_name!r}: "
                f"delta={delta_after:.3e}, zeta={zeta_after:.3e} m.")

        rows.append({
            "name":          cavity_name,
            "s":             _as_float(table["s", energy_name]),
            "Delta_p0c":     _as_float(line[energy_name].Delta_p0c),
            "zeta_shift":    _as_float(line[zeta_name].shift_zeta),
            "p0c_before":    p0c_before,
            "delta_before":  delta_before,
            "zeta_before":   zeta_before,
            "p0c_after":     _as_float(pilot.p0c[0]),
            "delta_after":   delta_after,
            "zeta_after":    zeta_after})

        ele_start = zeta_idx + 1

    ########################################
    # Report configured values
    ########################################
    return xt.Table({
        key: np.array([row[key] for row in rows])
        for key in rows[0]})
