# Observability Tests

This folder contains tests for user-visible output policy.

Use these tests to protect quiet mode, verbose mode, and the absence of
uncontrolled output from the converter and SAD helpers. Behavioural converter
correctness belongs in `tests/conversion/`.

## Output Policy

- Errors are raised, with diagnostics embedded in the exception.
- Warnings are always emitted (logging WARNING), even in quiet mode.
- Progress (INFO) and detail (DEBUG) are opt-in via `_verbose=True` or
  `sad2xs.set_log_level`.
- A clean conversion at the default level is completely silent.
- All diagnostics go through the `sad2xs` logger to stderr; stdout is never
  used by the library.

## What Belongs Here

- Full-pipeline silence at the default level (including the writer, the
  generated-file reload, and progress bars).
- Warnings remaining visible at the default level.
- `_verbose=True` / `set_log_level` enabling the progress narrative.
- Formatter and level-control contracts of `sad2xs._logging`.

## What Does Not Belong Here

- Converter physics or element correctness.
- SAD helper output parsing or correctness.
- Installation or packaging behaviour.

## Coverage

### `test_quiet_converter_output.py` — 7 tests, all expected to pass

Tests the converter output policy. Uses minimal in-memory SAD lattices
written to `tmp_path` — does not call the SAD executable. Placed in the
**SAD-free** CI job.

| Test | What it asserts |
|------|-----------------|
| `test_full_conversion_is_silent_by_default` | `capfd` captures nothing for a warning-free full-pipeline conversion (solenoid pair and offset marker in the lattice cover the tqdm and generated-file reload leaks) |
| `test_quiet_mode_emits_no_progress_records` | no INFO/DEBUG records at the default level |
| `test_parser_warnings_visible_at_default_level` | electron-mass assumption warns in quiet mode |
| `test_verbose_enables_progress_narrative` | `_verbose=True` emits INFO records; stdout stays empty |
| `test_set_log_level_debug_enables_debug_records` | `set_log_level("debug")` exposes DEBUG records |
| `test_set_log_level_rejects_unknown_level` | invalid level raises `ValueError` |
| `test_formatter_prefixes_warnings_but_not_narrative` | `SAD2XS <LEVEL>:` prefix on WARNING/ERROR only |

### `test_no_print_statements.py` — 1 test, expected to pass

AST source scan of every `sad2xs/**/*.py` file asserting zero `print()`
call nodes: runtime silence tests only cover the code paths their lattices
exercise, so this closes the gap for all other paths. Generated-file string
templates pass naturally (string literals are not call nodes). Placed in
the **SAD-free** CI job.

### `test_sad_helper_output_controls.py` — 10 tests, all expected to pass

Two categories. Signature checks (7 tests) guard the single-mechanism
design: helper verbosity is controlled by `sad2xs.set_log_level`, so a
`_verbose` parameter appearing on any helper means a second, parallel
output mechanism was introduced. Behaviour tests (3 tests) confirm helpers
are silent by default and expose SAD's terminal output at debug level.
Uses a minimal transfer-line lattice and requires the SAD executable.
Placed in the **SAD-required** CI job.

| Test | What it asserts |
|------|-----------------|
| `test_*_has_no_verbose_parameter` (7 helpers) | no `_verbose` parameter on any helper signature |
| `test_twiss_sad_is_silent_by_default` | `capfd` captures nothing for a successful call |
| `test_survey_sad_is_silent_by_default` | `capfd` captures nothing for a successful call |
| `test_twiss_sad_logs_sad_output_at_debug_level` | debug records include the narrative and SAD's terminal output |
