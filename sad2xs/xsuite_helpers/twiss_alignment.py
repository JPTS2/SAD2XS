"""
================================================================================
Xsuite Helpers: Twiss Alignment
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-29
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import logging
import re
from collections import defaultdict
from collections.abc import Iterable

import numpy as np
import xtrack as xt

logger  = logging.getLogger(__name__)

_REPEAT_SUFFIX_RE  = re.compile(r"^(.*)\.(\d+)$")

# Suffixes for a SAD element split into several Xsuite placements
# (solenoid boundary, soft quadrupolar fringe) that _collapse_slicing folds
# back into one; see docs/helpers/xsuite-helpers.md.
_COMPOUND_SUFFIXES  = {"bound", "dxy", "dz", "rot", "fringe_in", "fringe_out"}
_COMPOUND_SUFFIX_RE = re.compile(
    r"_(?:" + "|".join(_COMPOUND_SUFFIXES) + r")(\.\d+)?$")

################################################################################
# Name helpers
################################################################################
def _collapse_slicing(name: str) -> str:
    """
    Strip xtrack's ``::N`` table-disambiguation and ``..N``/``..entry_map``
    slicing suffixes, and sad2xs's own compound-piece suffixes (keeping
    any trailing repeat digit), leaving the name of the one logical placement
    a row belongs to.

    Parameters
    ----------
    name : str
        An Xsuite twiss-table row name.

    Returns
    -------
    str
        The name of the logical placement this row belongs to.
    """
    name    = name.split("::")[0].split("..")[0]
    m       = _COMPOUND_SUFFIX_RE.search(name)
    if m:
        name    = name[:m.start()] + (m.group(1) or "")
    return name

def _parse_repeat_suffix(name_lower: str) -> tuple[str, int | None]:
    """
    Undo `line.replace_all_repeated_elements()`'s ``{name}.{i}`` renaming ->
    (base, i), or (name_lower, None) if it doesn't match.

    Parameters
    ----------
    name_lower : str
        A lowercased element name, possibly ``{base}.{i}``-suffixed.

    Returns
    -------
    tuple of (str, int or None)
        `(base, i)` if `name_lower` matches the repeat-suffix
        pattern, otherwise `(name_lower, None)`.
    """
    m   = _REPEAT_SUFFIX_RE.match(name_lower)
    if m is None:
        return name_lower, None
    return m.group(1), int(m.group(2))

# sad2xs's only two TimeDelay-generating suffixes (solenoid-boundary "_dz",
# reference-energy "_ref_zeta_update"); allows a repeat's trailing ".N" too.
_TIMEDELAY_SUFFIX_RE    = re.compile(r"_(?:dz|ref_zeta_update)(?:\.\d+)?$")

def compute_s_sad(xsuite_twiss: xt.TwissTable) -> np.ndarray | None:
    """
    Recover SAD's own `s` (real path length) from an Xsuite twiss result,
    whose `s` is nominal/design length. The two diverge only right after a
    TimeDelay's artificial `zeta` jump (bookkeeping for a real geometric
    offset SAD's own `s` already includes); that jump is added back into
    `s` here. `zeta`'s evolution everywhere else is real physics and is
    left alone. Full derivation: docs/helpers/xsuite-helpers.md.

    Parameters
    ----------
    xsuite_twiss : xt.TwissTable
        A converted line's twiss result.

    Returns
    -------
    numpy.ndarray or None
        SAD-equivalent `s` values, or `None` if there's no usable
        `zeta` column (e.g. an open-line 4D twiss without a real
        6D/RF setup).
    """
    if "zeta" not in xsuite_twiss.keys():
        return None
    xs_zeta = np.asarray(xsuite_twiss.zeta, dtype = float)
    if not np.all(np.isfinite(xs_zeta)):
        return None

    xs_names    = [str(n) for n in xsuite_twiss.name]
    xs_s        = np.asarray(xsuite_twiss.s, dtype = float)

    dzeta   = np.diff(xs_zeta, prepend = 0.0)
    dzeta[0]    = 0.0

    is_timedelay        = np.array([
        _TIMEDELAY_SUFFIX_RE.search(name.lower()) is not None for name in xs_names])
    after_timedelay             = np.zeros(len(xs_names), dtype = bool)
    after_timedelay[1:]         = is_timedelay[:-1]
    artificial_jump             = np.where(after_timedelay, dzeta, 0.0)

    return xs_s + np.cumsum(artificial_jump)

################################################################################
# Align an Xsuite twiss table onto a SAD twiss table's element grid
################################################################################
def align_xsuite_twiss_with_sad_twiss(
        xsuite_twiss:       xt.TwissTable,
        sad_twiss:          xt.TwissTable,
        *,
        s_tol:              float               = 1E-9,
        use_s_sad:          bool                = True,
        excluded_elements:  list[str] | None    = None) -> tuple[xt.Table, xt.Table]:
    """
    Match every SAD element to its unique Xsuite row and return
    `(xsuite_aligned, sad_twiss_aligned)`: same length, row-matched, in
    `sad_twiss`'s own order. No interpolation -- an Xsuite row with no
    single-element SAD counterpart (solenoid geometry pieces, offset
    markers, gap-filling drifts, ...) is dropped rather than guessed at.
    Every remaining SAD element must find a match (see Raises).

    Matched by name in three passes (exact name, dot-suffixed family name,
    solenoid-interior rename), each only tried for elements still
    unmatched and always checked against `s_tol`. Full pass-by-pass
    rationale: docs/helpers/xsuite-helpers.md.

    Parameters
    ----------
    xsuite_twiss : xt.TwissTable
        A converted line's twiss result.
    sad_twiss : xt.TwissTable
        SAD's own twiss result for the same lattice, taken as the target
        element grid.
    s_tol : float, optional
        Max `abs(s_sad - s_xsuite)` for a match to be accepted. Default
        1E-9.
    use_s_sad : bool, optional
        Default `True`: match against `compute_s_sad(xsuite_twiss)` where
        available (see `compute_s_sad`), attached as `xsuite_aligned.s_sad`.
        `False` matches and returns `xsuite_twiss.s` unmodified.
    excluded_elements : list of str, optional
        SAD element names (case-insensitive, base name only) to drop from
        `sad_twiss` before matching -- e.g. `convert_sad_to_xsuite`'s own
        `excluded_elements`, plus any offset markers
        `convert_offset_markers` reports absent from the live line.

    Returns
    -------
    (xt.Table, xt.Table)
        `(xsuite_aligned, sad_twiss_aligned)` -- `xsuite_aligned.betx -
        sad_twiss_aligned.betx` is a direct element-by-element comparison.
        `xsuite_aligned.s` is untouched; a `use_s_sad` correction is
        attached separately as `.s_sad`, not overwritten onto `.s`.

    Raises
    ------
    AssertionError
        If any SAD element (after `excluded_elements`) found no Xsuite match.
    """

    ########################################
    # SAD side: target element grid
    ########################################
    if excluded_elements:
        excluded_lower  = {e.lower() for e in excluded_elements}
        keep    = np.array([
            _parse_repeat_suffix(str(n).lower())[0] not in excluded_lower
            for n in sad_twiss.name])
        sad_twiss   = sad_twiss.rows[keep]

    sad_names   = [str(n) for n in sad_twiss.name]
    n_sad       = len(sad_names)
    sad_s       = np.asarray(sad_twiss.s, dtype = float)

    sad_rows_by_name  = defaultdict(list)
    for sad_row, name in enumerate(sad_names):
        sad_rows_by_name[name.lower()].append(sad_row)

    ########################################
    # Xsuite side (drop the trailing "_end_point" row, if present).
    # Match SAD's physical s, corrected for reference-frame TimeDelays
    # where that information is available.
    ########################################
    xs_names    = [str(n) for n in xsuite_twiss.name]
    xs_s        = np.asarray(xsuite_twiss.s, dtype = float)
    s_sad       = compute_s_sad(xsuite_twiss) if use_s_sad else None
    if xs_names and xs_names[-1] == "_end_point":
        xs_names, xs_s  = xs_names[:-1], xs_s[:-1]
        if s_sad is not None:
            s_sad   = s_sad[:-1]
    s_for_tol   = s_sad if s_sad is not None else xs_s

    ########################################
    # Face row per placement: earliest row (table order, not s -- ties
    # on s must still resolve to the earlier row).
    ########################################
    face_row_for_placement     = {}
    for row, name in enumerate(xs_names):
        placement_name  = _collapse_slicing(name)
        previous_row    = face_row_for_placement.get(placement_name)
        if previous_row is None or row < previous_row:
            face_row_for_placement[placement_name]  = row
    for row, name in enumerate(xs_names):
        if name.endswith("_entry"):
            placement_name  = name[:-len("_entry")]
            previous_row    = face_row_for_placement.get(placement_name)
            if previous_row is None or row < previous_row:
                face_row_for_placement[placement_name]  = row

    # Repeat-suffixed placements by family name; only consulted after an
    # exact-match miss, so a real SAD ".<digits>" name (e.g. "QEAP.44") is
    # never mistaken for one.
    xsuite_repeat_rows_by_family  = defaultdict(list)
    xsuite_repeat_families        = set()
    for placement_name, row in face_row_for_placement.items():
        family_name, repeat_index  = _parse_repeat_suffix(
            placement_name.lower())
        if repeat_index is not None:
            xsuite_repeat_rows_by_family[family_name].append(row)
            xsuite_repeat_families.add(family_name)

    ########################################
    # Matching machinery
    ########################################
    matched_sad_rows     = []
    matched_xsuite_rows  = []
    rejected_s_tol       = []
    claimed_sad_rows     = set()
    claimed_xsuite_rows  = set()

    def _position_match(
            sad_rows:       list[int],
            candidates:     Iterable[int]) -> None:
        """
        Match one SAD name/family group by physical longitudinal position.

        A reversed compound can put a ``-name_fringe_*`` row and the
        direction-symmetric ``name`` body at the same placement. Xtrack
        numbers those repeated definitions independently, so ordinal
        suffixes cannot identify the placement. Match within `s_tol`
        instead, choosing the earliest table row when several compound
        pieces share a position; that row is the physical entrance face.

        Parameters
        ----------
        sad_rows : list of int
            SAD element indices for one name/family group.
        candidates : iterable of int
            Xsuite row indices carrying a compatible name.
        """
        available_rows  = set(candidates) - claimed_xsuite_rows
        for sad_row in sorted(sad_rows, key = lambda row: sad_s[row]):
            if not available_rows:
                break

            nearest_xsuite_row = min(
                available_rows,
                key = lambda row: (
                    abs(s_for_tol[row] - sad_s[sad_row]), row))
            xsuite_s  = s_for_tol[nearest_xsuite_row]
            if abs(xsuite_s - sad_s[sad_row]) > s_tol:
                rejected_s_tol.append(
                    (sad_names[sad_row], sad_s[sad_row], xsuite_s))
                continue

            matched_sad_rows.append(sad_row)
            matched_xsuite_rows.append(nearest_xsuite_row)
            claimed_sad_rows.add(sad_row)
            claimed_xsuite_rows.add(nearest_xsuite_row)
            available_rows.remove(nearest_xsuite_row)

    ########################################
    # Pass 1: SAD's exact name
    ########################################
    for name, sad_rows in sad_rows_by_name.items():
        # A SAD name that itself looks like "base.N" (e.g. "LXL28467.1")
        # could coincidentally match an unrelated xtrack repeat -- defer to pass 2.
        family_name, repeat_index  = _parse_repeat_suffix(name)
        if repeat_index is not None and (
                family_name in xsuite_repeat_families
                or f"-{family_name}" in xsuite_repeat_families):
            continue

        candidates  = []
        exact_row   = face_row_for_placement.get(name)
        if exact_row is not None:
            candidates.append(exact_row)
        if len(sad_rows) > 1 or exact_row is None:
            candidates.extend(xsuite_repeat_rows_by_family.get(name, []))
        if candidates:
            _position_match(sad_rows, candidates)

    ########################################
    # Pass 2: SAD's dot-suffixed family name
    ########################################
    sad_rows_by_family  = defaultdict(list)
    for sad_row, name in enumerate(sad_names):
        if sad_row in claimed_sad_rows:
            continue
        family_name, repeat_index  = _parse_repeat_suffix(name.lower())
        if repeat_index is not None:
            sad_rows_by_family[family_name].append(sad_row)

    for family_name, sad_rows in sad_rows_by_family.items():
        # Pool the plain and "-"-prefixed variant: a family can be split
        # across both if some placements came via a reversed sub-line.
        candidates  = list(xsuite_repeat_rows_by_family.get(family_name, []))
        candidates  += xsuite_repeat_rows_by_family.get(f"-{family_name}", [])
        for candidate_name in (family_name, f"-{family_name}"):
            exact_row   = face_row_for_placement.get(candidate_name)
            if exact_row is not None:
                candidates.append(exact_row)
        if candidates:
            _position_match(sad_rows, candidates)

    ########################################
    # Pass 3: solenoid-interior rename ({name}_{neighbouring_solenoid}).
    # The neighbour isn't known in advance, so candidates are found by
    # string-prefix search; `s_tol` guards against a coincidental match.
    ########################################
    for sad_row, name in enumerate(sad_names):
        if sad_row in claimed_sad_rows:
            continue
        prefix  = f"{name.lower()}_"
        candidates  = [
            xsuite_row
            for xsuite_name, xsuite_row in face_row_for_placement.items()
            if xsuite_name.startswith(prefix)]
        _position_match([sad_row], candidates)

    # Same family-pooling as pass 2, but keyed on "{base}_{neighbour}" --
    # a repeated element's neighbour can alternate along the family.
    sad_interior_rows_by_family  = defaultdict(list)
    for sad_row, name in enumerate(sad_names):
        if sad_row in claimed_sad_rows:
            continue
        family_name, repeat_index  = _parse_repeat_suffix(name.lower())
        if repeat_index is not None:
            sad_interior_rows_by_family[family_name].append(sad_row)

    for family_name, sad_rows in sad_interior_rows_by_family.items():
        prefix  = f"{family_name}_"
        candidates  = [
            xsuite_row
            for xsuite_family, xsuite_rows in xsuite_repeat_rows_by_family.items()
            if xsuite_family.startswith(prefix)
            for xsuite_row in xsuite_rows]
        if candidates:
            _position_match(sad_rows, candidates)

    ########################################
    # Assemble result
    ########################################
    order = np.argsort(matched_sad_rows) \
        if matched_sad_rows else np.array([], dtype = int)
    matched_sad_rows     = np.array(matched_sad_rows, dtype = int)[order]
    matched_xsuite_rows  = np.array(matched_xsuite_rows, dtype = int)[order]

    matched_mask            = np.zeros(n_sad, dtype = bool)
    matched_mask[matched_sad_rows]  = True
    unmatched_sad_names     = [sad_names[i] for i in range(n_sad) if not matched_mask[i]]
    unmatched_xsuite_names  = [
        name for i, name in enumerate(xs_names)
        if i not in set(matched_xsuite_rows.tolist())]

    logger.info(
        f"align_xsuite_twiss_with_sad_twiss: matched {len(matched_sad_rows)}/{n_sad} "
        f"SAD elements ({len(unmatched_sad_names)} unmatched, {len(rejected_s_tol)} "
        f"rejected by s_tol={s_tol:g}); dropped {len(unmatched_xsuite_names)}/"
        f"{len(xs_names)} Xsuite-only rows.")
    if rejected_s_tol:
        logger.info(
            "s_tol rejections: " + ", ".join(
                f"{name} (SAD s={sad_s_val:.6f}, Xsuite s={xs_s_val:.6f})"
                for name, sad_s_val, xs_s_val in rejected_s_tol[:10])
            + (" ..." if len(rejected_s_tol) > 10 else ""))

    assert not unmatched_sad_names, (
        f"{len(unmatched_sad_names)} SAD element(s) had no Xsuite match: "
        f"{unmatched_sad_names[:20]}"
        + (" ..." if len(unmatched_sad_names) > 20 else ""))

    xsuite_aligned  = xsuite_twiss.rows[matched_xsuite_rows]
    if s_sad is not None:
        xsuite_aligned.s_sad   = s_sad[matched_xsuite_rows]

    return xsuite_aligned, sad_twiss
