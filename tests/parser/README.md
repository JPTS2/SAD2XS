# Parser Tests

This folder contains tests for the SAD text parser and the parser-owned
expression conversion layer.

Parser tests assert on cleaned SAD input sections and on the structure of the
`parsed` dictionary returned by the parser: `parsed["globals"]`,
`parsed["elements"]`, `parsed["lines"]`, and `parsed["expressions"]`. They
may also test expression conversion into an `xtrack.Environment` when that
behaviour belongs to the deferred parser expression layer.

Parser tests should not assert on Xsuite element class selection, element
tracking physics, full SAD-to-Xsuite pipeline behaviour, output writer
formatting, or SAD helper command construction. Those behaviours belong in
`tests/conversion`, `tests/writer`, or `tests/sad_helpers`.

## Coverage

**Functions** is the count of `def test_` entries in the file. **Fail** is
actual failing instances from the test run. `test_errors.py` is parametrised
(one function contributes 3 instances for the protected-name cases), so its
instance count exceeds its function count.

| File | Functions | Fail | Notes |
|------|-----------|------|-------|
| `test_preprocessing.py` | 4 | 0 | — |
| `test_comments.py` | 10 | 0 | — |
| `test_globals.py` | 10 | 0 | — |
| `test_units.py` | 15 | 0 | — |
| `test_lines.py` | 6 | 0 | — |
| `test_line_names.py` | 3 | 0 | — |
| `test_element_parameters.py` | 13 | 0 | — |
| `test_element_expressions.py` | 8 | 0 | — |
| `test_deferred_expressions.py` | 15 | 0 | — |
| `test_functions.py` | 5 | 5 | SAD user-defined function definitions not yet implemented |
| `test_repeated_definitions.py` | 9 | 0 | — |
| `test_errors.py` | 13 | 0 | — |

### `test_globals.py` note

`CHARGE` is recognised as a protected global keyword so that SAD files
containing it do not cause parse errors. However, SAD only supports positrons
and silently ignores `CHARGE` at runtime (confirmed by K. Oide, 2026-06-27),
so the parser does not store `CHARGE` in `q0`. Any `CHARGE != 1` line emits a
`UserWarning` directing users to `reverse_charge_sign=True`. The `q0` global always
defaults to `+1` regardless of what `CHARGE` is set to.

### `test_functions.py` note

SAD supports user-defined functions with the syntax `f[x_] := expr`. The parser
does not yet handle this syntax. All five tests fail with parse errors. These
tests document the full planned behaviour: definition, module body, and use in
both deferred and element expressions. The implementation is deferred to its own
branch — see `dev/parser_completeness_plan.md`.

## Shared Fixtures

`conftest.py` provides `write_lattice`, which writes a temporary SAD file from
a dedented string and changes the working directory to the file's parent so
the parser can find it by name. All parser tests should use this fixture
rather than defining local file-writing helpers.
