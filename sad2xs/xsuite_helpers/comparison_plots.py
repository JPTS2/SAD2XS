"""
(Unofficial) SAD to XSuite Converter: Xsuite Helpers Comparison Plots
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-17
"""
################################################################################
# Required Packages
################################################################################
import numpy as np

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
def _zero_small_values(array, tol):
    """Zero values below `tol` so floating-point noise doesn't clutter a plot."""
    array   = np.array(array, dtype = float)
    array[np.abs(array) < tol]  = 0
    return array

def _difference(xs_values, sad_values, sad_column):
    """(Xsuite - SAD), relative (%) for beta functions, absolute otherwise."""
    if sad_column in _RELATIVE_DIFF_COLUMNS:
        with np.errstate(divide = "ignore", invalid = "ignore"):
            return np.where(
                sad_values != 0,
                (xs_values - sad_values) / sad_values * 1E2,
                np.nan)
    return xs_values - sad_values

def _window_by_element(xsuite_aligned, sad_aligned, ele_start, ele_stop):
    """Cut both aligned tables to the row range [ele_start, ele_stop] (by
    SAD element name, case-insensitive like align_xsuite_twiss_with_sad_twiss's
    own name matching, inclusive). No-op if neither is given."""
    if ele_start is None and ele_stop is None:
        return xsuite_aligned, sad_aligned

    names   = [str(n).lower() for n in sad_aligned.name]
    lo  = names.index(ele_start.lower()) if ele_start is not None else 0
    hi  = names.index(ele_stop.lower()) if ele_stop is not None else len(names) - 1
    if hi < lo:
        lo, hi  = hi, lo

    idx = np.arange(lo, hi + 1)
    return xsuite_aligned.rows[idx], sad_aligned.rows[idx]

################################################################################
# Lattice ribbon -- Xsuite's own element-type bars (xt.TwissTable.plot),
# computed for real once and copied onto every other axis. It's the same
# lattice for every quantity and every figure in one comparison call, so
# there's no reason to make Xsuite redraw thousands of magnets from scratch
# on each of them.
################################################################################
def _draw_lattice_ribbon(overlay_ax, xsuite_aligned, cache):
    """
    First call (`cache["bars"] is None`): let `xt.TwissTable.plot
    (lattice_only=True)` do the real work, then read the bars it drew
    straight off the axis and cache that geometry. Every later call just
    copies those bars onto its own axis instead of asking Xsuite to
    recompute and redraw the whole ribbon again.

    Returns `(data_axis, legend_handles, legend_labels)` -- `data_axis` is
    where the SAD/Xsuite comparison curves belong, a twin axis of
    `overlay_ax`, matching how Xsuite layers real data over its own bars.
    """
    if cache["bars"] is None:
        pl  = xsuite_aligned.plot(lattice_only = True, ax = overlay_ax, x = "s", grid = False)
        cache["bars"]   = [
            (bar.get_x(), bar.get_y(), bar.get_width(), bar.get_height(), bar.get_facecolor())
            for bar in pl.lattice.patches]
        cache["legend"] = (list(pl.lines), list(pl.legends))
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

    rectangles  = [Rectangle((x, y), width, height) for x, y, width, height, _ in cache["bars"]]
    colors      = [color for *_, color in cache["bars"]]
    ribbon_ax.add_collection(
        PatchCollection(rectangles, facecolor = colors, edgecolor = colors))

    return (ribbon_ax, *cache["legend"])

################################################################################
# One quantity-group figure
################################################################################
def _plot_group(
        plt, xsuite_aligned, sad_aligned, title, quantities, *,
        figsize, include_diff, xsuite_column_overrides, zero_tol,
        title_prefix, lattice_cache):

    fig     = plt.figure(figsize = figsize)
    outer   = fig.add_gridspec(len(quantities), 1, hspace = 0.4)

    axs         = []
    first_ax    = None
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
            plot_ax.legend(
                lattice_handles + [sad_line, xsuite_line],
                lattice_labels + ["SAD", "Xsuite"])
        axs.append(plot_ax)

        if diff_ax is not None:
            diff_ax.plot(s_sad, _difference(y_xs, y_sad, sad_col), color = "k")
            diff_ax.set_ylabel(diff_label)
            axs.append(diff_ax)

    axs[-1].set_xlabel("s [m]")
    fig.suptitle(f"{title_prefix}: {title}" if title_prefix else title)
    fig.align_labels()

    return fig, axs

################################################################################
# Public comparison-plot function
################################################################################
def plot_xsuite_sad_comparison(
        xsuite_aligned, sad_aligned, *,
        groups                  = None,
        ele_start                = None,
        ele_stop                 = None,
        figsize                  = (8, 6),
        include_diff             = True,
        xsuite_column_overrides  = None,
        zero_tol                 = 1E-12,
        title_prefix             = None,
        show_lattice             = True):
    """
    Overlay Xsuite against SAD for each quantity group in `groups` (default
    `AVAILABLE_GROUPS`, i.e. all of them), one figure per group, with an
    optional difference row flush under each overlay row. Does not call
    `plt.show()` -- that's the caller's choice.

    Parameters
    ----------
    xsuite_aligned, sad_aligned : xt.Table
        Same-length, row-matched tables, e.g. from
        `align_xsuite_twiss_with_sad_twiss`.
    groups : iterable of str, optional
        Subset of `AVAILABLE_GROUPS` to draw.
    ele_start, ele_stop : str, optional
        SAD element names (matched against `sad_aligned.name`) bounding the
        row range plotted, inclusive. Both tables (and the lattice ribbon,
        which is drawn from the same `sad_aligned` rows) narrow together --
        e.g. `groups=["orbit_xy"], ele_start="ip.4", ele_stop="ip.4"` for an
        orbit-only close-up around one IP, reusing the same function used
        for a full-ring overview.
    figsize : tuple, optional
        Passed to `plt.figure` for every figure.
    include_diff : bool, optional
        Add a (Xsuite - SAD) row flush under every overlay row. Relative
        (%) for `betx`/`bety`, absolute otherwise.
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

    Returns
    -------
    dict[str, (Figure, list[Axes])]
        One entry per plotted group, keyed by its `AVAILABLE_GROUPS` name.
    """
    import matplotlib.pyplot as plt    # lazy: xsuite_helpers stays dependency-free

    xsuite_column_overrides    = xsuite_column_overrides or {}
    xsuite_aligned, sad_aligned = _window_by_element(
        xsuite_aligned, sad_aligned, ele_start, ele_stop)

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

    return figures
