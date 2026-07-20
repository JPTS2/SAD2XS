# Writer Element Tests

This folder contains element-specific writer serialisation tests, one file per
Xsuite element family.

Each file tests the roundtrip contract for that element type: build an
`xt.Line` directly with representative field values, write with
`sad2xs.write_lattice` and `sad2xs.write_optics`, reload in a clean Xsuite
environment, and assert that all supported fields are preserved.

Known-failure tests receive the centrally managed `known_issue` marker. They
remain ordinary failures and are routed to the non-blocking CI job.

## Coverage

- `test_drift_writer.py` — `xt.Drift`: length
- `test_bend_writer.py` — `xt.Bend` (h≠0): `angle` written as a fixed literal (geometry/survey), `k0` tunable via `k0_{name}` optics expression (field strength), `k1` tunable via `k1_{name}` optics expression (combined-function gradient), length, edge angles (bare literals), edge fint/hgap (F1/FRINGE soft-edge fringe import, bare literals — also confirmed a fringe-only bend is not misclassified as the writer's "simple" compact form), shift_x/y, knl/ksl combined multipole components (literal arrays), all fields simultaneously, vertical (rot_s_rad=π/2 on base element), skew (rot_s_rad on clone), multiple bends, shared base element for same-length bends; all tests expected to pass
- `test_corr_writer.py` — `xt.Bend` (h=0, k0 set explicitly): k0 via `k0_{name}` optics expression (direct, not via angle×length), length, edge angles (bare literals), edge fint/hgap (FB1/FB2/FRINGE soft-edge fringe import, bare literals — same simple-form misclassification check as the bend writer), shift_x/y, knl/ksl combined multipole components (literal arrays), all fields simultaneously, vertical (rot_s_rad=π/2 on base), skew (rot_s_rad on clone), multiple correctors, shared base element for same-length correctors, precision; all tests expected to pass
- `test_quad_writer.py` — `xt.Quadrupole`: k1, k1s, shift_x/y, rot_s_rad, knl/ksl combined multipole components (literal arrays); all tests expected to pass
- `test_sext_writer.py` — `xt.Sextupole`: k2, k2s, shift_x/y, rot_s_rad, knl/ksl combined multipole components (literal arrays); all tests expected to pass
- `test_oct_writer.py` — `xt.Octupole`: k3, k3s, shift_x/y, rot_s_rad, knl/ksl combined multipole components (literal arrays); all tests expected to pass
- `test_mult_writer.py` — `xt.Multipole`: knl/ksl literal arrays (not optics variables), shift_x/y, rot_s_rad
- `test_sol_writer.py` — `xt.UniformSolenoid`: ks literal number (not optics variable), x0/y0 axis offsets, knl/ksl, shift_x/y, rot_s_rad
- `test_cavi_writer.py` — `xt.Cavity`: voltage/frequency/phase as optics expressions, fshift global shift mechanism; harmonic mode writes `harm_{name}` instead of `freq_{name}`
- `test_refshift_writer.py` — `xt.Translation` (shift_x/shift_y), `xt.TimeDelay` (shift_zeta), `xt.Rotation` (rot_y_rad/chi1, rot_x_rad/chi2, rot_s_rad/chi3); all as optics expressions; zero default_to_zero behaviour; all five types in one line
- `test_aper_writer.py` — `xt.LimitEllipse` (a/b), `xt.LimitRect` (min/max x/y), `xt.LimitRectEllipse` (max_x/max_y/a/b), offsets, asymmetric bounds, mixed types; aperture dimensions are written as live optics variables (`<dim>_<name>`, e.g. `a_ap1`, `min_x_ap1`) so they are accessible and tunable after reload. Dimension variables are bootstrapped to safe placeholders in the lattice file because `xt.LimitEllipse` rejects `a/b = 0` at construction; the optics file (loaded last) sets the real values. Note: tracking-grid tests are not needed here; field-value equality is sufficient because the writer serialises Python values to Python code with no interpretation step — physical correctness is Xsuite's contract, not SAD2XS's.
- `test_marker_writer.py` — `xt.Marker`: type/name/order, multiple markers, start/end convention; offset marker insertion via `offset_marker_locations` (marker created, correct s-position after reload with `_install_offset_markers=True`, multiple offset markers independently)

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
