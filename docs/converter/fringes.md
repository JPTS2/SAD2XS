# Fringe models

How SAD's fringe fields are imported, and which are not modelled.

SAD does not have one fringe mechanism. It has several, they are controlled by different parameters, they use different numbering conventions, and they are implemented by different SAD subroutines. SAD2XS imports some of them.

This page covers every fringe mechanism SAD applies. For what SAD itself does in each case, see [SAD behaviour notes](../reference/sad-behaviour.md).

**On this page:**

- [What is imported](#what-is-imported)
- [FRINGE means three different things](#fringe-means-three-different-things)
- [Bend fringe](#bend-fringe)
- [Quadrupole fringe](#quadrupole-fringe)
- [Multipole fringe](#multipole-fringe)
- [Sextupole and octupole fringe](#sextupole-and-octupole-fringe)
- [Cavity fringe](#cavity-fringe)

## What is imported

| Element | Mechanism | SAD control | SAD2XS |
| --- | --- | --- | --- |
| `BEND`, `CORRECTOR` | soft-edge | `FRINGE`, `F1`, `FB1`, `FB2` | **imported** as `fint`/`hgap`, on by default |
| `BEND` | hard-edge | `DISFRIN` | edge model applied unconditionally; `DISFRIN` not read |
| `QUAD` | soft-edge, linear | `FRINGE`, `F1`, `F2`, `F1K1F`, `F1K1B`, `F2K1F`, `F2K1B` | **imported** as a Taylor map, on by default |
| `QUAD` | hard-edge | `DISFRIN`, plus `FRINGE` side gating | edge model applied unconditionally; neither read |
| `MULT` | K1 soft-edge, linear | `FRINGE`, `F1`, `F2`, per-face K1 terms | **imported** with zero BZ, on by default |
| `MULT` | dipole soft-edge and generic hard-edge | `FB1`/`FB2`, `DISFRIN` | not imported |
| `MULT` | `K0`/`SK0` dipole fringe | — | not reproduced; converter warns |
| `SEXT`, `OCT` | hard-edge | `DISFRIN` | not modelled |
| `CAVI` | RF edge-focusing kick | `FRINGE`, `DISFRIN` | not modelled |
| `SOL` | fringe kick | `DISFRIN` | not modelled; converter warns — see [solenoids](solenoids.md) |

Three private `Config` flags control the imports: `_import_sad_bend_fringes`, `_import_sad_quad_fringes`, and `_import_sad_mult_fringes`. All default to `True`.

Every fringe parameter must be a concrete number. A deferred (symbolic) expression raises a clear error rather than silently producing wrong values.

## FRINGE means three different things

`FRINGE` does not use one numbering system. It uses three, depending on the element type. This is the easiest thing to get wrong when reading a SAD file.

| Element | Convention |
| --- | --- |
| `BEND` | sign-based: `> 0` both edges, `-1` entrance only, `-2` exit only, `<= -3` neither, `0` no import |
| `QUAD`, `MULT` | membership: `1` entrance only, `2` exit only, `3` both. `<= -4` is a master disable on `QUAD`'s hard edge |
| `CAVI` | `1` entrance only, `2` exit only, anything else non-negative enables both, any negative value disables entirely |

`SEXT` and `OCT` have no `FRINGE` keyword at all.

## Bend fringe

### Soft-edge: imported

The bend soft-edge fringe fits Xsuite's native edge model, so no extra element is needed. For each edge that `FRINGE` activates:

```text
edge_entry_fint = F1 + FB1        edge_entry_hgap = 1/12
edge_exit_fint  = F1 + FB2        edge_exit_hgap  = 1/12
```

This applies on both bend paths: the sector-bend path where `ANGLE != 0`, and the `K0`-only corrector path where `ANGLE == 0`.

The writer serialises these four fields whenever they are non-zero. A bend or corrector that carries only `fint` and `hgap`, and is otherwise at its defaults, does not qualify for the compact one-line output form. This matters: such an element would otherwise be written with every extra attribute silently dropped.

### Soft-edge accuracy

The closed form matches SAD both on-momentum and off-momentum. Measured agreement on the tested geometries is `5e-7` on-momentum for a bend, rising to `8e-6` at `delta = +-0.05`. The corrector sits at `2.4e-5`, near-constant in `delta`.

This was not always so. Xsuite's native edge fringe formula scaled the wrong way with `delta` relative to SAD, leaving a residual of a few percent that grew with `delta` and with magnet strength. The cause was never in SAD2XS, and that was established rather than assumed:

- an independent from-scratch derivation, following Forest's PTC paper (KEK Preprint 2005-109, §B), reproduces SAD's closed form, not Xsuite's;
- real compiled PTC, driven through `cpymad`, confirms it — PTC implements the same paper's *other* formula, the one that historically matched Xsuite and MAD-NG.

The upstream fix landed in Xsuite 0.57.0, below the supported minimum. The residual it removed was large: a bend that read `3.46%` at `delta = -0.03` now reads `0.001%`.

`test_bend_fringe_import_matches_sad_off_momentum` and its corrector equivalent now assert agreement to `1e-4` relative, so a regression in the momentum scaling fails rather than passing quietly.

What remains is a small offset, not a scaling error. The corrector's `2.4e-5` barely moves with `delta`, so it is not momentum-dependent at all. The earlier percent-level error had masked it.

The writer round-trip is covered separately, by the `fint`/`hgap` tests in `test_bend_writer.py` and `test_corr_writer.py`. Conversion-level tests track the in-memory line directly, so they would not catch a writer serialisation gap.

### Hard-edge: applied unconditionally

A SAD `BEND` also carries a nonlinear hard-edge fringe kick, gated by `DISFRIN`. On a `BEND` this is completely independent of `FRINGE`: each controls its own term, with no interaction.

`DISFRIN` is a strict boolean. Unset means `0`, which **enables** the kick. Any non-zero value disables it, identically and bit-for-bit.

Xsuite already implements the same mechanism natively through the bend edge model. The agreement is close: `"full"` matches SAD's `DISFRIN=0` to about `2e-5` relative, and `"suppressed"` matches `DISFRIN=1` to about `2e-6` relative.

**SAD2XS applies `EDGE_MODEL_BEND = "full"` to every bend and never reads `DISFRIN`.** A source lattice that sets `DISFRIN=1` on a bend, intending to disable the hard-edge fringe, still gets the fringe after conversion. See [models and integrators](models-integrators.md) for why `full` is the default rather than Xsuite's `linear`.

On the corrector path the question does not arise. SAD does not allow a corrector to carry a non-zero `K1` alongside `K0` when `ANGLE` is absent or zero. This is a confirmed, separate SAD bug: the combination silently no-ops the whole element instead of raising an error. There is therefore no quadrupole content for the hard-edge term to act on.

## Quadrupole fringe

### Soft-edge: imported as a Taylor map

The quadrupole linear fringe has no equivalent native Xsuite field, so a dedicated Taylor map is the natural fit.

Each side gets an `(a, b)` pair:

```text
akk   = K1 / L

a_in  = -|akk * (F1 + F1K1F)^2| / 24        b_in  = |akk| * (F2 + F2K1F)
a_out = -|akk * (F1 + F1K1B)^2| / 24        b_out = |akk| * (F2 + F2K1B)
```

A side is only built if `FRINGE` activates it **and** it is numerically non-trivial, so no placeholder identity map is ever created.

A quadrupole with no length is a no-op. SAD itself defines `F1 = F2 = 0` for a thin `QUAD`.

### What the Taylor map truncates

SAD's kick is non-polynomial in `delta` — it contains `exp(a/(1+delta))` and `1/(1+delta)**2` terms. The converter Taylor-expands to `O(delta)` and builds an `xt.SecondOrderTaylorMap`.

The expansion is a hand-derived closed form, cross-checked to machine precision against an independent symbolic derivation over a wide `(a, b)` grid. It is not evaluated symbolically at runtime.

This is exact for the electron and positron lattices it targets, where Xsuite's `pzeta` equals SAD's `delta`. It is **not** verified for lower-`beta0` species.

### The compound sub-line

A SAD `QUAD` can become up to three Xsuite elements, so the converter wraps them:

```text
[entrance fringe?, quadrupole body, exit fringe?]
```

The physical quadrupole body keeps the element's bare SAD name. Only the wrapping sub-line is renamed, to `{name}_compound`, because an Xsuite environment cannot have an element and a line sharing one name. Any component reference to the bare name is transparently redirected onto the compound.

Keeping the body's bare name matters beyond cosmetics. Twiss alignment originally matched SAD's element row to the body, which is already past the entrance fringe kick — a silent discrepancy in the comparison itself, unrelated to whether the fringe physics was right. It was fixed by treating `_fringe_in` and `_fringe_out` as compound pieces of one placement, the same mechanism already used for the solenoid boundary compound.

### Surviving a line reversal

Each fringe map stores the source-neutral `(a, b, frame_rotation)` it was
built from as plain attributes: `_sad_k1_fringe_a`, `_sad_k1_fringe_b`, and
`_sad_k1_fringe_frame_rotation`.

These are ordinary Python attributes, not xofields. Xsuite has no field for them, but the object carries them through line building and `line.mirror()`. This lets the reversal step rebuild each map's coefficients in place under `-LINE` or `reverse_element_order`. Only the surviving side's `a` flips sign; `b` and `theta` are unchanged.

### Requires Xsuite 0.59.0

The import builds an `xt.SecondOrderTaylorMap` through `env.new`. Xsuite 0.58.0 is the first release to support that.

The supported minimum is higher. Xtrack 0.111.0, shipped in Xsuite 0.59.0, split `xtrack.twiss` from a module into a package, and the project tracks current Xsuite rather than pinning behind it.

### Hard-edge: applied unconditionally, and it does not compose additively

A `QUAD` also carries a `DISFRIN`-gated hard-edge kick, with the same boolean convention as the bend.

Unlike the bend, `FRINGE` on a `QUAD` is **not** independent of `DISFRIN`. It additionally selects *which side* of the hard-edge fringe applies, whatever `DISFRIN` is set to. The entrance hard-edge kick is skipped whenever `FRINGE == 2`, and the exit one whenever `FRINGE == 1`. `FRINGE <= -4` disables both sides unconditionally.

The scale of this effect is easy to underestimate. The hard-edge contributions of the two sides largely cancel when both are present. Losing one side is therefore not a small correction: the effect is more than an order of magnitude larger than the net two-sided residual that `DISFRIN` alone removes.

A direct consequence: the linear and hard-edge fringes on a `QUAD` do **not** compose additively for every `FRINGE` value. They were confirmed additive only at `FRINGE = 3`, where neither hard-edge side is excluded.

**SAD2XS applies `EDGE_MODEL_QUAD = "full"` to every quadrupole and reads neither `DISFRIN` nor the `FRINGE` side gating for the hard edge.**

## Multipole fringe

A SAD `MULT` combines bend-style content (`ANGLE`, `K0`, soft-edge `FB1`/`FB2`) and quadrupole-style content (`K1`, soft-edge `F1`/`F2`/`F1K1F`/`F2K1F`/`F1K1B`/`F2K1B`) in one element. Its source mirrors the quadrupole's almost line for line: a `MULT` with only `K1` set gives bit-identical tracking output to the equivalent `QUAD`.

`FRINGE` uses the same `{1, 2, 3}` numbering as `QUAD`, and it selects the side for **all** of the element's fringe sub-mechanisms simultaneously — the quad-style linear fringe, the dipole-style linear fringe, and the `DISFRIN`-gated hard-edge kick all read the same value.

### K1 soft edge: imported with zero longitudinal field

The K1 part is imported with the same second-order Taylor-map machinery as a
`QUAD`. For integrated normal and skew strengths `K1` and `SK1`,

```text
akk = |K1 + i SK1| / L
a   = -akk * f1_raw^2 / 24
b   =  akk * f2_raw
theta = ROTATE + akang(K1 + i SK1)
```

The entrance map uses `a`; the exit uses `-a`. `b` keeps its sign. Both signs
of `F1` were checked against the real SAD binary: the square is literal, not
`F1*abs(F1)`. Active faces bracket the complete converted MULT body, including
a generic multipole, an auto- or user-simplified quadrupole, and an RF-sliced
body. A user replacement that discards K1/SK1 also discards the fringe and
raises a warning.

`DROT` is not applied to the converted MULT body. An active linear fringe with
nonzero `DROT` is therefore warned about and skipped rather than rotating only
one part of the element.

The map currently assumes zero overlapping longitudinal field. When it occurs
inside a powered bound-solenoid region, the body still receives the local `ks`
but conversion warns that the fringe uses the zero-BZ approximation. A targeted
SuperKEKB study found the omitted local-BZ term changed the tested IP beta
values by at most `0.094 um`, and contributed roughly `0.1%` of the target
fringe tune response. That supports the approximation for those symmetric,
`F1`-only QC cases; it is not a general exact result. A deliberately one-sided
stress case reached about `11%` relative map error.

The dipole-style `FB1`/`FB2` term and the `DISFRIN`-gated generic hard-edge
kick remain unmodelled.

### The `K0`/`SK0` dipole fringe residual

A `MULT` with only `K0` set, or only `SK0`, has a dipole-fringe contribution that Xsuite's bend and corrector edge models do not reproduce exactly.

SAD's fringe term contributes exactly `m43 = -K0^2/L` to the linear transfer matrix, or `m21` for `SK0`. Xsuite's bend edge models either add `theta^4`-order terms or give zero. The two codes therefore agree at `theta^2` and diverge at `theta^4`.

This was measured, not estimated. The difference equals `-theta^4` at leading order — between `-1.0005` and `-1.008` times `theta^4` across `theta = 0.025, 0.05, 0.1` — and scales by exactly `2^4 = 16` per doubling of `theta`.

The converter warns when a dipole-only `MULT` is simplified to an Xsuite bend or corrector element, so the residual is not silent.

## Sextupole and octupole fringe

`SEXT` and `OCT` have no soft-edge fringe at all. SAD rejects `FRINGE`, `F1`, `F2`, `FB1`, `FB2`, `F1K1F`, `F2K1F`, `F1K1B`, and `F2K1B` outright on these element types. That was confirmed empirically against the parser, not inferred from the absence of a converter path.

They do accept `DISFRIN`, which gates the same generic hard-edge kick mechanism shared with `BEND` and `QUAD`. It applies identically at both entrance and exit, with no per-side control, because there is no `FRINGE` mode to select a side.

SAD2XS does not model this.

## Cavity fringe

A `CAVI` with `VOLT != 0` applies a genuine edge-focusing kick at each end, linear in `x` and `y`. It is separate from the RF-focusing body term, and it is not shared with `MULT`.

`CAVI` rejects the quadrupole and bend style soft-edge parameters entirely. It accepts its own `V1`, `V20`, `V11`, and `V02` transverse RF-multipole coefficients instead.

`DISFRIN` gates the edge kick with the usual boolean convention. `FRINGE` uses the third numbering system described above.

SAD2XS does not model the cavity edge kick. See [element conversion](elements.md) for the related RF-focusing body term.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
