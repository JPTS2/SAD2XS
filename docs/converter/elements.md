# Element conversion

How each SAD element family is converted into Xsuite elements.

`convert_elements` dispatches to one converter function per SAD element type, in a fixed order: drifts, bends and correctors, quadrupoles, sextupoles, octupoles, multipoles, cavities, apertures, solenoids, coordinate transformations, markers, monitors, beam-beam, maps.

**On this page:**

- [Conversion map](#conversion-map)
- [Thin and thick elements](#thin-and-thick-elements)
- [Drifts](#drifts)
- [Bends](#bends)
- [Correctors](#correctors)
- [Quadrupoles, sextupoles and octupoles](#quadrupoles-sextupoles-and-octupoles)
- [Multipoles](#multipoles)
- [Cavities](#cavities)
- [Apertures](#apertures)
- [Coordinate transformations](#coordinate-transformations)
- [Transparent elements](#transparent-elements)
- [Warnings raised during conversion](#warnings-raised-during-conversion)

## Conversion map

| SAD element | Converts to |
| --- | --- |
| `DRIFT` | `xt.Drift` |
| `BEND`, `ANGLE != 0` | `xt.Bend`, or `xt.Multipole` when thin |
| `BEND`, `ANGLE == 0` | corrector: `xt.Bend` with `h = 0`, or `xt.Multipole` when thin |
| `QUAD` | `xt.Quadrupole`, or `xt.Multipole` when thin |
| `SEXT` | `xt.Sextupole`, or `xt.Multipole` when thin |
| `OCT` | `xt.Octupole`, or `xt.Multipole` when thin |
| `MULT` | depends on content — see below |
| `CAVI` | `xt.Cavity` |
| `APERT` | `xt.LimitRect`, `xt.LimitEllipse`, or `xt.LimitRectEllipse` |
| `SOL` | `xt.UniformSolenoid` — see [solenoids](solenoids.md) |
| `COORD` | `xt.Translation` and `xt.Rotation` |
| `MARK` | `xt.Marker` |
| `MONI` | `xt.Marker` |
| `BEAMBEAM` | `xt.Marker` |
| `MAP` | `xt.Marker` |

## Thin and thick elements

A magnetic element with no length, or zero length, converts to `xt.Multipole` rather than its typed Xsuite class. The typed classes describe a thick element; a thin one is a pure kick.

For a thin bend this matters beyond bookkeeping. The converter sets `hxl` to `k0l`, so the element still bends the reference orbit and generates dispersion. Dropping that would silently change the optics.

## Drifts

A SAD `DRIFT` becomes an `xt.Drift` directly.

Negative-length drifts are converted as-is. The converter warns once per lattice when it finds any, because they usually indicate overlapping element geometry or survey rounding in the source lattice. They are also known to break tracking, Twiss, and offset-marker insertion — see [offset markers](offset-markers.md).

## Bends

A `BEND` with a non-zero `ANGLE` is a real bend. One with `ANGLE == 0`, or no `ANGLE` at all, is a corrector and is handled separately.

A thick bend becomes an `xt.Bend`. `E1`, `E2`, `AE1`, and `AE2` are combined into `edge_entry_angle` and `edge_exit_angle`. Fringe fields are imported when enabled — see [fringe models](fringes.md).

Some rotations are absorbed rather than kept. SAD encodes a `pi` or `-pi/2` rotation as a field-sign flip, and the converter folds these into `k0` and `k1` instead of leaving an element rotation in place.

### Offset bends: the reference-orbit convention is not reproduced

SAD2XS does not reproduce SAD's reference-orbit convention for a curved element that also carries a non-zero `DX` or `DY` misalignment. This applies to both the thick `xt.Bend` and the thin `xt.Multipole` representation.

The converted lattice keeps the element's design curvature — `h` when thick, `hxl` when thin — fixed to the unshifted design orbit, whatever the misalignment. SAD instead reconstructs its reference orbit through the displaced element.

Both readings are defensible. A displacement can leave the design orbit fixed, or the orbit can follow the displacement. Xsuite's curved elements are built on the first, and SAD's behaviour is closer to the second. Which is intended is a question for the SAD and Xsuite authors, not something to guess a converter fix for.

Combined with a non-zero `ROTATE`, a further and separate artifact appears in SAD's own reported coupling, in `R1` through `R4`.

The converter warns once per lattice when it finds any `ANGLE != 0` bend with a non-zero `DX` or `DY`. The affected cases are locked in as passing, quantified tests in `tests/conversion/elements/test_bend.py` rather than left failing:

- `test_bend_offset_orbit_residual_is_angle_squared_order`
- `test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order`
- `test_bend_offset_rotated_coupling_is_a_sad_side_artifact`

Correctors never carry curvature, and `MULT`-derived dipoles do not either. Both are confirmed unaffected.

## Correctors

A thin corrector becomes an `xt.Multipole` carrying `K0` and `K1` as a pure kick.

A thick corrector becomes an `xt.Bend` with design curvature `h = 0`, `K0` and `K1` as its field strengths, and both edge angles fixed at zero. Fringe import follows the same path as the bend.

## Quadrupoles, sextupoles and octupoles

These three share one implementation, differing only in field order and strength parameter:

| SAD element | Order | Strength |
| --- | --- | --- |
| `QUAD` | 2 | `K1` |
| `SEXT` | 3 | `K2` |
| `OCT` | 4 | `K3` |

The quadrupole is the exception. When quadrupole fringe import is enabled and the element carries an active linear fringe, the converted element becomes a sub-line wrapping the body between fringe maps. See [fringe models](fringes.md).

## Multipoles

A SAD `MULT` can mean several different things, so the converter takes the first applicable case in a fixed order.

**1. RF-carrying** — `VOLT`, `HARM`, or `FREQ` present. Xsuite has no single element combining a multipole kick with RF, so the element is sliced into alternating `xt.Multipole` and `xt.Cavity` pairs, wrapped in a sub-line named after the element. The slice count is `N_SLICES_MULT_RF`, or 1 if the element is thin.

**2. User-replaced** — matched by name prefix through `user_multipole_replacements`. Converted to the requested single-purpose element, using only the field order that element type supports.

**3. Auto-simplified** — when `SIMPLIFY_MULTIPOLES` is enabled and exactly one field order is non-zero, the element becomes the corresponding single-purpose element.

**4. Otherwise** — a true `xt.Multipole` carrying every order up to `MAX_KNL_ORDER`.

Cases 2 and 3 both canonicalise a `K0`/`SK0`-only rotation the same way the bend converter does, and both require a non-zero length, because integrated strengths must be divided by length.

### The dipole fringe residual when a MULT is simplified

Xsuite's bend fringe model does not exactly reproduce SAD's `MULT` dipole fringe convention. A `MULT` with only `K0` set, or only `SK0`, carries a fringe contribution of exactly `m43 = -K0^2/L` to the linear transfer matrix, or `m21` for `SK0`. Xsuite's bend edge models either add `theta^4`-order terms or give zero.

The two codes therefore agree at `theta^2` and diverge at `theta^4`. This was measured rather than estimated: the difference is between `-1.0005` and `-1.008` times `theta^4` across `theta = 0.025, 0.05, 0.1`, and scales by exactly `16` per doubling of `theta`.

The converter warns once per lattice when any `MULT` is auto-simplified to a bend or corrector, so the residual is not silent.

## Cavities

A SAD `CAVI` becomes an `xt.Cavity`.

### The transverse RF-focusing kick is not modelled

SAD applies a transverse RF-focusing kick to accelerating elements — a `MULT` or `CAVI` with `VOLT != 0`, tracked with `RFSW` on, independent of `TRPT`. SAD2XS does not implement it.

Every converted `xt.Cavity` behaves as if the term were absent, whether it came from a plain `CAVI` or from the interleaved slices of a combined `K1`-plus-`VOLT` `MULT`.

`xt.Cavity` has no transverse coupling in its tracking code at all. That was confirmed by tracking, not by reading the source once. The kick-application machinery does exist in xtrack, attached to `xt.RFMultipole`. Reproducing SAD's coefficient inside `xt.Cavity` would be the cleaner fix, but the exact phase convention has not been validated against the literature closed form (Rosenzweig and Serafini, 1994) or against SAD, so it is implemented on neither side.

The converter warns once per lattice whenever any `xt.Cavity` ends up in the converted line. The warning is raised in `convert_elements` rather than duplicated into both the cavity path and the RF-`MULT` path.

The size of the omission depends on the machine. It is expected to be negligible for typical high-energy, low-gradient RF such as main synchrotron cavities, and potentially significant for low-energy, high-gradient structures such as photoinjector-like LINAC sections. The coefficient scales with `VOLT` and with `(frequency/momentum)^2`.

This limitation is locked in by `tests/xtrack/test_cavity.py`, which asserts directly against xtrack — not against SAD2XS conversion logic — that `xt.Cavity` gives zero `x -> px` coupling. If xtrack ever adds the term natively, that test fails loudly and this decision needs revisiting.

The cavity edge-focusing kick is a separate mechanism, also not modelled. See [fringe models](fringes.md).

## Apertures

The converter chooses the aperture class from which parameters are present among `AX`, `AY`, `DX1`, `DX2`, `DY1`, `DY2`.

`xt.LimitRectEllipse` supports only bounds symmetric about the element centre. A combined `APERT` with rectangular bounds that cannot be proven symmetric is therefore split into a `LimitRect` and a `LimitEllipse`, wrapped in a sub-line named after the element.

## Coordinate transformations

A SAD `COORD` becomes Xsuite translation and rotation elements. The converter picks the simplest representation that covers the active transforms:

| Active transforms | Result |
| --- | --- |
| one | a single `xt.Translation` or `xt.Rotation` |
| `DX` and `DY` only | one combined `xt.Translation` |
| anything more | a sub-line of individually named elements |

In the sub-line case the order is `DX`/`DY`, then `CHI1`, `CHI2`, `CHI3`. If `DIR` is set the rotations come first, per the SAD manual's stated convention.

A `COORD` with no recognised transform at all is installed as a no-op translation, with a warning.

## Transparent elements

`MONI`, `BEAMBEAM`, and `MAP` are installed as zero-length, transparent `xt.Marker` elements. SAD2XS does not model beam-position-monitor behaviour, beam-beam interactions, or map contents.

Only empty `MAP` elements are understood. A `MAP` carrying parameters is not supported, because its physical meaning is not known.

## Warnings raised during conversion

Most warnings are summarised once per lattice, with a count, rather than repeated per element. Two are per-element, because they name the specific element whose parameters were ignored.

Once per lattice:

| Condition | Meaning |
| --- | --- |
| any drift with negative length | overlapping geometry or survey rounding; may break tracking, Twiss, or marker insertion |
| `ANGLE != 0` bend with non-zero `DX`/`DY` | reference-orbit convention not reproduced |
| `MULT` auto-simplified to a bend or corrector | dipole fringe residual at `O(theta^4)` |
| any `xt.Cavity` in the converted line | transverse RF-focusing kick not modelled |
| `SOL` without `DISFRIN=1` | solenoid fringe kick not modelled |

Per element:

| Condition | Meaning |
| --- | --- |
| `GEO` solenoid that also defines `DZ` | `DZ` is invalid with `GEO` and is ignored |
| `COORD` with no recognised transform | installed as a no-op translation |

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
