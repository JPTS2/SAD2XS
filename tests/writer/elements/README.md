# Writer Element Tests

This folder contains element-specific writer serialisation tests, one file per
Xsuite element family.

Each file tests the roundtrip contract for its element type. Build an `xt.Line`
directly with representative field values, write it with `sad2xs.write_lattice`
and `sad2xs.write_optics`, reload it in a clean Xsuite environment, then assert
every supported field is preserved.

Known-failure tests receive the centrally managed `known_issue` marker. They
remain ordinary failures and are routed to the non-blocking CI job.

## Coverage

Every file follows the roundtrip contract above. The table lists what each one
serialises.

| File | Tests | Xsuite class | Fields covered |
|------|-------|--------------|----------------|
| `test_drift_writer.py` | 8 | `xt.Drift` | length |
| `test_bend_writer.py` | 34 | `xt.Bend`, `h != 0` | `angle` as a fixed literal, `k0` and `k1` as optics expressions, length, edge angles, edge `fint`/`hgap`, `shift_x`/`shift_y`, `knl`/`ksl` literal arrays, vertical and skew variants, multiple bends, shared base element |
| `test_corr_writer.py` | 33 | `xt.Bend`, `h = 0` | `k0` as an optics expression set directly, not through angle x length; otherwise as the bend, plus precision |
| `test_quad_writer.py` | 30 | `xt.Quadrupole` | `k1`, `k1s`, `shift_x`/`shift_y`, `rot_s_rad`, `knl`/`ksl` literal arrays |
| `test_sext_writer.py` | 30 | `xt.Sextupole` | `k2`, `k2s`, `shift_x`/`shift_y`, `rot_s_rad`, `knl`/`ksl` literal arrays |
| `test_oct_writer.py` | 30 | `xt.Octupole` | `k3`, `k3s`, `shift_x`/`shift_y`, `rot_s_rad`, `knl`/`ksl` literal arrays |
| `test_mult_writer.py` | 25 | `xt.Multipole` | `knl`/`ksl` literal arrays, not optics variables; `shift_x`/`shift_y`, `rot_s_rad` |
| `test_sol_writer.py` | 26 | `xt.UniformSolenoid` | `ks` as a literal number, `x0`/`y0` axis offsets, `knl`/`ksl`, `shift_x`/`shift_y`, `rot_s_rad` |
| `test_cavi_writer.py` | 24 | `xt.Cavity` | voltage, frequency, and phase as optics expressions; the `fshift` global shift; harmonic mode writing `harm_{name}` instead of `freq_{name}` |
| `test_refshift_writer.py` | 39 | `xt.Translation`, `xt.TimeDelay`, `xt.Rotation` | every shift and rotation field as an optics expression, zero `default_to_zero` behaviour, all five types in one line |
| `test_aper_writer.py` | 33 | `xt.LimitEllipse`, `xt.LimitRect`, `xt.LimitRectEllipse` | bounds, offsets, asymmetric bounds, mixed types |
| `test_marker_writer.py` | 11 | `xt.Marker` | type, name, order, multiple markers, start/end convention, offset marker insertion |
| `test_taylor_maps_writer.py` | 21 | `xt.FirstOrderTaylorMap`, `xt.SecondOrderTaylorMap` | map arrays as full-precision literals, quad-fringe reversal metadata, minus-sign root-name cleanup, multiple maps in one line |

### `test_bend_writer.py` and `test_corr_writer.py` note

The `fint`/`hgap` tests come from the `F1`/`FB1`/`FB2` soft-edge fringe import.
They also confirm a fringe-only bend is not misclassified as the writer's
compact "simple" form, which would silently drop every other attribute.

### `test_aper_writer.py` note

Aperture dimensions are written as live optics variables, such as `a_ap1` and
`min_x_ap1`, so they stay tunable after reload.

This creates an ordering constraint. `xt.LimitEllipse` rejects `a` or `b` equal
to zero at construction, so the lattice file bootstraps the dimensions to safe
placeholders, and the optics file, loaded second, sets the real values.

Tracking-grid tests are not needed here. Field-value equality is sufficient,
because the writer serialises Python values to Python code with no
interpretation step. Physical correctness is Xsuite's contract, not SAD2XS's.

### `test_taylor_maps_writer.py` note

`_new_quad_fringe_element` stashes `_sad_quad_fringe_a`, `_sad_quad_fringe_b`,
and `_sad_quad_fringe_theta` on a quad-fringe map. The tests confirm these are
preserved when present and absent when not.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
