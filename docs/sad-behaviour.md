# SAD behaviour notes

This file catalogues empirically-established facts about how SAD itself
behaves — physics conventions, quirks, and limitations discovered while
building and testing the converter. These are not SAD2XS design choices;
they are what SAD does, verified against the real SAD binary (or, for the
Xsuite side, against an independent computation), not assumed from
documentation. Where a fact here led to a SAD2XS decision (a converter
warning, a config default, an accepted test limitation), the decision
itself and its reasoning live in `docs/design-decisions.md`, which points
back here for the underlying evidence.

## Solenoid fringe kick (`DISFRIN`)

SAD's solenoid Hamiltonian includes a nonlinear, hard-edge fringe kick,
distinct from the solenoid's main linear field, controlled by SAD's
`DISFRIN` parameter (default `0` applies the kick, `1` disables it):

```
H = -Bz / (8 p^2 B*rho) * p_phi * p_r
p_phi = x*py - y*px
p_r   = x*px + y*py
```

`p_phi` and `p_r` are each quadratic in phase space, so `H` is quartic — a
genuine nonlinear ("octupolar") term, not a linear edge effect or a
finite-length ramp. Neither `xt.UniformSolenoid` nor `xt.VariableSolenoid`
implements it. Agreement between SAD and Xsuite is otherwise excellent once
this is accounted for: setting `DISFRIN=1` on the SAD side makes SAD's own
output match Xsuite's.

`F1` ("fringe length") is a red herring for this — SAD's own documentation
states `F1` only affects the emittance/radiation calculation ("if `F1`=0,
no radiation arises at the fringe"), not the orbital kick.

This fringe kick was checked and ruled out as the cause of a separately
observed ~28% SAD-vs-Xsuite radiation-loss gap for solenoids: SAD's radiated
power is unchanged by `DISFRIN`, so the fringe kick explains the coupling
gap (below) but not the radiation gap. That radiation discrepancy remains
open and unexplained.

See `docs/design-decisions.md` ("Solenoid fringe kick (DISFRIN) is not
modelled") for the resulting converter decision and warning.

## `MULT` `K0`/`SK0` dipole fringe

A SAD `MULT` with only `K0` (or only `SK0`) set has a dipole-fringe
contribution that Xsuite's `Bend`/corrector edge models do not reproduce
exactly. SAD's fringe term contributes exactly `m43 = -K0^2/L` (`m21` for
`SK0`) to the linear transfer matrix; Xsuite's bend edge models either add
`theta^4`-order terms or give zero, so the two codes agree at `theta^2` and
diverge at `theta^4`.

Confirmed via the parametrisation-free transfer-matrix anchor
(`tests/support/coupled_optics.linear_transfer_matrix_4d`, compared against
`transfer_matrix_sad`): the SAD-vs-Xsuite difference in this term equals
`-theta^4` at leading order (measured `-1.0005` to `-1.008 x theta^4` across
`theta = 0.025, 0.05, 0.1`), and scales by exactly `2^4 = 16` per doubling
of `theta` — locked in by
`test_mult_k0_dipole_fringe_difference_is_theta_fourth_order`
(`tests/conversion/elements/test_mult.py`). SAD-side ground truth for the
fringe formula itself is pinned in `tests/sad/test_mult.py`.

See `docs/design-decisions.md` ("Bend/Quadrupole/Sextupole/Octupole/
Multipole model and integrator retune") for the converter warning this
motivated.

## Bend element-offset (`DX`/`DY`) reference-orbit convention

A `DX`/`DY` misalignment on a curved element (a `BEND` with `ANGLE != 0`,
thick or thin) admits two defensible physical readings: an alignment
error, where the design orbit and its curvature (`h`) stay fixed and the
quantity of interest is the orbit distortion relative to the unmoved
design; or a deliberate offset, where the reference orbit follows the
displaced element and the curvature reflects the displaced geometry.
Xsuite's curved elements are built on the first reading. SAD's own
behaviour is closer to the second: it reconstructs its reference orbit
through the displaced element rather than keeping it fixed.

Confirmed empirically, not assumed, on a simple two-element (`START`/`END`)
open line with `betx = bety = 1` initial conditions: Xsuite's own `x`
(thick bend) or `dx` (thin bend) at the exit is numerically zero regardless
of `ANGLE`, while SAD's is nonzero and scales cleanly as `ANGLE^2` (a
consistent ~4x growth per angle doubling), matching `DX*(1-cos(ANGLE))` to
within ~1% — consistent with a rigid displacement of a curved element whose
curvature direction is unchanged. The thin representation shows the same
residual in the dispersion (`dx`) column rather than the orbit (`x`)
column, with the opposite sign (`-DX*(1-cos(ANGLE))`; there is no a priori
reason an orbit and a dispersion residual share a sign convention).

This is a distinct, independently-derived quantification from the open
issue's own four-case `x_corr` grid, which reports a different
`ANGLE^2`-vs-`ANGLE^4` scaling pattern for a different observable; the two
have not been reconciled and should not be assumed to describe the same
number.

Correctors (`ANGLE == 0`) and `MULT`-derived dipoles (both the
`user_multipole_replacements` `"Bend"` path and `SIMPLIFY_MULTIPOLES`'s
dipole-simplification path) never carry a nonzero curvature and are
confirmed unaffected.

Locked in as passing, quantified tests in
`tests/conversion/elements/test_bend.py`
(`test_bend_offset_orbit_residual_is_angle_squared_order` and
`test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order`).
See `docs/design-decisions.md` ("Bend element-offset (DX/DY) reference-
orbit convention is not modelled") for the resulting converter warning.

### Combined with `ROTATE`: a further, separate coupling artifact

Combined with a nonzero `ROTATE`, the residual above also perturbs
`betx`/`bety`/`alfx`/`alfy`, and a further, separate SAD-side artifact
appears on top: SAD's own reported linear coupling parameters (`R1`-`R4`)
for a rotated, offset, curved element become discontinuous the instant the
offset is nonzero — sitting on `sin(ROTATE)`/`cos(ROTATE)` (whichever is
smaller; the branch switches at a fixed ~52.3°, not at 45° as first
appeared) essentially independent of the offset's actual magnitude or
direction, unlike a real coupling effect, which would scale with the
offset and vanish as it does.

Confirmed:

- **Not an Edwards-Teng/Mais-Ripken twiss-convention mismatch** (see
  below): Xsuite's own, independently-computed Edwards-Teng coupling stays
  small and continuous in the offset throughout — it is specifically SAD's
  own reported `R1`-`R4` that jumps.
- **Not a sad2xs converter bug**: `ROTATE` and `DX`/`DY` are passed straight
  through to `xt.Bend`'s `rot_s_rad`/`shift_x`/`shift_y` unchanged; the
  anomaly reproduces identically in pure SAD with no converter involved at
  all.
- **Requires curvature specifically**: the identical `ROTATE`+offset
  combination on a `QUAD` (real rotation-induced coupling of its own, much
  larger than the bend's baseline) or a `MULT` with an equivalent dipole
  field shows no such effect — offset makes no difference in either case.
- **Not proportional to the offset**: a six-order-of-magnitude change in
  `DX` (`1e-12` to `0.1` m) produces no meaningful change in the reported
  value, and the jump is a hard discontinuity at exactly `DX=0` with no
  smooth crossover at any scale tested.
- **The ~52.3° branch point is a fixed constant**, confirmed insensitive to
  `ANGLE`, `DX` magnitude, and element length.

Working hypothesis (not confirmed against SAD source — no further
diagnosis was possible without it): this ties to the same reference-orbit
reconstruction described above. Once the displaced curved element is also
rotated, SAD's reconstructed downstream frame plausibly ends up tilted by
close to the geometric `ROTATE` angle relative to the design frame (unlike
Xsuite's fixed-frame convention), and `R1`-`R4` — which measure frame
mismatch — pick that up as if it were dynamical coupling. Why the
`sin`/`cos` branch switches at ~52.3° specifically looks like a separate,
purely numerical detail internal to SAD's own decomposition algorithm
(a branch-cut or eigenvalue-ordering threshold), not something with direct
physical meaning — it is completely insensitive to every physical
parameter tested, which a real physical crossover would not be.

Locked in by `test_bend_offset_rotated_coupling_is_a_sad_side_artifact`
(`tests/conversion/elements/test_bend.py`), which asserts the directly-
observable evidence (SAD's `R1` tracks `sin(ROTATE)` regardless of offset
magnitude; Xsuite's own coupling stays small and continuous) rather than a
full mechanistic explanation.

## Twiss conventions in coupled regions (skew quads, solenoids, ...)

SAD's `twiss_sad` output (`betx`/`bety`/`alfx`/`alfy`) reports coupled
optics in the **Edwards-Teng** (decoupled normal-mode) parametrisation —
the same convention MAD-X uses — propagated from the line start. Its
`R1`-`R4` columns are the Edwards-Teng decoupling matrix, normalised as
`R / sqrt(1 + det R)` (verified to ~1e-9 on both skew-quad and solenoid
cases via `coupled_optics.normalized_r_matrix()` — SAD's `R1`-`R4` are not
the raw decoupling matrix).

Xsuite's `line.twiss4d()`/`twiss6d()` reports something different by
default: its `betx`/`bety`/`alfx`/`alfy` fields are the **mode-1**/
**mode-2** (Mais-Ripken eigenmode) components only, with the cross-mode
leakage terms in separate `betx2`/`bety1`/`alfx2`/`alfy1` columns. Xsuite
can compute Edwards-Teng parameters natively (`coupling_edw_teng=True`),
but only for periodic lines; `tests/support/coupled_optics.py` wraps
Xtrack's open-line Edwards-Teng propagation so converted transfer lines can
be compared against SAD through coupled regions — see `docs/sad-helpers.md`
for the practical usage.

The convention map, established empirically (each case anchored by SAD and
Xsuite 4x4 transfer-matrix equality at the 1e-10 level, so the twiss
residuals below are purely parametrisation, not physics):

| case | Edwards-Teng | Mais-Ripken projected sums (`betx1+betx2`, ...) | plain mode values |
|------|--------------|--------------------------------------------------|-------------------|
| skew-quad line | matches SAD (≤1e-9) | off by ~3e-5 (beta), ~2e-4 (alfa) | off by ~2e-5 |
| solenoid line (`BZ=1.5`) | matches SAD (≤5e-10) | identical to Edwards-Teng (≤2e-15) | off by ~5% |
| uncoupled line | matches SAD (≤1e-9) | identical to Edwards-Teng | identical to Edwards-Teng |

Two traps this map removes:

- **The projected sums are not SAD's convention**, even though they match
  it exactly for solenoids. Rotational (solenoid) coupling is a special
  case in which the Mais-Ripken projected sums numerically coincide with
  the Edwards-Teng values; for skew-quad coupling they disagree with SAD by
  more than the plain values do. An earlier hypothesis recommended the
  projected sums based on the solenoid evidence alone — wrong, once the
  skew-quad case was checked.
- **SAD's `R1`-`R4` carry a normalisation** (`1/sqrt(1 + det R)`), so they
  are not directly the raw Edwards-Teng decoupling matrix components.

These facts are locked in, agreement and disagreement both asserted, by
`tests/conversion/test_coupled_twiss_convention.py`.

The solenoid mismatch was originally misdiagnosed as a SAD solenoid
GEO-exit-transform reference-frame issue. It isn't: the mismatch is present
already inside the solenoid body itself (before any reference-frame
transform is applied), it scales cleanly as `(Ks*L)^2`, and an independent
from-scratch derivation of the exact solenoid transfer matrix (linearizing
Xsuite's own documented solenoid Hamiltonian, cross-checked against a
central-difference Jacobian built directly from Xsuite's own tracking)
matches SAD's reported `betx` exactly — confirming both codes' underlying
physics (Hamiltonian and tracking) agree, and the gap is purely this
reporting convention.

`R1`-`R4` are not a SAD-specific quantity: they are the standard
Edwards-Teng coupling matrix, which Xsuite already computes natively
(`coupling_edw_teng=True`). Nothing about the coupling calculation itself
needed to be requested upstream — it already existed; the solenoid fringe
kick (above) was the only genuine physics gap raised with the Xsuite side,
and was declined for the reasons given there.
