"""
================================================================================
Tests for sad2xs.xsuite_helpers.comparison_plots
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-22
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

def _all_ribbon_types_pair():
    """
    Like `_aligned_pair`, but with one of every lattice-ribbon element
    type (bend, quad, sextupole, h/v kick) so the legend has its full
    7 entries (5 element types + SAD + Xsuite), needed to tell "one row"
    apart from "wrapped" -- `_aligned_pair`'s quad+bend line only ever
    has 4 entries, where a wrap (min(4, 4)) looks identical to one row.
    """
    env = xt.Environment()
    env.particle_ref   = xt.Particles(p0c = 1.0E9)
    line    = env.new_line(components = [
        env.new("q1", xt.Quadrupole, k1 = 0.3, length = 0.5, at = 1.0),
        env.new("b1", xt.Bend, angle = 0.05, length = 1.0, at = 3.0),
        env.new("s1", xt.Sextupole, k2 = 0.5, length = 0.2, at = 5.0),
        env.new(
            "m1", xt.Multipole,
            knl = [1E-4, 0, 0], ksl = [1E-4, 0, 0], at = 6.0)])
    line.build_tracker()
    xsuite  = line.twiss4d(betx = 5.0, bety = 5.0)

    sad     = xt.Table({
        "name": np.array(xsuite.name),
        "s":    np.array(xsuite.s),
        "betx": np.array(xsuite.betx) * 1.01,
        "bety": np.array(xsuite.bety) * 1.01})
    return xsuite, sad

################################################################################
# plot_xsuite_sad_comparison
################################################################################
def test_returns_one_figure_per_requested_group():
    """
    Requesting a single group should return exactly one figure, keyed by
    that group name, with one overlay+diff axis pair per quantity in the
    group.
    """
    xsuite, sad = _aligned_pair()

    figures = plot_xsuite_sad_comparison(xsuite, sad, groups = ["beta"])

    assert set(figures) == {"beta"}
    fig, axs    = figures["beta"]
    assert fig is not None
    assert len(axs) == 4  # 2 quantities x (overlay + diff)

def test_omitting_groups_defaults_to_all_available():
    """
    Omitting `groups` should plot every group in AVAILABLE_GROUPS;
    `include_diff=False` should drop the difference row, leaving only
    the overlay axis per quantity.
    """
    xsuite, sad = _aligned_pair()

    figures = plot_xsuite_sad_comparison(xsuite, sad, include_diff = False)

    assert set(figures) == set(AVAILABLE_GROUPS)
    fig, axs    = figures["beta"]
    assert len(axs) == 2  # 2 quantities, no diff row

def test_show_lattice_true_includes_ribbon_legend_entries():
    """
    With the default show_lattice=True, the overlay legend should include
    `SAD`/`Xsuite` plus at least one lattice-ribbon element-type entry.
    """
    xsuite, sad = _aligned_pair()

    fig, axs    = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"])["beta"]
    labels      = [t.get_text() for t in axs[0].get_legend().get_texts()]

    assert "SAD" in labels and "Xsuite" in labels
    assert len(labels) > 2  # at least one element-type entry alongside SAD/Xsuite

def test_group_title_is_a_plain_suptitle_not_boxed_in_the_legend():
    """
    Regression test: a separate fig.suptitle() plus a normal (non-"outside")
    axes-anchored legend is what constrained layout reserves space for
    correctly. Folding the title into the legend's own `title=` instead
    would put a visible border around it, which reads oddly for a plot
    title -- the two must stay separate: a plain suptitle above an
    unboxed-title legend.
    """
    xsuite, sad = _aligned_pair()

    fig, axs    = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"], title_prefix = "Check")["beta"]

    assert fig._suptitle is not None
    assert fig._suptitle.get_text() == "Check: Beta Functions"
    legend  = axs[0].get_legend()
    assert legend.get_title().get_text() == ""

def test_legend_stays_one_row_when_it_fits():
    """
    At the default figsize, a legend with all 7 possible entries (5
    lattice element types + SAD + Xsuite) should fit on one row -- the
    "one line if we have the space" case.
    """
    xsuite, sad = _all_ribbon_types_pair()

    fig, axs    = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"])["beta"]
    legend      = axs[0].get_legend()

    assert legend._ncols == len(legend.get_texts()) == 7

def test_legend_wraps_when_it_does_not_fit():
    """
    At a figsize too narrow for all 7 entries on one row, the legend must
    fall back to the wrapped, multi-row layout instead of overflowing (or
    being clipped) past the edge of the figure.
    """
    xsuite, sad = _all_ribbon_types_pair()

    fig, axs    = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"], figsize = (5, 4))["beta"]
    legend      = axs[0].get_legend()

    assert legend._ncols < len(legend.get_texts()) == 7

def test_show_lattice_false_does_not_raise():
    """
    show_lattice=False should skip the lattice ribbon without raising,
    still returning the requested group's figure.
    """
    xsuite, sad = _aligned_pair()

    figures = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"], show_lattice = False)

    assert "beta" in figures

def test_ele_start_ele_stop_narrows_plotted_rows():
    """
    Passing ele_start/ele_stop should narrow the plotted row range
    compared to the unwindowed default.
    """
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

def test_default_figsize_is_larger_than_matplotlib_default():
    """
    The default figsize should be large enough that a group with the
    lattice ribbon, legend and two quantity rows is actually readable.
    """
    xsuite, sad = _aligned_pair()

    fig, _  = plot_xsuite_sad_comparison(xsuite, sad, groups = ["beta"])["beta"]

    assert tuple(fig.get_size_inches()) == (10.0, 8.0)

def test_second_group_axis_autoscales_to_real_data_not_ribbon_scale():
    """
    Regression test: `_draw_lattice_ribbon` caches the lattice bars after
    the first quantity row it ever draws, and every later row (any
    quantity in any group after the first) reuses that cache. That reused
    branch must still return the real, autoscaling data axis -- not the
    hidden ribbon axis fixed at ylim=(-1.5, 1.5) -- or the SAD/Xsuite
    curves get drawn on the wrong axis and the visible one is left at
    matplotlib's untouched default ylim=(0, 1), with no visible ylabel
    (the ribbon axis's own axis is turned off).

    `betx` on this fixture's line runs roughly 3.9-5.1 -- well outside
    both matplotlib's default (0, 1) and the ribbon's fixed (-1.5, 1.5).
    """
    xsuite, sad = _aligned_pair()

    # "orbit_xy" is drawn first (AVAILABLE_GROUPS order) and is the one
    # that seeds the lattice cache; "beta" is drawn from the reused branch.
    fig, axs    = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["orbit_xy", "beta"])["beta"]

    betx_ax     = axs[0]
    xsuite_line = betx_ax.lines[-1]  # Xsuite curve, plotted last
    lo, hi      = betx_ax.get_ylim()

    assert hi > 2.0  # real betx range, not left at the default (0, 1)
    assert lo <= xsuite_line.get_ydata().min()
    assert hi >= xsuite_line.get_ydata().max()
    assert betx_ax.get_ylabel() != ""  # not hidden on an axis("off") twin

def test_diff_axis_offset_text_is_folded_into_ylabel():
    """
    Regression test: matplotlib's own y-axis offset/scientific-notation
    text for a diff row sits flush against the row above it (hspace=0
    overlay/diff pairs), with nothing to stop it overlapping that row's
    own ticks -- it must be hidden and folded into the ylabel instead.
    """
    env = xt.Environment()
    env.particle_ref   = xt.Particles(p0c = 1.0E9)
    line    = env.new_line(components = [
        env.new("q1", xt.Quadrupole, k1 = 0.3, length = 0.5, at = 1.0),
        env.new("b1", xt.Bend, angle = 0.05, length = 1.0, at = 3.0)])
    line.build_tracker()
    xsuite  = line.twiss4d(betx = 5.0, bety = 5.0)

    # A near-perfect match -- tiny, per-element-varying residual -- is the
    # realistic case this fold-in targets. A uniform (element-independent)
    # offset is a separate, rarer case where matplotlib's own offset text
    # is itself an unclear concatenation of scale and baseline; not covered
    # here.
    tiny_residual   = np.linspace(-1E-12, 1E-12, len(xsuite))
    sad     = xt.Table({
        "name": np.array(xsuite.name),
        "s":    np.array(xsuite.s),
        "betx": np.array(xsuite.betx) + tiny_residual,
        "bety": np.array(xsuite.bety) + tiny_residual})

    fig, axs    = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"])["beta"]
    diff_ax     = axs[1]  # betx's diff row
    offset_text = diff_ax.yaxis.get_offset_text()

    assert offset_text.get_text() != ""
    assert offset_text.get_visible() is False
    assert offset_text.get_text() in diff_ax.get_ylabel()

################################################################################
# plot_xsuite_sad_comparison -- aligned=False
################################################################################
def _unaligned_pair():
    """
    An Xsuite twiss table and a SAD-side table over a coarser subset of
    the same name/s grid (as if consecutive drifts had been merged) --
    different lengths, not row-matched.
    """
    xsuite, sad_full    = _aligned_pair()
    keep    = np.arange(0, len(sad_full), 2)
    sad     = sad_full.rows[keep]
    return xsuite, sad

def test_aligned_false_accepts_mismatched_length_tables():
    """
    With aligned=False, the two tables need not be the same length or
    row-matched -- the overlay curves are drawn independently per side.
    """
    xsuite, sad = _unaligned_pair()
    assert len(xsuite) != len(sad)

    figures = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"], aligned = False)

    assert "beta" in figures

def test_aligned_false_forces_include_diff_off():
    """
    A row-by-row difference needs row-matched tables, so aligned=False
    must force include_diff off even if the caller explicitly asked for
    it (the default is include_diff=True).
    """
    xsuite, sad = _unaligned_pair()

    fig, axs    = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"],
        aligned = False, include_diff = True)["beta"]

    assert len(axs) == 2  # 2 quantities, no diff row despite include_diff=True

def test_aligned_false_windows_each_table_independently():
    """
    ele_start/ele_stop under aligned=False must be found in each table's
    own name column separately, since a shared row index wouldn't mean
    the same thing on both sides.
    """
    xsuite, sad = _unaligned_pair()

    ele_start, ele_stop = sad.name[1], sad.name[-1]
    fig, axs    = plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"], aligned = False,
        ele_start = ele_start, ele_stop = ele_stop)["beta"]

    sad_line, xsuite_line   = axs[0].lines[-2], axs[0].lines[-1]
    assert len(sad_line.get_xdata()) == len(sad) - 1  # sad.name[1:] inclusive
    assert len(xsuite_line.get_xdata()) < len(xsuite)

################################################################################
# plot_xsuite_sad_comparison -- save_dir/save_format
################################################################################
def test_save_dir_none_does_not_save(tmp_path):
    """
    Default save_dir=None must not write anything -- saving is opt-in.
    """
    xsuite, sad = _aligned_pair()

    plot_xsuite_sad_comparison(xsuite, sad, groups = ["beta"])

    assert list(tmp_path.iterdir()) == []

def test_save_dir_saves_one_pdf_per_group_by_default(tmp_path):
    """
    save_dir should create the directory if needed and save every
    plotted group as a vector (PDF, by default) file within it, so a
    report figure stays sharp at any zoom.
    """
    xsuite, sad = _aligned_pair()
    save_dir    = tmp_path / "plots"

    plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta", "alpha"], save_dir = str(save_dir))

    saved   = {p.name for p in save_dir.iterdir()}
    assert saved == {"beta.pdf", "alpha.pdf"}

def test_save_format_overrides_the_extension(tmp_path):
    """
    save_format should control the saved file extension/format, e.g. a
    raster PNG instead of the default vector PDF.
    """
    xsuite, sad = _aligned_pair()
    save_dir    = tmp_path / "plots"

    plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"],
        save_dir = str(save_dir), save_format = "png")

    assert {p.name for p in save_dir.iterdir()} == {"beta.png"}

def test_save_dir_filenames_include_sanitized_title_prefix(tmp_path):
    """
    A title_prefix should be folded into each saved filename (lowercased,
    non-alphanumeric runs collapsed to underscores) so files from
    different calls into the same save_dir don't collide.
    """
    xsuite, sad = _aligned_pair()
    save_dir    = tmp_path / "plots"

    plot_xsuite_sad_comparison(
        xsuite, sad, groups = ["beta"],
        save_dir = str(save_dir), title_prefix = "First IP")

    assert {p.name for p in save_dir.iterdir()} == {"first_ip_beta.pdf"}
