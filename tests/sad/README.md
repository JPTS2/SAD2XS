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

The parameter-acceptance findings are consistent with direct confirmation from the
SAD author:

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

472 tests across 16 files. All require the SAD binary.

| File | Tests | Fail | Element or behaviour covered |
|------|-------|------|------------------------------|
| `test_quad.py` | 44 | 0 | QUAD parameters, soft-edge and hard-edge fringe |
| `test_sext.py` | 33 | 0 | SEXT parameters and hard-edge fringe |
| `test_oct.py` | 33 | 0 | OCT parameters and hard-edge fringe |
| `test_bend.py` | 43 | 0 | BEND parameters, soft-edge and hard-edge fringe |
| `test_mult.py` | 58 | 0 | MULT parameters, every fringe sub-mechanism, RF content |
| `test_cavi.py` | 39 | 0 | CAVI parameters, RF focusing, edge-focusing kick |
| `test_sol.py` | 38 | 0 | SOL parameters and the solenoid fringe kick |
| `test_drift.py` | 29 | 0 | DRIFT accepts length only |
| `test_apert.py` | 39 | 0 | APERT bounds, offsets, and rotation |
| `test_mark.py` | 30 | 0 | MARK parameters |
| `test_moni.py` | 30 | 0 | MONI parameters |
| `test_line.py` | 3 | 0 | LINE definition syntax |
| `test_line_reversal.py` | 5 | 0 | native `-LINE` reversal sign conventions |
| `test_reference_particle.py` | 15 | 0 | MOMENTUM, MASS, and CHARGE handling |
| `test_angle_units.py` | 7 | 0 | ROTATE and ANGLE unit suffixes |
| `test_parser_behaviors.py` | 29 | 0 | SAD parser quirks, including the comma bug |

### Parameter matrix (accept/reject)

Every element below has a complete matrix: every parameter in its relevant universe
(`ANGLE, K0-K4, SK0-SK4, DX, DY, ROTATE, HARM, FREQ, BZ, FRINGE, DISFRIN, F1, F2,
FB1, FB2, F1K1F, F2K1F, F1K1B, F2K1B`, plus element-specific extras)
is tested as either accepted or rejected — nothing is left untested either way.

| Element | Accepted | Rejected |
|---------|----------|---------|
| QUAD | K1, DX, DY, ROTATE, F1, F2, FRINGE, F1K1F, F2K1F, F1K1B, F2K1B, DISFRIN | ANGLE, K0, SK0, SK1, K2–K4, SK2–SK4, HARM, FREQ, BZ, FB1, FB2 |
| SEXT | K2, DX, DY, ROTATE, DISFRIN | ANGLE, K0, SK0, K1, SK1, SK2, K3–K4, SK3–SK4, HARM, FREQ, BZ, F1, F2, FRINGE, FB1, FB2, F1K1F, F2K1F, F1K1B, F2K1B |
| OCT | K3, DX, DY, ROTATE, DISFRIN | ANGLE, K0, SK0, K1–K2, SK1–SK2, SK3, K4, SK4, HARM, FREQ, BZ, F1, F2, FRINGE, FB1, FB2, F1K1F, F2K1F, F1K1B, F2K1B |
| BEND | ANGLE, K0, K1, DX, DY, ROTATE, F1, FRINGE, FB1, FB2, DISFRIN | SK0, SK1, K2–K4, SK2–SK4, HARM, FREQ, BZ, F2, F1K1F, F2K1F, F1K1B, F2K1B |
| MULT | ANGLE, K0–K4, SK0–SK4, DX, DY, ROTATE, HARM, FREQ, FRINGE, DISFRIN, F1, F2, FB1, FB2, F1K1F, F2K1F, F1K1B, F2K1B | BZ |
| CAVI | VOLT, FREQ, HARM, PHI, DX, DY, ROTATE, FRINGE, DISFRIN, V1, V20, V11, V02 | ANGLE, K0–K4, SK0–SK4, BZ, F1, F2, FB1, FB2, F1K1F, F2K1F, F1K1B, F2K1B |
| SOL | BZ, DX, DY, DISFRIN, F1 | ANGLE, K0–K4, SK0–SK4, HARM, FREQ, ROTATE, F2, FRINGE, FB1, FB2, F1K1F, F2K1F, F1K1B, F2K1B |
| DRIFT | bare only (L) | ANGLE, K0–K4, SK0–SK4, BZ, HARM, FREQ, DX, DY, ROTATE, FRINGE, DISFRIN, F1, F2, FB1, FB2, F1K1F, F2K1F, F1K1B, F2K1B |
| APERT | AX, AY, DX, DY, ROTATE, DX1/DX2, DY1/DY2 | ANGLE, K0–K4, SK0–SK4, BZ, HARM, FREQ, FRINGE, DISFRIN, F1, F2, FB1, FB2, F1K1F, F2K1F, F1K1B, F2K1B |
| MARK | bare, BZ, DX, DY | ANGLE, K0–K4, SK0–SK4, ROTATE, FREQ, HARM, FRINGE, DISFRIN, F1, F2, FB1, FB2, F1K1F, F2K1F, F1K1B, F2K1B |
| MONI | bare, DX, DY, ROTATE | K0–K4, SK0–SK4, BZ, ANGLE, FREQ, HARM, FRINGE, DISFRIN, F1, F2, FB1, FB2, F1K1F, F2K1F, F1K1B, F2K1B |

### Effect on Twiss / effect on tracking

Every element with a defining strength parameter gets both a Twiss-side test and a
tracking-side test, rather than whichever one happened to work.

- **Linear elements**, meaning QUAD's K1, BEND's ANGLE and K1, and MULT's K1. The
  parameter changes the linear optics, seen in Twiss `betx`, and gives a direct kick
  in tracking. Both are asserted.
- **Nonlinear elements**, meaning SEXT's K2, OCT's K3, and MULT's K2 and K3. The
  parameter has *no* effect on Twiss at zero orbit, and that is asserted as a positive
  fact rather than left as a gap. The reference particle stays at x=0, where the
  field's Jacobian is the identity whatever the field strength. Tracking shows the
  quadratic or cubic kick.
- **Pure orbit-kick elements**, meaning BEND's and MULT's K0. There is no *linear*
  effect on Twiss `betx`, and tracking shows the direct kick.

  BEND's K0 carries a small residual that scales as K0². This was confirmed by
  checking the scaling, not assumed, which is why BEND's K0 test asserts a scaling
  ratio rather than exact invariance.
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
- **MULT's F1/F2 quad-style soft-edge fringe** (`test_mult.py`). A MULT carrying
  `K1` applies the identical linear fringe that QUAD does, through `F1`/`F2` and
  the per-side `F1K1F`/`F2K1F`/`F1K1B`/`F2K1B`. It gives bit-identical pinned
  values to the equivalent QUAD, because a `K1`-only MULT with no other order
  content is physically a QUAD
  (`test_mult_k1_f1_f2_matches_sad_reference_values`).

  `FRINGE` gates it using QUAD's `{1,2,3}` numbering: 0 for neither edge, 1 for
  entrance, 2 for exit, 3 for both. Confirmed against the real binary
  (`test_mult_k1_fringe_mode_gates_entrance_exit`), including the same
  reversed-`-LINE` mode permutation as QUAD
  (`test_mult_reversed_line_fringe_mode_permutes`).
- **MULT's FB1/FB2 dipole-style soft-edge fringe** (`test_mult.py`). A MULT
  carrying `ANGLE` or `K0` also has BEND-style `FB1`/`FB2` fringe. It is gated by
  the **same `{1,2,3}` numbering as the `K1` fringe above, not by BEND's own
  sign-based scheme**. Confirmed against the real binary with asymmetric
  `FB1 != FB2` (`test_mult_fb1_fb2_fringe_mode_gates_entrance_exit`) and pinned
  (`test_mult_fb1_fb2_matches_sad_reference_values`).

  This explains the real difference at `FRINGE=1` found by
  `test_mult_k0_fringe_with_nonzero_fb_does_not_match_equivalent_bend` above.
  BEND reads `FRINGE=1` as a positive value, meaning both edges active. MULT
  reads it as entrance-only.
- **MULT's default hard-edge fringe, and its interaction with FRINGE
  (`test_mult.py`)**: the same generic hard-edge kick BEND/QUAD/SEXT/OCT
  use, gated by `DISFRIN` (default `0`/enabled, strictly boolean, pinned
  against real SAD binary output identical to the equivalent QUAD) —
  `test_mult_disfrin_default_matches_explicit_zero`/
  `test_mult_disfrin_is_boolean`/
  `test_mult_disfrin_hard_edge_matches_sad_reference_values`. Like QUAD,
  `FRINGE` additionally gates *which side* of this hard-edge kick applies,
  independent of `DISFRIN`
  (`test_mult_fringe_mode_also_gates_hard_edge_fringe_sides`) — but
  **unlike QUAD, MULT has no `FRINGE<=-4` master-disable**: confirmed
  empirically that `FRINGE=-4` leaves both hard-edge sides fully active on
  a MULT, where the identical value disables both on a QUAD (`tmulti.f`'s
  hard-edge gate has no lower-bound check; `tquad.f`'s does).
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
  `docs/reference/sad-behaviour.md` for the closed-form mapping onto Xsuite's native edge
  model this enables.
- **BEND's default hard-edge fringe (`test_bend.py`)**: a separate,
  `K1`-dependent nonlinear kick, gated by `DISFRIN` — unrelated to `FRINGE`
  above (each controls its own term, unlike on QUAD below). Unset defaults
  to `DISFRIN=0` (fringe enabled), bit-identically
  (`test_bend_disfrin_default_matches_explicit_zero`); strictly boolean, any
  nonzero value disables it identically
  (`test_bend_disfrin_is_boolean`); pinned against real SAD binary output
  (`test_bend_disfrin_hard_edge_matches_sad_reference_values`). On the
  `ANGLE == 0` K0-only corrector path the question does not arise. SAD does
  not allow a corrector to carry a nonzero K1 alongside K0 at all, which is a
  separate, confirmed SAD bug (see `docs/reference/sad-behaviour.md`). A real
  corrector therefore has no quadrupole content for DISFRIN to gate
  (`test_corrector_disfrin_has_no_effect_without_k1`).
- **QUAD's F1/F2/FRINGE soft-edge fringe (`test_quad.py`)**: a genuinely
  linear kick at each edge, sized by `F1`/`F2` (symmetric) or
  `F1K1F`/`F2K1F`/`F1K1B`/`F2K1B` (per-edge), gated by `FRINGE` — confirmed
  inert without `FRINGE` (`test_quad_f1_f2_is_inert_without_fringe`), active
  with it (`test_quad_fringe_3_activates_f1_f2`). QUAD's `FRINGE` (internal
  `mfring`) is a **different numbering system from BEND's** `FRMD_BEND`: a
  strict membership test on `{1,2,3}` (1=entrance-only, 2=exit-only,
  3=both), not sign-graded — values outside that set, including positive
  ones like `4`, leave the linear fringe off entirely, unlike BEND's "any
  positive enables both" rule — confirmed against the full grid
  (`test_quad_fringe_mode_gates_entrance_exit`). Reversing a line permutes
  *which side* gets the kick, not just which raw parameter feeds which side
  (`FRINGE` 1↔2, confirmed exactly against real SAD's own `-LINE` output,
  `test_quad_reversed_line_fringe_mode_permutes`). Pinned against real SAD
  binary output for K1>0, K1<0, and skewed (`ROTATE!=0`) cases
  (`test_quad_f1_f2_matches_sad_reference_values` and variants).
- **QUAD's `FRINGE` also gates the hard-edge (`DISFRIN`) fringe, per side**
  — a real cross-parameter interaction confirmed directly against the
  binary (`test_quad_fringe_mode_also_gates_hard_edge_fringe_sides`):
  `FRINGE=1` additionally disables the *exit*-side hard-edge kick,
  `FRINGE=2` the *entrance*-side, independent of `DISFRIN` itself;
  `FRINGE<=-4` disables the hard-edge on both sides unconditionally,
  bit-identical to `DISFRIN=1`. `FRINGE=0`/unset and `FRINGE=3` leave both
  hard-edge sides exactly as `DISFRIN` alone would set them.
- **QUAD's default hard-edge fringe (`test_quad.py`)**: SAD applies a default
  hard-edge quadrupole fringe kick, gated by `DISFRIN` — the same convention
  used by BEND and SOL: unset defaults to `DISFRIN=0` (fringe enabled),
  bit-identically (`test_quad_disfrin_default_matches_explicit_zero`);
  strictly boolean, any nonzero value disables it identically
  (`test_quad_disfrin_is_boolean`). The kick is nonlinear in the transverse
  offset, so it is invisible at the tiny (1E-4) amplitudes most QUAD
  tracking tests use; pinned against real SAD binary output at a realistic
  centimeter/10s-of-mrad-scale offset, with both sides active (`FRINGE`
  unset — see above for what changes once `FRINGE` is set)
  (`test_quad_disfrin_hard_edge_matches_sad_reference_values`). Xsuite's
  `Quadrupole` already supports the identical mechanism natively
  (`edge_entry_active`/`edge_exit_active`) — SAD2XS now enables it by default
  via `configure_quadrupole_model(edge='full')`, mirroring how bend edges are
  configured, though it does not yet read each QUAD's own `DISFRIN` value
  individually (open converter-side gap, out of scope for this ground-truth
  pass). See `docs/reference/sad-behaviour.md` and `tests/conversion/elements/test_quad.py`.
- **SEXT/OCT reject FRINGE entirely (`test_sext.py`/`test_oct.py`)**: unlike
  BEND/QUAD/MULT, SEXT and OCT have no `FRMD`/soft-edge-fringe keyword at
  all — `FRINGE`, `F1`, `F2`, `FB1`, `FB2`, `F1K1F`, `F2K1F`, `F1K1B`,
  `F2K1B` are all rejected outright by the parser, confirmed empirically
  (`REJECTED_PARAMS`), not assumed from the absence of a converter path.
  They do accept `DISFRIN`, gating the same generic hard-edge fringe
  mechanism BEND/QUAD use, applied identically at both entrance and exit
  with no per-side control (there is no `FRINGE` mode to select a single
  side): default `DISFRIN=0` (enabled), bit-identical to unset
  (`test_sext_disfrin_default_matches_explicit_zero`/
  `test_oct_disfrin_default_matches_explicit_zero`); strictly boolean
  (`test_sext_disfrin_is_boolean`/`test_oct_disfrin_is_boolean`); pinned
  against real SAD binary output
  (`test_sext_disfrin_hard_edge_matches_sad_reference_values`/
  `test_oct_disfrin_hard_edge_matches_sad_reference_values`).
- **CAVI's VOLT**: no orbit perturbation in CALC4D Twiss (a real SAD/COD limitation,
  not a bug); a real energy deviation (delta != 0) in tracking.
- **CAVI's FRINGE/DISFRIN RF edge-focusing kick (`test_cavi.py`)**: a
  `VOLT != 0` CAVI applies a genuine edge-focusing kick (linear in x/y),
  distinct from the RF-focusing "vcorr" body term (see "RF focusing"
  below) — CAVI rejects the QUAD/BEND/MULT-style `F1`/`F2`/`FB1`/`FB2`/
  `F1K1x` parameters entirely (`REJECTED_PARAMS`), and accepts its own
  `V1`/`V20`/`V11`/`V02` transverse RF-multipole coefficients instead
  (syntax only — their physics is out of scope for this pass). `DISFRIN`
  gates the edge kick: default `0` (enabled), strictly boolean, pinned
  (`test_cavi_disfrin_default_matches_explicit_zero`/
  `test_cavi_disfrin_is_boolean`/
  `test_cavi_fringe_disfrin_matches_sad_reference_values`). **CAVI's
  `FRINGE` is a THIRD distinct numbering system**, different again from
  BEND's, QUAD's/MULT's `{1,2,3}` scheme, and SEXT/OCT/SOL's "no `FRINGE`
  at all": `0`/unset (or any value other than exactly `1`/`2`) enables
  both edges, `1`=entrance-only, `2`=exit-only, and any **negative**
  value disables the kick entirely (matching `DISFRIN=1`), confirmed
  against the real binary (`test_cavi_fringe_mode_gates_entrance_exit`).
- **SOL's BZ**: nonzero Twiss coupling (R1/R4) that *persists* past the exit fringe —
  unlike a pure geometric GEO/DX frame shift, which is undone by the exit fringe (see
  `test_reference_particle.py` and `test_sol_reference_transform_restores_design_orbit_at_end`
  in `tests/conversion/elements/test_sol.py` for the geometric-shift case). Confirmed
  independently via both Twiss and tracking.
- **SOL rejects FRINGE entirely, but accepts F1 as a no-op for optics
  (`test_sol.py`)**: like SEXT/OCT, SOL has no `FRMD`/soft-edge-fringe
  keyword — `FRINGE`, `F2`, `FB1`, `FB2`, `F1K1F`, `F2K1F`, `F1K1B`,
  `F2K1B` are all rejected outright, confirmed empirically
  (`REJECTED_PARAMS`). Unlike those elements, SOL *does* accept `F1`, but
  `F1` does not affect tracking or optics. SAD's own documentation
  states that `F1` affects only the emittance and radiation calculation, not
  the orbital kick (see `docs/reference/sad-behaviour.md`, "Solenoid fringe kick"). The
  real orbital hard-edge fringe is gated by `DISFRIN` alone: default `0`
  (enabled), strictly boolean, pinned against real SAD binary output
  (`test_sol_disfrin_default_matches_explicit_zero`/
  `test_sol_disfrin_is_boolean`/
  `test_sol_disfrin_hard_edge_matches_sad_reference_values`) — the same
  convention as BEND/QUAD/SEXT/OCT/MULT, applied to SOL's own distinct,
  nonlinear ("octupolar") Hamiltonian term rather than the generic
  `ttfrin` mechanism those elements share.
- **Passive/transparent elements (MARK, MONI, DRIFT's absence of field parameters,
  APERT away from its own boundary)**: no effect on Twiss *or* tracking, asserted
  explicitly rather than left implicit. All four also reject `FRINGE`/`DISFRIN`
  and every soft-edge fringe sub-parameter outright (`REJECTED_PARAMS` in each
  file), confirmed empirically — completing the FRINGE/DISFRIN matrix
  uniformly across every element type in this suite, not just the
  field-carrying ones above.

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
  `test_apert_missing_ellipse_axis_behavior`. A standalone SAD-only reproduction
  exists for the SAD side. Not yet resolved.
- **APERT: an earlier reading of the DX/rectangle formula was wrong, not SAD.** DX
  recentres *both* the elliptical and rectangular clauses (`min(DX1,DX2) < (x-DX) <
  max(DX1,DX2)`), not just the ellipse. Resolved: see
  `test_apert_offset_shifts_both_ellipse_and_rectangle`.
- **BEND reversal: small linear-in-angle residual, cause not identified.** See
  `test_reversed_line_bend_angle_sign_matches_converter_assumption`'s docstring —
  confirmed not to be a sign error or numerical noise (scales cleanly as
  ~4.2e-7 rad⁻¹ across three angle values), but the root cause (likely something in
  SAD's bend edge/reference-trajectory model) was not investigated further.
- **CAVI: PHI=0 did not give the expected on-crest energy gain.** Noted in
  `test_cavi_volt_gives_nonzero_energy_deviation_in_tracking`'s docstring; the tests
  use the known-working PHI=pi/4 setup from `test_reference_particle.py` instead.
  Not investigated further.
- **The LimitRectEllipse question is separate** from everything above. It is
  blocked on an upstream Xsuite discussion, over whether `xt.LimitRectEllipse` can
  be extended to support `min_x` and `min_y`. It is not blocked on SAD-side
  testing.

## Elements not tested and why

**BEAMBEAM** — Beam–beam elements are not currently converted by SAD2XS. Testing
their SAD parameter acceptance is premature and out of scope.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
