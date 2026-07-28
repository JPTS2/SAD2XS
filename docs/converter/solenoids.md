# Solenoid conversion

How SAD solenoid regions are converted, how the SAD and Xsuite solenoid models differ, and what is not modelled.

*The mechanism description for this page is still being written. The decisions below are complete.*

## Design decisions

## Solenoid fringe kick (DISFRIN) is not modelled

Decision: SAD2XS does not implement SAD's nonlinear solenoid fringe kick (controlled by SAD's `DISFRIN` parameter — default `0` applies the kick, `1` disables it). Every converted solenoid behaves as if `DISFRIN=1` were set, regardless of the source SAD file.

Reasoning: neither `xt.UniformSolenoid` nor `xt.VariableSolenoid` implements this term — see `docs/reference/sad-behaviour.md` for what the fringe kick actually is and how that was confirmed. This was discussed with the Xsuite lead developer — there are no current plans to adopt a bolted-on, SAD-specific Hamiltonian term for this; the recommended direction for accurate modelling of complex/overlapped solenoid fields is field maps with a spline Boris integrator.

Consequence: the converter warns once per lattice (not once per element) when it finds one or more SAD `SOL` elements without `DISFRIN=1`, so users know their solenoid's fringe-kick physics is not being reproduced. Test comparisons involving solenoid physics should set `DISFRIN=1` on the SAD side to get a fair, apples-to-apples comparison; a dedicated test (`test_sol_disfrin_off_diverges_from_xsuite_in_tracking`) locks in the expected divergence without it as a permanent, accepted limitation rather than an open bug — it must not be added to `tests/support/known_issues.py`. A related consequence: spin-tracking studies through solenoid lattices are not well supported by this converter either, since spin precession is highly sensitive to exactly this kind of fine field detail at the fringe.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
