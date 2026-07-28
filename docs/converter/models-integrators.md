# Models and integrators

The tracking model, integrator, and kick count chosen for each element type, and why.

*The mechanism description for this page is still being written. The decisions below are complete.*

## Design decisions

## Bend/Quadrupole/Sextupole/Octupole/Multipole model and integrator retune

Decision: `sad2xs/config.py`'s default `model`/`integrator`/`num_multipole_kicks` per element type changed from `mat-kick-mat`/`uniform`/`20` (Bend/Quad/Sext/Oct) and no explicit setting at all (Multipole) to: `bend-kick-bend`/`uniform`/`10` for Bend (and, since a zero-angle SAD corrector converts to a plain `xt.Bend`, Correctors too); `rot-kick-rot-high-order`/`yoshida4`/`14` for Quadrupole, Sextupole, Octupole, and the newly-added `MODEL_MULT`/`INTEGRATOR_MULT` for Multipole.

Reasoning: a systematic, SAD-cross-validated study found `mat-kick-mat` carries a real, measured bias against an exact reference (`~3.8e-6` for a corrector, growing with multipole order to `~1.4e-4` for an octupole-like term), and that leaving `model`/`integrator` unset (the prior Multipole behaviour) silently resolves to Xsuite's `adaptive` default, confirmed unsafe for every element type that has one. `14` kicks for Quad/Sext/Oct/Mult is a deliberate, explicit tradeoff against the study's fully-validated `21` — both map to the same `yoshida4` internal slice-count family as Bend's `10` kicks (`ceil(14/7)=2` slices vs `ceil(21/7)=3`, ~33% cheaper), at a real but small accuracy cost specifically for Sextupole/Octupole/Multipole (no thick-map shortcut exists for `k2`/`k3`/multipole content the way one exists for Bend's `k0`/`h` and Quadrupole's `k1`).

Consequence: this closed the corrector-specific discrepancy entirely (all 14 previously-failing `test_corrector.py` instances now pass) — the corrector discrepancy was a pure model-choice bias, not a sign or converter-logic bug. It did not close the remaining bend element-offset discrepancy (a `DX`-offset combined with `ANGLE != 0`), which was confirmed structural and unaffected by kick count — see the next decision below. Solenoid was deliberately left out of this retune — it has no `model` attribute at all, and the study's own solenoid guidance (`uniform`+`50` for radiation-critical use) is a different pattern from the `yoshida4`+kicks approach used here. Adding uniform `zeta`/single-order-multipole test coverage as part of validating this retune also surfaced two small, separate converter bugs (a sign error and a missing-function crash in `MULT`'s `K0`/`SK0` handling), fixed, plus two SAD behaviour facts documented in `docs/reference/sad-behaviour.md`: `MULT` skew-quadrupole optics agreement depends on the twiss convention used for comparison (not a rotation-convention bug), and a small, accepted `K0`/`SK0` dipole-fringe residual, for which the converter warns when dipole-only `MULT` elements are simplified to Xsuite Bend/corrector elements.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
