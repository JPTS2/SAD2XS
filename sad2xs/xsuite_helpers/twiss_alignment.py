"""
================================================================================
Xsuite Helpers: Twiss Alignment
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
import logging
import re
from collections import defaultdict

import numpy as np

logger  = logging.getLogger(__name__)

_REPEAT_SUFFIX_RE  = re.compile(r"^(.*)\.(\d+)$")

# One SAD solenoid-boundary element becomes 4 Xsuite placements (only
# "_bound" carries real physics); see docs/xsuite-helpers.md for why the
# front face isn't always "_bound". _collapse_slicing folds all 4 into one.
_BOUNDARY_COMPOUND_SUFFIXES    = {"bound", "dxy", "dz", "rot"}
_COMPOUND_SUFFIX_RE = re.compile(
    r"_(?:" + "|".join(_BOUNDARY_COMPOUND_SUFFIXES) + r")(\.\d+)?$")

################################################################################
# Name helpers
################################################################################
def _collapse_slicing(name: str) -> str:
    """
    Strip xtrack's ``::N`` table-disambiguation and ``..N``/``..entry_map``
    slicing suffixes, and sad2xs's solenoid-boundary compound suffix (keeping
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

def _parse_repeat_suffix(name_lower: str):
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

def compute_s_sad(xsuite_twiss):
    """
    Recover SAD's own `s` (real path length) from an Xsuite twiss result,
    whose `s` is nominal/design length. The two diverge only right after a
    TimeDelay's artificial `zeta` jump (bookkeeping for a real geometric
    offset SAD's own `s` already includes); that jump is added back into
    `s` here. `zeta`'s evolution everywhere else is real physics and is
    left alone. Full derivation: docs/xsuite-helpers.md.

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
        xsuite_twiss, sad_twiss, *,
        s_tol: float = 1E-9,
        use_s_sad: bool = True,
        excluded_elements: list | None = None):
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
    rationale: docs/xsuite-helpers.md.

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

    sad_positions_by_base  = defaultdict(list)
    for i, name in enumerate(sad_names):
        sad_positions_by_base[name.lower()].append(i)

    ########################################
    # Xsuite side (drop the trailing "_end_point" row, if present).
    # Matching/ranking always uses raw xs_s, never s_sad -- s_sad isn't
    # constant across a solenoid-boundary compound's own pieces.
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
    # Face row per placement: smallest s, or the {name}_entry marker
    # slice_thick_elements() adds, which wins any tie on s.
    ########################################
    face_row_for_placement     = {}
    for i, (name, s) in enumerate(zip(xs_names, xs_s)):
        collapsed   = _collapse_slicing(name)
        prev        = face_row_for_placement.get(collapsed)
        if prev is None or s < prev[1]:
            face_row_for_placement[collapsed]  = (i, s)
    for i, name in enumerate(xs_names):
        if name.endswith("_entry"):
            face_row_for_placement[name[:-len("_entry")]]  = (i, xs_s[i])

    # Repeat-suffixed placements by stripped base; only consulted after an
    # exact-match miss, so a real SAD ".<digits>" name (e.g. "QEAP.44") is
    # never mistaken for one.
    repeat_candidates_by_base  = defaultdict(list)
    xs_family_bases            = set()
    for collapsed, hit in face_row_for_placement.items():
        base, index = _parse_repeat_suffix(collapsed.lower())
        if index is not None:
            repeat_candidates_by_base[base].append(hit)
            xs_family_bases.add(base)

    ########################################
    # Matching machinery
    ########################################
    matched_sad_idx = []
    matched_xs_idx  = []
    rejected_s_tol  = []
    claimed_sad     = set()
    claimed_xs      = set()

    def _accept(sad_i, row_idx, s_xs):
        """
        Accept or reject a candidate SAD-to-Xsuite row match by
        `s_tol`, recording it in the shared matched/claimed state on
        acceptance.

        Acceptance always checks `s_for_tol` (s_sad where available),
        not the raw `s_xs` used for ranking.

        Parameters
        ----------
        sad_i : int
            Index into `sad_names`/`sad_s` of the candidate SAD
            element.
        row_idx : int
            Index into `xs_names`/`xs_s` of the candidate Xsuite row.
        s_xs : float
            The candidate row's ranking `s` value (unused for the
            tolerance check itself, kept for the rejection log).
        """
        # Acceptance always checks s_for_tol (s_sad where available), not
        # the raw s_xs used for ranking.
        s_compare   = s_for_tol[row_idx]
        if abs(s_compare - sad_s[sad_i]) > s_tol:
            rejected_s_tol.append((sad_names[sad_i], sad_s[sad_i], s_compare))
            return
        matched_sad_idx.append(sad_i)
        matched_xs_idx.append(row_idx)
        claimed_sad.add(sad_i)
        claimed_xs.add(row_idx)

    def _rank_match(sad_idx_sorted_by_s, candidates):
        """
        Pair SAD elements to Xsuite candidates in matching rank order
        by `s`, then hand each pair to `_accept`.

        Both `sad_idx_sorted_by_s` and `candidates` are sorted by
        position and paired index-for-index, so the Nth-lowest-s SAD
        element gets the Nth-lowest-s remaining candidate -- correct
        when a family's members are consistently ordered on both
        sides, which every caller of `_rank_match` in this function
        already ensures.

        Parameters
        ----------
        sad_idx_sorted_by_s : list of int
            SAD element indices for one name/family group, sorted by
            `s`.
        candidates : iterable of tuple of (int, float)
            `(row_idx, s_xs)` Xsuite row candidates for the same
            group; already-claimed rows are filtered out and the rest
            sorted by `s_xs` before pairing.
        """
        candidates  = sorted(
            {c for c in candidates if c[0] not in claimed_xs},
            key = lambda c: c[1])
        for rank, sad_i in enumerate(sad_idx_sorted_by_s):
            if rank >= len(candidates):
                break
            row_idx, s_xs   = candidates[rank]
            _accept(sad_i, row_idx, s_xs)

    ########################################
    # Pass 1: SAD's exact name
    ########################################
    for base, sad_idx_list in sad_positions_by_base.items():
        # A SAD name that itself looks like "base.N" (e.g. "LXL28467.1")
        # could coincidentally match an unrelated xtrack repeat -- defer to pass 2.
        self_base, self_index  = _parse_repeat_suffix(base)
        if self_index is not None and (
                self_base in xs_family_bases
                or f"-{self_base}" in xs_family_bases):
            continue

        candidates  = []
        exact_hit   = face_row_for_placement.get(base)
        if exact_hit is not None:
            candidates.append(exact_hit)
        if len(sad_idx_list) > 1 or exact_hit is None:
            candidates.extend(repeat_candidates_by_base.get(base, []))
        if candidates:
            _rank_match(sad_idx_list, candidates)

    ########################################
    # Pass 2: SAD's dot-suffixed family name
    ########################################
    sad_family_groups   = defaultdict(list)
    for i, name in enumerate(sad_names):
        if i in claimed_sad:
            continue
        base, sad_index     = _parse_repeat_suffix(name.lower())
        if sad_index is not None:
            sad_family_groups[base].append(i)

    for base, sad_idx_list in sad_family_groups.items():
        # Pool the plain and "-"-prefixed variant: a family can be split
        # across both if some placements came via a reversed sub-line.
        pool    = list(repeat_candidates_by_base.get(base, []))
        pool    += repeat_candidates_by_base.get(f"-{base}", [])
        for candidate_base in (base, f"-{base}"):
            exact_hit   = face_row_for_placement.get(candidate_base)
            if exact_hit is not None:
                pool.append(exact_hit)
        if pool:
            _rank_match(sorted(sad_idx_list, key = lambda i: sad_s[i]), pool)

    ########################################
    # Pass 3: solenoid-interior rename ({name}_{neighbouring_solenoid}).
    # The neighbour isn't known in advance, so candidates are found by
    # string-prefix search; `s_tol` guards against a coincidental match.
    ########################################
    for i, name in enumerate(sad_names):
        if i in claimed_sad:
            continue
        prefix  = f"{name.lower()}_"
        for xs_name, hit in face_row_for_placement.items():
            if xs_name.startswith(prefix) and hit[0] not in claimed_xs \
                    and abs(hit[1] - sad_s[i]) <= s_tol:
                _accept(i, hit[0], hit[1])
                break

    # Same family-pooling as pass 2, but keyed on "{base}_{neighbour}" --
    # a repeated element's neighbour can alternate along the family.
    sad_interior_groups     = defaultdict(list)
    for i, name in enumerate(sad_names):
        if i in claimed_sad:
            continue
        base, sad_index = _parse_repeat_suffix(name.lower())
        if sad_index is not None:
            sad_interior_groups[base].append(i)

    for base, sad_idx_list in sad_interior_groups.items():
        prefix  = f"{base}_"
        pool    = [
            hit
            for xs_base, hits in repeat_candidates_by_base.items()
            if xs_base.startswith(prefix)
            for hit in hits]
        if pool:
            _rank_match(sorted(sad_idx_list, key = lambda i: sad_s[i]), pool)

    ########################################
    # Assemble result
    ########################################
    order               = np.argsort(matched_sad_idx) if matched_sad_idx else np.array([], dtype = int)
    matched_sad_idx     = np.array(matched_sad_idx, dtype = int)[order]
    matched_xs_idx      = np.array(matched_xs_idx, dtype = int)[order]

    matched_mask            = np.zeros(n_sad, dtype = bool)
    matched_mask[matched_sad_idx]  = True
    unmatched_sad_names     = [sad_names[i] for i in range(n_sad) if not matched_mask[i]]
    unmatched_xsuite_names  = [
        name for i, name in enumerate(xs_names)
        if i not in set(matched_xs_idx.tolist())]

    logger.info(
        f"align_xsuite_twiss_with_sad_twiss: matched {len(matched_sad_idx)}/{n_sad} "
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

    xsuite_aligned  = xsuite_twiss.rows[matched_xs_idx]
    if s_sad is not None:
        xsuite_aligned.s_sad   = s_sad[matched_xs_idx]

    return xsuite_aligned, sad_twiss
