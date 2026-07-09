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
modified to pass artificially. Tests linked to known-failure entries are
selected through the central `known_issue` mapping; this marker changes CI
routing, not outcomes.

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
| `test_bend.py` | 32 | 0 | — |
| `test_cavi.py` | 19 | 0 | — |
| `test_coord.py` | 10 | 0 | — |
| `test_corrector.py` | 18 | 0 | — |
| `test_drift.py` | 6 | 0 | — |
| `test_mark.py` | 5 | 0 | — |
| `test_moni.py` | 5 | 0 | — |
| `test_mult.py` | 18 | 0 | — |
| `test_oct.py` | 18 | 0 | — |
| `test_quad.py` | 18 | 0 | — |
| `test_sext.py` | 18 | 0 | — |
| `test_sol.py` | 23 | 0 | — |

### `test_sol.py` note

The former solenoid optics known failure is resolved. The
original diagnosis (SAD's GEO exit transforms computed at runtime during
`COD`/`CALC`, not statically derivable) turned out not to be the cause for this
test: the actual mismatch was that SAD reports coupled `betx`/`bety`/`alfx`/
`alfy` in the Edwards-Teng (decoupled normal-mode) convention, while Xsuite's
`twiss4d`/`twiss6d` report the mode-1/mode-2 (Mais-Ripken eigenmode)
components separately — real, physically meaningful quantities in their own
right, just a different convention. A solenoid genuinely couples the two
modes, so the two conventions disagree there (confirmed via an independent
analytic re-derivation of the exact solenoid transfer matrix, not just a
converter-side assumption). `_sol_xsuite_optics_values()` now computes
Edwards-Teng values via `tests/support/coupled_optics.py`; for rotational
(solenoid) coupling these coincide numerically with the previously used
projected sums (`betx1+betx2`, ...), but Edwards-Teng is the convention that
also holds for skew-quad coupling, where the projected sums do not match
SAD. The full convention map is locked in by
`tests/conversion/test_coupled_twiss_convention.py`; see
`docs/sad-behaviour.md` for the general explanation and `docs/sad-helpers.md`
for the worked usage example.

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
kick (see `docs/sad-behaviour.md` for what the fringe kick is). This
documents an accepted, permanent limitation (see `docs/design-decisions.md`
for the converter decision), not an open bug — it is deliberately not in
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

`test_mult_conversion_matches_sad_twiss_for_single_order` isolates powered
multipole orders (`K1`-`K3`, `SK1`-`SK3`) after the model retune above
surfaced discrepancies previously hidden inside the combined-order test. This
found and fixed two separate converter bugs, plus a twiss-convention mismatch:

- **Fixed**: a `MULT` with only `SK0` set is auto-simplified
  (`SIMPLIFY_MULTIPOLES=True`, the default) into an `xt.Bend` with
  `rot_s_rad` rotated by 90 degrees — the rotation sign was wrong, giving
  `y`/`py` negated versus SAD. The true, unsimplified `Multipole` path
  (`ksl[0]`) was already correct.
- **Fixed**: a combined `K0`+`SK0` `MULT`, when the values arrive as
  symbolic/deferred expressions rather than plain floats, crashed with
  `Unknown function arctan2` — Xsuite's expression evaluator uses `atan2`,
  not `arctan2`.
- **Resolved**: `SK1` alone appeared to
  disagree with SAD by `~1.9e-5` on `betx`/`bety`/`alfx`/`alfy`. The 4×4
  transfer matrices agree to `~5e-11` and the residual was bit-identical
  across six different skew representations, so it was never a physics or
  rotation-convention bug: SAD reports coupled twiss in the Edwards-Teng
  convention, and comparing Edwards-Teng values (via
  `tests/support/coupled_optics.py`) agrees with SAD to `~1e-9`. The twiss
  comparisons in this file now use that convention; the earlier
  `ROTATE`/`xt.Rotation` hypothesis is dead (all rotated representations
  gave identical results).
- **Accepted limitation**: `K0`/`SK0` dipole-only `MULT` elements have a SAD
  fringe convention that Xsuite Bend/corrector elements do not reproduce
  exactly. SAD's default `MULT` dipole fringe contributes exactly
  `m43 = -K0²/L` (`m21` for `SK0`); Xsuite's bend edge models either add
  `theta^4`-order terms or give zero. SAD-side ground truth is pinned in
  `tests/sad/test_mult.py`, the converter warning is covered here, and
  `test_mult_k0_dipole_fringe_difference_is_theta_fourth_order` locks in the
  expected `theta^4` residual as a passing accepted-limitation test.

See `docs/sad-behaviour.md` for both the `K0`/`SK0` fringe formula and the
Edwards-Teng/Mais-Ripken twiss convention in full.

Separately: the combined `K0`+`SK0` `MULT` path (auto-simplification and user
`Bend` replacement) selected its numeric-vs-deferred-expression branch by
checking whether either value was a `float`, when it needed to check for
`str` instead. A `MULT` with both `K0` and `SK0` given as deferred SAD
expressions crashed with `TypeError` on `str ** int`; a `MULT` with numeric
`K0`/`SK0` but a deferred `ROTATE` crashed with `TypeError` on `str + float`.
While consolidating the fix, a second, pre-existing bug in the same branch
was also found: the only-`SK0` path built its deferred rotation as
`f"{rotation} - np.pi / 2"`, embedding the literal unresolved text `np.pi`
rather than its numeric value — Xsuite's expression evaluator has no `np` or
`pi` binding, so a `MULT` with only `SK0` set and a deferred `ROTATE` crashed
with `KeyError: 'np.pi'`. Fixed the same way as the existing correct
precedent at `_004_element_converter.py`'s cavity phi-offset handling
(`f"{np.pi} + {phi_offset}"`, embedding the resolved float). Both fixes live
in one extracted `combine_k0_sk0()` in `_000_helpers.py`, shared between both
call sites, with direct unit coverage (evaluated through a real Xsuite
environment, not just string comparison) in
`tests/conversion/test_converter_helpers.py` and integration coverage here
(`test_mult_converter_combines_deferred_k0_sk0`).

### `test_bend.py` note

The bend element-offset reference-orbit-convention limitation (`ANGLE != 0`
combined with a nonzero `DX`/`DY`) is resolved as a known-failing-test
pattern, the same way the solenoid `DISFRIN` and `MULT` `K0`/`SK0` fringe
limitations were: `..._for_element_offsets` and
`..._for_thin_bend_element_offsets` now cover only the parametrisations
that genuinely match SAD (offsets out of the bending plane); the
parametrisations that diverge are instead covered by three dedicated,
passing tests that lock in the expected, quantified residual:

- `test_bend_offset_orbit_residual_is_angle_squared_order` (thick bend)
- `test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order`
  (thin bend, `L=0`)
- `test_bend_offset_rotated_coupling_is_a_sad_side_artifact` (`ROTATE != 0`
  combined with an offset — a further, separate SAD-side coupling artifact
  on top of the same residual)

See `docs/sad-behaviour.md` for the full empirical characterisation (the
`ANGLE^2` orbit/dispersion residual, and the `ROTATE`-combined `R1`/`R4`
discontinuity) and `docs/design-decisions.md` for the resulting converter
decision.

The converter warns once per lattice when it finds an `ANGLE != 0` bend with
a nonzero `DX`/`DY` (`test_bend_converter_warns_once_for_lattice_with_offset_angled_bends`
and its two companion tests), covering both the thick and thin
representations. Correctors (`ANGLE == 0`) and MULT-derived dipoles never
carry a nonzero curvature and are confirmed unaffected.

## Shared Fixtures

`conftest.py` provides:
- `xsuite_environment` — a fresh `xt.Environment` for direct converter tests
- `parsed_elements` — helper for constructing minimal parsed element dictionaries
- `assert_environment_element` — assertion helper for environment element contents
