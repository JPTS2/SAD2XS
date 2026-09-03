# SAD behaviour notes

This page catalogues empirically-established facts about how SAD behaves:
physics conventions, quirks, and limitations found while building and
testing the converter.

These are not SAD2XS design choices. They are what SAD does. Every fact
here was verified against the real SAD binary, or, for the Xsuite side,
against an independent computation. None is assumed from the documentation.

Many of these facts led to a SAD2XS decision, such as a converter warning,
a config default, or an accepted test limitation. Each decision is
documented with the feature it concerns, in the
[converter documentation](../converter/README.md), and points back here for
the underlying evidence.

**On this page:**

- [Solenoid fringe kick (`DISFRIN`)](#solenoid-fringe-kick-disfrin)
- [`MULT` `K0`/`SK0` dipole fringe](#mult-k0sk0-dipole-fringe)
- [`BEND` `F1`/`FRINGE` soft-edge fringe](#bend-f1fringe-soft-edge-fringe)
- [`BEND` `DISFRIN` hard-edge fringe](#bend-disfrin-hard-edge-fringe)
- [`QUAD` `F1`/`F2`/`FRINGE` soft-edge fringe](#quad-f1f2fringe-soft-edge-fringe)
- [`QUAD` `DISFRIN` hard-edge fringe](#quad-disfrin-hard-edge-fringe)
- [`MULT` fringe: QUAD's mechanism, generalized](#mult-fringe-quads-mechanism-generalized)
- [`SEXT`/`OCT` `DISFRIN` hard-edge fringe](#sextoct-disfrin-hard-edge-fringe)
- [RF focusing in accelerating `MULT`/`CAVI` elements](#rf-focusing-in-accelerating-multcavi-elements)
- [`CAVI` `FRINGE`/`DISFRIN` RF edge-focusing kick](#cavi-fringedisfrin-rf-edge-focusing-kick)
- [Bend element-offset (`DX`/`DY`) reference-orbit convention](#bend-element-offset-dxdy-reference-orbit-convention)
- [Twiss conventions in coupled regions (skew quads, solenoids, ...)](#twiss-conventions-in-coupled-regions-skew-quads-solenoids-)
- [`LINE X = (-Y);` reversal is a MAIN-file declaration, not a live command](#line-x---y-reversal-is-a-main-file-declaration-not-a-live-command)

## Solenoid fringe kick (`DISFRIN`)

SAD's solenoid Hamiltonian includes a nonlinear, hard-edge fringe kick,
distinct from the solenoid's main linear field, controlled by SAD's
`DISFRIN` parameter (default `0` applies the kick, `1` disables it):

```
H = -Bz / (8 p^2 B*rho) * p_phi * p_r
p_phi = x*py - y*px
p_r   = x*px + y*py
```

`p_phi` and `p_r` are each quadratic in phase space, so `H` is quartic.
This is a genuine nonlinear, octupolar term. It is not a linear edge effect
and not a finite-length ramp. Neither `xt.UniformSolenoid` nor
`xt.VariableSolenoid` implements it.

Once this term is accounted for, agreement between SAD and Xsuite is
excellent: setting `DISFRIN=1` on the SAD side makes SAD's own output match
Xsuite's.

This matches the derivation in K. Oide, "Fringe Field of Solenoid", 15th
KEKB-ARC (2010). The same nonlinear Hamiltonian follows from the
delta-function terms in the fringe's vector potential, which are required to
satisfy Maxwell's equations at a hard edge. It is independent of the fringe
length `f`. The linear terms of the field model are a separate effect,
captured by ordinary hard-edge slicing.

`F1`, the fringe length, does not control this kick. SAD's own documentation
states that `F1` affects only the emittance and radiation calculation: "if
`F1`=0, no radiation arises at the fringe". It does not affect the orbital
kick.

`SOL` has no `FRINGE` keyword at all. It also rejects
`F2`/`FB1`/`FB2`/`F1K1F`/`F2K1F`/`F1K1B`/`F2K1B` outright, confirmed
empirically in `tests/sad/test_sol.py` (`REJECTED_PARAMS`). `DISFRIN` alone
gates the orbital kick above.

This fringe kick was checked and ruled out as the cause of a separate
finding: a ~28% SAD-vs-Xsuite radiation-loss gap for solenoids. SAD's
radiated power is unchanged by `DISFRIN`. The fringe kick therefore explains
the coupling gap described below, but not the radiation gap. That radiation
discrepancy remains open and unexplained.

See [solenoid conversion](../converter/solenoids.md) for the resulting
converter decision and warning.

## `MULT` `K0`/`SK0` dipole fringe

A SAD `MULT` with only `K0` set, or only `SK0`, has a dipole-fringe
contribution. Xsuite's `Bend` and corrector edge models do not reproduce it
exactly.

SAD's fringe term contributes exactly `m43 = -K0^2/L` to the linear transfer
matrix, or `m21` for `SK0`. Xsuite's bend edge models either add
`theta^4`-order terms or give zero. The two codes therefore agree at
`theta^2` and diverge at `theta^4`.

This was confirmed with the parametrisation-free transfer-matrix anchor
`tests/support/coupled_optics.linear_transfer_matrix_4d`, compared against
`transfer_matrix_sad`. The SAD-vs-Xsuite difference in this term equals
`-theta^4` at leading order, measured as `-1.0005` to `-1.008 x theta^4`
across `theta = 0.025, 0.05, 0.1`. It scales by exactly `2^4 = 16` per
doubling of `theta`.

`test_mult_k0_dipole_fringe_difference_is_theta_fourth_order`
(`tests/conversion/elements/test_mult.py`) locks this in. SAD-side ground
truth for the fringe formula itself is pinned in `tests/sad/test_mult.py`.

See [element conversion](../converter/elements.md) for the converter warning
this motivated.

## `BEND` `F1`/`FRINGE` soft-edge fringe

A SAD `BEND` applies a fringe kick at each edge that is linear plus cubic
in `y`.

`F1` sizes the kick symmetrically. `FB1` and `FB2` size it per edge, and add
on top of `F1`: the effective fringe length is `F1+FB1` at the entrance and
`F1+FB2` at the exit.

`FRINGE` gates the kick. Its internal SAD name is `FRMD_BEND`. It is
unrelated to `DISFRIN`, which is a separate hard-edge term.

| `FRINGE` | Effect |
| --- | --- |
| `0`, or any value `<= -3` | both edges disabled |
| `-1` | entrance only |
| `-2` | exit only |
| any positive value | both edges enabled unconditionally |

This full grid was confirmed against the real SAD binary, not read off the
manual alone: `tests/sad/test_bend.py`,
`test_bend_fringe_mode_gates_entrance_exit` and
`test_bend_corrector_fringe_mode_gates_entrance_exit`.

`F1` has no effect unless `FRINGE` is also set. This was also confirmed
empirically rather than assumed from the manual
(`test_bend_f1_is_inert_without_fringe`).

The behaviour is identical on the two SAD code paths that carry it: the
`ANGLE != 0` sector bend (`tbend.f`), and the `ANGLE == 0`, `K0`-only
corrector (`tsteer.f`, a `BEND` with no `ANGLE`). SAD2XS converts both to
`xt.Bend`.

This is a large effect on real magnets. On-momentum, it reaches +20% error
on the vertical kick for `ANGLE != 0` sector bends. For `K0`-only
correctors it reaches 100% error, because their kick is exactly zero without
any fringe treatment. SAD2XS does not model it unless
`_import_sad_bend_fringes` is enabled. See [fringe models](../converter/fringes.md).

Xsuite's native `edge_entry_model="full"`, which uses `fint` and `hgap` on
`xt.Bend`, is already structurally capable of reproducing SAD's kick. No
composite element or custom physics is needed.

Taylor-matching SAD's edge formula against Xsuite's term by term gives a
closed form, not a curve fit:

```text
fh = fint*hgap = (F1+FB1)/12    (entrance)
                 (F1+FB2)/12    (exit)
```

This follows from the requirement that the linear and cubic `y`-coefficients
of the kick match simultaneously at `delta=0`. Both maps were transcribed
explicitly and validated independently against the real SAD binary and real
`xtrack`, rather than treated as opaque implementations and compared only by
their output.

On-momentum, this matches SAD to a fraction of a percent for both magnet
families. The remaining residual comes from the small-`fh` approximation
`tan(x)≈x` used to derive the closed form. At the `fh` scale of a real
magnet this residual is negligible.

Only the product `fint*hgap` reaches Xsuite's edge formula, so the split
between the two factors is free. SAD2XS sets `fint` to the raw SAD value,
`F1+FB1` or `F1+FB2`, and fixes `hgap` at `1/12`. This keeps `fint` on a
converted element directly traceable back to its SAD source.

**Off-momentum, the two codes once disagreed on principle, not just in
magnitude.** SAD's fringe-integral term scales as `1/(1+delta)`. Xsuite's
native formula (faithfully ported from MAD-NG's own `bend_fringe`, confirmed
variable-for-variable against MAD-NG's source) scaled as `(1+delta)`, which
is the opposite direction. Xsuite 0.57.0 adopted the `1/(1+delta)` form, and
the two codes now agree. The rest of this section records why that was the
right resolution, because the reasoning still applies to MAD-NG and PTC.

The mechanism is understood. The two codes share an identical hard-edge
contribution, driven by `px` from the bend's own dispersion. That part agrees
exactly, at any `fh`, and this was proven through the identity
`tan(atan(xp))=xp` rather than only measured. The mismatch lives entirely in
the soft, `F1`-driven term. There, SAD's Taylor series and Xsuite's
Taylor-expanded `tan()`-based construction disagree in the sign of the
`delta`-dependence.

A fully independent derivation confirms SAD's form. Forest, Leemann &
Schmidt, "Fringe Effects in MAD, Part I: Second Order Fringe in MAD-X for
the Module PTC" (KEK Preprint 2005-109) derives the same fringe-integral
term from scratch through a Lie-operator calculation, with no reference to
SAD. Its rigorous result gets `1/(1+delta)`, the same closed form as SAD's.
The two are algebraically identical once the field-integral normalizations
of the two papers are matched (`F1 = 6*g*K`).

Real PTC does not implement that rigorous result. This was checked live
through `cpymad` against compiled PTC, not read from the paper. PTC
implements the same paper's other, "MAD8-compliant" practical formula.
Tracking through real PTC matches the `(1+delta)` scaling of Xsuite and
MAD-NG to 8 significant figures, not SAD's.

The honest state is therefore this. A paper's own rigorous derivation
matches SAD exactly, but no currently-runnable software other than SAD
implements it. Real PTC, MAD-NG, and Xsuite all implement the paper's other
formula and agree with each other. This includes Xsuite's own second
implementation, ported directly from PTC's Fortran source rather than from
MAD-NG.

That looked like one shared implementation choice, traceable to PTC's own
Fortran source and reproduced repeatedly, rather than independent
confirmation. It was never a SAD2XS bug to work around: it was a genuine
upstream formalism question.

Xsuite resolved it in 0.57.0 by adopting the rigorous `1/(1+delta)` form.
PTC and MAD-NG have not been re-checked since, so the comparison above
describes them as they were measured, not necessarily as they are now.

`test_bend_fringe_import_matches_sad_off_momentum` and its corrector
equivalent (`tests/conversion/elements/test_bend.py`, `test_corrector.py`)
lock the agreement in. They assert a match to `1e-4` relative, so a
regression in the momentum scaling fails and surfaces for review.

## `BEND` `DISFRIN` hard-edge fringe

A SAD `BEND` also carries a separate nonlinear hard-edge fringe kick, gated
by `DISFRIN`. It is structurally distinct from the linear-plus-cubic
`F1`/`FRINGE` soft-edge term above. On `BEND`, `DISFRIN` and `FRINGE` are
unrelated: each controls its own term, and they do not interact. This is
unlike `QUAD`, described below.

`DISFRIN` is a strict boolean gate, not a graded mode like `FRINGE`. Unset
defaults to `DISFRIN=0`, which enables the fringe. Any nonzero value
disables it identically, bit-for-bit. This was checked at `1, 2, -1, 3, 0.5`
against the real binary (`tests/sad/test_bend.py`,
`test_bend_disfrin_default_matches_explicit_zero` and
`test_bend_disfrin_is_boolean`).

The kick is `K1`-dependent, and it is only resolvable at a realistic
transverse offset of a few cm. It is pinned against real SAD binary output
in `test_bend_disfrin_hard_edge_matches_sad_reference_values`.

Xsuite's native `edge_entry_model` and `edge_exit_model` on `xt.Bend`
already implement the identical mechanism. Measured on a sector bend with
`L=2.0`, `ANGLE=0.2`, `K1=1.0`, `y=0.03`:

| Xsuite edge model | Matches SAD | Relative agreement |
| --- | --- | --- |
| `"full"` | `DISFRIN=0` | ~2e-5 |
| `"suppressed"` | `DISFRIN=1` | ~2e-6 |

No physics beyond the existing bend fringe-import work is needed.

On the `ANGLE == 0`, `K0`-only corrector path the question does not arise.
SAD does not allow a corrector to carry a nonzero `K1` alongside `K0` when
`ANGLE` is absent or zero. This is a confirmed, separate SAD bug: the
combination silently no-ops the whole element instead of raising an error,
and it has been reported upstream. A real corrector therefore has no
quadrupole content for the hard-edge term of `DISFRIN` to gate
(`test_corrector_disfrin_has_no_effect_without_k1`).

## `QUAD` `F1`/`F2`/`FRINGE` soft-edge fringe

A SAD `QUAD` applies a strictly **linear** fringe kick at each edge. There
is no cubic term, unlike `BEND`'s `F1`.

`F1` and `F2` size the kick symmetrically. The per-edge terms are
`F1K1F`/`F2K1F` at the entrance and `F1K1B`/`F2K1B` at the exit. `FRINGE`
gates the kick, and the parameters are inert unless `FRINGE` is set. This
matches `BEND`'s own `F1` convention (`tests/sad/test_quad.py`,
`test_quad_f1_f2_is_inert_without_fringe`).

**`QUAD`'s `FRINGE` uses a different numbering system from `BEND`'s, despite
sharing the same SAD keyword name.** Its internal name is `mfring`, against
`BEND`'s `FRMD_BEND`. It is a strict membership test on `{1, 2, 3}`, and it
is not sign-graded:

| `FRINGE` | Effect |
| --- | --- |
| `1` | entrance only |
| `2` | exit only |
| `3` | both edges |
| any other value, including positive values such as `4` | linear fringe off entirely |

There is no `BEND`-style rule that any positive value enables both edges.
This was confirmed against the real binary across the full grid, using
genuinely asymmetric `F1K1F`/`F1K1B`/`F2K1F`/`F2K1B`
(`test_quad_fringe_mode_gates_entrance_exit`).

Reversing a line with `-LINE` permutes which side receives the linear fringe
kick. It does not simply change which raw per-side parameter feeds which
side. A reversed `FRINGE=1` element matches a forward `FRINGE=2` element
exactly, with `F1K1F`/`F1K1B` and `F2K1F`/`F2K1B` swapped. This was confirmed
against SAD's own `-LINE` output, not assumed from the parameter swap alone
(`test_quad_reversed_line_fringe_mode_permutes`).

`FRINGE=3` and `FRINGE=0` are fixed points of this permutation, because both
sides are symmetric under it. The permutation therefore matters in practice
only for a quadrupole that uses `FRINGE=1` or `FRINGE=2` and is traversed in
reverse.

The behaviour is pinned against real SAD binary output for `K1>0`, `K1<0`,
and skewed (`ROTATE != 0`) cases
(`test_quad_f1_f2_matches_sad_reference_values` and its `_negative_k1` and
`_skew` variants). The `K1<0` case confirms that SAD internally encodes a
defocusing quadrupole as a focusing quadrupole rotated by 90 degrees,
through `ROTATE + akang(K1)`.

**The kick itself** (`tquad.f:52-67/86-102`) is a per-side linear map in two
coefficients, `a` and `b`. These are derived from the user-facing parameters
in `tsetfringep` (`tffs.f:952-980`, the `cmp%ori=True` branch):

```text
akk = K1/L
a   = -abs(akk * f1_raw^2)/24
b   = abs(akk) * f2_raw
```

`f1_raw` and `f2_raw` are `F1+F1K1F` and `F2+F2K1F` at the entrance, and
`F1+F1K1B` and `F2+F2K1B` at the exit.

`tquad.f` applies `+a` at the entrance and `-a` at the exit. `b` keeps the
same sign at both. This is why a reversed element's surviving fringe side
flips only `a`, and leaves `b` and the frame angle `ROTATE + akang(K1)`
unchanged.

The exact kick is non-polynomial in `delta`, through `exp(a/(1+delta))` and
`1/(1+delta)^2`. See [fringe models](../converter/fringes.md) for how SAD2XS
represents it.

## `QUAD` `DISFRIN` hard-edge fringe

`QUAD` follows the same convention as `BEND` and `SOL`. `DISFRIN` gates a
separate nonlinear hard-edge fringe kick. It defaults to `DISFRIN=0`, which
enables the kick, and it is strictly boolean.

Values `1, 2, -1, 3, 0.5` were all checked against the real binary and are
bit-identical to `DISFRIN=1`
(`test_quad_disfrin_default_matches_explicit_zero` and
`test_quad_disfrin_is_boolean`). The kick is pinned at a realistic offset in
`test_quad_disfrin_hard_edge_matches_sad_reference_values`.

**Unlike `BEND`, `FRINGE` on a `QUAD` is not independent of `DISFRIN`**: it
additionally gates *which side* of the hard-edge fringe applies, regardless
of `DISFRIN`'s own value. The entrance hard-edge kick is skipped outright
whenever `FRINGE==2`, the exit one whenever `FRINGE==1` — the same
`mfring` value that selects the linear fringe side also selects the
hard-edge side. Confirmed directly against real SAD with no `F1`/`F2`/
`F1K1x` terms set at all, isolating the hard-edge mechanism alone
(`test_quad_fringe_mode_also_gates_hard_edge_fringe_sides`): the effect
size from losing one hard-edge side is over an order of magnitude *larger*
than the net two-sided residual `DISFRIN` alone removes — the two sides'
hard-edge contributions mostly cancel when both are present, so isolating
one side is not a small correction. `FRINGE<=-4` is a master disable for
the hard-edge fringe on both sides unconditionally, matching `DISFRIN=1`
bit-identically; `FRINGE=0`/unset and `FRINGE=3` leave both hard-edge sides
exactly as `DISFRIN` alone would set them.

This means the linear (`F1`/`F2`) and hard-edge (`DISFRIN`) fringes on a
`QUAD` do **not** simply compose additively for every `FRINGE` value —
confirmed additive only at `FRINGE=3`
(`test_quad_f1_f2_composes_additively_with_default_nonlinear_fringe`),
where neither hard-edge side is excluded.

## `MULT` fringe: QUAD's mechanism, generalized

A SAD `MULT` combines two kinds of content in a single element:

- BEND-style bending content: `ANGLE`/`K0`, with soft-edge `FB1`/`FB2`;
- QUAD-style quadrupole content: `K1`, with soft-edge
  `F1`/`F2`/`F1K1F`/`F2K1F`/`F1K1B`/`F2K1B`.

Its source, `tmulte.f`, mirrors the quadrupole path closely. A `MULT` with
only `K1` set and positive face lengths gives bit-identical tracking output
to the equivalent `QUAD` in the pinned reference cases. The parameter path is
not identical for signed face lengths: `tsetfringepe` passes raw MULT face
values to `tqlfre`, whereas the QUAD path uses its precomputed table.

For combined normal/skew K1 content, the linear soft-edge coefficients use
`abs(K1+i*SK1)/abs(L)` and the frame angle uses
`ROTATE+akang(K1+i*SK1)`. The live formula in `tqlfre.f` retains the face
sign:
`a=-abs(K1+i*SK1)/abs(L)*f1_raw*abs(f1_raw)/24`.
The negative-F1 real-SAD regression pins this signed form directly.

`FRINGE`, internally `mfring`, uses the **same `{1, 2, 3}` numbering as
`QUAD`**: `1` is entrance-only, `2` is exit-only, and `3` is both. It
applies to **all** of `MULT`'s fringe sub-mechanisms at once. The `K1`
quad-style linear fringe, the `FB1`/`FB2` dipole-style linear fringe, and
the `DISFRIN`-gated hard-edge kick all read the same `mfring` value to
select the entrance or the exit. This was confirmed against the real binary
for `FB1`/`FB2` (`test_mult_fb1_fb2_fringe_mode_gates_entrance_exit`).
Although the tracking source calls `NINT`, SAD's input layer has already
truncated this integer-valued keyword: for example, `FRINGE=1.5` tracks
bit-identically to `FRINGE=1`, not `FRINGE=2`.

This explains a finding recorded above. A `K0`-only `MULT` and the
equivalent `K0`-only `BEND`, both given the same `FRINGE=1`, `FB1`, and
`FB2`, give clearly different `py(y)`
(`test_mult_k0_fringe_with_nonzero_fb_does_not_match_equivalent_bend`). The
cause is not a different fringe *formula*. `FRINGE=1` simply means something
different on each element: both edges active on `BEND`, under its sign-based
scheme, against entrance-only on `MULT`, under the `{1,2,3}` membership
scheme.

The mode permutation under a reversed `-LINE`, where `FRINGE` `1` and `2`
swap along with the parameters, is identical to `QUAD`'s
(`test_mult_reversed_line_fringe_mode_permutes`).

`DISFRIN` gates the same generic hard-edge kick as `BEND`, `QUAD`, `SEXT`,
and `OCT`. It defaults to `0`, which enables the kick, it is strictly
boolean, and it is pinned identical to the equivalent `QUAD`
(`test_mult_disfrin_hard_edge_matches_sad_reference_values`). As on `QUAD`,
`FRINGE` additionally gates which side of this hard-edge kick applies,
independently of `DISFRIN`
(`test_mult_fringe_mode_also_gates_hard_edge_fringe_sides`).

**Unlike `QUAD`, `MULT` has no `FRINGE<=-4` master-disable for the hard-edge
term.** The hard-edge gate in `tmulti.f` checks only `mfring /= 1` and
`mfring /= 2`, with no lower-bound condition, where `tquad.f` also adds
`mfring .gt. -4`. It was confirmed empirically that `FRINGE=-4` leaves both
hard-edge sides fully active on a `MULT`, while the identical value disables
both on a `QUAD`.

The `K0`/`SK0` dipole-fringe transfer-matrix finding above, where `FRINGE=1`
zeroes `m43`/`m21` exactly and `DISFRIN` does not control it, comes from a
different code path. It is a Twiss and linear-map-level fact from SAD's
`CALC4D` and `TransferMatrix[]` machinery, not from the particle-tracking
`tmulti` routine described here.

The two findings are complementary, not in tension. `DISFRIN` does affect
tracked orbits through a `MULT` carrying `K1` or higher-order content, by
the hard-edge mechanism above. It leaves the fringe term of the `K0`-order
linear map exactly as `FRINGE` alone sets it.

## `SEXT`/`OCT` `DISFRIN` hard-edge fringe

Unlike `BEND`, `QUAD`, and `MULT`, `SEXT` and `OCT` have no soft-edge fringe
keyword at all. The parser rejects `FRINGE`, `F1`, `F2`, `FB1`, `FB2`,
`F1K1F`, `F2K1F`, `F1K1B`, and `F2K1B` outright. This was confirmed
empirically, not inferred from the absence of a converter path
(`tests/sad/test_sext.py` and `test_oct.py`, `REJECTED_PARAMS`).

The cause is traceable to source. In the per-element-type parameter setup
switch of `tffs.f`, the `icSEXT`/`icOCTU`/`icDECA`/`icDODECA` case derives
only the sine and cosine of `ROTATE`. It has no `FRMD` or `FRIN` handling,
so there is no keyword slot for the parser to recognise.

Both elements do accept `DISFRIN`. It gates the same generic hard-edge
fringe kick mechanism as `BEND` and `QUAD`, through `ttfrin`, reached from
the `tthin` tracking routine. The kick applies identically at **both** the
entrance and the exit, with no per-side control. These elements have no
`FRINGE` mode to select a single side, the way `QUAD` does.

`DISFRIN` defaults to `0`, which enables the kick, and it is strictly
boolean. Values `1, 2, -1, 3, 0.5` are all bit-identical to `DISFRIN=1`,
confirmed against the real binary and pinned
(`test_sext_disfrin_hard_edge_matches_sad_reference_values` and
`test_oct_disfrin_hard_edge_matches_sad_reference_values`).

Because these elements have no `FRINGE` keyword, the `QUAD`-specific
interaction where `FRINGE` gates the side of the `DISFRIN` kick does not
arise here.

## RF focusing in accelerating `MULT`/`CAVI` elements

SAD's accelerating-element tracking, `tmultiacc` in `tmulti.f`, applies an
explicit transverse RF-focusing kick whenever `RFSW` is on and `VOLT != 0`.
The kick is quadratic in `x` and `y`, and proportional to `(V*omega/p)^2`.
It is applied on top of the ordinary multipole kick and the momentum update.

The kick is present **regardless of `TRPT`**. Its coefficient, `vcorr` in
the source, is computed from the entry and exit reference energy either way.
Under the default `RING`/`NOTRPT`, the exit reference energy equals the entry
value, which gives a nonzero `vcorr = v*(w/p0)^2/4` rather than zero.

This is the standard Rosenzweig-Serafini RF-focusing effect for
standing-wave-like accelerating structures, not a SAD peculiarity
(Rosenzweig, J. & Serafini, L., "Transverse particle motion in
radio-frequency linear accelerators", *Phys. Rev. E* **49**, 1599 (1994),
DOI [10.1103/PhysRevE.49.1599](https://link.aps.org/doi/10.1103/PhysRevE.49.1599)).
It depends only on `VOLT`, `FREQ` or `HARM`, and the reference momentum. It
applies to a plain accelerating `CAVI` as much as to a combined K1+VOLT
`MULT`.

`vcorr` has no explicit dependence on the RF phase `PHI`. It depends only on
the entry and exit reference momentum, `p0` and `pe`. Its phase dependence is
therefore indirect, through `pe`, which differs from `p0` whenever the
element imparts a net energy change.

This was confirmed empirically (`tests/sad/test_mult.py`). The kick is
nonzero even exactly at `PHI = 0`, SAD's RF zero-crossing. There the net
energy gain is exactly zero and `pe = p0`, so `vcorr` reduces to the fixed
value `v*(w/p0)^2/4`. Moving towards the accelerating crest, where `pe`
diverges further from `p0`, the kick grows by more than a factor of 10 in the
locked-in test. The effect is present at every phase, including the
zero-crossing. It is not switched on and off by phase.

Xsuite's `xt.Cavity` has no such term. `Cavity_track_local_particle`
(`xtrack/beam_elements/elements_src/cavity.h`) calls the shared RF-kick
routine with `order = -1, knl = NULL`, which disables the entire `x` and
`y`-dependent kick block in `track_rf.h`.

This was confirmed by tracking, not only by reading the source. For a 1 m
accelerating element at `MOMENTUM = 0.05 GeV` and `VOLT = 1e8`, with TRPT
and RFSW on, SAD's own tracked transfer matrix has a sizeable `x -> px`
coupling term: `M21 = -0.183` for a pure accelerating drift with no
quadrupole at all, where a plain drift gives exactly zero. An Xsuite
reconstruction of the same case, using `Multipole` + `Cavity` +
`ReferenceEnergyIncrease` slices, gives *exactly* zero `M21`.

Both tracked matrices satisfy `det(M) = p_entry/p_exit`. This confirms that
the two codes are compared in the same canonical, local-momentum-normalized
convention, so the difference is not an artefact of mismatched Twiss
normalization. Note that Xsuite's own `line.twiss()` applies a further, and
separately real, `p_exit/p_entry` scaling to `betx` on top of this raw
matrix. Do not conflate that scaling with the RF-focusing question.

`tests/xtrack/test_cavity.py` locks this in.

## `CAVI` `FRINGE`/`DISFRIN` RF edge-focusing kick

A `CAVI` with `VOLT != 0` applies a genuine edge-focusing kick at each end,
through `tcavfrin` in `tcav.f`. This is separate from the `vcorr` body term
above. It is linear in `x` and `y`, not quadratic like `vcorr`, and it is not
shared with `MULT`.

`CAVI` rejects the soft-edge fringe parameters used by `QUAD`, `BEND`, and
`MULT`: `F1`, `F2`, `FB1`, `FB2`, `F1K1F`, `F2K1F`, `F1K1B`, and `F2K1B`.
This was confirmed empirically (`tests/sad/test_cavi.py`, `REJECTED_PARAMS`).
It accepts its own `V1`/`V20`/`V11`/`V02` transverse RF-multipole
coefficients instead. These are confirmed accepted, but their physics is out
of scope for this pass.

`DISFRIN` gates the edge kick with the usual convention. It defaults to `0`,
which enables the kick, and it is strictly boolean. It is pinned against real
SAD binary output (`test_cavi_disfrin_default_matches_explicit_zero`,
`test_cavi_disfrin_is_boolean`, and
`test_cavi_fringe_disfrin_matches_sad_reference_values`).

**`CAVI`'s `FRINGE` is a third distinct numbering system.** It differs from
`BEND`'s sign-based scheme and from the strict `{1,2,3}` membership test used
by `QUAD` and `MULT`:

| `FRINGE` | Effect |
| --- | --- |
| `0`, unset, or any value other than exactly `1` or `2` | both edges enabled |
| `1` | entrance only |
| `2` | exit only |
| any negative value | kick disabled entirely, matching `DISFRIN=1` |

This full grid was confirmed against the real binary
(`test_cavi_fringe_mode_gates_entrance_exit`), and traced to `tcav.f`. The
entrance kick is gated by `fringe .and. mfring >= 0 .and. mfring /= 2`, and
the exit kick by `fringe .and. mfring >= 0 .and. mfring /= 1`.

The `mfring >= 0` clause is what makes any negative value a master-disable.
This is structurally distinct from `QUAD`'s `mfring .gt. -4` threshold, and
from `MULT`'s complete absence of a lower bound.

## Bend element-offset (`DX`/`DY`) reference-orbit convention

A `DX`/`DY` misalignment on a curved element admits two defensible physical
readings. This applies to a `BEND` with `ANGLE != 0`, thick or thin.

- **An alignment error.** The design orbit and its curvature `h` stay fixed.
  The quantity of interest is the orbit distortion relative to the unmoved
  design.
- **A deliberate offset.** The reference orbit follows the displaced element,
  and the curvature reflects the displaced geometry.

Xsuite's curved elements are built on the first reading. SAD's behaviour is
closer to the second: it reconstructs its reference orbit through the
displaced element rather than keeping it fixed.

This was confirmed empirically, not assumed. The test uses a simple
two-element `START`/`END` open line with `betx = bety = 1` initial
conditions. Xsuite's own `x` for a thick bend, or `dx` for a thin bend, is
numerically zero at the exit regardless of `ANGLE`. SAD's is nonzero. It
scales cleanly as `ANGLE^2`, growing by a consistent factor of about 4 per
angle doubling, and matches `DX*(1-cos(ANGLE))` to within about 1%. This is
consistent with a rigid displacement of a curved element whose curvature
direction is unchanged.

The thin representation shows the same residual in the dispersion column
`dx` rather than the orbit column `x`, and with the opposite sign,
`-DX*(1-cos(ANGLE))`. There is no reason in principle for an orbit residual
and a dispersion residual to share a sign convention.

This quantification is distinct from, and independently derived from, the
open issue's own four-case `x_corr` grid. That grid reports a different
`ANGLE^2`-against-`ANGLE^4` scaling pattern, for a different observable. The
two have not been reconciled. Do not assume they describe the same number.

The residual is not confined to the orbit/dispersion column. Confirmed
empirically, per representation:

- **Thick bend.** `zeta`, the dispersion `dx`, `betx`, `bety`, `alfx`, and
  `alfy` all diverge alongside `x` at every angle tested: `0.025`, `0.05`,
  and `0.1`. `px` also diverges, but at `ANGLE^4`, which is faster than the
  rest. It clears the standard `(1e-9, 1e-5)` comparison tolerance only from
  `ANGLE≈0.05` upward, not at `0.025`. `s`, `y`, `py`, `delta`, `dpx`, and
  `dpy` all match.

  This `px` divergence is confirmed distinct from the unrelated `MULT`
  `K0`/`SK0` `ANGLE^4` fringe-order mismatch described above. A plain bend
  with `DX=DY=0`, at the same three angles, matches SAD on all 15 columns
  with no divergence anywhere. The divergence here is therefore genuinely
  triggered by the offset. It is not the unrelated fringe-order effect appearing
  in these columns.
- **Thin bend.** Only `dx` and `zeta` diverge. `x`, `px`, `y`, `py`, `delta`,
  `betx`, `bety`, `alfx`, and `alfy` all match exactly. A zero-length element
  has no separate betatron distortion of its own.
- **Combined `DX`+`DY`.** The result is a clean superposition of the pure
  `DX` residual on every column, for both thick and thin bends. The
  contribution of `DY` is zero to numerical noise.

  There is one exception. A genuine but tiny cross-term, of order `1e-9`,
  appears in the `dx` column of a thick bend when `DX` and `DY` are
  simultaneously nonzero. It clears tolerance only at the largest angle
  tested, `0.1`.
- **Tracking**, as opposed to twiss and closed-orbit. The same residual
  appears as a divergence on `x`, `px`, and `zeta` for the thick bend, and on
  `x`, `y`, and `zeta` for the thin bend. The thin-bend `x` and `y`
  divergence is a small rigid shift of order `1e-8`, identical for every
  particle regardless of its own initial coordinates. `y`, `py`, and `delta`
  still match for the thick bend, as do `px`, `py`, and `delta` for the thin
  bend.

Four tests in `tests/conversion/elements/test_bend.py` lock this in. For
twiss, extended to the combined-offset case and the columns above:
`test_bend_offset_orbit_residual_is_angle_squared_order` and
`test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order`. For
tracking: `test_bend_offset_orbit_residual_diverges_in_tracking` and
`test_bend_offset_thin_bend_dispersion_residual_diverges_in_tracking`.

Correctors (`ANGLE == 0`) and `MULT`-derived dipoles never carry a nonzero
curvature, and are confirmed unaffected. This covers both the
`user_multipole_replacements` `"Bend"` path and the dipole-simplification
path of `SIMPLIFY_MULTIPOLES`.

See [element conversion](../converter/elements.md) for the resulting
converter warning.

### Combined with `ROTATE`: a further, separate coupling artifact

Combined with a nonzero `ROTATE`, the residual above also perturbs `betx`,
`bety`, `alfx`, and `alfy`. A further, separate SAD-side artifact appears on
top of it.

SAD's own reported linear coupling parameters, `R1` to `R4`, become
discontinuous for a rotated, offset, curved element the instant the offset is
nonzero. They sit on `sin(ROTATE)` or `cos(ROTATE)`, whichever is smaller.
The branch switches at a fixed angle of about 52.3°, not at 45° as it first
appeared. The value is essentially independent of the magnitude and direction
of the offset. A real coupling effect would instead scale with the offset and
vanish as the offset vanishes.

The following points are confirmed.

- **It is not an Edwards-Teng/Mais-Ripken twiss-convention mismatch**, as
  described below. Xsuite's own independently-computed Edwards-Teng coupling
  stays small and continuous in the offset throughout. It is specifically
  SAD's reported `R1`-`R4` that jumps.
- **It is not a sad2xs converter bug.** `ROTATE`, `DX`, and `DY` pass
  straight through to `xt.Bend`'s `rot_s_rad`, `shift_x`, and `shift_y`
  unchanged. The anomaly reproduces identically in pure SAD, with no
  converter involved.
- **It requires curvature specifically.** The identical `ROTATE` and offset
  combination shows no such effect on a `QUAD`, which has real
  rotation-induced coupling of its own that is much larger than the bend's
  baseline, nor on a `MULT` with an equivalent dipole field. The offset makes
  no difference in either case.
- **It is not proportional to the offset.** Changing `DX` over six orders of
  magnitude, from `1e-12` to `0.1` m, produces no meaningful change in the
  reported value. The jump is a hard discontinuity at exactly `DX=0`, with no
  smooth crossover at any scale tested.
- **The 52.3° branch point is a fixed constant.** It is confirmed insensitive
  to `ANGLE`, to `DX` magnitude, and to element length.
- **It is not confined to the axis carrying the offset.** This was confirmed
  at `ROTATE = +-pi/2`, in addition to the `pi/4` case originally
  investigated.

  `betx`, `bety`, `alfx`, and `alfy` still diverge by the same order of
  magnitude even when the offset lies entirely on the axis that tracking
  matches SAD on exactly. `DX` at `ROTATE = +-pi/2` is such a case, and
  `test_bend_conversion_matches_sad_tracking_for_rotated_element_offsets`
  asserts it is a full tracking match. Tracking never computes twiss
  parameters, so the divergence is invisible there whichever axis carries the
  offset. Only a dedicated twiss-side comparison sees it.

  Quantified at `ROTATE=pi/4` and `ANGLE=0.05`: `betx` and `bety` diverge by
  about `1.3e-3`, and `alfx` and `alfy` by about `2.9e-3`. This is three
  orders of magnitude past the normal `(1e-9, 1e-5)` twiss tolerance. Like
  `R1`, these values barely change between two offset magnitudes three orders
  of magnitude apart, which is the same magnitude-independent signature.

  Two tests lock this in:
  `test_bend_conversion_matches_sad_twiss_for_rotated_element_offsets` for
  the general case across all axes, and the `betx`/`bety`/`alfx`/`alfy`
  assertions in `test_bend_offset_rotated_coupling_is_a_sad_side_artifact`
  for the `pi/4` case specifically.

The committed regression tests lock in a narrower slice than was explored.

`test_bend_offset_rotated_coupling_is_a_sad_side_artifact` checks `DX` in
`[1e-6, 1e-3]` at one fixed `ANGLE=0.05` and `ROTATE=pi/4`.
`test_bend_conversion_matches_sad_twiss_for_rotated_element_offsets` checks
`ROTATE = +-pi/2` with `(DX,DY)` in `{(1e-3,0), (0,-1e-3), (1e-3,-1e-3)}` at
one fixed `ANGLE=0.1`.

The wider claims above are not regression-locked. These are the `DX`
insensitivity over six orders of magnitude, from `1e-12` to `0.1`, and the
independence of both the effect and the 52.3° branch point from `ANGLE` and
element length. They were established through a standalone empirical scan
over 58 independent native-SAD runs, which is not part of the committed test
suite.

If the narrower slice covered by the committed tests ever starts passing in
the "matches" direction, re-check this wider characterisation too, not only
the committed assertions.

Working hypothesis (not confirmed against SAD source — no further
diagnosis was possible without it): this ties to the same reference-orbit
reconstruction described above. Once the displaced curved element is also
rotated, SAD's reconstructed downstream frame plausibly ends up tilted by
close to the geometric `ROTATE` angle relative to the design frame (unlike
Xsuite's fixed-frame convention. `R1`-`R4` measure frame mismatch, so they
pick that tilt up as if it were dynamical coupling.

The 52.3° branch switch looks like a separate, purely numerical detail
internal to SAD's own decomposition algorithm, such as a branch cut or an
eigenvalue-ordering threshold. It appears to have no direct physical meaning.
It is completely insensitive to every physical parameter tested, which a real
physical crossover would not be.

Three tests in `tests/conversion/elements/test_bend.py` lock this in:
`test_bend_offset_rotated_coupling_is_a_sad_side_artifact`,
`test_bend_conversion_matches_sad_twiss_for_rotated_element_offsets`, and
`test_bend_conversion_matches_sad_tracking_for_rotated_element_offsets`.

They assert the directly observable evidence rather than a full mechanistic
explanation:

- SAD's `R1` tracks `sin(ROTATE)` regardless of offset magnitude;
- Xsuite's own coupling stays small and continuous;
- `betx`, `bety`, `alfx`, and `alfy` diverge on every axis;
- tracking coordinates match or diverge exactly as in the unrotated case,
  with the axes swapped.

## Twiss conventions in coupled regions (skew quads, solenoids, ...)

SAD's `twiss_sad` output reports coupled optics in the **Edwards-Teng**
decoupled normal-mode parametrisation, propagated from the line start. This
is the same convention MAD-X uses. It applies to the `betx`, `bety`, `alfx`,
and `alfy` columns.

SAD's `R1`-`R4` columns are the Edwards-Teng decoupling matrix, normalised as
`R / sqrt(1 + det R)`. They are not the raw decoupling matrix. This was
verified to about `1e-9` on both the skew-quad and the solenoid case, through
`coupled_optics.normalized_r_matrix()`.

Xsuite's `line.twiss4d()` and `twiss6d()` report something different by
default. Their `betx`, `bety`, `alfx`, and `alfy` fields are the **mode-1**
and **mode-2** Mais-Ripken eigenmode components only. The cross-mode leakage
terms sit in separate `betx2`, `bety1`, `alfx2`, and `alfy1` columns.

Xsuite can compute Edwards-Teng parameters natively with
`coupling_edw_teng=True`, but only for periodic lines.
`sad2xs.xsuite_helpers.propagate_edwards_teng` covers the open-line case, so
converted transfer lines can be compared against SAD through coupled
regions. See
[SAD helpers](../helpers/sad-helpers.md) for the practical usage.

The convention map, established empirically (each case anchored by SAD and
Xsuite 4x4 transfer-matrix equality at the 1e-10 level, so the twiss
residuals below are purely parametrisation, not physics):

| case | Edwards-Teng | Mais-Ripken projected sums (`betx1+betx2`, ...) | plain mode values |
|------|--------------|--------------------------------------------------|-------------------|
| skew-quad line | matches SAD (≤1e-9) | off by ~3e-5 (beta), ~2e-4 (alfa) | off by ~2e-5 |
| solenoid line (`BZ=1.5`) | matches SAD (≤5e-10) | identical to Edwards-Teng (≤2e-15) | off by ~5% |
| uncoupled line | matches SAD (≤1e-9) | identical to Edwards-Teng | identical to Edwards-Teng |

Two traps this map removes:

- **The projected sums are not SAD's convention**, even though they match it
  exactly for solenoids. Rotational solenoid coupling is a special case, in
  which the Mais-Ripken projected sums numerically coincide with the
  Edwards-Teng values. For skew-quad coupling they disagree with SAD by more
  than the plain mode values do. An earlier hypothesis recommended the
  projected sums on the solenoid evidence alone. Checking the skew-quad case
  showed that hypothesis to be wrong.
- **SAD's `R1`-`R4` carry a normalisation** of `1/sqrt(1 + det R)`. They are
  therefore not directly the raw Edwards-Teng decoupling matrix components.

`tests/conversion/test_coupled_twiss_convention.py` locks these facts in, and
asserts both the agreement and the disagreement.

The solenoid mismatch was originally misdiagnosed as a reference-frame issue
in SAD's solenoid GEO exit transform. It is not. The mismatch is already
present inside the solenoid body itself, before any reference-frame transform
is applied, and it scales cleanly as `(Ks*L)^2`.

An independent from-scratch derivation of the exact solenoid transfer matrix
matches SAD's reported `betx` exactly. That derivation linearizes Xsuite's own
documented solenoid Hamiltonian, and was cross-checked against a
central-difference Jacobian built directly from Xsuite's own tracking. This
confirms that the underlying physics of both codes agrees, in Hamiltonian and
in tracking. The gap is purely a reporting convention.

`R1`-`R4` are not a SAD-specific quantity. They are the standard Edwards-Teng
coupling matrix, which Xsuite already computes natively with
`coupling_edw_teng=True`. Nothing about the coupling calculation itself
needed to be requested upstream. The solenoid fringe kick described above was
the only genuine physics gap raised with the Xsuite side, and it was declined
for the reasons given there.

## `LINE X = (-Y);` reversal is a MAIN-file declaration, not a live command

SAD's beamline-reversal syntax, `LINE X = (-Y);`, defines a new named line as
the reverse of an existing one. It belongs to the MAIN-file declaration
grammar that `GetMAIN` parses. This is the same statement class as `BEND`,
`QUAD`, and `LINE` element and line definitions.

It is **not** a live FFS command. Issuing it as a runtime statement, after
`GetMAIN` has already loaded the file, fails when the resulting name is passed
to `USE`. The errors are `???General::wrongtype: Argument must be
BeamLine[ ... ]:` and `???-FFS-Error-Missing beamline in USE.`

This was confirmed by direct probe. `GetMAIN["./file.sad"]; USE FWD;
LINE REV = (-FWD); USE REV;` fails with the errors above. Defining
`LINE REV = (-FWD);` inside `file.sad` itself, so that it is present when
`GetMAIN` parses the file, and then running `USE REV;`, succeeds.

The error handling of `run_sad` does not catch this failure mode. SAD exits 0
and prints the error to stdout instead of raising. A caller that does not
inspect the console output therefore gets a silently degenerate result rather
than an exception. One reproduction returned
`name: ['$DUMMYMARK', '$DUMMYDRIFT']`, `betx: [inf, inf]`, and
`alfx: [nan, nan]`.

**Consequence.** `reverse_element_order=True` in
`sad2xs.sad_helpers.twiss_sad` and `survey_sad` reverses the already-`USE`'d
beamline live instead, through `LINE <name> = -ExtractBeamLine[];
USE <name>;`. `ExtractBeamLine[]` is a runtime FFS function that returns a
`BeamLine[...]` object directly. It is not part of the MAIN-file declaration
grammar, so the restriction above does not apply to it.

This was verified directly against real SAD. It gives bit-for-bit identical
Twiss and survey results to a `LINE REV = (-FWD);` declared natively in the
lattice file. It also matches element names exactly, where an earlier
workaround based on a temporary lattice file matched them only partially.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
