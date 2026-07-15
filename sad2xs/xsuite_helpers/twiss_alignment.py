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

logger  = logging.getLogger(__name__)

_REPEAT_SUFFIX_RE  = re.compile(r"^(.*)\.(\d+)$")

################################################################################
# Name helpers
################################################################################
def _collapse_slicing(name: str) -> str:
    """
    Strip xtrack's ``::N`` table-disambiguation and ``..N``/``..entry_map``
    slicing suffixes, leaving the name of the placed element a row belongs to.
    """
    return name.split("::")[0].split("..")[0]

def _parse_repeat_suffix(name_lower: str):
    """
    Undo `line.replace_all_repeated_elements()`'s ``{name}.{i}`` renaming ->
    (base, i), or (name_lower, None) if it doesn't match.
    """
    m   = _REPEAT_SUFFIX_RE.match(name_lower)
    if m is None:
        return name_lower, None
    return m.group(1), int(m.group(2))

################################################################################
# Align an Xsuite twiss table onto a SAD twiss table's element grid
################################################################################
def align_xsuite_twiss_with_sad_twiss(
        xsuite_twiss, sad_twiss, *,
        s_tol: float = 1E-9):
    """
    Match every SAD element to its unique Xsuite row and return
    `(xsuite_aligned, sad_twiss)`: `xsuite_aligned` cut to just the matched
    rows, in `sad_twiss`'s own row order; `sad_twiss` is returned unchanged.
    No interpolation -- an Xsuite row sad2xs generated with no single-element
    SAD counterpart (solenoid geometry pieces, RF-interleaved slices, offset
    markers, gap-filling drifts, ...) is dropped rather than guessed at.
    Every SAD element must find a match (see Raises) -- filter known-
    unconvertable elements out of `sad_twiss` before calling.

    Matched by name in four passes, each only tried for elements still
    unmatched, and always checked against `s_tol` before being accepted:
    1. SAD's exact name, ranked by `s` if placed more than once.
    2. SAD's dot-suffixed family name (distinct SAD elements sharing a
       sad2xs-generated Xsuite base name, e.g. same-length gap-filling
       drifts), ranked by `s`, pooling the plain and "-"-prefixed
       (reversed-sub-line) variant of the Xsuite name.
    3. sad2xs's solenoid-interior rename: `{name}_{neighbouring_solenoid}`.
    4. sad2xs's solenoid-boundary compound: `{name}_bound`.

    Parameters
    ----------
    xsuite_twiss : xt.TwissTable
        A converted line's twiss result.
    sad_twiss : xt.TwissTable
        SAD's own twiss result for the same lattice, taken as the target
        element grid.
    s_tol : float, optional
        Max `abs(s_sad - s_xsuite)` for a match to be accepted. Default
        1E-9 (floating-point noise) -- SAD's `s` is path length, so it can
        genuinely differ from Xsuite's by more than that inside a large-
        orbit region (e.g. a solenoid); pass a looser `s_tol` there.

    Returns
    -------
    (xt.Table, xt.Table)
        `(xsuite_aligned, sad_twiss)`, same length -- `xsuite_aligned.betx -
        sad_twiss.betx` is a direct element-by-element comparison.

    Raises
    ------
    AssertionError
        If any SAD element found no Xsuite match.
    """

    ########################################
    # SAD side: target element grid
    ########################################
    sad_names   = [str(n) for n in sad_twiss.name]
    n_sad       = len(sad_names)
    sad_s       = np.asarray(sad_twiss.s, dtype = float)

    sad_positions_by_base  = defaultdict(list)
    for i, name in enumerate(sad_names):
        sad_positions_by_base[name.lower()].append(i)

    ########################################
    # Xsuite side (drop the trailing "_end_point" row, if present)
    ########################################
    xs_names    = [str(n) for n in xsuite_twiss.name]
    xs_s        = np.asarray(xsuite_twiss.s, dtype = float)
    xs_etype    = (
        [str(t) for t in xsuite_twiss.element_type]
        if "element_type" in xsuite_twiss.keys() else [None] * len(xs_names))
    if xs_names and xs_names[-1] == "_end_point":
        xs_names, xs_s, xs_etype   = xs_names[:-1], xs_s[:-1], xs_etype[:-1]

    ########################################
    # Face row per placement: smallest s, or the explicit {name}_entry
    # marker slice_thick_elements() wraps every sliced element with, which
    # is guaranteed to be the true front face even if an entry edge/fringe
    # map ties it on s.
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

    solenoid_bases  = {
        _collapse_slicing(name).lower()
        for name, etype in zip(xs_names, xs_etype)
        if etype in ("UniformSolenoid", "VariableSolenoid")}

    # Repeat-suffixed placements, indexed by their stripped base -- only
    # consulted once a name has failed an exact match, so a real SAD name
    # containing a literal ".<digits>" (e.g. "QEAP.44") is never mistaken
    # for one of these.
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

    ########################################
    # Pass 1: SAD's exact name
    ########################################
    for base, sad_idx_list in sad_positions_by_base.items():
        # A name that itself parses as a family placement (e.g. SAD's own
        # "LXL28467.1") can coincidentally string-match an unrelated
        # xtrack-numbered placement -- defer those entirely to pass 2.
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
    # Pass 3: solenoid-interior rename ({name}_{neighbouring_solenoid})
    ########################################
    for i, name in enumerate(sad_names):
        if i in claimed_sad:
            continue
        for sol_base in solenoid_bases:
            hit     = face_row_for_placement.get(f"{name.lower()}_{sol_base}")
            if hit is not None and hit[0] not in claimed_xs:
                _accept(i, hit[0], hit[1])
                break

    ########################################
    # Pass 4: solenoid-boundary compound ({name}_bound)
    ########################################
    for i, name in enumerate(sad_names):
        if i in claimed_sad:
            continue
        hit     = face_row_for_placement.get(f"{name.lower()}_bound")
        if hit is not None and hit[0] not in claimed_xs:
            _accept(i, hit[0], hit[1])

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
                f"{name} (SAD s={s_sad:.6f}, Xsuite s={s_xs:.6f})"
                for name, s_sad, s_xs in rejected_s_tol[:10])
            + (" ..." if len(rejected_s_tol) > 10 else ""))

    assert not unmatched_sad_names, (
        f"{len(unmatched_sad_names)} SAD element(s) had no Xsuite match: "
        f"{unmatched_sad_names[:20]}"
        + (" ..." if len(unmatched_sad_names) > 20 else ""))

    return xsuite_twiss.rows[matched_xs_idx], sad_twiss
