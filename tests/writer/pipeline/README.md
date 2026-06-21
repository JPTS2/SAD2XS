# Writer Pipeline Tests

This folder contains tests for whole-writer entry points and supported-element
policy.

Use these tests when the behaviour is about the writer pipeline as a whole
rather than one serialised element or feature.

## Coverage

- `test_line_roundtrip.py` (1 test) — end-to-end roundtrip with a directly
  constructed Xsuite line containing all supported element types (drift, bend,
  corrector, quad, sext, oct, multipole, solenoid, cavity, all five reference
  shifts, LimitRect, LimitEllipse). Checks element order, element classes,
  particle reference, and supported scalar/array fields for every element in
  one shot. 1 test expected to FAIL: k1 for the combined-function bend is not
  written (issue #63 — same limitation exposed at the element level by
  `test_bend_writer.py`).

- `test_supported_elements.py` (17 tests) — supported-element policy: one test
  per element type the writer handles. Each test builds a minimal
  single-element line, calls `write_lattice` and `write_optics`, asserts the
  output file is created, and calls it via `env.call()` to confirm it is
  syntactically valid and loadable. Bend (h≠0) and corrector (h=0, k0 set) are
  tested as distinct writer paths. All 17 tests expected to pass.

- `test_lattice_writer.py` (7 tests) — `write_lattice` entry point:
  - File creation, correct filename, `output_header` written to file,
    executable via `env.call()` (4 core tests).
  - `offset_marker_locations` path: non-empty dict writes a `MARKER_POSITIONS`
    block with the correct marker name; empty dict omits the block; file with
    `_install_offset_markers=False` is callable without error (3 offset marker
    tests).
  All 7 tests expected to pass.

- `test_optics_writer.py` (22 tests) — `write_optics` entry point: file
  creation, `output_header`, executable Python (3 core tests). Per element
  family, checks that strength variables are present in the file when non-zero
  and suppressed when zero:
  - Quadrupole: `k1_{name}` and `k1s_{name}` (3 tests)
  - Bend (h≠0): `k0_{name}` (1 test)
  - Corrector (h=0): `k0_{name}` present/suppressed (2 tests)
  - Sextupole: `k2_{name}` present/suppressed, `k2s_{name}` for skew (3 tests)
  - Octupole: `k3_{name}` present/suppressed, `k3s_{name}` for skew (3 tests)
  - Cavity: `freq_{name}`, `volt_{name}`, `lag_{name}` always written (1 test)
  - Translation: `dx_{name}` and `dy_{name}` independently present/suppressed (2 tests)
  - TimeDelay: `dz_{name}` (1 test)
  - XRotation: `chi2_{name}` (1 test)
  - YRotation: `chi1_{name}` (1 test)
  - SRotation: `chi3_{name}` (1 test)
  All 22 tests expected to pass.

## Expected Failures

| Test | Count | Issue |
|------|-------|-------|
| `test_line_roundtrip.py` — k1 for combined-function bend not preserved | 1 | #63 |

All other pipeline tests are expected to pass.
