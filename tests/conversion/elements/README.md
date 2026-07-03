# Element Conversion Tests

This folder contains conversion tests for individual SAD element families.

Each file covers one element mnemonic or one tightly related element group.
The usual progression within a file is: direct converter checks (calling the
element converter with a parsed element dictionary and asserting on the produced
Xsuite object), full pipeline checks (calling `convert_sad_to_xsuite` and
asserting on the resulting line), then SAD optics and tracking comparisons
where relevant.

Shared fixtures live in `conftest.py`. Cross-file support belongs in
`tests/support/` rather than being copied between element files.

## Coverage

**Functions** is the count of `def test_` entries in the file. Parametrised
tests expand to more instances at runtime — the **Fail** column is actual
failing instances from the test run, not failing functions. For non-parametrised
files these are equal; for heavily parametrised files (sol, corrector, bend)
the fail instance count exceeds the failing function count.

Tests that currently fail document known converter bugs. They must not be
modified to pass artificially. Tests linked to open issues are selected through
the central `known_issue` mapping; this marker changes CI routing, not outcomes.

Total collected from this folder: see `tests/README.md`.

| File | Functions | Fail | Failure root cause |
|------|-----------|------|--------------------|
| `test_apert.py` | 20 | 0 | — |
| `test_beambeam.py` | 5 | 0 | — |
| `test_bend.py` | 23 | 4 | Element offsets with horizontal shift |
| `test_cavi.py` | 19 | 0 | — |
| `test_coord.py` | 10 | 0 | — |
| `test_corrector.py` | 18 | 14 | Corrector physics incorrect — optics and tracking both wrong for kicks, rotations, offsets |
| `test_drift.py` | 6 | 0 | — |
| `test_mark.py` | 5 | 0 | — |
| `test_moni.py` | 5 | 0 | — |
| `test_mult.py` | 12 | 1 | Combined multipole orders — cross-order physics wrong |
| `test_oct.py` | 18 | 0 | — |
| `test_quad.py` | 18 | 0 | — |
| `test_sext.py` | 18 | 0 | — |
| `test_sol.py` | 23 | 0 | — |

### `test_sol.py` note

Issue #58 (`test_sol_optics_matches_sad_twiss_at_end[±0.1]`) is resolved. The
original diagnosis (SAD's GEO exit transforms computed at runtime during
`COD`/`CALC`, not statically derivable) turned out not to be the cause for this
test: the actual mismatch was that SAD's `betx`/`bety`/`alfx`/`alfy` report the
*projected* (physical) beam-envelope optics functions, while Xsuite's
`twiss4d`/`twiss6d` report the mode-1/mode-2 (Courant-Snyder eigenmode)
components separately — real, physically meaningful quantities in their own
right, just a different convention. A solenoid genuinely couples the two
modes, so the two conventions disagree there (confirmed via an independent
analytic re-derivation of the exact solenoid transfer matrix, not just a
converter-side assumption). `_sol_xsuite_optics_values()` now sums the mode
components (`betx1+betx2`, `bety1+bety2`, `alfx1+alfx2`, `alfy1+alfy2`) to
match SAD's convention. See `docs/sad-helpers.md` for the general explanation
and worked example.

This file also has a solenoid `DISFRIN` (fringe kick) limitation test —
`test_sol_disfrin_off_diverges_from_xsuite_in_tracking` — which is not a
failing test: it asserts that SAD and Xsuite genuinely diverge when
`DISFRIN=1` is not set, since SAD2XS does not model the SAD solenoid fringe
kick. This documents an accepted, permanent limitation (see
`docs/design-decisions.md`), not an open bug — it is deliberately not in
`known_issues.py`.

### `test_corrector.py` note

14 failing instances come from 6 test functions, each parametrised over kick
sign or offset direction (2–3 parameter values each). Optics and tracking both
fail for horizontal kicks, rotated kicks, and element offsets, confirming the
corrector physics is broadly wrong in the converter.

## Shared Fixtures

`conftest.py` provides:
- `xsuite_environment` — a fresh `xt.Environment` for direct converter tests
- `parsed_elements` — helper for constructing minimal parsed element dictionaries
- `assert_environment_element` — assertion helper for environment element contents
