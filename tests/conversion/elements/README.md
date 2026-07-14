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

See `docs/testing.md`'s Known Failures section for the `known_issue` marker
mechanism.

SAD-comparison tracking and Twiss checks uniformly use `rfsw=True` and compare
`zeta`/`delta` alongside the transverse coordinates, matching `test_cavi.py`'s
original pattern. Files with only a raw `s`/length check via `line.get_table()`
(`test_apert.py`, `test_beambeam.py`, `test_mark.py`, `test_moni.py`) are the
exception — they have no twiss/tracking comparison to extend.

| File | Functions | Fail | Failure root cause |
|------|-----------|------|--------------------|
| `test_apert.py` | 24 | 0 | — |
| `test_beambeam.py` | 5 | 0 | — |
| `test_bend.py` | 41 | 0 | — |
| `test_cavi.py` | 10 | 0 | — |
| `test_coord.py` | 10 | 0 | — |
| `test_corrector.py` | 23 | 0 | — |
| `test_drift.py` | 7 | 0 | — |
| `test_mark.py` | 5 | 0 | — |
| `test_moni.py` | 5 | 0 | — |
| `test_mult.py` | 26 | 0 | — |
| `test_oct.py` | 18 | 0 | — |
| `test_quad.py` | 20 | 0 | — |
| `test_sext.py` | 18 | 0 | — |
| `test_sol.py` | 26 | 0 | — |

### `test_sol.py` note

The former solenoid optics known failure is resolved: it was a twiss-
parametrisation mismatch (SAD reports Edwards-Teng, Xsuite's plain twiss
reports Mais-Ripken mode projections), not a GEO-exit-transform bug —
`_sol_xsuite_optics_values()` now computes Edwards-Teng values via
`tests/support/coupled_optics.py`, locked in by
`tests/conversion/test_coupled_twiss_convention.py`. See
`docs/sad-behaviour.md` for the full convention explanation and
`docs/sad-helpers.md` for the worked usage example.

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
failing test: it asserts the genuine, accepted divergence from not
modelling SAD's solenoid fringe kick (see `docs/sad-behaviour.md` for what
it is, `docs/design-decisions.md` for the converter decision). Deliberately
not in `known_issues.py`.

### `test_corrector.py` note

Previously had 14 failing instances (horizontal kicks, rotated kicks, and
element offsets, optics and tracking) from a `MODEL_BEND = 'mat-kick-mat'`
bias — SAD zero-angle correctors convert to a plain `xt.Bend` with
`angle=0`, so this affected them too. Fixed by retuning `sad2xs/config.py`'s
Bend/Quadrupole/Sextupole/Octupole/Multipole model/integrator settings to
match a systematic SAD-cross-validated study (`bend-kick-bend` for
Bend/Corrector, `rot-kick-rot-high-order`/`yoshida4` for
Quad/Sext/Oct/Mult). All 20 functions in this file now pass.

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
- **Resolved**: `SK1` alone appeared to disagree with SAD by `~1.9e-5` on
  `betx`/`bety`/`alfx`/`alfy` — not a physics or rotation-convention bug
  (4×4 transfer matrices agreed to `~5e-11`), but the Edwards-Teng-vs-
  Mais-Ripken twiss-parametrisation mismatch (see `docs/sad-behaviour.md`).
  The twiss comparisons in this file now use `tests/support/coupled_optics.py`;
  the earlier `ROTATE`/`xt.Rotation` hypothesis is dead.
- **Accepted limitation**: `K0`/`SK0` dipole-only `MULT` elements have a SAD
  fringe convention Xsuite's Bend/corrector edge models don't reproduce
  exactly (see `docs/sad-behaviour.md` for the formula). SAD-side ground
  truth is pinned in `tests/sad/test_mult.py`, the converter warning is
  covered here, and `test_mult_k0_dipole_fringe_difference_is_theta_fourth_order`
  locks in the expected `theta^4` residual as a passing accepted-limitation
  test.

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
limitations were: the `..._for_element_offsets`, `..._for_thin_bend_element_offsets`,
and `..._for_rotated_element_offsets` twiss/tracking tests each cover only
the parametrisations that genuinely match SAD; the parametrisations that
diverge (including the combined `DX`+`DY` case) are covered instead by
dedicated, passing tests that lock in the expected, quantified or bounded
residual:

- `test_bend_offset_orbit_residual_is_angle_squared_order` (thick bend,
  twiss) and `test_bend_offset_orbit_residual_diverges_in_tracking` (its
  tracking-mode counterpart)
- `test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order`
  (thin bend, `L=0`, twiss) and
  `test_bend_offset_thin_bend_dispersion_residual_diverges_in_tracking`
  (tracking)
- `test_bend_conversion_matches_sad_twiss_for_rotated_element_offsets`
  and `test_bend_offset_rotated_coupling_is_a_sad_side_artifact`
  (`ROTATE != 0` combined with an offset — a further, separate SAD-side
  coupling artifact on top of the same residual, confirmed to affect
  `betx`/`bety`/`alfx`/`alfy` regardless of which axis carries the offset)

See `docs/sad-behaviour.md` for the full empirical characterisation (the
`ANGLE^2` orbit/dispersion residual and its full column map, and the
`ROTATE`-combined `R1`/`R4` discontinuity) and `docs/design-decisions.md`
for the resulting converter decision.

### `test_bend.py`/`test_corrector.py` fringe import note

`_import_sad_bend_fringes` (private, default `False`) reproduces SAD's
`FRINGE`/`F1`/`FB1`/`FB2` soft-edge fringe via Xsuite's native
`fint`/`hgap`. Both files follow the same three-test pattern: a
`..._defaults_off` test locking in that the flag has no effect unless
explicitly enabled; a `..._matches_sad_on_momentum` test asserting a
tight match at `delta=0`; and a `..._off_momentum_residual_is_bounded`
test asserting the known, currently-characterised residual explicitly
rather than skipping it — a future upstream Xsuite/MAD-NG momentum-scaling
fix should make this test fail (residual outside the asserted band) and
surface for review, not silently pass. See `docs/sad-behaviour.md`
("`BEND` `F1`/`FRINGE` soft-edge fringe") for the derivation and
`docs/design-decisions.md` ("`BEND` `F1`/`FRINGE` fringe import is
private and on-momentum only") for why the flag is private and
default-off.

The converter warns once per lattice when it finds an `ANGLE != 0` bend with
a nonzero `DX`/`DY` (`test_bend_converter_warns_once_for_lattice_with_offset_angled_bends`
and its two companion tests), covering both the thick and thin
representations. Correctors (`ANGLE == 0`) and MULT-derived dipoles never
carry a nonzero curvature and are confirmed unaffected.

### `test_quad.py` default edge fringe note

SAD applies a default hard-edge quadrupole fringe kick (gated by `DISFRIN`,
verified against real SAD in `tests/sad/test_quad.py`). Xsuite's
`Quadrupole` supports the identical mechanism natively via
`edge_entry_active`/`edge_exit_active`, so — unlike the private, opt-in
`_import_sad_bend_fringes` bend flag — SAD2XS enables it by **default** via
`configure_quadrupole_model(edge='full')` (`config.py`'s `EDGE_MODEL_QUAD`,
applied in `main.py` and the writer's `_014_model.py` alongside
`configure_bend_model`). `test_quad_conversion_default_enables_edge_fringe`
locks in the default; `test_quad_conversion_matches_sad_tracking_for_large_transverse_offsets`
confirms it materially improves agreement with SAD at realistic
(centimeter-scale) orbit amplitudes — the kick is nonlinear in the offset,
so it is invisible at the tiny amplitudes most other QUAD tracking tests
use. A small residual remains even with the fringe enabled, consistent with
a genuine small formula-level difference between SAD's and Xsuite's
quadrupole fringe implementations rather than a further converter bug; the
test asserts a bounded tolerance, not exact agreement.

## Shared Fixtures

`conftest.py` provides:
- `xsuite_environment` — a fresh `xt.Environment` for direct converter tests
- `parsed_elements` — helper for constructing minimal parsed element dictionaries
- `assert_environment_element` — assertion helper for environment element contents
