# Line reversals and charge conventions

This document records the sign conventions, empirical verifications, and design
decisions behind the three line-transformation flags in `convert_sad_to_xsuite`:

- `reverse_element_order`
- `reverse_charge_sign`
- `reverse_survey_horizontal`

---

## Xsuite element parameters are charge-sign-neutral

A fundamental property of Xsuite (confirmed empirically) is that element
parameters do not depend on the sign of the reference particle charge q0.
The same `k1` focuses equally for electrons (q0=−1) and positrons (q0=+1).
The same `ks` produces the same coupling strength for both species.

This is a deliberate API choice in Xsuite: the physics encoded in a parameter
is the **effect on the beam**, not the raw field.

### Consequence for the converter

Because Xsuite parameters are charge-sign-neutral, the converter should also
produce charge-sign-neutral parameters wherever possible.  The only SAD input
that naively introduces a charge dependence is the solenoid field `BZ` [T],
which must be normalised to `ks = BZ / Bρ`.

**Convention adopted**: the converter always uses `Bρ = p0 / e` (unit positive
charge) when computing `ks`, regardless of the reference particle q0.  This
means:

- `ks` is charge-sign-neutral, consistent with `k0`, `k1`, `k1s`, etc.
- `reverse_charge_sign=True` does **not** change `ks`.

Without this convention, `reverse_charge_sign=True` would invert `ks` while leaving
`k1s` (skew quadrupoles) unchanged, breaking any coupling-compensation scheme
where skew quads are tuned against the solenoid.

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

### 2. Solenoid ks sign

Reversing the element order means the beam traverses the solenoid field in the
opposite longitudinal direction.  The axial field now acts as if `BZ` has
changed sign, so `ks` must be negated for each solenoid.

**Verified**: a BOUND solenoid with `DX = 0.001 GEO = 1` (requiring
`rebuild_sad_lattice` to bake in GEO reference shifts) was tracked through
`LINE TESTREV = (-TEST)` in SAD and through the sad2xs-reversed Xsuite line.
Both give identical final `y` and `py`.  The negation of `ks` in
`reverse_line_element_order` is correct.

### 3. Translations: solenoid GEO vs COORD

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

---

## `reverse_charge_sign`

### What it does

Changes `q0` on the Xsuite reference particle from +1 to −1 (or vice versa).

**Element parameters are not changed.**  Specifically, `ks` is not changed
(see the charge-sign-neutral convention above).  This means tracking and Twiss
results are **identical** before and after `reverse_charge_sign=True`.

### When to use it

Use `reverse_charge_sign=True` to relabel the reference particle species without
affecting physics — for example, to set q0=−1 on a lattice that was designed
and converted assuming q0=+1.  This can matter for radiation integral
calculations or output file species labelling, but does not affect element
focusing, coupling, or orbit.

### What it does NOT do

- It does **not** invert `ks`.
- It does **not** model "run the opposite species through the same physical
  magnets" (that would require also inverting all skew-quad corrections, which
  is not done).
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
| Solenoid | `ks` negates; knl/ksl parity; offsets negate |
| Translation | `shift_x` negates, `shift_y` unchanged |
| Rotation | `rot_y_rad` negates, `rot_s_rad` negates, `rot_x_rad` unchanged |

### Twiss invariance

Verified: 4D Twiss `betx` and `bety` are identical before and after
`reverse_survey_horizontal=True` for a lattice containing BEND + QUAD + SEXT +
DRIFT.  The k0/k2 sign changes cancel in the optics; k1 is unchanged.

### Independence from `reverse_charge_sign`

`reverse_survey_horizontal` and `reverse_charge_sign` are fully independent flags.
They address different physical questions and can be combined freely.

---

## SAD empirical verifications

The following SAD behaviours were verified by running lattices through the SAD
executable and inspecting output, to confirm assumptions used in the converter:

| Claim | Verification |
|---|---|
| `LINE TESTREV = (-TEST)` syntax accepted | `sad_accepts` test in `tests/sad/test_line_reversal.py` |
| Reversed SAD line gives different element order | Two correctors C1/C2 with different K0: reversed line gives different final x |
| COORD(DX=d) gives same x in forward and reversed SAD line | Tracked both; final x matches to < 1e-12 |
| Solenoid GEO shifts must be baked in before conversion | `rebuild_sad_lattice` required; without it, GEO offsets are zero in converter |
| Asymmetric bend poleface reversal matches SAD reversed line | y/py match after element-order reversal |

---

## Summary table

| Flag | Changes q0 | Changes ks | Changes k0/k1 | Changes element order |
|---|---|---|---|---|
| `reverse_element_order` | No | Yes (negate) | No | Yes (mirror) |
| `reverse_charge_sign` | Yes | No | No | No |
| `reverse_survey_horizontal` | No | Yes (negate) | Partial (see table) | No |
