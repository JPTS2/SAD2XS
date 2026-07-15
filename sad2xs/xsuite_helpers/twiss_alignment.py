"""
(Unofficial) SAD to XSuite Converter: Xsuite Helpers Twiss Alignment
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-15
"""

################################################################################
# Required Packages
################################################################################
import logging
import re
from collections import defaultdict

import numpy as np
import xtrack as xt

logger  = logging.getLogger(__name__)

_REPEAT_SUFFIX_RE  = re.compile(r"^(.*)\.(\d+)$")

################################################################################
# Strip xtrack's own slicing/repeat-table name decoration
################################################################################
def _collapse_slicing(name: str) -> str:
    """
    Strip xtrack's thin/thick-slicing suffix (``..0``, ``..entry_map``,
    ``..exit_map``, ...) and its pre-`replace_all_repeated_elements` table
    disambiguation suffix (``::N``), leaving the name of the one logical,
    still possibly-repeated, placed element a raw table row belongs to.
    """
    return name.split("::")[0].split("..")[0]

################################################################################
# Split a collapsed name into (base, repeat_index)
################################################################################
def _parse_repeat_suffix(name_lower: str):
    """
    `line.replace_all_repeated_elements()` (separator=".", the xtrack/sad2xs
    default) renames every placement of a name used more than once to
    ``{name}.{i}`` in line order, `i` counting from 0. This undoes that,
    returning (base, i) -- or (name_lower, None) if it doesn't match.

    Only ever tried as a fallback once a name has already failed to match a
    SAD name directly (see `align_xsuite_twiss_with_sad_twiss`), so a real
    SAD element name containing a literal ``.<digits>`` (seen in these
    lattices, e.g. ``QEAP.44``) is never at risk of being misparsed here --
    it would already have matched directly, before this is ever called.
    """
    m   = _REPEAT_SUFFIX_RE.match(name_lower)
    if m is None:
        return name_lower, None
    return m.group(1), int(m.group(2))

################################################################################
# Keep only the row-shaped columns of a table (drop scalars like qx/qy)
################################################################################
def _row_shaped_columns(table, n_rows):
    return [
        col for col in table.keys()
        if np.asarray(getattr(table, col)).shape[:1] == (n_rows,)]

################################################################################
# Align an Xsuite twiss table onto a SAD twiss table's element grid
################################################################################
def align_xsuite_twiss_with_sad_twiss(
        xsuite_twiss, sad_twiss, *,
        s_tol: float = 1E-9,
        allowed_index_shift: int = 1,
        excluded_elements = None):
    """
    Match every SAD element to the one Xsuite row that is unambiguously the
    same physical element, and return each side reduced to just that
    matched set -- two ordinary, independent twiss tables of equal length.

    SAD's twiss table has one row per element in the SAD lattice, reported
    at each element's front face. An Xsuite twiss table of a converted line
    has more rows than that -- xtrack's own thin/thick-element slicing and
    repeated-placement renaming, and sad2xs's own generated structure
    (solenoid-interior element renaming, solenoid boundary geometry-
    transform components, RF-interleaved Multipole/Cavity slice pairs,
    inserted offset markers, gap-filling drifts) all add rows with no
    single-element counterpart in SAD's table, and (for a sliced element)
    reports several s positions across the element rather than one.

    This does not interpolate. For every SAD element, it looks for the one
    Xsuite row that is unambiguously the same physical element -- by name,
    after undoing exactly the renaming sad2xs and xtrack are each known to
    do -- checks that its `s` agrees with SAD's to within `s_tol`, and
    keeps that row as-is. Anything sad2xs had to invent to represent one
    SAD element as several Xsuite elements (compound geometry transforms,
    RF-interleaved slices, offset markers, connective drifts) is dropped
    for this comparison rather than guessed at -- as is any SAD element no
    match was found for.

    Matching rules, in three passes:
    0. (Applies throughout.) Collapse xtrack's own decoration: for a
       thin/thick-sliced element, several raw rows share one logical
       placement (e.g. an entry-fringe map, one or more body slices, an
       exit-fringe map all belonging to one quadrupole) -- among those,
       the smallest-`s` row is kept as that placement's representative,
       matching both codes' front-face twiss convention (confirmed
       empirically: SAD's row for a quad matches the *first* Xsuite
       slice's `s`, not the last).
    1. Exact name match, case-insensitive, against SAD's element names.
       If a name was placed more than once in the SAD lattice under that
       one exact name (so it appears several times in `sad_twiss.name`)
       and `line.replace_all_repeated_elements()` has renamed the Xsuite
       placements to ``{name}.0``, ``{name}.1``, ... in line order, the
       n-th SAD occurrence is matched to the n-th Xsuite placement (both
       sorted by `s`) -- rather than every occurrence collapsing onto one
       row.
    2. SAD's own dot-suffixed family naming: several *distinct* SAD
       elements can share a sad2xs-generated Xsuite base name -- e.g.
       same-length gap-filling drifts are all named after their length
       regardless of position, so 37 different SAD elements
       (``LXL15814.1`` .. ``LXL15814.37``) can become one shared Xsuite
       name (``lxl15814``) that `replace_all_repeated_elements()` then
       disambiguates. Unlike pass 1, this is matched by explicit index
       arithmetic, not by re-ranking by `s`: `xsuite_index = sad_index -
       allowed_index_shift`, where `sad_index`/`xsuite_index` are the
       literal digits parsed from each side's name. See
       `allowed_index_shift` below.
    3. sad2xs's solenoid-interior renaming: an element between two
       solenoids is renamed ``{name}_{neighbouring_solenoid_name}``
       (`_006_solenoid_converter.py`). The neighbouring-solenoid name isn't
       known in advance, so it's discovered from the Xsuite table itself
       (`element_type` in `{"UniformSolenoid", "VariableSolenoid"}`) rather
       than hardcoded, then tried as a suffix to strip. Last resort, tried
       only for SAD elements the first two passes left unmatched.
    Every candidate match found this way is still rejected (and the SAD
    element reported as unmatched) if its Xsuite `s` disagrees with SAD's
    by more than `s_tol` -- a defensive check against a wrong pairing
    slipping through the name-based rules above. No Xsuite row is ever
    used for more than one SAD element.

    Parameters
    ----------
    xsuite_twiss : xt.TwissTable
        A converted line's twiss result.
    sad_twiss : xt.TwissTable
        SAD's own twiss result for the same lattice (e.g. from
        `sad2xs.sad_helpers.twiss_sad`), taken as the target element grid.
    s_tol : float, optional
        Maximum allowed `abs(s_sad - s_xsuite)` for a name-based match to
        be accepted. Default 1E-9, since almost everywhere `s` is just a
        cumulative sum of element lengths and both codes should agree to
        floating-point precision. SAD's `s` is path-length, not arc-length
        along the design trajectory -- inside a region with a large orbit
        (e.g. a solenoid with significant transverse orbit, as in the real
        SuperKEKB LER/HER lattices), the physical path is longer than the
        naive sum of element `L`s, so `s` genuinely disagrees there by more
        than floating-point noise. That's a real difference to know about,
        not a matching bug -- don't paper over it with a looser default
        here. Pass an explicit, larger `s_tol` (with a comment saying why)
        only for lattices/regions you already know have this.
    allowed_index_shift : int, optional
        `sad_index - xsuite_index` for pass 2 above (SAD's own dot-suffixed
        family naming). Default 1: SAD numbers these families from 1,
        xtrack's `replace_all_repeated_elements()` from 0 -- confirmed
        empirically (`LXL15814.1` .. `LXL15814.37` in the real LER lattice
        map to `lxl15814.0` .. `lxl15814.36`). This is a workaround for
        xtrack's current fixed 0-based numbering, not a SAD convention
        worth encoding as a magic number forever -- worth raising upstream
        as a `replace_all_repeated_elements(start=...)` option; once/if
        that lands and sad2xs uses `start=1`, this should become 0.
    excluded_elements : iterable of str, optional
        SAD element names (case-insensitive) known in advance to have no
        Xsuite counterpart -- typically the same list passed as
        `excluded_elements` to `convert_sad_to_xsuite` for this lattice.
        Skipped entirely: never attempted, and never listed in
        `unmatched_sad_names`, so that list reflects genuine gaps only.

    Returns
    -------
    (xt.Table, xt.Table)
        `(xsuite_aligned, sad_aligned)`: two ordinary twiss tables, each
        the same length, holding only the matched elements in matched
        order -- so e.g. `xsuite_aligned.betx - sad_aligned.betx` is a
        direct, uninterpolated, element-by-element difference between two
        normal tables, with no NaN padding and no columns from one baked
        into the other. Each keeps its own genuine `name` column (so
        `xsuite_aligned.name` and `sad_aligned.name` can differ, e.g. for a
        solenoid-interior-renamed element -- compare them directly to see
        which rename applied). Both carry the same three extra attributes
        (not table columns, since they aren't the same length as either
        table): `unmatched_sad_names`, `unmatched_xsuite_names`, and
        `s_tol_rejections` (name-based matches rejected by the `s_tol`
        check: list of `(name, s_sad, s_xsuite)`).
    """

    ########################################
    # SAD side: target element grid, in line order
    ########################################
    sad_names               = [str(n) for n in sad_twiss.name]
    n_sad                    = len(sad_names)
    sad_s                    = np.asarray(sad_twiss.s, dtype = float)

    excluded_set    = {e.lower() for e in excluded_elements} if excluded_elements else set()

    sad_positions_by_base    = defaultdict(list)
    for i, name in enumerate(sad_names):
        if name.lower() in excluded_set:
            continue
        sad_positions_by_base[name.lower()].append(i)

    ########################################
    # Xsuite side: raw rows (drop the closing "_end_point" row, if present)
    ########################################
    xs_names_full            = [str(n) for n in xsuite_twiss.name]
    n_xs_full                = len(xs_names_full)
    xs_s_full                = np.asarray(xsuite_twiss.s, dtype = float)
    if "element_type" in xsuite_twiss.keys():
        xs_etype_full        = [str(t) for t in xsuite_twiss.element_type]
    else:
        xs_etype_full        = [None] * n_xs_full

    end     = n_xs_full
    if n_xs_full and xs_names_full[-1] == "_end_point":
        end     = n_xs_full - 1
    xs_names    = xs_names_full[:end]
    xs_s        = xs_s_full[:end]
    xs_etype    = xs_etype_full[:end]

    ########################################
    # Face row (smallest s -- the front, per both codes' twiss convention)
    # for every logical, thin/thick-sliced placed element
    ########################################
    face_row_for_placement     = {}    # collapsed (still repeat-suffixed) name -> (row idx, s)
    for i, (name, s) in enumerate(zip(xs_names, xs_s)):
        collapsed   = _collapse_slicing(name)
        prev        = face_row_for_placement.get(collapsed)
        if prev is None or s < prev[1]:
            face_row_for_placement[collapsed]  = (i, s)

    solenoid_bases  = {
        _collapse_slicing(name).lower()
        for name, etype in zip(xs_names, xs_etype)
        if etype in ("UniformSolenoid", "VariableSolenoid")}

    ########################################
    # Index placements by their repeat-stripped base name too -- but only
    # ever *consulted* as a fallback below, once a name has already failed
    # to match a SAD name directly. A real SAD element name containing a
    # literal ``.<digits>`` (common in these lattices, e.g. ``QEAP.44``)
    # must never be reinterpreted as a repeat placement just because it
    # parses like one -- it will already have an exact match, so these
    # indices are never even consulted for it.
    ########################################
    repeat_candidates_by_base  = defaultdict(list)     # base -> [(row_idx, s)]
    xs_indexed_by_base         = defaultdict(dict)     # base -> {xsuite_index: (row_idx, s)}
    for collapsed, hit in face_row_for_placement.items():
        base, index = _parse_repeat_suffix(collapsed.lower())
        if index is not None:
            repeat_candidates_by_base[base].append(hit)
            xs_indexed_by_base[base][index]    = hit

    ########################################
    # Match, in three passes; every candidate still has to pass the s_tol
    # check to be accepted, and no Xsuite row is ever used twice.
    ########################################
    matched_sad_idx     = []
    matched_xs_idx      = []
    rejected_s_tol      = []
    claimed_sad         = {
        i for i, name in enumerate(sad_names) if name.lower() in excluded_set}
    claimed_xs          = set()

    def _accept(sad_i, row_idx, s_xs):
        if abs(s_xs - sad_s[sad_i]) > s_tol:
            rejected_s_tol.append((sad_names[sad_i], sad_s[sad_i], s_xs))
            return
        matched_sad_idx.append(sad_i)
        matched_xs_idx.append(row_idx)
        claimed_sad.add(sad_i)
        claimed_xs.add(row_idx)

    def _rank_match(sad_idx_sorted_by_s, candidates):
        candidates  = sorted(
            {c for c in candidates if c[0] not in claimed_xs},
            key = lambda c: c[1])
        for rank, sad_i in enumerate(sad_idx_sorted_by_s):
            if rank >= len(candidates):
                break
            row_idx, s_xs   = candidates[rank]
            _accept(sad_i, row_idx, s_xs)

    # Pass 1: SAD's own full name. Covers singleton elements (one
    # candidate) and elements SAD itself placed more than once under one
    # shared name (several candidates, xtrack's own repeat-suffixed
    # placements of that same name) -- there's no SAD-side index to check
    # here (SAD never numbers these, it just repeats the bare name), so
    # both sides are ranked by s and paired in order.
    for base, sad_idx_list in sad_positions_by_base.items():
        # Guard against a coincidental string collision: if this SAD name
        # itself parses as a dot-suffixed family placement, and that base
        # genuinely is a sad2xs-generated Xsuite family (confirmed via
        # xs_indexed_by_base, not just string shape), a same-string "exact"
        # hit here isn't trustworthy -- SAD's own 1-based disambiguation
        # index and xtrack's independent 0-based one are unrelated
        # numbering schemes that can coincide by pure chance (e.g. SAD's
        # "LXL28467.1" string-matching xtrack's independently-assigned
        # "lxl28467.1", which is actually that family's *second*
        # placement, not its first). Defer entirely to pass 2's explicit
        # index arithmetic for these instead of risking that coincidence.
        self_base, self_index  = _parse_repeat_suffix(base)
        if self_index is not None and (
                self_base in xs_indexed_by_base
                or f"-{self_base}" in xs_indexed_by_base):
            continue

        candidates  = []
        exact_hit   = face_row_for_placement.get(base)
        if exact_hit is not None:
            candidates.append(exact_hit)
        if len(sad_idx_list) > 1 or exact_hit is None:
            candidates.extend(repeat_candidates_by_base.get(base, []))
        if candidates:
            _rank_match(sad_idx_list, candidates)

    # Pass 2: SAD's own dot-suffixed family naming (distinct SAD elements
    # that share a sad2xs-generated Xsuite base name -- e.g. same-length
    # gap-filling drifts, all called "lxl15814" regardless of position,
    # then disambiguated by xtrack's replace_all_repeated_elements).
    # sad2xs also prefixes an element with "-" when it was placed via a
    # reversed sub-line reference (`_005_line_converter.py`) -- a real,
    # separate element, not a duplicate, but sharing the same family base
    # name (confirmed empirically: a wiggler-corrector family's odd-
    # numbered SAD placements land on the plain name, even-numbered ones
    # on the "-"-prefixed name). Pool candidates from both the plain and
    # "-"-prefixed variant of a base, sorted by `s`, and index into that
    # pool by `allowed_index_shift` arithmetic on SAD's own family index --
    # explicit and checkable, like pass 1's exact case, but robust to
    # which of the two naming variants a given placement actually used.
    sad_family_groups   = defaultdict(list)    # base -> [(sad_index, sad_i)]
    for i, name in enumerate(sad_names):
        if i in claimed_sad:
            continue
        base, sad_index     = _parse_repeat_suffix(name.lower())
        if sad_index is not None:
            sad_family_groups[base].append((sad_index, i))

    for base, entries in sad_family_groups.items():
        pool    = list(repeat_candidates_by_base.get(base, []))
        pool    += repeat_candidates_by_base.get(f"-{base}", [])
        for candidate_base in (base, f"-{base}"):
            exact_hit   = face_row_for_placement.get(candidate_base)
            if exact_hit is not None:
                pool.append(exact_hit)
        if not pool:
            continue
        pool_sorted     = sorted(set(pool), key = lambda c: c[1])
        for sad_index, sad_i in entries:
            rank    = sad_index - allowed_index_shift
            if 0 <= rank < len(pool_sorted):
                row_idx, s_xs   = pool_sorted[rank]
                if row_idx not in claimed_xs:
                    _accept(sad_i, row_idx, s_xs)

    # Pass 3: sad2xs's solenoid-interior renaming
    # (`{name}_{neighbouring_solenoid_name}`, `_006_solenoid_converter.py`)
    # -- last resort, for anything still unmatched. The neighbouring-
    # solenoid name isn't known in advance, so it's discovered from the
    # Xsuite table itself (`element_type` in
    # `{"UniformSolenoid", "VariableSolenoid"}`) rather than hardcoded.
    for i, name in enumerate(sad_names):
        if i in claimed_sad:
            continue
        base    = name.lower()
        for sol_base in solenoid_bases:
            hit     = face_row_for_placement.get(f"{base}_{sol_base}")
            if hit is not None and hit[0] not in claimed_xs:
                _accept(i, hit[0], hit[1])
                break

    ########################################
    # Order matches by SAD row order; compute unmatched sets
    ########################################
    order               = np.argsort(matched_sad_idx) if matched_sad_idx else np.array([], dtype = int)
    matched_sad_idx     = np.array(matched_sad_idx, dtype = int)[order]
    matched_xs_idx      = np.array(matched_xs_idx, dtype = int)[order]

    matched_mask                    = np.zeros(n_sad, dtype = bool)
    matched_mask[matched_sad_idx]   = True
    unmatched_sad_names             = [
        sad_names[i] for i in range(n_sad)
        if not matched_mask[i] and sad_names[i].lower() not in excluded_set]

    matched_xs_idx_set              = set(matched_xs_idx.tolist())
    unmatched_xsuite_names          = [
        name for i, name in enumerate(xs_names) if i not in matched_xs_idx_set]

    logger.info(
        f"align_xsuite_twiss_with_sad_twiss: matched {len(matched_sad_idx)}/"
        f"{n_sad} SAD elements ({len(unmatched_sad_names)} unmatched, "
        f"{len(rejected_s_tol)} name-matched but rejected by s_tol={s_tol:g}); "
        f"dropped {len(unmatched_xsuite_names)}/{len(xs_names)} Xsuite-only rows.")
    if rejected_s_tol:
        logger.info(
            "s_tol rejections (name matched, s disagreed): " + ", ".join(
                f"{name} (SAD s={s_sad:.6f}, Xsuite s={s_xs:.6f})"
                for name, s_sad, s_xs in rejected_s_tol[:10])
            + (" ..." if len(rejected_s_tol) > 10 else ""))

    ########################################
    # Two ordinary, independent tables -- plain fancy indexing, no NaN
    # handling needed since only matched rows are kept in either one.
    ########################################
    sad_aligned = xt.Table({
        col: np.asarray(getattr(sad_twiss, col))[matched_sad_idx]
        for col in _row_shaped_columns(sad_twiss, n_sad)})
    xsuite_aligned  = xt.Table({
        col: np.asarray(getattr(xsuite_twiss, col))[matched_xs_idx]
        for col in _row_shaped_columns(xsuite_twiss, n_xs_full)})

    for table in (sad_aligned, xsuite_aligned):
        table.unmatched_sad_names      = unmatched_sad_names
        table.unmatched_xsuite_names   = unmatched_xsuite_names
        table.s_tol_rejections         = rejected_s_tol

    return xsuite_aligned, sad_aligned
