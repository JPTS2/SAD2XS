# Xsuite helpers

The `sad2xs.xsuite_helpers` package contains Python utilities that operate
purely on an `xt.Line` — no SAD, no lattice file, no sad2xs conversion
involved. They exist because some accelerating-line bookkeeping that Xsuite
does not do automatically is still needed once a line has been converted (or
built directly) with real accelerating cavities in it.

Unlike `sad2xs.sad_helpers`, this package has no extra dependencies —
`xtrack` and `numpy` are already required by core sad2xs — so it is imported
eagerly as part of `import sad2xs`, not lazily. The one exception is
`plot_xsuite_sad_comparison`, which lazily imports `matplotlib` inside the
function body — install it with the `plotting` extra
(`pip install sad2xs[plotting]`) to use it; the rest of the package needs
nothing extra.

## Public helper functions

- `install_reference_energy_updates`: insert one `ReferenceEnergyIncrease` +
  `TimeDelay` pair immediately after every logical cavity in a line.
- `update_reference_energy_updates`: track a copy of the line's reference
  particle and configure the installed pairs so it has `delta=zeta=0`
  immediately after every cavity.
- `align_xsuite_twiss_with_sad_twiss`: match a converted line's twiss table
  onto SAD's own twiss table, element by element, by name and `s`.
- `plot_xsuite_sad_comparison`: overlay (and optionally difference) plots of
  an aligned Xsuite/SAD twiss pair.
- `assert_xsuite_matches_sad_twiss`: assert an aligned Xsuite/SAD twiss pair
  agrees within per-column tolerance.
- `check_symplecticity`: check a line's one-turn R matrix is symplectic,
  falling back to an element-by-element check if it isn't.

## Why this exists

Xsuite does not automatically carry the reference momentum along an
accelerating line: a line whose cavities impart a real energy gain still
reports the same `p0c` everywhere unless the reference is updated explicitly
at each cavity. This matters for any line with a genuine net energy gain
along its length (for example a LINAC-style lattice converted with sad2xs),
where tracking or Twiss around a fixed reference momentum no longer
describes the beam correctly downstream of the first cavity.

## Typical use from Python

```python
from sad2xs.xsuite_helpers import (
    install_reference_energy_updates,
    update_reference_energy_updates)

install_reference_energy_updates(line)
update_reference_energy_updates(line)
```

Call `update_reference_energy_updates` again after changing any cavity's
voltage, phase, or frequency, or the line upstream of an installed cavity —
it recomputes every installed pair from scratch in lattice order.

## Prerequisites

- Every cavity must be its own independent element. A cavity placed more
  than once from one shared definition cannot be used as a placement
  anchor. Call `line.replace_all_repeated_elements()` *before* slicing any
  thick cavities — resolving repeats after slicing does not work, since
  slicing gives each slice a uniquely-numbered name that is no longer
  grouped by placement. `install_reference_energy_updates` raises a clear
  error naming the offending cavity for both orderings, rather than either
  failing inside `line.insert` or silently collapsing two cavities into
  one.
- Cavities using `absolute_time=True` are not currently supported —
  `install_reference_energy_updates` raises `NotImplementedError`.
- The line's entrance particle (`line.particle_ref`, or the `particle`
  passed to `update_reference_energy_updates`) must already be at
  `delta=zeta=0` when `verify=True` (the default) — the whole scheme assumes
  the line starts on the reference trajectory.

## What counts as a cavity

`install_reference_energy_updates` recognises an element as a logical
cavity from the line's table `element_type`: `Cavity`, or one of the slice
types Xsuite produces when tracking or slicing a thick `xt.Cavity`
(`ThinSliceCavity`, `ThickSliceCavity`, `DriftSliceCavity`, confirmed
empirically against real Xsuite output). A sliced thick cavity contributes
several table rows for one logical cavity; these are collapsed into a
single update pair anchored at the cavity's exit marker. Any other element
type is not treated as a cavity.

## Reference energy: current limitations

- Relies on `line.tracker` (public) but also on `line._context` for
  building the pilot particle copy, since `xt.Line` has no public accessor
  for its compute context. An accepted, documented dependency on Xsuite
  internals, not a bug.
- Not upstreamed into `xtrack` itself — checked with the Xtrack lead
  developer, who does not plan to add this there for now. Revisit if that
  changes.

## SAD-vs-Xsuite comparison

`align_xsuite_twiss_with_sad_twiss`, `plot_xsuite_sad_comparison`,
`assert_xsuite_matches_sad_twiss`, and `check_symplecticity` are the
standard toolkit for comparing a converted line against SAD's own twiss.

```python
tw_xs   = line.twiss4d()
tw_sad  = sad2xs.sad_helpers.twiss_sad(...)

# Filter out any SAD element known to have no Xsuite counterpart first --
# align_xsuite_twiss_with_sad_twiss requires every remaining SAD element to
# find a match.
tw_sad  = tw_sad.rows[mask]

tw_xs_aligned, tw_sad_aligned = align_xsuite_twiss_with_sad_twiss(tw_xs, tw_sad)

assert_xsuite_matches_sad_twiss(tw_xs_aligned, tw_sad_aligned)
plot_xsuite_sad_comparison(tw_xs_aligned, tw_sad_aligned)
```

`align_xsuite_twiss_with_sad_twiss` does not interpolate: it matches each
SAD element to the one Xsuite row that is unambiguously the same physical
element (undoing xtrack's own slicing/repeat-naming and sad2xs's generated
naming), and raises if any SAD element found no match.

### Matching passes

Tried in order, each only for elements still unmatched, always checked
against `s_tol` before being accepted:

1. **SAD's exact name**, ranked by `s` if placed more than once.
2. **SAD's dot-suffixed family name** (distinct SAD elements sharing a
   sad2xs-generated Xsuite base name, e.g. same-length gap-filling drifts),
   ranked by `s`, pooling the plain and `-`-prefixed (reversed-sub-line)
   variant of the Xsuite name.
3. **sad2xs's solenoid-interior rename**, `{name}_{neighbouring_solenoid}`
   (or `{base}_{neighbouring_solenoid}` for a family placement), pooled
   across every neighbouring solenoid and ranked by `s` like pass 2 — the
   neighbour's name isn't known in advance, so candidates come from a
   string-prefix search over Xsuite's own names.

A SAD name that itself looks like a repeat (`base.N`, e.g. `LXL28467.1`)
skips pass 1 entirely when Xsuite also has a family under that base, since
it could otherwise coincidentally string-match an unrelated xtrack repeat.

### Solenoid-boundary compound

One SAD solenoid-boundary element becomes 4 Xsuite placements
(`_004_element_converter.py`): `{name}_bound` (the only one that can carry
real field/kick physics) plus 3 pure reference-frame transforms. Which one
is placed *first* — the true front face — depends on whether the solenoid
is being entered or exited (`_006_solenoid_converter.py`), so it isn't
always `_bound`; `_collapse_slicing` folds all 4 back into one logical
placement and lets row order, not the suffix name, decide the face.

### `compute_s_sad` derivation

SAD's `s` is real path length; Xsuite's is nominal/design length. The two
genuinely diverge right where a solenoid-boundary compound's TimeDelay
piece applies its artificial reference-frame `shift_zeta` — that jump in
`zeta` is bookkeeping for a real geometric `dz` offset SAD's own `s`
already includes, so it's added back into `s` (confirmed by sign against
real SAD `s`: the opposite sign roughly *doubles* the raw discrepancy
instead of cancelling it). Only that specific, named jump is removed —
`zeta`'s natural evolution everywhere else (e.g. a wiggler/corrector
genuinely traversing off the design orbit) is real physics that SAD's own
`s` does *not* subtract (confirmed empirically), which is why the
correction is gated to right after a TimeDelay by name, rather than
applying `s = s - dzeta` at every step.

For coupled (Edwards-Teng) optics, pass `xsuite_column_overrides` to both
`plot_xsuite_sad_comparison` and `assert_xsuite_matches_sad_twiss`, e.g.
`{"betx": "betx_edw_teng", "bety": "bety_edw_teng", "alfx": "alfx_edw_teng",
"alfy": "alfy_edw_teng"}`, computed with `line.twiss4d(coupling_edw_teng=True)`.

`plot_xsuite_sad_comparison` draws Xsuite's own element-type ribbon (the
same background bars `xt.TwissTable.plot()` draws, reused as-is via
`lattice_only=True`) behind each overlay row by default
(`show_lattice=True`), built from `xsuite_aligned` — no extra data needed.
`groups` selects which quantity groups to draw (default: all of
`AVAILABLE_GROUPS`); `ele_start`/`ele_stop` narrow both tables (and the
ribbon) to one element range by name, so the same function serves a
full-ring overview and an IP close-up:

```python
plot_xsuite_sad_comparison(
    tw_xs_aligned, tw_sad_aligned,
    groups      = ["orbit_xy", "orbit_pxpy"],
    ele_start   = "qf1.l4",
    ele_stop    = "qf1.r4")
```
