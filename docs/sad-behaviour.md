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

## `BEND` `F1`/`FRINGE` soft-edge fringe

A SAD `BEND` applies a linear-plus-cubic-in-`y` fringe kick at each edge,
sized by `F1` (symmetric) or `FB1`/`FB2` (per-edge, additive on top of
`F1` — the effective entrance/exit fringe length is `F1+FB1`/`F1+FB2`)
and gated by `FRINGE` (its internal name is `FRMD`; unrelated to
`DISFRIN`, which is a separate hard-edge term): `0`/unset = off at both
edges, `-1` = entrance only, `-2` = exit only, any other nonzero = both
edges. `F1` has no effect unless `FRINGE` is also set — confirmed
empirically (`tests/sad/test_bend.py`,
`test_bend_f1_is_inert_without_fringe`), not assumed from the manual.
This applies identically on the two SAD code paths that carry it: the
`ANGLE != 0` sector bend (`tbend.f`) and the `ANGLE == 0`, `K0`-only
corrector (`tsteer.f`, i.e. a `BEND` with no `ANGLE`) — SAD2XS already
converts both to `xt.Bend`.

This is a real, large effect on real magnets — up to +20% error on the
vertical kick even on-momentum for `ANGLE != 0` sector bends, and up to
100% error for `K0`-only correctors (their kick is exactly zero without
any fringe treatment). It is not modelled unless
`_import_sad_bend_fringes` is enabled (`docs/design-decisions.md`).

Xsuite's native `edge_entry_model="full"` (`fint`/`hgap` on `xt.Bend`)
turns out to already be structurally capable of reproducing SAD's kick —
no composite element or custom physics needed. Taylor-matching SAD's
edge formula against Xsuite's term by term (both maps transcribed
explicitly and validated independently against the real SAD binary and
real `xtrack`, not compared as black boxes) gives a closed form, not a
curve fit: `fh = fint*hgap = (F1+FB1)/12` (entrance), `(F1+FB2)/12`
(exit), derived from the requirement that both the linear and cubic
`y`-coefficients of the kick match simultaneously at `delta=0`. This
matches SAD to a fraction of a percent on-momentum, for both magnet
families — the residual that remains is the small-`fh`
(`tan(x)≈x`) approximation inherent in deriving the closed form, entirely
negligible at the `fh` scale of a real magnet. Only the product `fint*hgap`
reaches Xsuite's edge formula, so the split between the two is a free
choice: SAD2XS sets `fint = F1+FB1`/`F1+FB2` directly (the raw SAD value,
not a derived one) and `hgap` to the fixed `1/12`, so `fint` on a
converted element is always directly traceable back to its SAD source.

**Off-momentum, the two codes disagree on principle, not just in
magnitude.** SAD's fringe-integral term scales as `1/(1+delta)`; Xsuite's
native formula (faithfully ported from MAD-NG's own `bend_fringe`,
confirmed variable-for-variable against MAD-NG's source) scales as
`(1+delta)` — the opposite direction. Mechanism: the two codes share an
identical "hard-edge" contribution (`px`-driven, from the bend's own
dispersion) exactly, at any `fh` — proven via the identity
`tan(atan(xp))=xp`, not just measured. The mismatch lives entirely in the
"soft" (`F1`-driven) term, where SAD's Taylor series and Xsuite's
Taylor-expanded `tan()`-based construction disagree in the sign of the
`delta`-dependence.

Checked against a fully independent derivation: Forest, Leemann & Schmidt,
"Fringe Effects in MAD, Part I: Second Order Fringe in MAD-X for the
Module PTC" (KEK Preprint 2005-109) derives the same fringe-integral term
from scratch via a Lie-operator calculation, with no reference to SAD at
all, and its rigorous result gets `1/(1+delta)` — the same closed form as
SAD's, algebraically identical once the two papers' field-integral
normalizations are matched (`F1 = 6*g*K`). But checked live, via `cpymad`
against real, compiled PTC (not just the paper): PTC does **not**
implement that rigorous result — it implements the same paper's different
"MAD8-compliant" practical formula, and tracking through real PTC matches
Xsuite/MAD-NG's `(1+delta)` scaling almost exactly (8 significant figures),
not SAD's. So the honest state is: a paper's own rigorous derivation
matches SAD exactly, but no currently-runnable software (SAD aside)
implements it — real PTC, MAD-NG, and Xsuite (including Xsuite's own
independent second implementation ported directly from PTC's Fortran
source, not from MAD-NG) all implement the paper's other formula and
agree with each other. This looks like one shared implementation choice,
traceable to PTC's own actual Fortran source, reproduced repeatedly rather
than independent confirmation. This is not a SAD2XS bug to work around —
it is a genuine upstream formalism question, not yet raised with the
Xsuite/MAD-NG maintainers.

Locked in by `test_bend_fringe_import_off_momentum_residual_is_bounded`
and its corrector equivalent (`tests/conversion/elements/test_bend.py`,
`test_corrector.py`) as an explicit, bounded assertion on the current
residual — not skipped, not left to silently pass or silently stay
wrong. If Xsuite/MAD-NG's native formula ever changes upstream, these
tests fail and surface for review rather than passing silently.

## RF focusing in accelerating `MULT`/`CAVI` elements

SAD's accelerating-element tracking (`tmultiacc` in `tmulti.f`) applies an
explicit transverse RF-focusing kick — quadratic in x/y, proportional to
`(V*omega/p)^2` — on top of the ordinary multipole kick and the momentum
update, whenever `RFSW` is on and `VOLT != 0`. This is present **regardless
of `TRPT`**: the coefficient (`vcorr` in the source) is computed from the
entry/exit reference energy either way — under the default `RING`/`NOTRPT`
the exit reference energy simply equals the entry value, giving a nonzero
`vcorr = v*(w/p0)^2/4` rather than zero. It is the standard
Rosenzweig-Serafini RF-focusing effect for standing-wave-like accelerating
structures (Rosenzweig, J. & Serafini, L., "Transverse particle motion in
radio-frequency linear accelerators", *Phys. Rev. E* **49**, 1599 (1994),
DOI [10.1103/PhysRevE.49.1599](https://link.aps.org/doi/10.1103/PhysRevE.49.1599)),
not a SAD peculiarity, and depends only on `VOLT`/`FREQ` (or `HARM`) and the
reference momentum — it applies to a plain accelerating `CAVI` just as much
as to a combined K1+VOLT `MULT`.

`vcorr` has no explicit dependence on RF phase (`PHI`), only on the entry
and exit reference momentum (`p0`, `pe`). It is phase-dependent only
indirectly, through `pe`, which differs from `p0` whenever the element
imparts a net energy change. Confirmed empirically (`tests/sad/test_mult.py`):
the kick is nonzero even exactly at `PHI = 0` (SAD's RF zero-crossing,
where the net energy gain is exactly zero and `pe = p0`, so `vcorr` reduces
to the fixed value `v*(w/p0)^2/4`), and grows substantially (over 10x in
the locked-in test) moving towards the accelerating crest, where `pe`
diverges further from `p0`. This is not a simple on/off-by-phase effect —
it is present at every phase, including the zero-crossing.

Xsuite's `xt.Cavity` has no such term: `Cavity_track_local_particle`
(`xtrack/beam_elements/elements_src/cavity.h`) calls the shared RF-kick
routine with `order = -1, knl = NULL`, which disables the entire x/y-
dependent kick block in `track_rf.h`. Confirmed empirically by tracking
(not just by reading the source): for a 1 m accelerating element at
`MOMENTUM = 0.05 GeV`, `VOLT = 1e8` (TRPT on, RFSW on), SAD's own tracked
transfer matrix has a real, sizeable `x -> px` coupling term
(`M21 = -0.183` for a pure accelerating drift with no quadrupole at all,
where a plain drift has exactly zero); an Xsuite reconstruction using
`Multipole` + `Cavity` + `ReferenceEnergyIncrease` slices has *exactly*
zero `M21` for the same case. Both tracked matrices have
`det(M) = p_entry/p_exit`, confirming the two are being compared in the
same canonical, local-momentum-normalized convention (not an artefact of
mismatched Twiss normalization — Xsuite's own `line.twiss()` applies an
additional, separately real `p_exit/p_entry` scaling to `betx` on top of
this raw matrix, which must not be conflated with the RF-focusing question).
Locked in by `tests/xtrack/test_cavity.py`.

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

The residual is not confined to the orbit/dispersion column. Confirmed
empirically, per representation:

- **Thick bend**: `zeta`, `dx` (dispersion), `betx`, `bety`, `alfx`, and
  `alfy` all diverge alongside `x` at every angle tested (`0.025`, `0.05`,
  `0.1`). `px` also diverges, at `ANGLE^4` (faster than the rest) — it
  only clears the standard `(1e-9, 1e-5)` comparison tolerance from
  `ANGLE≈0.05` upward, not at `0.025`. This is confirmed distinct from the
  unrelated `MULT` `K0`/`SK0` `ANGLE^4` fringe-order mismatch above: a
  plain `DX=DY=0` bend at the same three angles matches SAD on all 15
  columns with no divergence anywhere, so `px`'s divergence here is
  genuinely offset-triggered, not that unrelated confound bleeding
  through. `s`, `y`, `py`, `delta`, `dpx`, `dpy` all match.
- **Thin bend**: only `dx` and `zeta` diverge; `x`, `px`, `y`, `py`,
  `delta`, `betx`, `bety`, `alfx`, `alfy` all match exactly — a
  zero-length element has no separate betatron distortion of its own.
- **Combined `DX`+`DY`**: a clean superposition of the pure-`DX` residual
  on every column, for both thick and thin bends — `DY`'s own
  contribution is zero to numerical noise. One exception: a genuine but
  tiny (~1e-9) `dx`-column cross-term appears only when `DX` and `DY` are
  simultaneously nonzero (thick bend), and only clears tolerance at the
  largest angle tested (`0.1`).
- **Tracking** (as opposed to twiss/closed-orbit): the same residual
  surfaces as a divergence on `x`/`px`/`zeta` for the thick bend and
  `x`/`y`/`zeta` for the thin bend (the thin-bend `x`/`y` divergence is a
  small, ~1e-8, rigid shift identical for every particle regardless of its
  own initial coordinates); `y`/`py`/`delta` (thick) and `px`/`py`/`delta`
  (thin) still match.

Locked in by `test_bend_offset_orbit_residual_is_angle_squared_order` and
`test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order`
(twiss, extended to the combined-offset case and the columns above) and
`test_bend_offset_orbit_residual_diverges_in_tracking` /
`test_bend_offset_thin_bend_dispersion_residual_diverges_in_tracking`
(tracking) in `tests/conversion/elements/test_bend.py`.

Correctors (`ANGLE == 0`) and `MULT`-derived dipoles (both the
`user_multipole_replacements` `"Bend"` path and `SIMPLIFY_MULTIPOLES`'s
dipole-simplification path) never carry a nonzero curvature and are
confirmed unaffected.

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
- **Not confined to the axis carrying the offset.** Confirmed at
  `ROTATE = +-pi/2` in addition to the `pi/4` case originally
  investigated: even when the offset lies entirely on the axis that
  tracking (and closed-orbit twiss columns) show matching SAD exactly —
  e.g. `DX` at `ROTATE = +-pi/2`, the case
  `test_bend_conversion_matches_sad_tracking_for_rotated_element_offsets`
  asserts is a full tracking match — `betx`/`bety`/`alfx`/`alfy` still
  diverge by the same order of magnitude. Tracking never computes twiss
  parameters, so this is invisible there regardless of which axis carries
  the offset; only a dedicated twiss-side comparison sees it. Quantified
  at `ROTATE=pi/4`, `ANGLE=0.05`: `betx`/`bety` diverge by ~1.3e-3,
  `alfx`/`alfy` by ~2.9e-3 — three orders of magnitude past the normal
  `(1e-9, 1e-5)` twiss tolerance — and, like `R1`, barely change between
  two offset magnitudes three orders of magnitude apart, the same
  magnitude-independent signature. Locked in by
  `test_bend_conversion_matches_sad_twiss_for_rotated_element_offsets` (the
  general case, all axes) and by the `betx`/`bety`/`alfx`/`alfy`
  assertions added to
  `test_bend_offset_rotated_coupling_is_a_sad_side_artifact` (the
  `pi/4` case specifically).

The committed regression tests lock in a narrower slice than was explored.
`test_bend_offset_rotated_coupling_is_a_sad_side_artifact` checks `DX` in
`[1e-6, 1e-3]` at one fixed `ANGLE=0.05`, `ROTATE=pi/4`;
`test_bend_conversion_matches_sad_twiss_for_rotated_element_offsets` checks
`ROTATE = +-pi/2` with `(DX,DY)` in
`{(1e-3,0), (0,-1e-3), (1e-3,-1e-3)}` at one fixed `ANGLE=0.1`. The wider
claims above — the six-order-of-magnitude `DX` insensitivity (`1e-12` to
`0.1`), and the `ANGLE`/length independence of both the effect and the
~52.3° branch point — were established via a standalone empirical scan
(`dev/sad_offset_bend_coupling/r1_r4_scan.py` plus 58 independent
native-SAD runs, not part of the committed test suite) and are not
themselves regression-locked. If the committed tests' narrower slice ever
starts passing in the "matches" direction, this wider characterisation
should be re-checked too, not just the committed assertions.

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

Locked in by `test_bend_offset_rotated_coupling_is_a_sad_side_artifact`,
`test_bend_conversion_matches_sad_twiss_for_rotated_element_offsets`, and
`test_bend_conversion_matches_sad_tracking_for_rotated_element_offsets`
(`tests/conversion/elements/test_bend.py`), which together assert the
directly-observable evidence (SAD's `R1` tracks `sin(ROTATE)` regardless of
offset magnitude; Xsuite's own coupling stays small and continuous;
`betx`/`bety`/`alfx`/`alfy` diverge on every axis; tracking coordinates
match or diverge exactly as the unrotated case does, just with axes
swapped) rather than a full mechanistic explanation.

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

## `LINE X = (-Y);` reversal is a MAIN-file declaration, not a live command

SAD's beamline-reversal syntax (`LINE X = (-Y);`, defining a new named line
as the reverse of an existing one) is part of the MAIN-file declaration
grammar that `GetMAIN` parses — the same statement class as `BEND`/`QUAD`/
`LINE` element and line definitions. It is **not** a live FFS command:
issuing it as a runtime statement after `GetMAIN` has already loaded the
file fails with `???General::wrongtype: Argument must be BeamLine[ ... ]:`
/ `???-FFS-Error-Missing beamline in USE.` when the resulting name is then
passed to `USE`.

Confirmed by direct probe: `GetMAIN["./file.sad"]; USE FWD; LINE REV = (-FWD);
USE REV;` fails with the error above, while defining `LINE REV = (-FWD);`
inside `file.sad` itself (so it is present when `GetMAIN` parses the file)
and then just running `USE REV;` succeeds.

`run_sad`'s error handling does not catch this failure mode — SAD exits
0 and prints the error to stdout rather than raising, so a caller that
doesn't inspect console output gets a silently degenerate result (in one
reproduction: `name: ['$DUMMYMARK', '$DUMMYDRIFT']`, `betx: [inf, inf]`,
`alfx: [nan, nan]`) rather than an exception.

**Consequence**: `sad2xs.sad_helpers.twiss_sad`/`survey_sad`'s
`reverse_element_order=True` instead reverses the already-`USE`'d beamline
live, via `LINE <name> = -ExtractBeamLine[]; USE <name>;` — `ExtractBeamLine[]`
is a runtime FFS function returning a `BeamLine[...]` object directly, not
the MAIN-file declaration grammar, so it is not subject to the restriction
above. Verified directly against real SAD: this gives bit-for-bit identical
Twiss/survey results to a `LINE REV = (-FWD);` declared natively in the
lattice file, and (unlike an earlier temp-lattice-file-based workaround)
matches element names exactly rather than only partially.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
