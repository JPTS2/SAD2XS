"""
================================================================================
Xsuite Helpers: Comparison Plots
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
import logging
import re
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import numpy as np
import xtrack as xt

if TYPE_CHECKING:
    import matplotlib.axes
    import matplotlib.figure

logger  = logging.getLogger(__name__)

################################################################################
# Quantity groups -- one figure per group, one row pair per quantity.
# (sad_column, overlay y-label, diff y-label)
################################################################################
_QUANTITY_GROUPS    = {
    "orbit_xy":     ("Orbit (x, y)", [
        ("x",       r"$x$ [m]",             r"$\Delta x$ [m]"),
        ("y",       r"$y$ [m]",             r"$\Delta y$ [m]")]),
    "orbit_pxpy":   ("Orbit (px, py)", [
        ("px",      r"$p_x$ [1]",           r"$\Delta p_x$ [1]"),
        ("py",      r"$p_y$ [1]",           r"$\Delta p_y$ [1]")]),
    "longitudinal": (r"Longitudinal ($\zeta$, $\delta$)", [
        ("zeta",    r"$\zeta$ [m]",         r"$\Delta \zeta$ [m]"),
        ("delta",   r"$\delta$ [1]",        r"$\Delta \delta$ [1]")]),
    "beta":         (r"Beta Functions", [
        ("betx",    r"$\beta_x$ [m]",       r"$\Delta \beta_x / \beta_x$ [%]"),
        ("bety",    r"$\beta_y$ [m]",       r"$\Delta \beta_y / \beta_y$ [%]")]),
    "alpha":        (r"Alpha Functions", [
        ("alfx",    r"$\alpha_x$ [1]",      r"$\Delta \alpha_x$ [1]"),
        ("alfy",    r"$\alpha_y$ [1]",      r"$\Delta \alpha_y$ [1]")]),
    "dispersion":   (r"Dispersion", [
        ("dx",      r"$D_x$ [m]",           r"$\Delta D_x$ [m]"),
        ("dy",      r"$D_y$ [m]",           r"$\Delta D_y$ [m]")]),
    "ddispersion":  (r"Dispersion ($D_{px}$, $D_{py}$)", [
        ("dpx",     r"$D_{px}$ [1]",        r"$\Delta D_{px}$ [1]"),
        ("dpy",     r"$D_{py}$ [1]",        r"$\Delta D_{py}$ [1]")])}

# Quantities where a relative (%) difference is more meaningful than absolute
# -- everything else (alfx, dispersion, ...) can cross zero, where a relative
# difference blows up.
_RELATIVE_DIFF_COLUMNS  = {"betx", "bety"}

AVAILABLE_GROUPS    = tuple(_QUANTITY_GROUPS)

################################################################################
# Small helpers
################################################################################
def _zero_small_values(array: np.ndarray, tol: float) -> np.ndarray:
    """
    Zero values below `tol` so floating-point noise doesn't clutter
    a plot.

    Parameters
    ----------
    array : array_like
        The values to clean.
    tol : float
        Absolute threshold below which a value is set to zero.

    Returns
    -------
    numpy.ndarray
        `array` as a float array, with values where `abs(value) < tol`
        set to zero.
    """
    array   = np.array(array, dtype = float)
    array[np.abs(array) < tol]  = 0
    return array

def _sanitize_filename_stem(text: str) -> str:
    """
    Turn `text` into a safe filename stem: lowercase, with any run of
    non-alphanumeric characters collapsed to a single underscore and no
    leading/trailing underscore.

    Parameters
    ----------
    text : str
        Arbitrary text (e.g. `title_prefix`) to use in a filename.

    Returns
    -------
    str
        `text`, lowercased and sanitized for use as a filename stem.
    """
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

def _difference(xs_values: np.ndarray, sad_values: np.ndarray, sad_column: str) -> np.ndarray:
    """
    Compute (Xsuite - SAD), relative (%) for beta functions, absolute
    otherwise.

    Parameters
    ----------
    xs_values : array_like
        Xsuite values for this quantity.
    sad_values : array_like
        SAD values for this quantity.
    sad_column : str
        The SAD column name, used to decide whether the difference is
        relative (see `_RELATIVE_DIFF_COLUMNS`) or absolute.

    Returns
    -------
    numpy.ndarray
        The difference, as a percentage of `sad_values` (NaN where
        `sad_values` is zero) for beta functions, or the plain
        difference otherwise.
    """
    if sad_column in _RELATIVE_DIFF_COLUMNS:
        with np.errstate(divide = "ignore", invalid = "ignore"):
            return np.where(
                sad_values != 0,
                (xs_values - sad_values) / sad_values * 1E2,
                np.nan)
    return xs_values - sad_values

def _window_one_table(
        table:      xt.Table,
        ele_start:  str | None,
        ele_stop:   str | None) -> tuple[xt.Table, np.ndarray]:
    """
    Find `[ele_start, ele_stop]` in one table's own `name` column and
    return the rows in between (inclusive), plus the row-index array used.

    Parameters
    ----------
    table : xt.Table
        The table to search and window.
    ele_start : str or None
        Name of the first element to keep (inclusive).
    ele_stop : str or None
        Name of the last element to keep (inclusive).

    Returns
    -------
    tuple of (xt.Table, numpy.ndarray)
        The windowed table, and the row-index array applied.
    """
    names   = [str(n).lower() for n in table.name]
    last    = len(names) - 1
    lo  = names.index(ele_start.lower()) if ele_start is not None else 0
    hi  = names.index(ele_stop.lower()) if ele_stop is not None else last
    if hi < lo:
        lo, hi  = hi, lo

    idx = np.arange(lo, hi + 1)
    return table.rows[idx], idx

def _window_by_element(
        xsuite_aligned: xt.Table,
        sad_aligned:    xt.Table,
        ele_start:      str | None,
        ele_stop:       str | None,
        *,
        aligned:        bool = True) -> tuple[xt.Table, xt.Table]:
    """
    Cut both tables to the row range [ele_start, ele_stop].

    Matched by element name, case-insensitive, the same way
    `align_xsuite_twiss_with_sad_twiss` matches names. No-op if
    neither `ele_start` nor `ele_stop` is given.

    Parameters
    ----------
    xsuite_aligned : xt.Table
        Xsuite-side table.
    sad_aligned : xt.Table
        SAD-side table.
    ele_start : str or None
        Name of the first element to keep (inclusive).
    ele_stop : str or None
        Name of the last element to keep (inclusive).
    aligned : bool, optional
        Default `True`: the two tables are same-length and row-matched
        (e.g. from `align_xsuite_twiss_with_sad_twiss`), so the row range
        is found once against `sad_aligned.name` and the same index array
        applied to both. `False`: the tables aren't row-matched (possibly
        different lengths), so each is searched and windowed against its
        own `name` column independently.

    Returns
    -------
    tuple of (xt.Table, xt.Table)
        `(xsuite_aligned, sad_aligned)`, windowed to the requested
        row range.
    """
    if ele_start is None and ele_stop is None:
        return xsuite_aligned, sad_aligned

    if not aligned:
        xsuite_windowed, _  = _window_one_table(
            xsuite_aligned, ele_start, ele_stop)
        sad_windowed, _     = _window_one_table(
            sad_aligned, ele_start, ele_stop)
        return xsuite_windowed, sad_windowed

    sad_windowed, idx   = _window_one_table(sad_aligned, ele_start, ele_stop)
    return xsuite_aligned.rows[idx], sad_windowed

################################################################################
# Lattice ribbon -- Xsuite's own element-type bars (xt.TwissTable.plot),
# computed for real once and copied onto every other axis. It's the same
# lattice for every quantity and every figure in one comparison call, so
# there's no reason to make Xsuite redraw thousands of magnets from scratch
# on each of them.
################################################################################
def _draw_lattice_ribbon(
        overlay_ax:     "matplotlib.axes.Axes",
        xsuite_aligned: xt.Table,
        cache:          dict) -> tuple["matplotlib.axes.Axes", list, list]:
    """
    First call (`cache["bars"] is None`): let `xt.TwissTable.plot
    (lattice_only=True)` do the real work, then read the bars it drew
    straight off the axis and cache that geometry. Every later call
    just copies those bars onto its own axis instead of asking Xsuite
    to recompute and redraw the whole ribbon again.

    Parameters
    ----------
    overlay_ax : matplotlib.axes.Axes
        The axis to draw the ribbon onto (or copy it onto, on
        subsequent calls).
    xsuite_aligned : xt.Table
        The table to draw the ribbon from, on the first call.
    cache : dict
        Shared cache dict with keys "bars" and "legend", populated on
        the first call and reused on every subsequent call.

    Returns
    -------
    tuple of (matplotlib.axes.Axes, list, list)
        `(data_axis, legend_handles, legend_labels)` -- `data_axis` is
        where the SAD/Xsuite comparison curves belong: it always keeps
        its own normal (autoscaling, visible) y-axis, with the lattice
        ribbon drawn behind it on a separate, hidden-axis twin.
    """
    if cache["bars"] is None:
        pl  = xsuite_aligned.plot(lattice_only = True, ax = overlay_ax, x = "s", grid = False)
        cache["bars"]   = [
            (bar.get_x(), bar.get_y(), bar.get_width(), bar.get_height(), bar.get_facecolor())
            for bar in pl.lattice.patches]
        cache["legend"] = (list(pl.lines), list(pl.legends))
        # Decoration-free axis -- exclude it from constrained-layout sizing.
        overlay_ax.set_in_layout(False)
        return (pl.left, *cache["legend"])

    # Every bar can have a different height (magnitude-scaled per magnet),
    # so one PatchCollection of individually-sized rectangles -- a single
    # artist -- replaces what would otherwise be one Rectangle per magnet.
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Rectangle

    ribbon_ax   = overlay_ax.twinx()
    ribbon_ax.set_zorder(0)
    overlay_ax.set_zorder(1)
    overlay_ax.patch.set_visible(False)
    ribbon_ax.set_ylim(-1.5, 1.5)      # Xsuite's own fixed ribbon scale
    ribbon_ax.axis("off")
    # Decoration-free twin -- exclude it from constrained-layout sizing.
    ribbon_ax.set_in_layout(False)

    rectangles  = [Rectangle((x, y), width, height) for x, y, width, height, _ in cache["bars"]]
    colors      = [color for *_, color in cache["bars"]]
    ribbon_ax.add_collection(
        PatchCollection(rectangles, facecolor = colors, edgecolor = colors))

    # Curves go on overlay_ax (visible), not the ribbon axis (hidden).
    return (overlay_ax, *cache["legend"])

################################################################################
# One quantity-group figure
################################################################################
def _plot_group(
        plt:                        ModuleType,
        xsuite_aligned:             xt.Table,
        sad_aligned:                xt.Table,
        title:                      str,
        quantities:                 list[tuple[str, str, str]],
        *,
        figsize:                    tuple[float, float],
        include_diff:               bool,
        xsuite_column_overrides:    dict[str, str],
        zero_tol:                   float,
        title_prefix:               str | None,
        lattice_cache:              dict | None
        ) -> tuple["matplotlib.figure.Figure", list["matplotlib.axes.Axes"]]:
    """
    Draw one quantity-group figure: one overlay (+ optional
    difference) row per quantity in `quantities`.

    Parameters
    ----------
    plt : module
        The `matplotlib.pyplot` module (passed in rather than
        imported here, so this stays a pure helper of
        `plot_xsuite_sad_comparison`, which does the lazy import).
    xsuite_aligned : xt.Table
        Xsuite-side aligned table (already windowed, if requested).
    sad_aligned : xt.Table
        SAD-side aligned table (already windowed, if requested).
    title : str
        The figure's title (see `_QUANTITY_GROUPS`).
    quantities : list of tuple
        `(sad_column, overlay_label, diff_label)` triples for this
        group (see `_QUANTITY_GROUPS`).
    figsize : tuple
        Passed to `plt.figure`.
    include_diff : bool
        Add a (Xsuite - SAD) row flush under every overlay row.
    xsuite_column_overrides : dict
        SAD column name -> Xsuite column name, for quantities where
        the two sides use different names.
    zero_tol : float
        Values with `abs(value) < zero_tol` are shown as exactly zero.
    title_prefix : str or None
        Prepended to the figure's title as
        `"{title_prefix}: {title}"`.
    lattice_cache : dict or None
        Shared cache for `_draw_lattice_ribbon`, or None to skip
        drawing the lattice ribbon.

    Returns
    -------
    tuple of (matplotlib.figure.Figure, list of matplotlib.axes.Axes)
        The figure and its axes (overlay and, if `include_diff`,
        difference axes interleaved).
    """
    # Constrained layout keeps legend/labels correctly spaced at any figsize.
    fig     = plt.figure(figsize = figsize, layout = "constrained")
    outer   = fig.add_gridspec(len(quantities), 1, hspace = 0.4)

    axs                             = []
    first_ax                        = None
    legend_handles, legend_labels   = [], []
    for i, (sad_col, overlay_label, diff_label) in enumerate(quantities):
        xs_col  = xsuite_column_overrides.get(sad_col, sad_col)

        s_sad   = _zero_small_values(sad_aligned.s, zero_tol)
        s_xs    = _zero_small_values(xsuite_aligned.s, zero_tol)
        y_sad   = _zero_small_values(getattr(sad_aligned, sad_col), zero_tol)
        y_xs    = _zero_small_values(getattr(xsuite_aligned, xs_col), zero_tol)

        if include_diff:
            inner       = outer[i].subgridspec(2, 1, height_ratios = [3, 1], hspace = 0)
            overlay_ax  = fig.add_subplot(inner[0], sharex = first_ax)
            diff_ax     = fig.add_subplot(inner[1], sharex = overlay_ax)
            plt.setp(overlay_ax.get_xticklabels(), visible = False)
        else:
            overlay_ax  = fig.add_subplot(outer[i], sharex = first_ax)
            diff_ax     = None
        first_ax    = first_ax or overlay_ax

        if lattice_cache is not None:
            plot_ax, lattice_handles, lattice_labels  = _draw_lattice_ribbon(
                overlay_ax, xsuite_aligned, lattice_cache)
            # Only the axis that triggered the real xtrack computation gets
            # its own auto-drawn legend (bars copied onto other axes don't)
            # -- drop it, the combined SAD/Xsuite + bar-type legend below
            # replaces it either way.
            stray_legend    = overlay_ax.get_legend()
            if stray_legend is not None:
                stray_legend.remove()
        else:
            plot_ax, lattice_handles, lattice_labels  = overlay_ax, [], []

        sad_line,       = plot_ax.plot(s_sad, y_sad, color = "r", label = "SAD", zorder = 3)
        xsuite_line,    = plot_ax.plot(s_xs, y_xs, color = "b", ls = "--", label = "Xsuite", zorder = 3)
        plot_ax.set_ylabel(overlay_label)
        if i == 0:
            legend_handles  = lattice_handles + [sad_line, xsuite_line]
            legend_labels   = lattice_labels + ["SAD", "Xsuite"]
        axs.append(plot_ax)

        if diff_ax is not None:
            diff_ax.plot(s_sad, _difference(y_xs, y_sad, sad_col), color = "k")
            diff_ax.set_ylabel(diff_label)
            axs.append(diff_ax)

    axs[-1].set_xlabel("s [m]")
    # A plain suptitle works correctly with constrained-layout spacing.
    fig.suptitle(f"{title_prefix}: {title}" if title_prefix else title)

    # Try one row first; fall back to the wrapped layout if it doesn't fit.
    legend  = axs[0].legend(
        legend_handles, legend_labels,
        loc             = "lower center",
        bbox_to_anchor  = (0.5, 1.02),
        ncol            = len(legend_handles),
        fontsize        = "small")
    fig.canvas.draw()
    if legend.get_window_extent().width > fig.get_window_extent().width:
        legend.remove()
        legend  = axs[0].legend(
            legend_handles, legend_labels,
            loc             = "lower center",
            bbox_to_anchor  = (0.5, 1.02),
            ncol            = min(len(legend_handles), 4),
            fontsize        = "small")
        fig.canvas.draw()

    # Fold offset text into ylabel; it would otherwise overlap the row above.
    for ax in axs:
        offset_text = ax.yaxis.get_offset_text()
        text        = offset_text.get_text()
        if text:
            offset_text.set_visible(False)
            ax.set_ylabel(f"{ax.get_ylabel()} ({text})")

    fig.align_labels()

    return fig, axs

################################################################################
# Public comparison-plot function
################################################################################
def plot_xsuite_sad_comparison(
        xsuite_aligned:             xt.Table,
        sad_aligned:                xt.Table,
        *,
        groups:                     Iterable[str] | None    = None,
        ele_start:                  str | None              = None,
        ele_stop:                   str | None              = None,
        figsize:                    tuple[float, float]     = (10, 8),
        include_diff:               bool                    = True,
        xsuite_column_overrides:    dict[str, str] | None   = None,
        zero_tol:                   float                   = 1E-12,
        title_prefix:               str | None              = None,
        show_lattice:               bool                    = True,
        aligned:                    bool                    = True,
        save_dir:                   str | None              = None,
        save_format:                str                     = "pdf"
        ) -> dict[str, tuple["matplotlib.figure.Figure", list["matplotlib.axes.Axes"]]]:
    """
    Overlay Xsuite against SAD for each quantity group in `groups` (default
    `AVAILABLE_GROUPS`, i.e. all of them), one figure per group, with an
    optional difference row flush under each overlay row. Does not call
    `plt.show()` -- that's the caller's choice.

    Parameters
    ----------
    xsuite_aligned, sad_aligned : xt.Table
        By default (`aligned=True`), same-length, row-matched tables, e.g.
        from `align_xsuite_twiss_with_sad_twiss`. With `aligned=False`, any
        two twiss tables -- no length/row-matching requirement.
    groups : iterable of str, optional
        Subset of `AVAILABLE_GROUPS` to draw. `AVAILABLE_GROUPS` is
        `("orbit_xy", "orbit_pxpy", "longitudinal", "beta", "alpha",
        "dispersion", "ddispersion")`.
    ele_start, ele_stop : str, optional
        Element names bounding the row range plotted, inclusive (matched
        against `sad_aligned.name` when `aligned=True`; against each
        table's own `name` column independently when `aligned=False`).
        Both tables (and the lattice ribbon, which is drawn from the same
        `xsuite_aligned` rows) narrow together -- e.g.
        `groups=["orbit_xy"], ele_start="ip.4", ele_stop="ip.4"` for an
        orbit-only close-up around one IP, reusing the same function used
        for a full-ring overview.
    figsize : tuple, optional
        Passed to `plt.figure` for every figure.
    include_diff : bool, optional
        Add a (Xsuite - SAD) row flush under every overlay row. Relative
        (%) for `betx`/`bety`, absolute otherwise. Forced to `False` when
        `aligned=False` -- a row-by-row difference needs row-matched
        tables.
    xsuite_column_overrides : dict, optional
        SAD column name -> Xsuite column name, for cases where the two
        sides use different names (e.g. `{"betx": "betx_edw_teng"}` for
        coupled Edwards-Teng optics).
    zero_tol : float, optional
        Values with `abs(value) < zero_tol` are shown as exactly zero.
    title_prefix : str, optional
        Prepended to each figure's title as `"{title_prefix}: {title}"`, e.g.
        to distinguish multiple calls for different twiss modes.
    show_lattice : bool, optional
        Default `True`: draw Xsuite's own element-type ribbon (as in
        `xt.TwissTable.plot()`) behind each overlay row, from
        `xsuite_aligned`.
    aligned : bool, optional
        Default `True`: `xsuite_aligned`/`sad_aligned` are same-length and
        row-matched. Set `False` to overlay two tables that aren't --
        e.g. SAD and Xsuite twiss straight from their own solvers, with no
        call to `align_xsuite_twiss_with_sad_twiss` (which would otherwise
        require every SAD element to find a unique Xsuite match, and can
        fail after lattice surgery such as merging consecutive drifts).
        Overlay curves are drawn independently per side either way; only
        the (Xsuite - SAD) difference row needs row alignment, so
        `include_diff` is forced off.
    save_dir : str, optional
        Default `None`: don't save. Otherwise a directory (created if it
        doesn't exist, mirroring the `output_directory` convention used
        elsewhere in sad2xs) that every plotted group is saved into, one
        file per group, named `"{title_prefix}_{group}.{save_format}"`
        (sanitized, lowercased; no `title_prefix` -> just `"{group}"`).
    save_format : str, optional
        Default `"pdf"`: file format/extension `Figure.savefig` saves
        each group as, under `save_dir`. Vector by default so a plot
        stays sharp at any zoom in a report; pass e.g. `"png"` for a
        raster file instead.

    Returns
    -------
    dict[str, (Figure, list[Axes])]
        One entry per plotted group, keyed by its `AVAILABLE_GROUPS` name.
    """
    import matplotlib.pyplot as plt    # lazy: xsuite_helpers stays dependency-free

    if not aligned and include_diff:
        logger.warning(
            "plot_xsuite_sad_comparison: aligned=False, forcing "
            "include_diff=False (needs row-matched tables).")
        include_diff    = False

    xsuite_column_overrides    = xsuite_column_overrides or {}
    xsuite_aligned, sad_aligned = _window_by_element(
        xsuite_aligned, sad_aligned, ele_start, ele_stop, aligned = aligned)

    # Same lattice for every quantity in every group below -- one shared
    # cache means Xsuite computes the ribbon for real exactly once, no
    # matter how many groups/axes end up showing it.
    lattice_cache   = {"bars": None, "legend": None} if show_lattice else None

    figures = {}
    for key in (groups if groups is not None else AVAILABLE_GROUPS):
        title, quantities   = _QUANTITY_GROUPS[key]
        figures[key]        = _plot_group(
            plt, xsuite_aligned, sad_aligned, title, quantities,
            figsize                     = figsize,
            include_diff                = include_diff,
            xsuite_column_overrides     = xsuite_column_overrides,
            zero_tol                    = zero_tol,
            title_prefix                = title_prefix,
            lattice_cache               = lattice_cache)

    if save_dir is not None:
        Path(save_dir).mkdir(parents = True, exist_ok = True)
        stem    = title_prefix and _sanitize_filename_stem(title_prefix)
        prefix  = f"{stem}_" if stem else ""
        for key, (fig, _) in figures.items():
            fig.savefig(f"{save_dir}/{prefix}{key}.{save_format}")

    return figures
