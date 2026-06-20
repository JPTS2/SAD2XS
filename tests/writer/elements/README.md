# Writer Element Tests

This folder contains element-specific writer serialisation tests, one file per
Xsuite element family.

Each file tests the roundtrip contract for that element type: build an
`xt.Line` directly with representative field values, write with
`sad2xs.write_lattice` and `sad2xs.write_optics`, reload in a clean Xsuite
environment, and assert that all supported fields are preserved.

## Coverage

- `test_drift_writer.py` — `xt.Drift`: length
- `test_bend_writer.py` — `xt.Bend` (h≠0): angle, k1, edge angles, shift_x/y, knl/ksl
- `test_corr_writer.py` — `xt.Bend` (h=0): horizontal, vertical, skew correctors; replication contract
- `test_quad_writer.py` — `xt.Quadrupole`: k1, k1s, shift_x/y, rot_s_rad, knl/ksl combined function
- `test_sext_writer.py` — `xt.Sextupole`: k2, k2s, shift_x/y, rot_s_rad, knl/ksl
- `test_oct_writer.py` — `xt.Octupole`: k3, k3s, shift_x/y, rot_s_rad, knl/ksl
- `test_mult_writer.py` — `xt.Multipole`: knl/ksl literal arrays (not optics variables), shift_x/y, rot_s_rad
- `test_sol_writer.py` — `xt.UniformSolenoid`: ks literal number (not optics variable), x0/y0 axis offsets, knl/ksl, shift_x/y, rot_s_rad
- `test_cavi_writer.py` — `xt.Cavity`: voltage/frequency/lag as optics expressions, fshift global shift mechanism
- `test_refshift_writer.py` — `xt.XYShift` (dx/dy), `xt.ZetaShift` (dzeta), `xt.YRotation` (chi1), `xt.XRotation` (chi2), `xt.SRotation` (chi3); all as optics expressions; zero default_to_zero behaviour; all five types in one line
- `test_aper_writer.py` — `xt.LimitEllipse`, `xt.LimitRect`
- `test_marker_writer.py` — `xt.Marker`: basic marker; offset marker output section
