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
| `test_aper.py` | 20 | 3 | `ROTATE` not preserved (issue #33) |
| `test_beambeam.py` | 5 | 0 | — |
| `test_bend.py` | 23 | 7 | Symbolic length/angle; thin bend; element offsets with horizontal shift |
| `test_cavi.py` | 19 | 0 | — |
| `test_coord.py` | 10 | 0 | — |
| `test_corrector.py` | 18 | 16 | Corrector physics incorrect — optics and tracking both wrong for kicks, rotations, offsets |
| `test_drift.py` | 6 | 2 | Symbolic variable support not implemented (parametric drift length) |
| `test_mark.py` | 5 | 0 | — |
| `test_moni.py` | 5 | 0 | — |
| `test_mult.py` | 12 | 2 | Combined multipole orders — cross-order physics wrong |
| `test_oct.py` | 15 | 3 | Symbolic variable support; thin octupole to `xt.Multipole` conversion |
| `test_quad.py` | 15 | 5 | Symbolic variable support; thin quadrupole; rotation tracking |
| `test_sext.py` | 15 | 3 | Symbolic variable support; thin sextupole to `xt.Multipole` conversion |
| `test_sol.py` | 17 | 41 | Solenoid reference transform physics |

### `test_sol.py` note

The solenoid tests are the most extensive in this folder. The `xt.Rotation` API
migration (slice 3) is now complete, so `test_sol_bound_reference_transforms_use_current_xsuite_api`
is no longer a known issue. 17 test functions expand to 41 failing instances at
runtime because three parametrised functions carry a full matrix of perturbation
types (`dxdy`, `dpx`, `dpy`, `dxdy_dpx_dpy`, `dxdy_chi1_chi2`) crossed with
reversal modes (`forward`, `rev_in`, `rev_out`, `rev_both`). The failures document
the production code work remaining for solenoid reference transform physics.

The root cause of all 41 failures is that SAD's GEO solenoid exit transforms are
computed at runtime during `COD`/`CALC` and depend on the interior elements of the
solenoid pair. For a GEO=1 boundary solenoid with entry transforms (DX, DPX etc.),
SAD propagates the reference trajectory through the interior and computes what
transforms the exit boundary solenoid needs to restore the orbit to zero. When a
powered quadrupole sits inside the solenoid, it deflects the local trajectory such
that the angle arriving at the exit boundary differs from the entry angle; the naive
"inverse of entry transforms" approximation leaves a residual angle comparable to
`K1 * x_inside * L` and is incorrect in general. The correct exit transforms cannot
be derived statically from the SAD file — they require running SAD's rebuild. This
is a SAD-side computation, not a sad2xs production code gap. See issue #58.

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
