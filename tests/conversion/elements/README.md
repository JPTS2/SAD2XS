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

SAD-comparison tracking and Twiss checks uniformly use `rfsw=True` and compare
`zeta`/`delta` alongside the transverse coordinates, matching `test_cavi.py`'s
original pattern. Files with only a raw `s`/length check via `line.get_table()`
(`test_apert.py`, `test_beambeam.py`, `test_mark.py`, `test_moni.py`) are the
exception — they have no twiss/tracking comparison to extend.

Total collected from this folder: see `tests/README.md`.

| File | Functions | Fail | Failure root cause |
|------|-----------|------|--------------------|
| `test_apert.py` | 20 | 0 | — |
| `test_beambeam.py` | 5 | 0 | — |
| `test_bend.py` | 23 | 4 | Element offsets with horizontal shift |
| `test_cavi.py` | 19 | 0 | — |
| `test_coord.py` | 10 | 0 | — |
| `test_corrector.py` | 18 | 0 | — |
| `test_drift.py` | 6 | 0 | — |
| `test_mark.py` | 5 | 0 | — |
| `test_moni.py` | 5 | 0 | — |
| `test_mult.py` | 13 | 4 | `SK1` rotation-convention mismatch; small `K0`/`SK0`-alone residual |
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

Adding `zeta` to the tracking/twiss comparisons here (see the `Coverage`
section above) surfaced a genuine converter bug in
`test_sol_reference_transform_restores_design_orbit_at_end`: several
parametrisations with a reversed line orientation and a `DPX`/`DPY`/`DX+DY`
reference-transform combination diverged from SAD on `zeta` only — `x`, `y`,
`px`, and `py` all matched. Root cause and fix are documented in
`docs/line-reversals.md` (new "Solenoid GEO reference-transform rotation
order" section). All 168 instances in this file now pass.

This file also has a solenoid `DISFRIN` (fringe kick) limitation test —
`test_sol_disfrin_off_diverges_from_xsuite_in_tracking` — which is not a
failing test: it asserts that SAD and Xsuite genuinely diverge when
`DISFRIN=1` is not set, since SAD2XS does not model the SAD solenoid fringe
kick. This documents an accepted, permanent limitation (see
`docs/design-decisions.md`), not an open bug — it is deliberately not in
`known_issues.py`.

### `test_corrector.py` note

Previously had 14 failing instances (horizontal kicks, rotated kicks, and
element offsets, optics and tracking) from a `MODEL_BEND = 'mat-kick-mat'`
bias — SAD zero-angle correctors convert to a plain `xt.Bend` with
`angle=0`, so this affected them too. Fixed by retuning `sad2xs/config.py`'s
Bend/Quadrupole/Sextupole/Octupole/Multipole model/integrator settings to
match a systematic SAD-cross-validated study (`bend-kick-bend` for
Bend/Corrector, `rot-kick-rot-high-order`/`yoshida4` for
Quad/Sext/Oct/Mult). All 18 functions in this file now pass.

### `test_mult.py` note

`test_mult_conversion_matches_sad_twiss_for_single_order` isolates each
multipole order (`K0`-`K3`, `SK0`-`SK3`) individually, added after the model
retune above surfaced discrepancies previously hidden inside the
combined-order test. This found and fixed two separate converter bugs, plus
one open, deeper question (issue #101):

- **Fixed**: a `MULT` with only `SK0` set is auto-simplified
  (`SIMPLIFY_MULTIPOLES=True`, the default) into an `xt.Bend` with
  `rot_s_rad` rotated by 90 degrees — the rotation sign was wrong, giving
  `y`/`py` negated versus SAD. The true, unsimplified `Multipole` path
  (`ksl[0]`) was already correct.
- **Fixed**: a combined `K0`+`SK0` `MULT`, when the values arrive as
  symbolic/deferred expressions rather than plain floats, crashed with
  `Unknown function arctan2` — Xsuite's expression evaluator uses `atan2`,
  not `arctan2`.
- **Open** (issue #101): `SK1` alone disagrees with SAD by `~1.9e-5`
  (`betx`/`bety`/`alfx`/`alfy`), confirmed not kick-count sensitive. Traced
  to SAD's `ROTATE` parameter and Xsuite's `xt.Rotation` element not
  representing quite the same transformation once combined with a
  multipole kick — both codes are internally self-consistent (native skew
  equals their own rotated-normal representation), but the two codes'
  rotated representations disagree with each other. A small, separate,
  much lower-priority residual (`~7.8e-6`, also not kick-count sensitive)
  affects `K0`/`SK0` alone too.

## Shared Fixtures

`conftest.py` provides:
- `xsuite_environment` — a fresh `xt.Environment` for direct converter tests
- `parsed_elements` — helper for constructing minimal parsed element dictionaries
- `assert_environment_element` — assertion helper for environment element contents
