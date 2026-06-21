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
| `test_aper.py` | 19 | 4 | `ROTATE` not preserved; combined rect+ellipse conversion unsupported |
| `test_beambeam.py` | 5 | 0 | — |
| `test_bend.py` | 23 | 10 | `k0 = angle/length` conversion wrong; symbolic length/angle; thin bend; element offsets |
| `test_cavi.py` | 10 | 6 | SAD uses phase (`PHI`), converter sets lag; harmonic-driven cavity not converted correctly |
| `test_coord.py` | 10 | 0 | — |
| `test_corrector.py` | 18 | 16 | Corrector physics incorrect — optics and tracking both wrong for kicks, rotations, offsets |
| `test_drift.py` | 6 | 2 | Symbolic variable support not implemented (parametric drift length) |
| `test_mark.py` | 5 | 0 | — |
| `test_moni.py` | 5 | 0 | — |
| `test_mult.py` | 12 | 2 | Combined multipole orders — cross-order physics wrong |
| `test_oct.py` | 15 | 3 | Symbolic variable support; thin octupole to `xt.Multipole` conversion |
| `test_quad.py` | 15 | 5 | Symbolic variable support; thin quadrupole; rotation tracking |
| `test_sext.py` | 15 | 3 | Symbolic variable support; thin sextupole to `xt.Multipole` conversion |
| `test_sol.py` | 18 | 42 | `xt.Rotation` API change (pending slice 3); solenoid reference transform physics |

### `test_sol.py` note

The solenoid tests are the most extensive in this folder. 18 test functions
expand to 42 failing instances at runtime because three parametrised functions
carry a full matrix of perturbation types (`dxdy`, `dpx`, `dpy`,
`dxdy_dpx_dpy`, `dxdy_chi1_chi2`) crossed with reversal modes (`forward`,
`rev_in`, `rev_out`, `rev_both`). All 42 instances fail — the test structure
is complete and correct; the failures document the production code work required.

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
