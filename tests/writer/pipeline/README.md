# Writer Pipeline Tests

This folder contains tests for whole-writer entry points and supported-element
policy.

Use these tests when the behaviour is about the writer pipeline as a whole
rather than one serialised element or feature.

## Coverage

Does not require the SAD binary.

| File | Tests | Fail | Failure root cause |
|------|-------|------|--------------------|
| `test_line_roundtrip.py` | 1 | 0 | — |
| `test_supported_elements.py` | 17 | 1 | `xt.SecondOrderTaylorMap` is not in the shipping xtrack release |
| `test_lattice_writer.py` | 9 | 0 | — |
| `test_optics_writer.py` | 23 | 0 | — |
| `test_magnet_length_precision.py` | 5 | 0 | — |
| `test_writer_observability.py` | 3 | 0 | — |
| `test_writer_preserves_input_line.py` | 3 | 0 | — |

- `test_line_roundtrip.py` — end-to-end roundtrip with a directly
  constructed Xsuite line containing all supported element types (drift, bend,
  corrector, quad, sext, oct, multipole, solenoid, cavity, all five reference
  shifts, LimitRect, LimitEllipse). Checks element order, element classes,
  particle reference, and supported scalar/array fields for every element in
  one shot. All tests expected to pass.

- `test_supported_elements.py` — supported-element policy: one test
  per element type the writer handles. Each test builds a minimal
  single-element line, calls `write_lattice` and `write_optics`, asserts the
  output file is created, and calls it via `env.call()` to confirm it is
  syntactically valid and loadable. Bend (h≠0) and corrector (h=0, k0 set) are
  tested as distinct writer paths. The `xt.SecondOrderTaylorMap` case is a known
  failure: the class is not in the shipping xtrack release yet.

- `test_lattice_writer.py` — `write_lattice` entry point:
  - File creation, correct filename, `output_header` written to file,
    executable via `env.call()`, input line not mutated, output uses
    `particle_ref` without mutating the line (6 core tests).
  - `offset_marker_locations` path: non-empty dict writes a `MARKER_POSITIONS`
    block with the correct marker name; empty dict omits the block; file with
    `_install_offset_markers=False` is callable without error (3 offset marker
    tests).
  All 9 tests expected to pass.

- `test_optics_writer.py` — `write_optics` entry point: file
  creation, `output_header`, executable Python, input line not mutated
  (4 core tests). Per element family, checks that strength variables are
  present in the file when non-zero and suppressed when zero:
  - Quadrupole: `k1_{name}` and `k1s_{name}` (3 tests)
  - Bend (h≠0): `k0_{name}` (1 test)
  - Corrector (h=0): `k0_{name}` present/suppressed (2 tests)
  - Sextupole: `k2_{name}` present/suppressed, `k2s_{name}` for skew (3 tests)
  - Octupole: `k3_{name}` present/suppressed, `k3s_{name}` for skew (3 tests)
  - Cavity (frequency-driven): `freq_{name}`, `volt_{name}`, `phase_{name}` always written (1 test)
  - Translation: `dx_{name}` and `dy_{name}` independently present/suppressed (2 tests)
  - TimeDelay: `dz_{name}` (1 test)
  - Rotation (rot_x_rad/chi2): `chi2_{name}` (1 test)
  - Rotation (rot_y_rad/chi1): `chi1_{name}` (1 test)
  - Rotation (rot_s_rad/chi3): `chi3_{name}` (1 test)
  All 23 tests expected to pass.

- `test_magnet_length_precision.py` — base-element length
  grouping/naming for replicated magnets: quad, bend, and corrector pairs
  whose lengths differ by less than `Config.MAGNET_LENGTH_PRECISION` reload
  without a base-element name collision, each keeping its own strength
  (3 tests); quad and bend pairs whose lengths differ by more than
  `MAGNET_LENGTH_PRECISION` stay on distinct base-element lengths, i.e. are
  not over-merged (2 tests). All 5 tests expected to pass.

- `test_writer_observability.py` — the writer respects the logging
  policy: silent at the default level, progress narrative only when the level
  is raised.

- `test_writer_preserves_input_line.py` — neither `write_lattice` nor
  `write_optics` mutates the `xt.Line` it is given.

## Expected Failures

`test_supported_elements_writer_handles_second_order_taylor_map` fails until
`xt.SecondOrderTaylorMap` reaches a released xtrack version. It carries the
`known_issue` marker and is routed to the non-blocking CI job. Every other
writer pipeline test is expected to pass.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
