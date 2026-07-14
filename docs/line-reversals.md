# Line reversals and charge conventions

This document records the sign conventions, empirical verifications, and design
decisions behind the three line-transformation flags in `convert_sad_to_xsuite`:

- `reverse_element_order`
- `reverse_charge_sign`
- `reverse_survey_horizontal`

and the reference-particle `CHARGE` handling that interacts with all three.

---

## Solenoid `ks` depends on the reference particle's charge

**Corrected 2026-07-01.** An earlier version of this document claimed the opposite
of what's below — that `ks` is charge-sign-neutral and the converter should always
compute it assuming unit positive charge. That claim, and the SAD parser code that
implemented it, were based on a belief (partly reinforced by a since-fixed
lattice-string comma-parsing bug, see below) that SAD "silently ignores" non-unity
`CHARGE`. Both the belief and the code have been corrected; see
`tests/sad/README.md` and `dev/codebase_review_2026-07-01.md` for the full
investigation history.

**What's actually true, verified against real SAD:**

- SAD's own Twiss and tracking computations DO respect `CHARGE`: `CHARGE=-1`
  gives the exact sign-reversed solenoid orbit/coupling, `CHARGE=2` gives a
  different (nonlinearly scaled) effect, `CHARGE=0` gives exactly zero coupling.
  Verified via `twiss_sad` and `track_sad` in `tests/sad/test_reference_particle.py`,
  and independently via hand-written standalone SAD scripts in `dev/sad_charge/`.
- **Xsuite's own tracking does NOT auto-scale solenoid coupling by the tracked
  particle's `q0`** — verified directly: the same `ks` gives an identical `y` for
  a `q0=+1` and a `q0=-1` particle tracked through the same `UniformSolenoid`.
  This part of the original document was correct, and it's *why* the converter
  must bake the reference charge into `ks` at conversion time: Xsuite will not
  correct for it during tracking.

**Convention now implemented**: `sad2xs/converter/_004_element_converter.py`'s
`convert_solenoids` computes `brho = p0 / (q0 * e)`, using the actual reference
particle charge `environment["q0"]`, not a fixed unit-positive-charge assumption.
`ks = BZ / brho` therefore correctly flips sign for an electron reference particle
and scales for other charge magnitudes.

### Why the wrong belief seemed to hold up

Two independent things reinforced the incorrect "CHARGE is ignored" belief before
this was corrected:

1. **A lattice-string comma bug.** SAD's LALR parser silently drops parameters
   after a comma inside an element's `(...)` list (e.g. `SOL S1 = (BZ=3.0, BOUND=1,
   GEO=1, DX=0.001)` silently loses `BOUND`, `GEO`, and `DX`), with no non-zero exit
   code. Both this project's own test lattices and the hand-written exploration
   scripts in `dev/sad_charge/` originally used commas, and the resulting broken
   solenoid definitions had no reference-frame setup at all, making CHARGE=-1 and
   CHARGE=+1 spuriously give identical (both-broken) results. Fixed throughout
   `tests/sad/` — see that folder's README for the full comma-bug writeup.
2. **A real, but separate, historical fact.** K. Oide (SAD author, confirmed
   2026-07-01) noted that real-world SAD lattice files — e.g. the SuperKEKB HER
   lattice, which is an electron ring — do not actually declare `CHARGE = -1;`,
   for historical reasons; they're written as if positron rings regardless of true
   species. That's a **lattice-authoring convention** problem, not a claim that
   SAD's computation engine ignores `CHARGE` when it *is* present. Both things are
   true simultaneously, which is why `reverse_charge_sign` remains useful (see
   below) even though the parser now reads `CHARGE` directly.

---

## `reverse_element_order`

### What it does

Reverses the sequence of elements so that the beam passes through the lattice
in the opposite direction.  Mirrors `LINE TESTREV = (-TEST)` in SAD.

Post-reversal, three categories of element require parameter adjustments to
maintain physically correct tracking:

### 1. Bend poleface angles

When the beam direction is reversed, the entry and exit polefaces swap.
The `edge_entry_angle` and `edge_exit_angle` of every `Bend` are exchanged.

**Verified**: a SAD lattice with `E1=0.05`, `E2=0.00` (asymmetric poleface) was
tracked through `LINE TESTREV = (-TEST)` in SAD and through the sad2xs-reversed
Xsuite line.  Both give identical final `y` and `py`.

### 2. Bend fringe fields (fint/hgap)

The soft-edge fringe fields imported from SAD's `F1`/`FB1`/`FB2` (see
`docs/sad-behaviour.md`'s `BEND` `F1`/`FRINGE` section) are entry/exit-face
quantities exactly like the poleface angles above: `edge_entry_fint`/
`edge_entry_hgap` and `edge_exit_fint`/`edge_exit_hgap` are exchanged
alongside `edge_entry_angle`/`edge_exit_angle` in the same per-bend loop,
so both whole-line-mirror and individual `-elementname` reversal are
covered uniformly.

**Verified**: a K0-only corrector with asymmetric fringe (`FB1=0.08`,
`FB2=0.01`) was tracked through `LINE TESTREV = (-TEST)` in SAD and through
the sad2xs-reversed Xsuite line (with `_import_sad_bend_fringes=True`).
Both give matching final `y` and `py` to within the fringe import's
existing on-momentum tolerance.

### 3. Solenoid ks sign

Reversing the element order means the beam traverses the solenoid field in the
opposite longitudinal direction.  The axial field now acts as if `BZ` has
changed sign, so `ks` must be negated for each solenoid — **in addition to**,
not instead of, the charge-dependent base value described above. These two
effects compose by simple negation of whatever `ks` the solenoid already has
(the charge-adjusted base value), so no special-casing is needed in the code.

**Verified**: a BOUND solenoid with `DX = 0.001 GEO = 1` (requiring
`rebuild_sad_lattice` to bake in GEO reference shifts) was tracked through
`LINE TESTREV = (-TEST)` in SAD and through the sad2xs-reversed Xsuite line.
Both give identical final `y` and `py`.  The negation of `ks` in
`reverse_line_element_order` is correct.

**Composability with a genuine non-unity CHARGE, verified against real SAD**:
`test_pipeline_reverse_element_order_solenoid_physics_matches_sad_with_charge_minus_one`
in `tests/conversion/pipeline/test_reverse_element_order.py` repeats the above
check with `CHARGE = -1;` added to the same lattice, confirming the two `ks`
negations (charge-dependent base value, then direction-reversal) compose
correctly — Xsuite-reversed `y`/`py` match real SAD's own `-LINE` reversal of the
same electron lattice to `1e-9`. This test also caught a third bug in the
process: `rebuild_sad_lattice` was silently dropping `MASS`/`CHARGE` when
regenerating the lattice file (only `MOMENTUM`/`FSHIFT` were written back out),
which would have silently reset the reference species for any bound-solenoid
(GEO) lattice with non-unity `CHARGE`. Fixed in
`sad2xs/sad_helpers/rebuild_lattice.py`.

### 4. Translations: solenoid GEO vs COORD

There are two distinct origins for `Translation` elements in the converter:

**Solenoid GEO translations** (element names ending in `_dxy`, e.g.
`sol_in_dxy`, `sol_out_dxy`): created by the solenoid converter to represent
reference-frame entry/exit offsets computed by SAD's GEO mechanism.  When
element order is reversed, `SOL_OUT` becomes the new entry and `SOL_IN` the
new exit, so both shifts must be negated.

**Standalone COORD translations** (any name without the `_dxy` suffix):
represent a beampipe offset at a specific location.  This is a geometric
property of the beampipe that does not change sign when the beam direction
reverses.  SAD's `LINE TESTREV = (-TEST)` gives identical `x` displacement
to the forward line for a `COORD(DX=d)` element — no negation is applied.

**Implementation**: `reverse_line_element_order` negates `shift_x` / `shift_y`
only if the element name ends in `_dxy`.  Standalone COORD translations are
left unchanged.

**Verified empirically**:

| Scenario | SAD forward x | SAD reversed x | Notes |
|---|---|---|---|
| `COORD(DX=0.001)` forward | −0.001 | −0.001 | Same — beampipe offset is invariant |
| `COORD(DX=0.001)` reversed Xsuite | − | −0.001 | Matches SAD reversed ✓ |

### 5. Solenoid GEO reference-transform rotation order

A bound GEO solenoid region is defined by a pair of `SOL` elements (e.g.
`SOL_IN`, `SOL_OUT`), one of which carries `GEO=1` (the reference-frame-defining
boundary) while the other carries the compensating `DX`/`DY`/`DZ`/`CHI1`/`CHI2`
that SAD's `REBUILD` computes to restore the design orbit. Either member of the
pair can independently be written reversed (`-SOL_IN` or `-SOL_OUT`) in the
`LINE` statement — this is unrelated to which one carries `GEO=1`.

Each boundary converts to a compound sub-line: `<name>_bound` (the solenoid
field), `<name>_dxy` (`Translation`), `<name>_dz` (`TimeDelay`), `<name>_rot`
(`Rotation`). `xt.Rotation`'s effect on `zeta` is proportional to the transverse
position (`x`/`y`) present when it runs. The inbound boundary's compound always
runs rotation first (at `x=y=0`, so it never picks up this term). The outbound
boundary's compound needs a different order depending on whether the pair's
reversal state matches: when `inbound_reversed == outbound_reversed`, the
existing `bound/dxy/dz/rot` order is correct; when they differ (exactly one end
of the pair reversed), the outbound rotation must also run first, otherwise it
runs after a transverse offset has already accumulated and picks up a spurious
`zeta` contribution.

**Bug (fixed)**: `solenoid_reference_shift_corrections` in
`sad2xs/converter/_006_solenoid_converter.py` used the `bound/dxy/dz/rot` order
for every outbound boundary unconditionally, regardless of the pair's reversal
state. This gave `x`/`y`/`px`/`py` that matched SAD exactly (translations and
rotations don't depend on `zeta`, so the bug was invisible there), but a `zeta`
that diverged from SAD's whenever the pair's reversal state didn't match —
found via `test_sol.py`'s `test_sol_reference_transform_restores_design_orbit_at_end`
once its comparison was extended to include `zeta`.

**Fix**: the outbound solenoid lists are now split by
`inbound_reversed == outbound_reversed`; the matching subset keeps the existing
order, the differing subset uses rotation-first, same as the inbound boundary.

**Verified**: across a full grid of line orientation (`forward`/`-SOL_IN`
reversed/`-SOL_OUT` reversed/both reversed) × which boundary carries `GEO=1` ×
transform (pure rotation, pure translation, combined and deliberately
asymmetric DX/DY/DPX/DPY values), Xsuite's `zeta` at the region exit now
matches SAD's own Twiss `zeta` exactly, with `x`/`y` unaffected in every case.

---

## `reverse_charge_sign`

### What it does

Changes `q0` on the Xsuite reference particle from +1 to −1 (or vice versa),
and nothing else. It does **not** change any element parameter — in
particular, solenoid `ks` is unaffected. Tracking and Twiss results are
therefore **identical** before and after `reverse_charge_sign=True`.

**Model**: `reverse_charge_sign` means "this lattice's field values were
designed assuming the opposite species from what's nominally declared" — for
example, a real-world historical lattice file that doesn't declare
`CHARGE=-1` even though it represents an electron ring (SuperKEKB HER is the
motivating example). The field values in the file already encode that
design assumption, so the field→strength conversion (solenoid `Bz→ks` via
`brho`) must always use the imported/as-declared charge — never a
`reverse_charge_sign`-corrected one. Only the final reference particle's
charge label changes.

**Verified**:
`test_pipeline_reverse_charge_sign_does_not_change_solenoid_ks` in
`tests/conversion/pipeline/test_reverse_charge_sign.py`.

### Interaction with `CHARGE` in the SAD file

A genuinely-declared `CHARGE` in the SAD file is a separate, legitimate
input: since that IS the imported charge, it correctly affects `ks` via
`brho` (see `tests/conversion/pipeline/test_reverse_element_order.py` for
this verified against real SAD). `reverse_charge_sign` and a declared
`CHARGE` are fully **independent** — `reverse_charge_sign` never feeds into
`ks`, regardless of what the file's own `CHARGE` already is. See
`test_pipeline_declared_charge_and_reverse_charge_sign_are_independent` in
the same test file.

### When to use it

Use `reverse_charge_sign=True` to relabel the reference particle's species
when you know a lattice file's stated (or defaulted) `CHARGE` is wrong for
how it's actually meant to be used, without changing any converted element.

### What it does NOT do

- It does **not** model "put a genuinely different charge particle through
  the same physical magnets" — that scenario is what a real, declared
  `CHARGE` difference in the file represents (see above), and it correctly
  does change `ks`. `reverse_charge_sign` is a different, narrower
  correction: relabelling the reference particle only.
- It is **not** the same as `reverse_survey_horizontal`.

---

## `reverse_survey_horizontal`

### What it does

Applies a horizontal mirror to the full lattice geometry.  This models the
same physical tunnel traversed from the other end, or equivalently, a ring
where the bending plane sense is reversed.

"Horizontal" here means the bend plane (x-plane).  All element parameters
are transformed to be consistent with a lattice mirrored in the x-z plane.

### Parameter transformations applied

| Element | Parameters changed |
|---|---|
| Bend | `angle`, `k0` negate; `edge_entry_angle`, `edge_exit_angle` both negate; even-order `knl` negate, odd-order `ksl` negate; `shift_x` negates, `rot_s_rad` negates |
| Quadrupole | `k1s` negates; knl/ksl parity pattern; `shift_x` negates, `rot_s_rad` negates |
| Sextupole | `k2` negates; knl/ksl parity pattern; offsets negate |
| Octupole | `k3s` negates; knl/ksl parity pattern; offsets negate |
| Multipole | knl/ksl parity pattern; offsets negate |
| Solenoid | `ks` negates (on top of the charge-dependent base value, same composition as `reverse_element_order` above); knl/ksl parity; offsets negate |
| Translation | `shift_x` negates, `shift_y` unchanged |
| Rotation | `rot_y_rad` negates, `rot_s_rad` negates, `rot_x_rad` unchanged |

### Twiss invariance

Verified: 4D Twiss `betx` and `bety` are identical before and after
`reverse_survey_horizontal=True` for a lattice containing BEND + QUAD + SEXT +
DRIFT.  The k0/k2 sign changes cancel in the optics; k1 is unchanged.

### Independence from `reverse_charge_sign`

`reverse_survey_horizontal` and `reverse_charge_sign` are fully independent flags.
They address different physical questions and can be combined freely.

### Composability with a genuine non-unity CHARGE — internal consistency only

`test_pipeline_reverse_survey_horizontal_negates_solenoid_ks_with_charge_minus_one`
in `tests/conversion/pipeline/test_reverse_survey_horizontal.py` confirms the two
`ks` negations (charge-dependent base value, then geometric-mirror) compose
arithmetically in the converter code. **This is not verified against real SAD** —
unlike `reverse_element_order`, this file has no real-SAD-verified test at all for
any element, since `reverse_survey_horizontal` is a whole-lattice geometric mirror
with no single native SAD operator to run for comparison (unlike `-LINE` for
element-order reversal). Closing this gap would mean hand-constructing an
equivalent mirrored SAD lattice file rather than reusing an existing SAD command —
noted as a known open item, not resolved here.

---

## SAD empirical verifications

The following SAD behaviours were verified by running lattices through the SAD
executable and inspecting output, to confirm assumptions used in the converter:

| Claim | Verification |
|---|---|
| `LINE TESTREV = (-TEST)` syntax accepted | `sad_accepts` test in `tests/sad/test_line_reversal.py` |
| Asymmetric bend fringe (FB1 != FB2) reversal matches SAD reversed line | `test_pipeline_reverse_element_order_corrector_fringe_physics_matches_sad` in `tests/conversion/pipeline/test_reverse_element_order.py` |
| Reversed SAD line gives different element order | Two correctors C1/C2 with different K0: reversed line gives different final x |
| COORD(DX=d) gives same x in forward and reversed SAD line | Tracked both; final x matches to < 1e-12 |
| Solenoid GEO shifts must be baked in before conversion | `rebuild_sad_lattice` required; without it, GEO offsets are zero in converter |
| Asymmetric bend poleface reversal matches SAD reversed line | y/py match after element-order reversal |
| BEND ANGLE sign negates under `-LINE` reversal | `test_reversed_line_bend_angle_sign_matches_converter_assumption` in `tests/sad/test_line_reversal.py` — sign/magnitude confirmed; small linear-in-angle residual found and tolerance-covered, cause not identified |
| QUAD K1 unchanged under `-LINE` reversal | `test_reversed_line_quad_k1_sign_matches_converter_assumption` — confirmed exactly |
| SOL BZ negates and GEO swaps ends under `-LINE` reversal | `test_reversed_line_solenoid_ks_sign_matches_converter_assumption` — confirmed exactly |
| CHARGE=-1 gives sign-reversed solenoid coupling (not "ignored") | `tests/sad/test_reference_particle.py` (twiss_sad and track_sad) and `dev/sad_charge/*.sad` (standalone, hand-written scripts, independently confirming the same sign flip) |

---

## Summary table

| Flag | Changes q0 | Changes ks | Changes k0/k1 | Changes element order |
|---|---|---|---|---|
| `reverse_element_order` | No | Yes (negate, composes with charge-dependent base) | No | Yes (mirror) |
| `reverse_charge_sign` | Yes | Yes (negate, since ks depends on q0) | No | No |
| `reverse_survey_horizontal` | No | Yes (negate, composes with charge-dependent base) | Partial (see table) | No |
