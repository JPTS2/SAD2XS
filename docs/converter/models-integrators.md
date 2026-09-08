# Models and integrators

The tracking model, integrator, and kick count chosen for each element type, why those choices were made, and why the alternatives were rejected.

Xsuite lets each element choose how it is tracked. SAD2XS sets these choices explicitly for every element type it converts. The defaults live in `sad2xs/config.py` and are applied in `sad2xs/main.py`. Every value is overridable through `Config`.

**On this page:**

- [How these choices were made](#how-these-choices-were-made)
- [Current defaults](#current-defaults)
- [Why `adaptive` is never used](#why-adaptive-is-never-used)
- [Choosing the model](#choosing-the-model)
- [Choosing the integrator](#choosing-the-integrator)
- [Choosing the kick count](#choosing-the-kick-count)
- [Edge models](#edge-models)
- [Solenoids](#solenoids)
- [Cavities](#cavities)
- [Multipole thickness](#multipole-thickness)
- [Known gap: radiation against SAD](#known-gap-radiation-against-sad)

## How these choices were made

Each choice was derived against three factors:

- **Tracking performance.** Does the choice reproduce the correct physics, and how fast does it converge?
- **Radiation performance.** Does it radiate the right amount, on average and statistically?
- **Cost.** Real lattices have hundreds to thousands of elements. The target is the best practical choice within a small kick budget, not the asymptotic limit.

Every element was cross-checked against SAD, an independent validated tracking code, not only against Xsuite's own internal convergence.

One methodological point matters for reading any claim below. The sigma of a single quantum-radiation trial is not reliable evidence of convergence.

Every "settled by N kicks" claim was therefore verified with five independent repeated trials at a fixed configuration. The check is whether the results scatter around zero, or sit consistently to one side.

That method caught two real biases that a single-trial sweep would have missed: 1.2% for Multipole at 20 kicks, and 0.27% for UniformSolenoid at 20 kicks.

## Current defaults

| Element | `model` | `integrator` | Kicks |
| --- | --- | --- | --- |
| Drift | `exact` | — | — |
| Bend | `bend-kick-bend` | `uniform` | 20 |
| Quadrupole | `mat-kick-mat` | `yoshida4` | 14 |
| Sextupole | `mat-kick-mat` | `yoshida4` | 14 |
| Octupole | `mat-kick-mat` | `yoshida4` | 14 |
| Multipole | `mat-kick-mat` | `yoshida4` | 14 |
| Cavity | `drift-kick-drift-exact` | `yoshida4` | — |
| Solenoid | no `model` attribute | `yoshida4` | 14 (two 7-kick blocks) |

A zero-angle SAD `CORRECTOR` converts to a plain `xt.Bend`, so correctors follow the Bend row.

`EDGE_MODEL_BEND` and `EDGE_MODEL_QUAD` both default to `full`.

## Why `adaptive` is never used

`adaptive` is Xsuite's default `model`. SAD2XS never leaves it in place.

`adaptive` was confirmed to silently resolve to the less accurate `expanded`-equivalent internal treatment for `Drift`, `Quadrupole`, `Sextupole`, `Octupole`, `Multipole`, and `Cavity` — every tested element type that has a `model` attribute.

Measured on an unpowered element tracked against SAD's plain `DRIFT`, comparing transverse position:

| Model | `x` error vs SAD |
| --- | --- |
| `Drift(model='exact')` | 0 |
| `Drift(model='expanded')` | 1.532e-06 |
| `Drift()`, the `adaptive` default | 1.532e-06 |
| `Quadrupole(k1=0, model='drift-kick-drift-exact')` | 6.9e-18 |
| `Quadrupole(k1=0)`, the `adaptive` default | 1.532e-06 |

The default lands on the expanded result in both cases. The failure is silent — nothing warns that a less accurate treatment was selected. This is the single strongest reason the converter sets `model` explicitly on every element it emits.

`Bend`'s `adaptive` behaviour was never directly tested. It is set explicitly anyway.

## Choosing the model

### What `mat-kick-mat` can and cannot shortcut

`mat-kick-mat` uses a closed-form thick map where one exists, and thin kicks where one does not.

A closed-form shortcut exists only for:

- `k0` and `h` on a Bend;
- `k1` on a Quadrupole.

Everything else is always thin-kicked, whatever the model: `k1s`, `k2`, `k2s`, `k3`, `k3s`, any Multipole `knl`/`ksl` content at any order, and Sextupole and Octupole strengths.

This is why Sextupole, Octupole, and Multipole need a real kick budget for tracking, while a bare `k1` quadrupole or `k0` bend does not. Radiation still needs its own resolution even where tracking is exact.

### Bend uses `bend-kick-bend`

A systematic study measured a real bias in `mat-kick-mat` against an exact reference: about `3.8e-6` for a corrector, growing with multipole order to about `1.4e-4` for an octupole-like term.

`bend-kick-bend` removes that bias for the bend and corrector case. Adopting it closed a corrector-specific discrepancy entirely — all 14 previously failing `test_corrector.py` instances passed. That discrepancy was a pure model-choice bias, not a sign error or a converter bug.

It did not close the bend element-offset discrepancy, a `DX` offset combined with a non-zero `ANGLE`. That was confirmed structural and unaffected by kick count. See [element conversion](elements.md).

### Quadrupole, Sextupole, Octupole and Multipole use `mat-kick-mat`

The alternative here is `rot-kick-rot-high-order`. It is more accurate in isolated single-element tests. It is not used, because it fails on a real lattice.

The failure needs a tilted thick element in a strongly x-y-coupled region, such as a skew-tilted quadrupole next to a solenoid. Repeated passage around a periodic ring then amplifies a bias that is small in a single pass. An isolated single-element test cannot show this.

The symptom is severe, and it is easy to miss. Single-pass tracking looks correct. The periodic closed-orbit solution does not: on the FCC-ee solenoid lattice, the `bety` peaks come out at roughly half their correct height.

`mat-kick-mat` does not have this problem at the same kick count. Its disadvantage in isolated-element accuracy is real, and it is outweighed by a failure that affects a lattice SAD2XS is used on.

## Choosing the integrator

`uniform` and `yoshida4` fail in opposite directions, so neither is correct everywhere.

`yoshida4` places its internal sub-kicks at fixed fractional positions, chosen to cancel the operator-splitting error of the overall map. This gives an excellent tracking order. It also means radiation occurs at a few clustered locations, rather than spread along the element.

`uniform` spreads its kicks across the real length of the element. This is what fidelity of the radiation trajectory spread needs.

For every element where this was tested — bend, quadrupole, and solenoid — `uniform` gives better radiation trajectory-spread fidelity than `yoshida4`, at comparable or lower cost.

The resulting rule:

- **Bend and corrector use `uniform`.** Radiation fidelity is a first-order concern for them. A wiggler is physically modelled as a strong corrector, so correctors are treated like bends by default, rather than as weak incidental orbit correctors.
- **Quadrupole, Sextupole, Octupole and Multipole use `yoshida4`.** Radiation is a secondary concern for a normally configured element of these types, so the large tracking advantage of `yoshida4` wins the trade.

Switch an individual element to `uniform` where its radiation fidelity does become a first-order concern, such as at large dispersion or at a large closed-orbit offset.

Radiation needs its own kick resolution whether or not the tracking is exact. This holds for bend, quadrupole, and solenoid alike. Even where the tracking map is closed-form and independent of kick count, the mean radiated energy still needs real spatial resolution to converge. The quantum trajectory spread needs it more.

## Choosing the kick count

### `yoshida4` batches kicks in groups of seven

`yoshida4` internally batches kicks into groups of seven sub-stages:

```text
num_slices = ceil(num_multipole_kicks / 7)
```

Results are bit-identical for any kick count mapping to the same slice count. The slice count, not the nominal kick number, is the real cost lever.

| Kicks | Slices | Relative cost |
| --- | --- | --- |
| 8–14 | 2 | 1.00x |
| 15–21 | 3 | ~1.50x |
| 22–28 | 4 | ~2.00x |

One consequence is worth knowing. 14 kicks and 10 kicks cost exactly the same and produce bit-identical output. On a 2-million-particle timing benchmark they measured 837 ms against 836 ms. Choosing 14 over 10 therefore looks more precise without being more precise.

### Why 14 and not 21

The per-element convergence studies landed on two slices for the quadrupole, and three for the sextupole, octupole, and multipole. The standard recommendation of the study was therefore 21 kicks, which covers all of them with margin.

SAD2XS uses 14. This is a deliberate trade. Dropping from three slices to two is a genuine 33% speedup for quadrupole, sextupole, octupole, and multipole tracking.

The accuracy cost is real but small, and it falls specifically on the Sextupole, Octupole, and Multipole. Two slices was more than enough for the quadrupole, where the error was around `1e-9`. It is measurably short of what the sextupole, octupole, and multipole need, because their `k2` and `k3` content has no thick shortcut at all.

Raise this to 21 for a lattice dominated by strong deliberate sextupole or octupole correction.

### The bend's kick count follows a different rule

The bend uses `uniform`, which has no internal batching to align with. There is no free alignment benefit to raising its kick count, so the number is justified on its own cost-benefit terms.

Kick count controls how much of the radiation trajectory-spread signal is captured:

| Kicks | Radiation trajectory-spread signal captured | Cost against 1 kick |
| --- | --- | --- |
| 1 | ~0% | 1.0x |
| 3 | 37% | 1.4x |
| 5 | 59% | 1.7x |
| 10 | 78–80% | 2.5x |
| 20 | 92% | 4.1x |

SAD2XS uses 20. The recommendation of the study was 10. 20 was adopted to make a skew-quadrupole case pass, and it captures 92% of the signal rather than 78–80%.

For plain tracking, meaning position and angle accuracy, closed orbit, and dynamic aperture, bend convergence is already at the `1e-6` level by 3 kicks. Lowering the count is defensible for those studies. It is not defensible for damping-ring or wiggler emittance work, where the quantum-radiation trajectory spread is the effect being measured.

## Edge models

`edge='full'` is applied to every Bend. It is not Xsuite's default, which is `linear`.

`linear` misses a real `k1`-dependent edge-focusing term, even at zero pole-face angle. Measured on a combined-function bend — `angle = 0.1`, `k1 = 0.05`, `bend-kick-bend`, 256 slices — against SAD with the same parameters:

| Edge model | Max residual vs SAD |
| --- | --- |
| `linear`, the Xsuite default | 8.641e-05 |
| **`full`** | **1.331e-05** |
| `dipole-only` | 1.404e-05 |
| `suppressed` | 8.641e-05 |

`full` is 6.5 times better than the default. The improvement is converged, and it is not a slicing artifact.

A rectangular-bend hypothesis, `e1 = e2 = angle/2`, was tested separately and ruled out. It made the residual worse, at `5.5e-4`. This confirms that Xsuite's sector-bend default of `e1 = e2 = 0` already matches SAD's assumption.

## Solenoids

The solenoid has no `model` attribute, so the model choice does not apply.

Its own field, `ks` or `ks_profile`, is fully thick whatever the kick count. This includes a genuine linear ramp on `VariableSolenoid`, not only a constant field. A pure solenoid therefore needs no kick budget at all. When the solenoid also carries `knl` or `ksl` content, SAD2XS explicitly uses `yoshida4`; the configured count of 14 selects two complete seven-kick blocks internally.

A solenoid carrying additional `knl` or `ksl` content is different. Treat it like any other `yoshida4`-tracked element.

For solenoid radiation fidelity specifically, the study recommends `uniform` with 50 kicks. At 20 kicks there is a small but real bias of about 0.2–0.3%. `UniformSolenoid` and `VariableSolenoid` share one recommendation throughout.

## Cavities

A SAD `CAVI` normally converts to a zero-length `xt.Cavity`. At `length=0` every setting in the table above is irrelevant, because the element is always exactly one instantaneous kick.

`Cavity` has no radiation participation at all. It has no `radiation_flag` attribute. This is physically correct, since an RF cavity does not bend the trajectory.

## Multipole thickness

`xt.Multipole` requires `isthick=True` to represent a real finite-length element.

The default, `isthick=False`, makes length, model, integrator, and kick count all complete no-ops — the element becomes exactly one instantaneous kick. The converter sets this explicitly.

## Known gap: radiation against SAD

A large SAD-versus-Xsuite quantum radiation discrepancy is open. It grows with multipole order and with element complexity:

| Element | Discrepancy |
| --- | --- |
| Sextupole | ~6.6% |
| Multipole | ~12% |
| Octupole | ~24.5% |
| Solenoid | ~28% |

For the solenoid, an amplitude scan spanning three orders of magnitude in radius confirmed that this is **not** a fringe-field modelling mismatch. The gap is flat with amplitude. That points to a fixed proportionality or convention difference in the underlying radiated-power calculation, rather than to a geometry artifact.

The root cause is not identified for any of these elements. Treat radiation results against SAD for these element types with caution at significant amplitude.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
