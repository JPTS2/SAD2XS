# Design decisions

This file is a lightweight decision log. It records project-level choices that should guide future changes.

## Xsuite is the canonical intermediate model

Decision: after SAD input is parsed and converted, Xsuite objects are the source of truth.

Reasoning: SAD input may not represent the final converted model after reversals, substitutions, offsets, apertures, solenoid handling, or user rematching. Writing outputs from the Xsuite model keeps the writer aligned with what the converter actually built.

Consequence: new converter features should assert on the Xsuite model where possible. Writer changes should avoid depending on raw SAD text unless there is a documented reason.

## Public tests must be shareable

Decision: public tests must use synthetic or publicly shareable inputs.

Reasoning: the repository and CI should be usable by contributors who do not have access to private lattices.

Consequence: private validation can still be used locally, but public bugs should be reduced to small synthetic reproductions before tests or issues are added.

## SAD helpers are optional

Decision: external SAD helper functionality should remain optional for the core converter.

Reasoning: helper functions are useful for validation and comparison, but they depend on an external SAD installation. Users should be able to import and use the converter without setting up every helper dependency.

Consequence: helper imports should not make core conversion imports fail. The public test suite itself is SAD-capable and requires SAD, but package import-boundary tests should still protect core imports from unnecessary helper coupling.

Current status: this is not fully implemented. The top-level package still re-exports `sad_helpers`, so import-time coupling should be reduced in a future packaging change.

## Keep SAD2XS as one package for now

Decision: do not split the project into separate SAD helper and SAD-to-Xsuite packages during the current release cycle.

Reasoning: the current priority is converter correctness, public tests, and writer clarity. A package split would add release and dependency complexity before the internal boundaries are stable.

Consequence: keep boundaries clear inside the current package. If the SAD helper layer becomes independently useful and testable, a future package split can be reconsidered.

## Writer should become reusable

Decision: the long-term writer direction is a reusable Xsuite serializer.

Reasoning: users may want to convert a SAD lattice, rematch or modify it in Xsuite, then regenerate readable lattice and optics files. That workflow should not require the original SAD input to remain the authoritative source.

Consequence: writer APIs should move toward accepting complete Xsuite lines or environments. The current writer already accepts an `xt.Line` for lattice output, but it still carries SAD2XS-specific assumptions that need to be documented and reduced.

## Configuration must not change semantics accidentally

Decision: diagnostic options such as verbosity should affect logging only, unless a setting is explicitly documented as changing conversion behaviour.

Reasoning: users need repeatable conversion results. A flag intended for observability should not silently enable or disable conversion steps.

Consequence: behaviour-affecting settings must be documented and tested. Logging settings should be tested to ensure they do not alter the converted Xsuite model.

## Parser hardening is staged, not a full grammar rewrite

Decision: `_001_parser.py` keeps its ad-hoc string-splitting approach for now. Parser errors cite the source line number (`"line N: ..."`) via line-tracked sections, and SAD's `:=` function-definition syntax is rejected with a clear error instead of being silently misparsed into a garbage deferred-expression key. A token-level/grammar-based rewrite is deliberately deferred to a future release.

Reasoning: `parsed_lattice_data` (the parser's `globals`/`elements`/`lines`/`expressions` output) is consumed by seven downstream converter files, so a grammar rewrite's risk is spread far wider than its benefit. The current ad-hoc parser also encodes a number of empirically-discovered SAD quirks (e.g. SAD's own parser silently drops comma-separated trailing parameters in element bodies — matched on purpose, not a bug to fix) that a from-scratch grammar risks re-deriving one at a time. The existing parser is not rated defective: 99% of parser tests pass, and an independent codebase review called the ad-hoc string handling "stylistic, not risky." Line numbers and explicit-rejection errors deliver most of the remaining hardening value without that risk.

Consequence: SAD user-defined functions (`f[x_] := expr`) are explicitly out of scope for now rather than silently half-supported — closer to how Xtrack deliberately does not parse MAD-X files containing expressions. When a full grammar-based parser is eventually built, build its parse tree in parallel with the current parser first and validate its output matches `parsed_lattice_data`'s shape byte-for-byte against the full `tests/sad/` ground-truth corpus before any cutover.

## Solenoid fringe kick (DISFRIN) is not modelled

Decision: SAD2XS does not implement SAD's nonlinear solenoid fringe kick (controlled by SAD's `DISFRIN` parameter — default `0` applies the kick, `1` disables it). Every converted solenoid behaves as if `DISFRIN=1` were set, regardless of the source SAD file.

Reasoning: neither `xt.UniformSolenoid` nor `xt.VariableSolenoid` implements this term — see `docs/sad-behaviour.md` for what the fringe kick actually is and how that was confirmed. This was discussed with the Xsuite lead developer — there are no current plans to adopt a bolted-on, SAD-specific Hamiltonian term for this; the recommended direction for accurate modelling of complex/overlapped solenoid fields is field maps with a spline Boris integrator.

Consequence: the converter warns once per lattice (not once per element) when it finds one or more SAD `SOL` elements without `DISFRIN=1`, so users know their solenoid's fringe-kick physics is not being reproduced. Test comparisons involving solenoid physics should set `DISFRIN=1` on the SAD side to get a fair, apples-to-apples comparison; a dedicated test (`test_sol_disfrin_off_diverges_from_xsuite_in_tracking`) locks in the expected divergence without it as a permanent, accepted limitation rather than an open bug — it must not be added to `tests/support/known_issues.py`. A related consequence: spin-tracking studies through solenoid lattices are not well supported by this converter either, since spin precession is highly sensitive to exactly this kind of fine field detail at the fringe.

## Bend/Quadrupole/Sextupole/Octupole/Multipole model and integrator retune

Decision: `sad2xs/config.py`'s default `model`/`integrator`/`num_multipole_kicks` per element type changed from `mat-kick-mat`/`uniform`/`20` (Bend/Quad/Sext/Oct) and no explicit setting at all (Multipole) to: `bend-kick-bend`/`uniform`/`10` for Bend (and, since a zero-angle SAD corrector converts to a plain `xt.Bend`, Correctors too); `rot-kick-rot-high-order`/`yoshida4`/`14` for Quadrupole, Sextupole, Octupole, and the newly-added `MODEL_MULT`/`INTEGRATOR_MULT` for Multipole.

Reasoning: a systematic, SAD-cross-validated study found `mat-kick-mat` carries a real, measured bias against an exact reference (`~3.8e-6` for a corrector, growing with multipole order to `~1.4e-4` for an octupole-like term), and that leaving `model`/`integrator` unset (the prior Multipole behaviour) silently resolves to Xsuite's `adaptive` default, confirmed unsafe for every element type that has one. `14` kicks for Quad/Sext/Oct/Mult is a deliberate, explicit tradeoff against the study's fully-validated `21` — both map to the same `yoshida4` internal slice-count family as Bend's `10` kicks (`ceil(14/7)=2` slices vs `ceil(21/7)=3`, ~33% cheaper), at a real but small accuracy cost specifically for Sextupole/Octupole/Multipole (no thick-map shortcut exists for `k2`/`k3`/multipole content the way one exists for Bend's `k0`/`h` and Quadrupole's `k1`).

Consequence: this closed the corrector-specific discrepancy entirely (all 14 previously-failing `test_corrector.py` instances now pass) — the corrector discrepancy was a pure model-choice bias, not a sign or converter-logic bug. It did not close the remaining bend element-offset discrepancy (a `DX`-offset combined with `ANGLE != 0`), which was confirmed structural and unaffected by kick count — see the next decision below. Solenoid was deliberately left out of this retune — it has no `model` attribute at all, and the study's own solenoid guidance (`uniform`+`50` for radiation-critical use) is a different pattern from the `yoshida4`+kicks approach used here. Adding uniform `zeta`/single-order-multipole test coverage as part of validating this retune also surfaced two small, separate converter bugs (a sign error and a missing-function crash in `MULT`'s `K0`/`SK0` handling), fixed, plus two SAD behaviour facts documented in `docs/sad-behaviour.md`: `MULT` skew-quadrupole optics agreement depends on the twiss convention used for comparison (not a rotation-convention bug), and a small, accepted `K0`/`SK0` dipole-fringe residual, for which the converter warns when dipole-only `MULT` elements are simplified to Xsuite Bend/corrector elements.

## Bend element-offset (DX/DY) reference-orbit convention is not modelled

Decision: SAD2XS does not reproduce SAD's reference-orbit convention for a curved element (a `BEND` with `ANGLE != 0`, thick or thin) that also carries a nonzero `DX`/`DY` misalignment. The converted lattice keeps the element's design curvature (`h` for the thick `xt.Bend` representation, `hxl` for the thin `xt.Multipole` representation used when `L` is absent or zero) fixed to the unshifted design orbit regardless of the misalignment; SAD instead reconstructs its reference orbit through the displaced element. Combined with a nonzero `ROTATE`, a further, separate SAD-side artifact appears in SAD's own reported coupling (`R1`-`R4`) too.

Reasoning: two physical readings of a `DX`/`DY` misalignment on a curved element are both defensible (fixed design orbit vs. orbit that follows the displacement); Xsuite's curved elements are built on the first, SAD's behaviour is closer to the second. See `docs/sad-behaviour.md` for the full empirical characterisation of both this and the `ROTATE`-combined coupling artifact, including what was ruled out (an Edwards-Teng/Mais-Ripken convention mismatch, a converter bug) and what could not be confirmed without SAD source access (the coupling artifact's exact internal cause).

Consequence: the converter warns once per lattice (not once per element) when it finds one or more `BEND` elements with `ANGLE != 0` and a nonzero `DX`/`DY`, covering both the thick and thin representations. The affected test parametrisations are locked in as passing, quantified tests in `tests/conversion/elements/test_bend.py`
(`test_bend_offset_orbit_residual_is_angle_squared_order`,
`test_bend_offset_thin_bend_dispersion_residual_is_angle_squared_order`,
`test_bend_offset_rotated_coupling_is_a_sad_side_artifact`) rather than left failing or tracked in `tests/support/known_issues.py` — which physical reading is intended is a design-decision-level question for the SAD and Xsuite authors, not something to guess a converter fix for. Correctors (`ANGLE == 0`) and MULT-derived dipoles never carry a nonzero curvature and are confirmed unaffected by either finding.

## `BEND` `F1`/`FRINGE` fringe import is private, default-on, and on-momentum only

Decision: add `_import_sad_bend_fringes` (default `True`) to `Config`. When enabled, `BEND` conversion (both the `ANGLE != 0` sector-bend path and the `ANGLE == 0`, `K0`-only corrector path — `sad2xs/converter/_004_element_converter.py`, `convert_bends`/`convert_correctors`) reads `FRINGE`/`F1`/`FB1`/`FB2` and sets the resulting `xt.Bend`'s `edge_entry_fint`/`edge_entry_hgap`/`edge_exit_fint`/`edge_exit_hgap` from the closed form derived in `docs/sad-behaviour.md`. The output writer (`sad2xs/output_writer/_002_bend.py`, `_003_corr.py`) serialises these four fields whenever nonzero, and `check_is_simple_bend_corr` (`_000_helpers.py`) treats them as disqualifying the compact one-line form — a bend/corrector with only fint/hgap set (otherwise default) would previously have been serialised with every extra attribute silently dropped. Not exposed as a public/documented feature yet.

Reasoning: the closed form is essentially exact on-momentum. Off-momentum, Xsuite's native edge fringe formula has scaled the wrong way with `delta` relative to SAD (`docs/sad-behaviour.md`) — a fully independent from-scratch derivation (Forest's PTC paper, KEK Preprint 2005-109, §B) gets the same closed form as SAD, not Xsuite's, and real compiled PTC (via `cpymad`) confirms it: PTC implements the same paper's other formula, the one that (historically) matched Xsuite/MAD-NG instead. The upstream fix correcting Xsuite's momentum-scaling has since been merged, so this becomes a temporary, closing gap rather than an open formalism question SAD2XS has to work around indefinitely — until it reaches a released Xsuite version SAD2XS depends on, the bounded off-momentum residual below still applies. Kept private (not yet a documented public feature) for that reason. Switched to default-**on**: the on-momentum improvement to SAD-vs-Xsuite comparisons is real and immediate, and the off-momentum residual is bounded and explicitly tested rather than silent.

Consequence: on-momentum tracking/Twiss comparisons with the flag enabled should match SAD to a fraction of a percent; off-momentum comparisons carry a known, bounded residual (a few percent on realistic magnet parameters, growing with `delta` and with magnet strength) until the upstream Xsuite fix reaches a released version. That residual is asserted explicitly, not skipped, in `test_bend_fringe_import_off_momentum_residual_is_bounded` and its corrector equivalent (`tests/conversion/elements/test_bend.py`, `test_corrector.py`) — once the upstream fix is available, these tests should fail (residual outside the asserted band) and surface for review, at which point the closed-form workaround here can likely be retired in favour of Xsuite's own native formula. The writer round-trip (element → write → reload → track) is locked in separately by `tests/writer/elements/test_bend_writer.py` and `test_corr_writer.py`'s fint/hgap tests, since conversion-level tests that track the in-memory line directly would not have caught a writer serialisation gap. `F1`/`FB1`/`FB2` must be concrete numbers; symbolic (deferred-expression) fringe lengths are not supported and raise a clear error rather than silently producing wrong `fint`/`hgap` values. `MULT`-as-bend fringe is explicitly out of scope: checked directly against the real SAD binary, a `MULT` with `K0` and matching `FRINGE`/`FB1`/`FB2` does not reproduce the same formula as the equivalent `BEND` (confirmed via a direct side-by-side probe) — it needs its own investigation, not an assumption that it shares `BEND`'s code path. `QUAD` fringe is understood to use a structurally different parameter set (`F1`/`F2` meaning entrance/exit directly, plus `F1K1F`/`F1K1B`) and SAD subroutine — unlike the `MULT` exclusion above, this has not been checked against the real SAD binary in this investigation, so treat it as a documented reason to scope QUAD out for now, not a verified fact; confirming it (or finding it shares more of `BEND`'s formula than expected) is exactly the kind of thing `tests/sad/` exists to pin down before any QUAD fringe conversion logic is written.

## Cavity RF-focusing kick is not modelled

Decision: SAD2XS does not implement SAD's transverse RF-focusing kick for accelerating elements (`MULT` or `CAVI` with `VOLT != 0`, tracked with `RFSW` on — independent of `TRPT`). Every converted `xt.Cavity`, whether from a plain SAD `CAVI` or from the interleaved slices of a combined K1+VOLT `MULT`, behaves as if this term were absent, regardless of the source SAD file.

Reasoning: `xt.Cavity`'s own tracking code has no transverse coupling at all — see `docs/sad-behaviour.md` for what the term actually is and how its absence was confirmed by tracking, not just by reading the source once. The kick-application machinery already exists in xtrack, attached to a different element (`xt.RFMultipole`); reproducing SAD's `vcorr` coefficient automatically inside `xt.Cavity` itself would be the cleaner fix, but the exact phase convention has not yet been validated against the literature closed form (Rosenzweig & Serafini 1994) or against SAD, so it is not implemented on either the sad2xs or xtrack side yet.

Consequence: the converter warns once per lattice (not once per element, not conditional on a computed strength threshold) whenever any `xt.Cavity` element ends up in the converted line, in `convert_elements` (`sad2xs/converter/_004_element_converter.py`) rather than duplicated into both `convert_cavities` and the RF-`MULT` path in `convert_multipoles`. The omission is locked in as a permanent, accepted limitation by `tests/xtrack/test_cavity.py`, which asserts directly against `xtrack` (not against sad2xs conversion logic) that `xt.Cavity` gives zero `x -> px` coupling — if xtrack ever adds this term natively, that test fails loudly and this decision needs revisiting. This is expected to be negligible for typical high-energy/low-gradient RF (e.g. main synchrotron RF cavities) and potentially significant for low-energy/high-gradient structures (e.g. photoinjector-like LINAC sections) — the coefficient scales with `VOLT` and with `(frequency/momentum)^2`. TRPT/accelerating-reference-momentum conversion support (`xt.ReferenceEnergyIncrease` insertion) is a separate, not-yet-implemented feature; this decision applies regardless of whether that support exists.
