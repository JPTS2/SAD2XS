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

Many parser tests cover planned or partially-implemented behaviour. Tests
written for features not yet implemented in the parser currently fail —
they document the parser's current limitations and must not be modified to
hide known failures. Issue-linked cases receive the `known_issue` marker from
the central mapping and run in CI as ordinary failures.

**Functions** is the count of `def test_` entries in the file. **Fail** is
actual failing instances from the test run. `test_errors.py` is parametrised
(one function contributes 4 instances for the protected-name cases), so its
fail count exceeds its failing function count.

| File | Functions | Fail | Failure root cause |
|------|-----------|------|--------------------|
| `test_preprocessing.py` | 4 | 1 | `on`/`off` prefix variable names removed during preprocessing instead of preserved |
| `test_comments.py` | 10 | 0 | — |
| `test_globals.py` | 10 | 1 | Global name prefix collision not handled correctly |
| `test_units.py` | 7 | 1 | `RAD` angle unit not parsed as numeric radians |
| `test_lines.py` | 6 | 0 | — |
| `test_line_names.py` | 3 | 0 | — |
| `test_element_parameters.py` | 13 | 0 | — |
| `test_element_expressions.py` | 8 | 4 | Parenthesised and math-function expressions return too many values when unpacked (API mismatch) |
| `test_deferred_expressions.py` | 15 | 1 | Multiline deferred expression syntax not supported |
| `test_functions.py` | 5 | 5 | SAD user-defined function definition and call parsing not yet implemented |
| `test_repeated_definitions.py` | 9 | 1 | Repeated element name across types does not raise `ValueError` as required |
| `test_errors.py` | 13 | 8 | Several parser error contracts not yet enforced (missing equals, unmatched parentheses, protected names) |

### `test_functions.py` note

SAD supports user-defined functions with the syntax `f[x_] := expr`. The parser
does not yet handle this syntax. All five tests fail with parse errors. These
tests document the full planned behaviour: definition, module body, and use in
both deferred and element expressions.

### `test_errors.py` note

Error contract tests check that the parser raises clear `ValueError`s for
malformed input. Several expected errors are not yet raised, and some error
messages do not yet match the expected regex patterns. The 8 failures
document planned parser defensive behaviour.

## Shared Fixtures

`conftest.py` provides `write_lattice`, which writes a temporary SAD file from
a dedented string and changes the working directory to the file's parent so
the parser can find it by name. All parser tests should use this fixture
rather than defining local file-writing helpers.
