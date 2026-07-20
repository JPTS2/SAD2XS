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
| `test_preprocessing.py` | 6 | 0 | — |
| `test_comments.py` | 10 | 0 | — |
| `test_globals.py` | 12 | 0 | — |
| `test_units.py` | 7 | 0 | — |
| `test_lines.py` | 6 | 0 | — |
| `test_line_names.py` | 3 | 0 | — |
| `test_element_parameters.py` | 13 | 0 | — |
| `test_element_expressions.py` | 8 | 0 | — |
| `test_deferred_expressions.py` | 17 | 0 | — |
| `test_functions.py` | 2 | 0 | — |
| `test_repeated_definitions.py` | 9 | 0 | — |
| `test_errors.py` | 14 | 0 | — |

### `test_preprocessing.py` note

FFS commands (SAD's own interactive command interpreter — `USE`, `CALCULATE`,
`GO`, etc.) were previously misparsed as deferred expressions whenever they
took an assignment-like form (e.g. `FFS USE = RING;`), which then failed deep
inside expression conversion with no indication that FFS was the actual
cause. FFS commands are now recognised and dropped alongside `ON`/`OFF`,
matching bare `FFS;`, `FFS USE = <name>;`, and the bracketed `FFS[...]`
command-string form.

### `test_deferred_expressions.py` note

When one or more deferred expressions cannot be resolved, the conversion
error now names each unresolved variable together with its source line
number and expression text, instead of a single blanket message — so a bad
or unsupported expression can be found directly in a large lattice file
without a debugger.

### `test_globals.py` note

`CHARGE` is recognised as a protected global keyword so that SAD files
containing it do not cause parse errors. However, SAD only supports positrons
and silently ignores `CHARGE` at runtime (confirmed by K. Oide, 2026-06-27),
so the parser does not store `CHARGE` in `q0`. Any `CHARGE != 1` line emits a
`UserWarning` directing users to `reverse_charge_sign=True`. The `q0` global always
defaults to `+1` regardless of what `CHARGE` is set to.

### `test_functions.py` note

SAD user-defined functions (`f[x_] := expr`) are explicitly rejected with a
clear `ValueError` citing the source line, rather than being silently
misparsed as a deferred expression (a bare `:=` previously produced a
garbage deferred-expression key with no indication of the real problem).
Covers a bare definition and one with a `Module[]` body. Three
"function call" tests (deferred expression, element expression, nested
calls) are not present here: since a definition is always rejected before
it is ever used, they had no reachable scenario left to exercise and were
consolidated into the two tests above rather than duplicated three times
over.

## Shared Fixtures

`conftest.py` provides `write_lattice`, which writes a temporary SAD file from
a dedented string and changes the working directory to the file's parent so
the parser can find it by name. All parser tests should use this fixture
rather than defining local file-writing helpers.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
