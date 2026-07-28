# SAD Helper Tests

This folder contains tests for `sad2xs.sad_helpers`, one file per public
helper function.

Each file covers both SAD-free tests (command string generation, structure of
the generated macro) and smoke tests (end-to-end execution against a real SAD
installation). Converter physics comparisons that consume helper output belong
in `tests/conversion/`.

## Coverage

| File | Function(s) | Tests | Lattice fixture |
|------|-------------|-------|-----------------|
| `test_twiss_sad.py` | `twiss_sad`, `compute_second_order_dispersions`, `compute_chromatic_functions`, `generate_twiss_print_function` | 23 | Minimal transfer-line (1 m drift, START/END markers); minimal bend (0.1 rad BEND); minimal vertical bend (0.1 rad BEND, ROTATE = pi/2); accelerating MULT (VOLT/FREQ) for TRPT; asymmetric closed ring for native-reversal ground truth |
| `test_survey_sad.py` | `survey_sad`, `generate_survey_print_function` | 17 | Same transfer-line, bend, and vertical bend lattices; asymmetric closed ring for native-reversal ground truth |
| `test_emit_sad.py` | `emit_sad` | 6 | 4-cell FODO ring with RF (45° bends, ρ = 1 m, K1 = ±0.2) |
| `test_chromaticity_sad.py` | `chromaticity_sad`, `generate_off_momentum_tune_function` | 11 | Same 4-cell FODO ring without RF |
| `test_transfer_matrix_sad.py` | `transfer_matrix_sad` | 8 | Minimal transfer-line |
| `test_track_sad.py` | `track_sad` | 12 | Minimal transfer-line |
| `test_rebuild_lattice.py` | `rebuild_sad_lattice` | 6 | Minimal transfer-line |

## Lattice fixture notes

All shared lattice-writing helpers live in `tests/support/lattices.py`. Import
from there rather than defining local copies.

- **Transfer-line** (`write_minimal_transfer_lattice`): `MOMENTUM = 1.0 GEV`, a
  single `DRIFT TEST_DRIFT = (L = 1.0)`, `START`/`END` markers, and
  `LINE TEST_LINE`.
- **Bend lattice** (`write_minimal_bend_lattice`): the same structure, with
  `BEND TEST_BEND = (L = 1.0 ANGLE = 0.1)`.
- **Vertical bend lattice** (`write_minimal_vertical_bend_lattice`): the same
  structure, with `ROTATE = pi/2` added to the bend. This gives vertical rather
  than horizontal dispersion and survey content, for the
  `reverse_survey_vertical` sign-flip tests.
- **FODO ring** (`write_fodo_ring`): 4 cells of 2 bends at 45 degrees, with
  rho = 1 m, `K1 = +-0.2`, `DRIFT D = (L = 0.5)`, and `CAVI FREQ = 18 MHz`.

  Both the emit and the chromaticity tests use it. Emit requires the cavity.
  Chromaticity is a transverse optics quantity, so the cavity is harmless
  there. Element parameters use SAD's whitespace-separated syntax.
- **Asymmetric closed ring** (`write_asymmetric_closed_ring`): a deliberately
  asymmetric ring, carrying a bend with `E1 != E2` and `F1`/`FRINGE`, a K0-only
  corrector with `FB1 != FB2`, and two opposite-sign quadrupoles.

  It defines both a `FWD` line and a native SAD-reversed `REV` line. This
  verifies `reverse_element_order` against SAD's own reversal, independently of
  the code path under test.

`test_track_sad.py` also uses a local marker-only lattice, with two markers and
no physical elements. It is unique to the tracking edge-case tests and is not
shared.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
