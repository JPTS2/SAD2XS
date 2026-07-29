# Conversion Pipeline Tests

This folder contains tests for public conversion pipeline behaviour that is not
owned by one SAD element family.

Use this folder for options and line-level behaviour: the public
`convert_sad_to_xsuite` entry point, explicit line selection, write/reload
behaviour, excluded elements, offset markers, reference-particle setup,
multipole replacements, reverse charge sign, reverse element order, reverse
survey horizontal, reverse survey vertical, and the per-element `-NAME`
reversal syntax.

Element-family physics belongs in `tests/conversion/elements/`. This folder
should stay focused on pipeline orchestration and public user options.

## Coverage

**Tests** is the number of test instances pytest collects, which counts
each parametrisation separately.

| File | Tests | Fail | Failure root cause |
|------|-----------|------|--------------------|
| `test_convert_sad_to_xsuite.py` | 45 | 0 | — |
| `test_math_function_expressions.py` | 7 | 0 | — |
| `test_excluded_elements.py` | 9 | 0 | — |
| `test_multipole_replacements.py` | 8 | 0 | — |
| `test_offset_markers.py` | 10 | 0 | — |
| `test_reference_particle.py` | 11 | 0 | — |
| `test_reverse_survey_horizontal.py` | 12 | 0 | — |
| `test_reverse_survey_vertical.py` | 13 | 0 | — |
| `test_reverse_charge_sign.py` | 6 | 0 | — |
| `test_reverse_element_order.py` | 17 | 0 | — |
| `test_reversed_component_syntax.py` | 7 | 0 | — |

### `test_convert_sad_to_xsuite.py` note

Covers the entry-point contract: output file creation, output filename
defaults, line name selection and defaulting, suppressed-element handling, and
`_test_mode` behaviour.

### `test_offset_markers.py` note

Covers offset marker resolution and installation:

- markers with no `OFFSET` parameter are left alone;
- `MARK` and `MONI` are moved to the computed `s` position;
- an `OFFSET` at or below 1 is a no-op, so the marker stays in place;
- a reversed `-NAME` reference walks the offset in the opposite direction;
- multiple offset markers are all moved, and non-offset markers survive
  alongside them;
- an excluded solenoid removes its marker permanently;
- symbolic `s` expressions resolve through the line's `xt.Environment`, not
  through a bare `eval()`.

### `test_reverse_charge_sign.py` note

Covers `reverse_charge_sign` and species-aware reference-particle setup:
default positron species, proton mass giving a proton species, charge-sign
reversal to electron and antiproton, `p0c`/`mass0` isolation, and the
`UserWarning` raised for `CHARGE != 1` in the SAD file.

### `test_reversed_component_syntax.py` note

Covers SAD's per-element `-NAME` reversal syntax, through
`create_reversed_component`. This is a separate path from the whole-line
`-LINE` reversal covered by `test_reverse_element_order.py`.

It covers direction-symmetric reuse for drifts and quadrupoles, solenoid `ks`
negation, the bend edge-angle swap, and the bend `fint`/`hgap` swap. Two
tracking comparisons run against SAD's own per-element-reversed line, with the
poleface angle and the soft-edge fringe isolated from each other.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
