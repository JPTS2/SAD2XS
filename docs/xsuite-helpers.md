# Xsuite helpers

The `sad2xs.xsuite_helpers` package contains Python utilities that operate
purely on an `xt.Line` — no SAD, no lattice file, no sad2xs conversion
involved. They exist because some accelerating-line bookkeeping that Xsuite
does not do automatically is still needed once a line has been converted (or
built directly) with real accelerating cavities in it.

Unlike `sad2xs.sad_helpers`, this package has no extra dependencies —
`xtrack` and `numpy` are already required by core sad2xs — so it is imported
eagerly as part of `import sad2xs`, not lazily.

## Public helper functions

- `install_reference_energy_updates`: insert one `ReferenceEnergyIncrease` +
  `TimeDelay` pair immediately after every logical cavity in a line.
- `update_reference_energy_updates`: track a copy of the line's reference
  particle and configure the installed pairs so it has `delta=zeta=0`
  immediately after every cavity.

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

## Current limitations

- Relies on `line.tracker` (public) but also on `line._context` for
  building the pilot particle copy, since `xt.Line` has no public accessor
  for its compute context. An accepted, documented dependency on Xsuite
  internals, not a bug.
- Not upstreamed into `xtrack` itself — checked with the Xtrack lead
  developer, who does not plan to add this there for now. Revisit if that
  changes.
