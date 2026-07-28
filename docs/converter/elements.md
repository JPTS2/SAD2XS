# Element conversion

How each SAD element family is converted into Xsuite elements.

*The mechanism description for this page is still being written. The decisions below are complete.*

## Design decisions

## Bend element-offset (DX/DY) reference-orbit convention is not modelled

Decision: SAD2XS does not reproduce SAD's reference-orbit convention for a curved element (a `BEND` with `ANGLE != 0`, thick or thin) that also carries a nonzero `DX`/`DY` misalignment. The converted lattice keeps the element's design curvature (`h` for the thick `xt.Bend` representation, `hxl` for the thin `xt.Multipole` representation used when `L` is absent or zero) fixed to the unshifted design orbit regardless of the misalignment; SAD instead reconstructs its reference orbit through the displaced element. Combined with a nonzero `ROTATE`, a further, separate SAD-side artifact appears in SAD's own reported coupling (`R1`-`R4`) too.

Reasoning: two physical readings of a `DX`/`DY` misalignment on a curved element are both defensible (fixed design orbit vs. orbit that follows the displacement); Xsuite's curved elements are built on the first, SAD's behaviour is closer to the second. See `docs/reference/sad-behaviour.md` for the full empirical characterisation of both this and the `ROTATE`-combined coupling artifact, including what was ruled out (an Edwards-Teng/Mais-Ripken convention mismatch, a converter bug) and what could not be confirmed without SAD source access (the coupling artifact's exact internal cause).

Consequence: the converter warns once per lattice (not once per element) when it finds one or more `BEND` elements with `ANGLE != 0` and a nonzero `DX`/`DY`, covering both the thick and thin representations. The affected test parametrisations are locked in as passing, quantified tests in `tests/conversion/elements/test_bend.py`
(`test_bend_offset_orbit_residual_is_angle_squared_order`,
`test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order`,
`test_bend_offset_rotated_coupling_is_a_sad_side_artifact`) rather than left failing or tracked in `tests/support/known_issues.py` — which physical reading is intended is a design-decision-level question for the SAD and Xsuite authors, not something to guess a converter fix for. Correctors (`ANGLE == 0`) and MULT-derived dipoles never carry a nonzero curvature and are confirmed unaffected by either finding.

## Cavity RF-focusing kick is not modelled

Decision: SAD2XS does not implement SAD's transverse RF-focusing kick for accelerating elements (`MULT` or `CAVI` with `VOLT != 0`, tracked with `RFSW` on — independent of `TRPT`). Every converted `xt.Cavity`, whether from a plain SAD `CAVI` or from the interleaved slices of a combined K1+VOLT `MULT`, behaves as if this term were absent, regardless of the source SAD file.

Reasoning: `xt.Cavity`'s own tracking code has no transverse coupling at all — see `docs/reference/sad-behaviour.md` for what the term actually is and how its absence was confirmed by tracking, not just by reading the source once. The kick-application machinery already exists in xtrack, attached to a different element (`xt.RFMultipole`); reproducing SAD's `vcorr` coefficient automatically inside `xt.Cavity` itself would be the cleaner fix, but the exact phase convention has not yet been validated against the literature closed form (Rosenzweig & Serafini 1994) or against SAD, so it is not implemented on either the sad2xs or xtrack side yet.

Consequence: the converter warns once per lattice (not once per element, not conditional on a computed strength threshold) whenever any `xt.Cavity` element ends up in the converted line, in `convert_elements` (`sad2xs/converter/_004_element_converter.py`) rather than duplicated into both `convert_cavities` and the RF-`MULT` path in `convert_multipoles`. The omission is locked in as a permanent, accepted limitation by `tests/xtrack/test_cavity.py`, which asserts directly against `xtrack` (not against sad2xs conversion logic) that `xt.Cavity` gives zero `x -> px` coupling — if xtrack ever adds this term natively, that test fails loudly and this decision needs revisiting. This is expected to be negligible for typical high-energy/low-gradient RF (e.g. main synchrotron RF cavities) and potentially significant for low-energy/high-gradient structures (e.g. photoinjector-like LINAC sections) — the coefficient scales with `VOLT` and with `(frequency/momentum)^2`. TRPT/accelerating-reference-momentum conversion support (`xt.ReferenceEnergyIncrease` insertion) is a separate, not-yet-implemented feature; this decision applies regardless of whether that support exists.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
