# Limitations

Where a converted lattice does not reproduce SAD.

Each of these is a known, characterised difference, not an open bug. Most raise a warning during conversion. For the current list of open bugs, see the [issue tracker](https://github.com/JPTS2/sad2xs/issues).

**On this page:**

- [Summary](#summary)
- [Solenoids](#solenoids)
- [Cavities](#cavities)
- [Displaced bends](#displaced-bends)
- [Fringe fields](#fringe-fields)
- [Radiation against SAD](#radiation-against-sad)
- [Transparent elements](#transparent-elements)
- [Written lattice files](#written-lattice-files)

## Summary

| Effect | Impact | Warns |
| --- | --- | --- |
| Solenoid fringe kick not modelled | solenoid optics, spin tracking | yes |
| Cavity RF-focusing kick not modelled | low-energy, high-gradient RF | yes |
| Offset bend reference-orbit convention | bends with `ANGLE != 0` and `DX`/`DY` | yes |
| `MULT` simplified to a bend | residual at `O(theta^4)` | yes |
| Hard-edge fringe gating ignored | bends and quadrupoles with `DISFRIN` | **no** |
| Quadrupole fringe radiation untested | quadrupole fringe, if enabled | no |
| Radiation against SAD | sextupole, octupole, multipole, solenoid | no |
| Deferred expressions baked to floats | written lattice files | no |

## Solenoids

SAD's nonlinear solenoid fringe kick is not modelled. Every converted solenoid behaves as if `DISFRIN=1` had been set, whatever the source file says.

Neither `xt.UniformSolenoid` nor `xt.VariableSolenoid` implements the term. For SAD comparisons, set `DISFRIN=1` on the SAD side to compare like with like.

A related consequence: spin-tracking studies through solenoid lattices are not well supported, because spin precession is highly sensitive to exactly this kind of fine field detail at the fringe.

See [solenoid conversion](../converter/solenoids.md).

## Cavities

SAD's transverse RF-focusing kick is not modelled. `xt.Cavity` has no transverse coupling in its tracking code at all.

The size of the omission depends on the machine. It is expected to be negligible for typical high-energy, low-gradient RF such as main synchrotron cavities, and potentially significant for low-energy, high-gradient structures such as photoinjector-like LINAC sections. The coefficient scales with `VOLT` and with `(frequency/momentum)^2`.

The separate cavity edge-focusing kick is also not modelled.

See [element conversion](../converter/elements.md).

## Displaced bends

For a bend with a non-zero `ANGLE` that also carries a `DX` or `DY` misalignment, the converted lattice keeps the design curvature fixed to the unshifted orbit. SAD instead reconstructs its reference orbit through the displaced element.

Both readings are physically defensible, and which is intended is a question for the SAD and Xsuite authors. The residual is quantified and locked into tests rather than left failing.

Correctors and `MULT`-derived dipoles never carry curvature and are unaffected.

See [element conversion](../converter/elements.md).

## Fringe fields

SAD has several distinct fringe mechanisms. Two are imported: the bend soft-edge fringe, on by default, and the quadrupole linear fringe, off by default pending an Xsuite release.

The rest are not. Most importantly, **`DISFRIN` is not read for bends or quadrupoles**, so a lattice that deliberately disables the hard-edge fringe still gets it after conversion. This one is silent — no warning is raised.

The imported bend fringe carries a known bounded off-momentum residual, a few percent on realistic magnet parameters, until an upstream Xsuite fix reaches a released version.

If quadrupole fringe import is enabled, the fringe is modelled as a thin second-order Taylor map. This reproduces the optics correctly, but whether the map radiates is untested. Treat radiation results through quadrupole fringes with caution.

See [fringe models](../converter/fringes.md).

## Radiation against SAD

A quantum radiation discrepancy against SAD is open, escalating with multipole order:

| Element | Discrepancy |
| --- | --- |
| Sextupole | ~6.6% |
| Multipole | ~12% |
| Octupole | ~24.5% |
| Solenoid | ~28% |

For the solenoid this was confirmed **not** to be a fringe-field mismatch — the gap is flat with amplitude across three orders of magnitude in radius, pointing to a fixed proportionality or convention difference in the radiated-power calculation.

The root cause is not identified. Treat radiation results against SAD for these element types with caution at significant amplitude.

See [models and integrators](../converter/models-integrators.md).

## Transparent elements

`MONI`, `BEAMBEAM`, and `MAP` are converted to zero-length markers. They keep their position in the line but carry no physics. Beam-position-monitor behaviour, beam-beam interactions, and map contents are not modelled.

## Written lattice files

The writer bakes deferred (xdeps) expressions to literal floats. A line built with expressions loses them on write: structure and values survive a round trip, the dependency graph does not.

Negative-length drifts are converted as-is, and are known to break offset-marker insertion in some cases.

See [output writer](../writer/README.md).

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
