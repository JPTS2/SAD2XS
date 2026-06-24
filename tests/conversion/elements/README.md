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
| `test_corrector.py` | 18 | 16 | Corrector physics incorrect — optics and tracking both wrong for kicks, rotations, offsets |
| `test_drift.py` | 6 | 0 | — |
| `test_mark.py` | 5 | 0 | — |
| `test_moni.py` | 5 | 0 | — |
| `test_mult.py` | 12 | 2 | Combined multipole orders — cross-order physics wrong |
| `test_oct.py` | 18 | 0 | — |
| `test_quad.py` | 18 | 2 | Rotation tracking (±45°) |
| `test_sext.py` | 18 | 0 | — |
| `test_sol.py` | 17 | 4 | Solenoid GEO exit-transform physics (issue #58) |

### `test_sol.py` note

The solenoid test functions are heavily parametrised. Most combinations pass
following the `xt.Rotation` API migration (issue #19). The 4 remaining failing
instances are:

- `test_sol_optics_matches_sad_twiss_at_end[±0.1]` (2 instances)
- `test_sol_reference_transform_restores_design_orbit_at_end[out-dxdy]` and
  `[out-dxdy_dpx_dpy]` (2 instances)

The root cause is that SAD's GEO solenoid exit transforms are computed at
runtime during `COD`/`CALC` and depend on the interior elements of the solenoid
pair. The correct exit transforms cannot be derived statically from the SAD file
— they require running SAD's rebuild. See issue #58.

### `test_corrector.py` note

16 failing instances come from 8 test functions, each parametrised over kick
sign or offset direction (2–3 parameter values each). Optics and tracking both
fail for horizontal kicks, thin kicks, rotated kicks, and element offsets,
confirming the corrector physics is broadly wrong in the converter.

## Shared Fixtures

`conftest.py` provides:
- `xsuite_environment` — a fresh `xt.Environment` for direct converter tests
- `parsed_elements` — helper for constructing minimal parsed element dictionaries
- `assert_environment_element` — assertion helper for environment element contents
