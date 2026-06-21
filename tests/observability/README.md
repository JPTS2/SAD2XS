# Observability Tests

This folder contains tests for user-visible output policy.

Use these tests to protect quiet mode, verbose mode, and the absence of
uncontrolled output from the converter and SAD helpers. Behavioural converter
correctness belongs in `tests/conversion/`.

## What Belongs Here

- Converter `_verbose=False` producing no stdout or stderr.
- Converter `_verbose=True` producing output.
- Documenting the absence of output suppression in `sad_helpers` functions
  (signature checks that fail if `_verbose` is added without corresponding
  coverage being written).
- Baseline output presence tests for helper functions that print
  unconditionally.

## What Does Not Belong Here

- Converter physics or element correctness.
- SAD helper output parsing or correctness.
- Installation or packaging behaviour.

## Coverage

### `test_quiet_converter_output.py` — 3 tests, all expected to pass

Tests that `convert_sad_to_xsuite` respects `_verbose`. Uses a minimal
in-memory SAD lattice written to `tmp_path` — does not call the SAD
executable. Placed in the **SAD-free** CI job.

| Test | What it asserts |
|------|-----------------|
| `test_converter_produces_no_stdout_when_verbose_is_false` | `capsys` captures empty stdout with `_verbose=False` |
| `test_converter_produces_no_stderr_when_verbose_is_false` | `capsys` captures empty stderr with `_verbose=False` |
| `test_converter_produces_stdout_when_verbose_is_true` | `capsys` captures non-empty stdout with `_verbose=True` |

### `test_sad_helper_output_controls.py` — 9 tests, all expected to pass

Two categories. Signature checks (7 tests) confirm that no `sad_helpers`
function yet accepts a `_verbose` parameter. These tests pass now and will
**intentionally fail** if `_verbose` is added to a helper without corresponding
quiet/verbose coverage being written first — they act as a forcing function.
Baseline output tests (2 tests) confirm that the helpers which do run SAD
produce stdout unconditionally, and will catch a regression where all output
is silently removed. Uses a minimal transfer-line lattice and requires the SAD
executable. Placed in the **SAD-required** CI job.

| Test | What it asserts |
|------|-----------------|
| `test_twiss_sad_has_no_verbose_parameter` | `twiss_sad` signature has no `_verbose` |
| `test_survey_sad_has_no_verbose_parameter` | `survey_sad` signature has no `_verbose` |
| `test_emit_sad_has_no_verbose_parameter` | `emit_sad` signature has no `_verbose` |
| `test_chromaticity_sad_has_no_verbose_parameter` | `chromaticity_sad` signature has no `_verbose` |
| `test_transfer_matrix_sad_has_no_verbose_parameter` | `transfer_matrix_sad` signature has no `_verbose` |
| `test_track_sad_has_no_verbose_parameter` | `track_sad` signature has no `_verbose` |
| `test_rebuild_sad_lattice_has_no_verbose_parameter` | `rebuild_sad_lattice` signature has no `_verbose` |
| `test_twiss_sad_produces_stdout_output` | `twiss_sad` call produces non-empty stdout |
| `test_survey_sad_produces_stdout_output` | `survey_sad` call produces non-empty stdout |
