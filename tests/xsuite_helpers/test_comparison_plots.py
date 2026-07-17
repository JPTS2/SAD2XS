"""
================================================================================
Tests for sad2xs.xsuite_helpers.comparison_plots
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-17
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import matplotlib
matplotlib.use("Agg")

import numpy as np
import xtrack as xt

from sad2xs.xsuite_helpers import plot_xsuite_sad_comparison
from sad2xs.xsuite_helpers.comparison_plots import AVAILABLE_GROUPS

################################################################################
# Helpers
################################################################################
# Every column any AVAILABLE_GROUPS quantity needs, on the SAD side.
_QUANTITY_COLUMNS   = [
    "x", "y", "px", "py", "zeta", "delta",
    "betx", "bety", "alfx", "alfy", "dx", "dy", "dpx", "dpy"]

def _aligned_pair():
    """
    A small real xt.Line's own twiss table (needed for `add_strengths()`'s
    `line._action` lookup, which the lattice ribbon relies on) as the
    Xsuite side, paired with a synthetic SAD-side table over the same
    name/s grid.
    """
    env = xt.Environment()
    env.particle_ref   = xt.Particles(p0c = 1.0E9)
    line    = env.new_line(components = [
        env.new("q1", xt.Quadrupole, k1 = 0.3, length = 0.5, at = 1.0),
        env.new("b1", xt.Bend, angle = 0.05, length = 1.0, at = 3.0)])
    line.build_tracker()
    xsuite  = line.twiss4d(betx = 5.0, bety = 5.0)

    values  = {col: np.full(len(xsuite), 1.2) for col in _QUANTITY_COLUMNS}
    sad     = xt.Table({
        "name": np.array(xsuite.name),
        "s":    np.array(xsuite.s),
        **values})
    return xsuite, sad

################################################################################
# plot_xsuite_sad_comparison
################################################################################
def test_returns_one_figure_per_requested_group():
    xsuite, sad = _aligned_pair()

    figures = plot_xsuite_sad_comparison(xsuite, sad, groups = ["beta"])

    assert set(figures) == {"beta"}
    fig, axs    = figures["beta"]
    assert fig is not None
    assert len(axs) == 4  # 2 quantities x (overlay + diff)

def test_omitting_groups_defaults_to_all_available():
    xsuite, sad = _aligned_pair()

    figures = plot_xsuite_sad_comparison(xsuite, sad, include_diff = False)

    assert set(figures) == set(AVAILABLE_GROUPS)
    fig, axs    = figures["beta"]
    assert len(axs) == 2  # 2 quantities, no diff row

def test_show_lattice_true_includes_ribbon_legend_entries():
    xsuite, sad = _aligned_pair()

    fig, axs    = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"])["beta"]
    labels      = [t.get_text() for t in axs[0].get_legend().get_texts()]

    assert "SAD" in labels and "Xsuite" in labels
    assert len(labels) > 2  # at least one element-type entry alongside SAD/Xsuite

def test_show_lattice_false_does_not_raise():
    xsuite, sad = _aligned_pair()

    figures = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"], show_lattice = False)

    assert "beta" in figures

def test_ele_start_ele_stop_narrows_plotted_rows():
    xsuite, sad = _aligned_pair()

    fig, axs    = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"])["beta"]
    full_n      = len(axs[0].lines[0].get_xdata())

    ele_start, ele_stop = sad.name[1], sad.name[-1]
    fig, axs    = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"],
        ele_start = ele_start, ele_stop = ele_stop)["beta"]
    narrowed_n  = len(axs[0].lines[0].get_xdata())

    assert narrowed_n < full_n
