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

| File | Functions | Fail | Failure root cause |
|------|-----------|------|--------------------|
| `test_convert_sad_to_xsuite.py` | 23 | 0 | — |
| `test_excluded_elements.py` | 9 | 0 | — |
| `test_multipole_replacements.py` | 5 | 0 | — |
| `test_offset_markers.py` | 7 | 0 | — |
| `test_reference_particle.py` | 10 | 0 | — |
| `test_reverse_survey_horizontal.py` | 12 | 0 | — |
| `test_reverse_survey_vertical.py` | 13 | 0 | — |
| `test_reverse_charge_sign.py` | 6 | 0 | — |
| `test_reverse_element_order.py` | 17 | 1 | `_import_sad_quad_fringes` not yet implemented (expected until the converter/reversal work lands) |
| `test_reversed_component_syntax.py` | 7 | 0 | — |

### `test_convert_sad_to_xsuite.py` note

Covers the entry-point contract in detail: output file creation, output
filename defaults, line name selection, suppressed-element handling,
`_test_mode` behaviour, and line name defaulting. All 23 tests pass.

### `test_offset_markers.py` note

Covers offset marker installation: dict format, s-position values, multiple
markers, marker names, and symbolic s-position expressions (`l0` as a named
variable), which are resolved through the line's `xt.Environment` rather than
bare `eval()`. All 7 pass.

### `test_reverse_charge_sign.py` note

Covers `reverse_charge_sign=True` and species-aware reference particle setup.
Tests: default positron species, proton mass → proton species, charge sign
reversal (positron → electron, proton → antiproton), p0c/mass0 isolation, and
UserWarning emission when `CHARGE != 1` is found in the SAD file. All 6 pass.

### `test_reversed_component_syntax.py` note

Covers SAD's per-element `-NAME` reversal syntax (`create_reversed_component`,
distinct from the whole-line `-LINE`/`reverse_element_order` path covered by
`test_reverse_element_order.py`): direction-symmetric reuse (drift, quad),
solenoid ks negation, bend edge-angle swap, bend fringe-field (fint/hgap)
swap, and two tracking comparisons against real SAD's own per-element-reversed
line (poleface angle and soft-edge fringe, isolated from each other). All 7
pass.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
