# Writer Pipeline Tests

This folder contains tests for whole-writer entry points and supported-element
policy.

Use these tests when the behaviour is about the writer pipeline as a whole
rather than one serialised element or feature.

## Coverage

- `test_line_roundtrip.py` — end-to-end roundtrip with a directly constructed
  Xsuite line containing all supported element types (drift, bend, corrector,
  quad, sext, oct, multipole, solenoid, cavity, all five reference shifts,
  LimitRect, LimitEllipse). Checks element order, element classes, particle
  reference, and supported scalar/array fields for every element in one shot.
  1 test expected to FAIL: k1 for the combined-function bend is not written
  (issue #63 — same limitation exposed at the element level by
  `test_bend_writer.py`).

- `test_supported_elements.py` — supported-element policy: one test per element
  type the writer handles. Each test builds a minimal single-element line,
  calls `write_lattice` and `write_optics`, and asserts the output file is
  created. Bend (h≠0) and corrector (h=0, k0 set) are tested as distinct
  writer paths. All 17 tests expected to pass.

- `test_lattice_writer.py` — `write_lattice` entry point: output file created
  at the correct path with the correct name, `output_header` written to the
  file, and the generated file is callable via `env.call()` in a clean Xsuite
  environment. All 4 tests expected to pass.

- `test_optics_writer.py` — `write_optics` entry point: output file created,
  `output_header` written to the file, optics variable `k1_{name}` present in
  file content for a non-zero-strength quadrupole, absent for a zero-strength
  quadrupole (zero values are skipped; resolved via `default_to_zero`), and the
  generated file is callable via `env.call()` after the lattice file is loaded.
  All 5 tests expected to pass.

## Expected Failures

| Test | Count | Issue |
|------|-------|-------|
| `test_line_roundtrip.py` — k1 for combined-function bend not preserved | 1 | #63 |

All other pipeline tests are expected to pass.
