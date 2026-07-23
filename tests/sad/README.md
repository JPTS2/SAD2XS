# SAD Ground-Truth Tests

This folder contains empirical tests that verify what each SAD element type actually
accepts and how it actually behaves at runtime, against the real SAD binary. They serve
as the machine-verified specification that the SAD2XS converter mirrors — for both
syntax (which parameters SAD recognises) and physics (what those parameters do).

## Motivation

The converter must only parse parameters that SAD itself recognises for each element
type, and must encode physics that matches what SAD itself computes. Building converter
paths for parameters SAD silently discards — or assuming a physics behaviour without
checking it — would create unreachable code, untestable branches, or silent conversion
errors. These tests pin both boundaries so the converter stays honest.

The parameter-acceptance findings are consistent with confirmation from K. Oide (SAD
author, 2026-06-24):

> *"QUAD, SEXT, OCT, DECA only take their specific component K1, K2, K3, K4,
> respectively. Similarly, BEND takes ANGLE and K0. So anything beyond that must
> be declared as MULT, which is an almighty, even an acceleration can be included.
> These are mostly by a historical reason."*

## Test harness

Each test builds a minimal lattice file, then calls either `twiss_sad` or `track_sad`
from `sad2xs.sad_helpers`. The test `os.chdir`s to `tmp_path` and passes a relative
filename; SAD's shell wrapper requires a relative path in the working directory.

- **Accept/reject tests** call `twiss_sad` via the `sad_accepts`/`sad_rejects` fixtures
  (see `conftest.py`) with `closed=False, calc6d=False` — a 4D transfer-line Twiss. If
  SAD exits non-zero the parameter is **rejected**; if it exits zero it is **accepted**.
- **Tracking tests** call `track_sad` directly and must check `assert_particle_survived`
  (also in `conftest.py`) before trusting any returned coordinate — a lost particle's
  x/px/y/py/zeta/delta are SAD's internal lost-particle sentinel values, not physics.

## Coverage

309 tests across 16 files. All require the SAD binary.

### Parameter matrix (accept/reject)

Every element below has a complete matrix: every parameter in its relevant universe
(`ANGLE, K0-K4, SK0-SK4, DX, DY, ROTATE, HARM, FREQ, BZ`, plus element-specific extras)
is tested as either accepted or rejected — nothing is left untested either way.

| Element | Accepted | Rejected |
|---------|----------|---------|
| QUAD | K1, DX, DY, ROTATE, DISFRIN | ANGLE, K0, SK0, SK1, K2–K4, SK2–SK4, HARM, FREQ, BZ |
| SEXT | K2, DX, DY, ROTATE | ANGLE, K0, SK0, K1, SK1, SK2, K3–K4, SK3–SK4, HARM, FREQ, BZ |
| OCT | K3, DX, DY, ROTATE | ANGLE, K0, SK0, K1–K2, SK1–SK2, SK3, K4, SK4, HARM, FREQ, BZ |
| BEND | ANGLE, K0, K1, DX, DY, ROTATE, F1, FRINGE, FB1, FB2 | SK0, SK1, K2–K4, SK2–SK4, HARM, FREQ, BZ |
| MULT | ANGLE, K0–K4, SK0–SK4, DX, DY, ROTATE, HARM, FREQ, FRINGE, DISFRIN | BZ |
| CAVI | VOLT, FREQ, HARM, PHI, DX, DY, ROTATE | ANGLE, K0–K4, SK0–SK4, BZ |
| SOL | BZ, DX, DY, DISFRIN | ANGLE, K0–K4, SK0–SK4, HARM, FREQ, ROTATE |
| DRIFT | bare only (L) | ANGLE, K0–K4, SK0–SK4, BZ, HARM, FREQ, DX, DY, ROTATE |
| APERT | AX, AY, DX, DY, ROTATE, DX1/DX2, DY1/DY2 | ANGLE, K0–K4, SK0–SK4, BZ, HARM, FREQ |
| MARK | bare, BZ, DX, DY | ANGLE, K0–K4, SK0–SK4, ROTATE, FREQ, HARM |
| MONI | bare, DX, DY, ROTATE | K0–K4, SK0–SK4, BZ, ANGLE, FREQ, HARM |

### Effect on Twiss / effect on tracking

For every element with a defining strength parameter, physics coverage follows one
consistent pattern — a Twiss-side test and a tracking-side test, not whichever one
happened to work:

- **Linear elements (QUAD's K1, BEND's ANGLE/K1, MULT's K1)**: the parameter changes
  linear optics (Twiss betx) *and* gives a direct kick in tracking. Both are asserted.
- **Nonlinear elements (SEXT's K2, OCT's K3, MULT's K2/K3)**: the parameter has *no*
  effect on Twiss at zero orbit (asserted as a positive fact, not left as a gap — the
  reference particle stays at x=0, so the field's Jacobian there is the identity
  regardless of field strength), but gives a quadratic/cubic kick in tracking.
- **Pure orbit-kick elements (BEND's/MULT's K0)**: no *linear* effect on Twiss betx —
  though for BEND's K0 specifically, a small residual was found that scales as K0²
  (confirmed by checking the scaling, not assumed); tracking shows the direct kick.
  This is why BEND's K0 test asserts a scaling ratio rather than exact invariance.
- **MULT's K0/SK0 dipole fringe (transfer-matrix ground truth)**: a K0-only MULT's
  default linear map carries the fringe term m43 = −K0²/L *exactly*; SK0 mirrors it
  as m21. The element-level `FRINGE` switch controls the term: `FRINGE=1` removes the
  fringe block exactly (m43 → 0, m44 → 1), while explicit `FRINGE=0/2/3/-1` behave
  identically to an unset `FRINGE` and keep it. `DISFRIN` does *not* control this
  term (unlike SOL, where DISFRIN is the fringe switch). Verified against
  SAD 1.4.4.2k64 via `transfer_matrix_sad`, see the dipole-fringe section of
  `test_mult.py`. A K0-only MULT with a real nonzero `FB1`/`FB2` does **not**
  reproduce the same fringe formula as the equivalent K0-only BEND — confirmed
  directly (`test_mult_k0_fringe_with_nonzero_fb_does_not_match_equivalent_bend`);
  MULT's fringe treatment is out of scope for the BEND fringe import below.
- **BEND's F1/FRINGE soft-edge fringe (`test_bend.py`)**: a linear-plus-cubic-in-`y`
  kick at each edge, sized by `F1` (symmetric) or `FB1`/`FB2` (per-edge, additive
  on top of `F1`), gated by `FRINGE` (full grid: 0 or <= -3 = off at both edges,
  -1 = entrance-only, -2 = exit-only, any positive value = both) — confirmed
  inert without `FRINGE` (`test_bend_f1_is_inert_without_fringe`), active with
  it (`test_bend_fringe_1_activates_f1`), and the full gating grid confirmed
  against the real binary (`test_bend_fringe_mode_gates_entrance_exit`,
  `test_bend_corrector_fringe_mode_gates_entrance_exit`). Applies identically to
  the `ANGLE != 0` sector-bend path and the `ANGLE == 0`, K0-only corrector path
  (a BEND with no ANGLE) — both pinned against real SAD binary output
  (`test_bend_angle_nonzero_f1_fringe_matches_sad_reference_values`,
  `test_corrector_fringe_matches_sad_reference_values`). See
  `docs/sad-behaviour.md` for the closed-form mapping onto Xsuite's native edge
  model this enables.
- **QUAD's default hard-edge fringe (`test_quad.py`)**: SAD applies a default
  hard-edge quadrupole fringe kick, gated off by `DISFRIN=1` — the same
  convention used by SOL. The kick is nonlinear in the transverse offset, so
  it is invisible at the tiny (1E-4) amplitudes most QUAD tracking tests use;
  confirmed with a realistic centimeter/10s-of-mrad-scale offset
  (`test_quad_disfrin_changes_tracking_at_large_offset`). Xsuite's
  `Quadrupole` already supports the identical mechanism natively
  (`edge_entry_active`/`edge_exit_active`) — SAD2XS now enables it by default
  via `configure_quadrupole_model(edge='full')`, mirroring how bend edges are
  configured. See `docs/sad-behaviour.md` and
  `tests/conversion/elements/test_quad.py`.
- **CAVI's VOLT**: no orbit perturbation in CALC4D Twiss (a real SAD/COD limitation,
  not a bug); a real energy deviation (delta != 0) in tracking.
- **SOL's BZ**: nonzero Twiss coupling (R1/R4) that *persists* past the exit fringe —
  unlike a pure geometric GEO/DX frame shift, which is undone by the exit fringe (see
  `test_reference_particle.py` and `test_sol_reference_transform_restores_design_orbit_at_end`
  in `tests/conversion/elements/test_sol.py` for the geometric-shift case). Confirmed
  independently via both Twiss and tracking.
- **Passive/transparent elements (MARK, MONI, DRIFT's absence of field parameters,
  APERT away from its own boundary)**: no effect on Twiss *or* tracking, asserted
  explicitly rather than left implicit.

`test_reference_particle.py` documents its own history as a cautionary example: an
earlier version of that file's SOL/CAVI charge-sensitivity claims (based on tracking
only, under the belief that "Twiss always computes for CHARGE=+1") turned out to be
partly built on a lattice-string comma bug (see below) and partly on reading the wrong
observable row — re-verified this session, now correct.

### The lattice-string comma bug (resolved, watch for regressions)

SAD's LALR parser silently drops parameters after a comma inside an element
definition's parameter list (e.g. `APERT A1 = (AX=0.05, AY=0.03)` silently loses
`AY`), with **no non-zero exit code** — `sad_accepts`/`sad_rejects` cannot detect this,
since they only check the process exit code. All element-parameter lists in this
folder use space separation (`AX=0.05 AY=0.03`), never commas. **New tests must not
reintroduce commas inside an element's `(...)` parameter list.** Commas remain valid
Mathematica-list syntax elsewhere (e.g. `beam = {1, {xs, pxs, ...}}` in tracking driver
scripts) — the restriction is specifically about SAD element-definition parameter lists.

### SOL structural requirement

SOL is a zero-length fringe element. The physical length lives in a DRIFT between
an entrance SOL and an exit SOL. `BOUND=1` is required on the entrance and exit
elements; inner SOL elements (if any) do not require it. `GEO=1` marks the
field-centre element of each solenoid body.

Minimum valid pattern: `SOL(BZ, BOUND=1, GEO=1) + DRIFT + SOL(BZ=0, BOUND=1)`

`test_sol.py` probes single-element, pair-without-drift, pair-without-GEO, and
pair-without-BOUND configurations before running the parameter accept/reject tests.
It also verifies that an inner SOL without BOUND is valid in a three-element chain.

A degenerate SOL pair with BOUND on both elements but no GEO (`test_sol_pair_no_geo_rejects`)
is not rejected by SAD's exit code — SAD exits 0 but writes Mathematica undefined symbols
(e.g. `medium`, `$DefaultFontWeight`) into the TFS output, indicating the Twiss computation
failed silently. `twiss_sad` detects these symbols and raises `ValueError`, which `sad_rejects`
treats as a rejection.

### LINE definitions and reversal

`test_line.py` verifies SAD's LINE naming/parsing syntax:

| Test | Verifies |
|------|----------|
| `test_line_name_containing_line_substring_is_accepted` | Line names containing the substring `line` (e.g. `MYLINE`) are valid identifiers — SAD does not treat the substring as the keyword |
| `test_nested_line_reference_containing_line_substring_is_accepted` | Such names are also valid when referenced nested inside another LINE definition |
| `test_line_keyword_with_newline_before_name_is_accepted` | A newline between the `LINE` keyword and the line name/definition is accepted by SAD |

`test_line_reversal.py` is kept separate from `test_line.py` deliberately: it verifies
the semantic/physics behaviour of the `-LINE` reversal operator, not name parsing.
`tests/conversion/pipeline/test_reverse_*.py` already test the sad2xs converter's own
`_007_reversals.py` Python logic in detail, but those tests only check the converter is
internally self-consistent with its own assumptions — they never import
`twiss_sad`/`track_sad` and never compare against real SAD. `test_line_reversal.py`
closes that gap for the converter's most impactful sign-convention assumptions:

| Test | Confirms |
|------|----------|
| `test_reversed_line_bend_angle_sign_matches_converter_assumption` | Reversal negates BEND's ANGLE (sign/magnitude confirmed; small linear-in-angle residual found and tolerance-covered, see below) |
| `test_reversed_line_quad_k1_sign_matches_converter_assumption` | Reversal leaves QUAD's K1 unchanged (confirmed exactly) |
| `test_reversed_line_solenoid_ks_sign_matches_converter_assumption` | Reversal negates SOL's BZ and swaps which end carries GEO (confirmed exactly) |

### Angle unit suffixes

`test_angle_units.py` verifies SAD's accepted angle unit forms for both `ROTATE`
(QUAD) and `ANGLE` (BEND — a separate SAD keyword, verified independently rather
than assumed to follow from ROTATE):

| Test | Verifies |
|------|----------|
| `test_rotate_without_unit_suffix_is_accepted` | A plain numeric ROTATE value is accepted; the default unit is radians |
| `test_rotate_with_rad_suffix_is_accepted` | An explicit RAD suffix is accepted and treated identically to a bare value |
| `test_rotate_with_deg_suffix_is_accepted` | A DEG suffix is accepted; SAD converts the value to radians internally |
| `test_angle_without_unit_suffix_is_accepted` | Same, for BEND's ANGLE |
| `test_angle_with_rad_suffix_is_accepted` | Same, for BEND's ANGLE |
| `test_angle_with_deg_suffix_is_accepted` | Same, for BEND's ANGLE |
| `test_angle_deg_suffix_converts_to_the_same_radian_value` | ANGLE=90 DEG gives the same Twiss betx as ANGLE=pi/2 radians — the conversion factor itself is correct, not just the syntax |

## Known open questions from this testing pass

- **APERT: missing ellipse axis is not treated as infinite.** An `APERT` with only
  `AX` set (`AY` entirely omitted) rejects even a dead-centre particle, contradicting
  the documented "absent axis = infinite" rule. See
  `test_apert_missing_ellipse_axis_behavior`, and
  `dev/apert_mwe_missing_axis_infinite.sad` for a standalone SAD-only reproduction
  ready to send to the SAD author. Not yet resolved.
- **APERT: an earlier reading of the DX/rectangle formula was wrong, not SAD.** DX
  recentres *both* the elliptical and rectangular clauses (`min(DX1,DX2) < (x-DX) <
  max(DX1,DX2)`), not just the ellipse. Resolved — see
  `test_apert_offset_shifts_both_ellipse_and_rectangle` and
  `dev/apert_mwe_offset_shifts_rectangle.sad`.
- **BEND reversal: small linear-in-angle residual, cause not identified.** See
  `test_reversed_line_bend_angle_sign_matches_converter_assumption`'s docstring —
  confirmed not to be a sign error or numerical noise (scales cleanly as
  ~4.2e-7 rad⁻¹ across three angle values), but the root cause (likely something in
  SAD's bend edge/reference-trajectory model) was not investigated further.
- **CAVI: PHI=0 did not give the expected on-crest energy gain.** Noted in
  `test_cavi_volt_gives_nonzero_energy_deviation_in_tracking`'s docstring; the tests
  use the known-working PHI=pi/4 setup from `test_reference_particle.py` instead.
  Not investigated further.
- **The LimitRectEllipse converter/Xsuite question is separate** from all of the
  above and is blocked on an upstream Xsuite discussion (whether `xt.LimitRectEllipse`
  can be extended to support `min_x`/`min_y`), not on SAD-side testing — see
  `dev/codebase_review_2026-07-01.md`.

## Elements not tested and why

**BEAMBEAM** — Beam–beam elements are not currently converted by SAD2XS. Testing
their SAD parameter acceptance is premature and out of scope.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
