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
| `test_twiss_sad.py` | `twiss_sad`, `compute_second_order_dispersions`, `compute_chromatic_functions`, `generate_twiss_print_function` | 22 | Minimal transfer-line (1 m drift, START/END markers); minimal bend (0.1 rad BEND); accelerating MULT (VOLT/FREQ) for TRPT; asymmetric closed ring for native-reversal ground truth |
| `test_survey_sad.py` | `survey_sad`, `generate_survey_print_function` | 16 | Same transfer-line and bend lattices; asymmetric closed ring for native-reversal ground truth |
| `test_emit_sad.py` | `emit_sad` | 6 | 4-cell FODO ring with RF (45° bends, ρ = 1 m, K1 = ±0.2) |
| `test_chromaticity_sad.py` | `chromaticity_sad`, `generate_off_momentum_tune_function` | 11 | Same 4-cell FODO ring without RF |
| `test_transfer_matrix_sad.py` | `transfer_matrix_sad` | 8 | Minimal transfer-line |
| `test_track_sad.py` | `track_sad` | 12 | Minimal transfer-line |
| `test_rebuild_lattice.py` | `rebuild_sad_lattice` | 6 | Minimal transfer-line |

## Lattice fixture notes

All shared lattice-writing helpers live in `tests/support/lattices.py`. Import
from there rather than defining local copies.

- **Transfer-line** (`write_minimal_transfer_lattice`): `MOMENTUM = 1.0 GEV`, single `DRIFT TEST_DRIFT = (L = 1.0)`, `START`/`END` markers, `LINE TEST_LINE`.
- **Bend lattice** (`write_minimal_bend_lattice`): same structure with `BEND TEST_BEND = (L = 1.0 ANGLE = 0.1)`.
- **FODO ring** (`write_fodo_ring`): 4 cells × 2 bends of 45° (π/4 rad, ρ = 1 m), `K1 = ±0.2`, `DRIFT D = (L = 0.5)`, `CAVI FREQ = 18 MHz`. Used by both emit and chromaticity tests — the cavity is required by emit and harmless for chromaticity (a transverse optics quantity unaffected by longitudinal RF). Element parameters use SAD's whitespace-separated syntax.
- **Asymmetric closed ring** (`write_asymmetric_closed_ring`): a deliberately asymmetric ring (bend `E1 != E2` with `F1`/`FRINGE`, K0-only corrector with `FB1 != FB2`, two opposite-sign quads) with both a `FWD` line and a native SAD-reversed `REV` line (`LINE REV = (-FWD)`). Used to verify `reverse_element_order=True` against SAD's own native reversal independently of the code path under test.

`test_track_sad.py` also uses a local marker-only lattice (two markers, no physical elements) that is unique to tracking edge-case tests and is not shared.
