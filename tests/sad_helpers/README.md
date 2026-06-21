# SAD Helper Tests

This folder contains tests for `sad2xs.sad_helpers`, one file per public
helper function.

Each file covers both SAD-free tests (command string generation, structure of
the generated macro) and smoke tests (end-to-end execution against a real SAD
installation). Converter physics comparisons that consume helper output belong
in `tests/conversion/`.

## Coverage

- `test_twiss_sad.py` — `twiss_sad`, `compute_second_order_dispersions`,
  `compute_chromatic_functions`, `generate_twiss_print_function`; SAD-free
  command generation tests and end-to-end smoke tests against a minimal
  transfer-line lattice
- `test_survey_sad.py` — `survey_sad`
- `test_emit_sad.py` — `emit_sad`
- `test_track_sad.py` — `track_sad`
- `test_chromaticity_sad.py` — `chromaticity_sad`
- `test_transfer_matrix_sad.py` — `transfer_matrix_sad`
- `test_rebuild_lattice.py` — `rebuild_sad_lattice`
