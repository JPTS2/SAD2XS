# Output writer

How the converted Xsuite model is serialised into lattice and optics files.

The writer takes an `xt.Line` and generates Python source that rebuilds it. It serialises the Xsuite model that the converter built, not the original SAD text.

Two public entry points produce two files:

| Entry point | Output | Contains |
| --- | --- | --- |
| `write_lattice` | lattice file | element definitions, the `LINE` definition, modelling settings |
| `write_optics` | optics file | every live optics variable, as one `env.vars.update(...)` call |

They are separate on purpose. A user can re-import strengths onto an already-loaded line without rebuilding its structure.

The modules live in `sad2xs/output_writer/`. The entry points themselves are in `sad2xs/converter/_009_write_lattice.py` and `_010_write_optics.py`.

**On this page:**

- [The lattice file](#the-lattice-file)
- [The optics file](#the-optics-file)
- [Supported elements](#supported-elements)
- [Taylor-map output](#taylor-map-output)
- [Limitations](#limitations)

## The lattice file

The generated file reconstructs the line from scratch when executed against a fresh `xt.Environment`. It is written in a fixed order:

1. reference-particle globals;
2. one section per element family — drifts, bends, correctors, quadrupoles, sextupoles, octupoles, multipoles, solenoids, cavities, reference shifts, apertures, markers, Taylor maps;
3. the `LINE` definition;
4. modelling settings — model, integrator, kick counts, edge models;
5. resolved offset-marker insertion points.

The order matters. Later steps depend on earlier ones existing, and the offset-marker insertions must come last because they slice elements that the `LINE` definition has already placed.

### Elements are grouped and cloned

Identical elements are written once and reused through `env.new(..., mode="clone")` rather than repeated.

Grouping is by length. `quantize_length` rounds lengths to `Config.MAGNET_LENGTH_PRECISION` so that elements which are identical in practice are recognised as such, rather than being written separately because of floating-point noise. The converter uses the same value as its minimum absolute nonzero concrete element length, keeping the thin/thick decision consistent with the writer's resolution.

### Reversed elements

A `-`-prefixed element is only written if the line contains no non-reversed sibling with the same root name.

Where both exist they are genuinely distinct elements and both are written. Where only the reversed one exists, the minus sign carries no information and the element is written under its stripped name.

### Compact forms

Several helpers decide whether an element qualifies for a compact one-line form: `check_is_simple_bend_corr`, `check_is_simple_quad_sext_oct`, `check_is_skew_quad_sext_oct`, `check_is_simple_unpowered_multipole`, and `check_is_simple_solenoid`.

An element qualifies only when every attribute outside the compact form is at its default. This is easy to get wrong when a new field is added: a bend carrying only `fint` and `hgap` once qualified as simple, and was written with those fields silently dropped. Any new serialised attribute must also be added to the corresponding check.

## The optics file

The optics file calls `env.vars.update(...)` with every live optics variable in a single keyword-argument block: bend, corrector, quadrupole, sextupole, and octupole strengths, cavity RF parameters, reference shifts, and aperture bounds.

It is executed against the environment produced by loading the lattice file.

Aperture dimensions are written as live variables rather than literals, so they stay tunable after reload. This creates an ordering constraint: `xt.LimitEllipse` rejects `a` or `b` equal to zero at construction, so the lattice file bootstraps aperture dimensions to safe placeholders and the optics file, loaded second, sets the real values.

## Supported elements

The writer's supported set is **not** the same question as which SAD elements the converter reads. This set is Xsuite classes.

| Class | Notes |
| --- | --- |
| `xt.Drift` | |
| `xt.Bend` | two distinct paths: `h != 0`, and corrector with `h = 0` |
| `xt.Quadrupole`, `xt.Sextupole`, `xt.Octupole` | |
| `xt.Multipole` | |
| `xt.UniformSolenoid` | |
| `xt.Cavity` | |
| `xt.Translation`, `xt.TimeDelay`, `xt.Rotation` | the reference shifts |
| `xt.LimitRect`, `xt.LimitEllipse`, `xt.LimitRectEllipse` | |
| `xt.Marker` | |
| `xt.FirstOrderTaylorMap`, `xt.SecondOrderTaylorMap` | |

`tests/writer/pipeline/test_supported_elements.py` covers this policy: one test per class, each building a minimal single-element line, writing it, and calling the generated file to confirm it is syntactically valid and loadable.

`xt.LimitRectEllipse` is the one class the policy test does not cover. It is serialised, and it is tested by the element-level aperture writer tests in `tests/writer/elements/test_aper_writer.py`, but it has no row in the policy test.

## Taylor-map output

Generic first- and second-order Taylor maps are written as full-precision
coefficient arrays.

SAD soft quadrupolar fringe maps are written differently: one self-contained
helper is emitted, followed by a compact call for each face containing only
`a`, `b`, the normal-field rotation, and the two offsets. This preserves a
thick QUAD fringe's dependency on the existing scalar quadrupole-strength
variables after reload, without adding fringe variables or requiring the
generated lattice to import SAD2XS. The defining records live in standard
`Environment.metadata`; no private fields are added to Xsuite elements.

Generic `xt.FirstOrderTaylorMap` and `xt.SecondOrderTaylorMap` elements are
serialised as literal arrays at full double precision, not as optics variables.

Their coefficients are not physically meaningful knobs a user would retune, and a second-order map's `T` tensor would produce an unusable number of variables.

## Limitations

**The writer is not a general Xsuite serialiser.** It handles the element classes listed above, and it still carries assumptions from being the final step of a SAD2XS conversion rather than a standalone tool.

**Most deferred expressions are baked to literal floats.** An arbitrary
`xt.Line` built with xdeps expressions generally loses those expressions on
write: the generated file contains evaluated numbers. The explicit exception
is a recognised SAD soft quadrupolar fringe, whose dependency on the existing
QUAD strength variables is preserved by its compact helper call.

Both are tracked in the [issue tracker](https://github.com/JPTS2/sad2xs/issues).

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
