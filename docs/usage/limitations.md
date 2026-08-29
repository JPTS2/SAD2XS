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
| `MULT` K1 fringe in overlapping BZ | zero-BZ map; bounded for tested SuperKEKB QCs | yes |
| `MULT` K1 fringe with `DROT` | fringe skipped | yes |
| Hard-edge fringe gating ignored | bends and quadrupoles with `DISFRIN` | **no** |
| Quadrupole fringe radiation untested | quadrupole fringe | no |
| Radiation against SAD | sextupole, octupole, multipole, solenoid | no |
| Deferred expressions baked to floats | written lattice files | no |

## Solenoids

SAD's nonlinear solenoid fringe kick is not modelled. Every converted solenoid behaves as if `DISFRIN=1` had been set, whatever the source file says.

Neither `xt.UniformSolenoid` nor `xt.VariableSolenoid` implements the term. For SAD comparisons, set `DISFRIN=1` on the SAD side. This ensures the two codes are modelling the same physical magnet.

The same limitation applies to spin tracking. Spin precession is highly sensitive to the fine field detail at the fringe, so this converter is not a reliable tool for spin-tracking studies through solenoid lattices.

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

SAD has several distinct fringe mechanisms. Three are imported, all on by default: the bend soft-edge fringe, the quadrupole linear fringe, and the zero-BZ K1 part of the MULT linear fringe.

The rest are not imported. Most importantly, **`DISFRIN` is not read for bends or quadrupoles**, and MULT's dipole soft edge and generic hard edge remain absent. A lattice that deliberately disables the bend or quadrupole hard-edge fringe still gets that fringe after conversion. This limitation is silent: no warning is raised.

The imported bend fringe once carried an off-momentum residual of a few percent. Xsuite 0.57.0 corrected the momentum scaling that caused it, and it is below the supported minimum, so the residual no longer applies.

The quadrupole fringe is modelled as a thin second-order Taylor map. This reproduces the optics correctly, but whether the map radiates is untested. Treat radiation results through quadrupole fringes with caution.

The MULT K1 map uses the same representation. Its exact SAD form also depends
on an overlapping longitudinal field. SAD2XS retains the zero-BZ map inside a
powered bound solenoid and warns. The tested SuperKEKB cases showed at most a
`0.094 um` change in IP beta from restoring the local BZ term, but one-sided
stress tests were materially worse; do not generalise that bound to arbitrary
fringe asymmetries.

See [fringe models](../converter/fringes.md).

## Radiation against SAD

A quantum radiation discrepancy against SAD is open. It grows with multipole order:

| Element | Discrepancy |
| --- | --- |
| Sextupole | ~6.6% |
| Multipole | ~12% |
| Octupole | ~24.5% |
| Solenoid | ~28% |

For the solenoid, this was confirmed **not** to be a fringe-field mismatch. The gap is flat with amplitude across three orders of magnitude in radius. That points to a fixed proportionality or convention difference in the radiated-power calculation.

The root cause is not identified. Treat radiation results against SAD for these element types with caution at significant amplitude.

See [models and integrators](../converter/models-integrators.md).

## Transparent elements

`MONI`, `BEAMBEAM`, and `MAP` are converted to zero-length markers. They keep their position in the line but carry no physics. Beam-position-monitor behaviour, beam-beam interactions, and map contents are not modelled.

## Written lattice files

The writer converts deferred (xdeps) expressions to literal floats. A line built with expressions loses them on write. Structure and values survive a round trip; the dependency graph does not.

Negative-length drifts are converted as-is, and are known to break offset-marker insertion in some cases.

See [output writer](../writer/README.md).

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
