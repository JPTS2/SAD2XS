# Parser tests

This folder contains tests for the SAD text parser and the parser-owned
expression conversion layer.

Parser tests should assert on:

- cleaned SAD input sections;
- `parsed["globals"]`;
- `parsed["elements"]`;
- `parsed["lines"]`;
- `parsed["expressions"]`;
- expression conversion into an `xtrack.Environment` when the behaviour belongs
  to deferred parser expressions.

Parser tests should not assert on:

- Xsuite element class selection;
- element tracking physics;
- full SAD-to-Xsuite pipeline behaviour;
- output writer formatting;
- generated lattice or optics files;
- SAD helper command construction or output parsing.

Those behaviours belong in `tests/conversion`, `tests/writer`,
`tests/roundtrip`, `tests/examples`, or `tests/sad_helpers`.

Parser tests should remain focused on parser ownership even though the broader
test suite is expected to run in a SAD-capable environment.

## File ownership

- `test_preprocessing.py`: command filtering, case normalization, and whitespace
  normalization before semantic parsing.
- `test_comments.py`: SAD comment stripping and comment-safe section splitting.
- `test_globals.py`: special globals, defaults, config overrides, and global name
  boundary rules.
- `test_units.py`: unit parsing helpers and unit-specific parser behaviour.
- `test_lines.py`: valid line syntax and component preservation.
- `test_line_names.py`: line names and references that contain the token `line`.
- `test_element_parameters.py`: valid element section and parameter parsing.
- `test_element_expressions.py`: element parameter expressions and their
  evaluation through the parser expression layer.
- `test_deferred_expressions.py`: deferred expression parsing, dependency
  resolution, and conversion.
- `test_functions.py`: SAD user-defined function parsing and use in expressions.
- `test_repeated_definitions.py`: repeated-definition policy for globals,
  expressions, lines, elements, and parameters.
- `test_errors.py`: malformed parser input and expected parser failure
  contracts.

## Shared fixtures

`conftest.py` provides `write_lattice`, which writes a temporary SAD file from a
dedented string. Parser tests should use this fixture instead of defining local
file-writing helpers.
