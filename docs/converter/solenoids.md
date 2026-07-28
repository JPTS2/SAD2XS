# Solenoid conversion

How SAD solenoid regions are converted, how the SAD and Xsuite solenoid models differ, and what is not modelled.

Solenoid conversion is handled by `sad2xs/converter/_006_solenoid_converter.py`.

**On this page:**

- [How SAD and Xsuite represent a solenoid](#how-sad-and-xsuite-represent-a-solenoid)
- [Converting the region](#converting-the-region)
- [Boundary elements and reference shifts](#boundary-elements-and-reference-shifts)
- [Conversion errors](#conversion-errors)
- [Charge sign and coupled optics](#charge-sign-and-coupled-optics)
- [Design decisions](#design-decisions)

## How SAD and Xsuite represent a solenoid

SAD and Xsuite describe a solenoid in different ways.

SAD marks out a **region**. A `SOL` element with `BOUND` is a boundary, not a magnet. Boundaries come in pairs: one entrance and one exit. Everything between the pair sits inside the solenoidal field. The field itself is a property of the region, not of the elements inside it.

Xsuite has no equivalent region concept. Each element carries its own field. A quadrupole inside a solenoid must therefore be an element that carries both the quadrupole field and the local `ks`.

The converter bridges this difference. It reads SAD's region and pushes the solenoidal field down into every element inside it.

## Converting the region

Between each pair of `BOUND` boundaries, every element picks up the solenoidal field active at that point. That field is the `ks` of the nearest preceding boundary solenoid. In a reversed line it is the nearest following boundary instead.

Elements are then converted by type:

| Element inside the region | Result |
| --- | --- |
| Drift | `xt.UniformSolenoid` |
| Bend, Quadrupole, Sextupole, Octupole, Multipole | `xt.UniformSolenoid` carrying its own field as `knl`/`ksl`, plus `ks` |
| Translation, TimeDelay, Rotation, Marker, aperture limits, zero-length Cavity | left unchanged |
| any other thick element | logged as a warning, left unconverted |

For the converted magnets, `x0` and `y0` are set so that the transverse offset stays consistent under the field rotation.

The thin, field-free elements in the third row are left alone because they carry no field to combine with `ks`.

### Elements SAD permits inside a solenoid region

SAD supports `DRIFT`, straight `BEND`, `QUAD`, and `MULT` as inserted elements between `SOL` boundaries. Direct `SEXT` and `OCT` elements are not supported inserted elements in that region. Represent higher-order content through `MULT` instead.

## Boundary elements and reference shifts

Each `BOUND` solenoid becomes a sub-line of four components, in a fixed generic order:

```text
UniformSolenoid -> Translation -> TimeDelay -> Rotation
```

That generic order is not correct for every boundary. `solenoid_reference_shift_corrections` fixes both the order and the signs of the Translation and Rotation parameters, one boundary at a time.

The correct combination depends on three things:

- whether the boundary is the entrance or the exit of its pair;
- whether it is the `GEO` boundary of the pair;
- whether the boundary was individually reversed by a line reversal.

Reversal is detected per solenoid, from a leading `-` on its own name.

These sign combinations were established empirically against real SAD Twiss output, not derived on paper. They are locked in by `test_sol_reference_transform_orbit_matches_sad_twiss` and `test_sol_reference_transform_restores_design_orbit_at_end`.

## Conversion errors

Conversion raises `ValueError` in two cases:

- `BOUND` solenoids in a line are not paired, meaning an odd number in entrance/exit order;
- neither solenoid in a pair is the `GEO` boundary.

Both are structural problems in the source lattice. Failing loudly is preferred to converting a region whose geometry cannot be resolved.

## Charge sign and coupled optics

The solenoid `ks` depends on the sign of the reference particle's charge. That interaction, and how it behaves under the reversal flags, is documented in [line reversals](line-reversals.md).

A solenoid couples the transverse planes, so Twiss output in a solenoid region needs care. SAD reports Edwards-Teng parameters. Xsuite's plain Twiss reports Mais-Ripken mode projections. Comparing the two directly is a convention mismatch, not a converter error. See [SAD behaviour notes](../reference/sad-behaviour.md).

## Design decisions

### Solenoid fringe kick (DISFRIN) is not modelled

Decision: SAD2XS does not implement SAD's nonlinear solenoid fringe kick (controlled by SAD's `DISFRIN` parameter — default `0` applies the kick, `1` disables it). Every converted solenoid behaves as if `DISFRIN=1` were set, regardless of the source SAD file.

Reasoning: neither `xt.UniformSolenoid` nor `xt.VariableSolenoid` implements this term — see `docs/reference/sad-behaviour.md` for what the fringe kick actually is and how that was confirmed. This was discussed with the Xsuite lead developer — there are no current plans to adopt a bolted-on, SAD-specific Hamiltonian term for this; the recommended direction for accurate modelling of complex/overlapped solenoid fields is field maps with a spline Boris integrator.

Consequence: the converter warns once per lattice (not once per element) when it finds one or more SAD `SOL` elements without `DISFRIN=1`, so users know their solenoid's fringe-kick physics is not being reproduced. Test comparisons involving solenoid physics should set `DISFRIN=1` on the SAD side to get a fair, apples-to-apples comparison; a dedicated test (`test_sol_disfrin_off_diverges_from_xsuite_in_tracking`) locks in the expected divergence without it as a permanent, accepted limitation rather than an open bug — it must not be added to `tests/support/known_issues.py`. A related consequence: spin-tracking studies through solenoid lattices are not well supported by this converter either, since spin precession is highly sensitive to exactly this kind of fine field detail at the fringe.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
