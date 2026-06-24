# Conversion Pipeline Tests

This folder contains tests for public conversion pipeline behaviour that is not
owned by one SAD element family.

Use this folder for options and line-level behaviour: the public
`convert_sad_to_xsuite` entry point, explicit line selection, write/reload
behaviour, excluded elements, offset markers, reference-particle setup,
multipole replacements, reverse charge, reverse element order, and reverse bend
direction.

Element-family physics belongs in `tests/conversion/elements/`. This folder
should stay focused on pipeline orchestration and public user options.

## Coverage

| File | Functions | Fail | Failure root cause |
|------|-----------|------|--------------------|
| `test_convert_sad_to_xsuite.py` | 22 | 0 | — |
| `test_excluded_elements.py` | 8 | 0 | — |
| `test_multipole_replacements.py` | 5 | 0 | — |
| `test_offset_markers.py` | 7 | 1 | Symbolic s-position expression for offset markers — `NameError: name 'l0' is not defined` |
| `test_reference_particle.py` | 10 | 0 | — |
| `test_reverse_bend_direction.py` | 10 | 0 | — |
| `test_reverse_charge.py` | 4 | 3 | `reverse_charge=True` does not negate `q0` — feature not working |
| `test_reverse_element_order.py` | 6 | 0 | — |

### `test_convert_sad_to_xsuite.py` note

Covers the entry-point contract in detail: output file creation, output
filename defaults, line name selection, suppressed-element handling,
`_test_mode` behaviour, and line name defaulting. All 22 tests pass.

### `test_offset_markers.py` note

Covers offset marker installation: dict format, s-position values, multiple
markers, marker names. The symbolic s-position test (`l0` as a named variable)
fails because the expression is not resolved before the marker is placed.

### `test_reverse_charge.py` note

`reverse_charge=True` should negate `q0` for all charge signs. Currently the
feature has no effect. All three physics tests fail; the structural test
(that the parameter is accepted without error) passes.
