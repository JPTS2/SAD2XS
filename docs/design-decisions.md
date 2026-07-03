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

Reasoning: the fringe kick is a genuine, nonlinear hard-edge term in SAD's solenoid Hamiltonian, distinct from the solenoid's main linear field. Neither `xt.UniformSolenoid` nor `xt.VariableSolenoid` implements it. This was discussed with the Xsuite lead developer — there are no current plans to adopt a bolted-on, SAD-specific Hamiltonian term for this; the recommended direction for accurate modelling of complex/overlapped solenoid fields is field maps with a spline Boris integrator. Agreement between SAD and Xsuite is otherwise excellent once this is accounted for (setting `DISFRIN=1` on the SAD side makes SAD's own output match Xsuite's).

Consequence: the converter warns once per lattice (not once per element) when it finds one or more SAD `SOL` elements without `DISFRIN=1`, so users know their solenoid's fringe-kick physics is not being reproduced. Test comparisons involving solenoid physics should set `DISFRIN=1` on the SAD side to get a fair, apples-to-apples comparison; a dedicated test (`test_sol_disfrin_off_diverges_from_xsuite_in_tracking`) locks in the expected divergence without it as a permanent, accepted limitation rather than an open bug — it must not be added to `tests/support/known_issues.py`. A related consequence: spin-tracking studies through solenoid lattices are not well supported by this converter either, since spin precession is highly sensitive to exactly this kind of fine field detail at the fringe.

## Bend/Quadrupole/Sextupole/Octupole/Multipole model and integrator retune

Decision: `sad2xs/config.py`'s default `model`/`integrator`/`num_multipole_kicks` per element type changed from `mat-kick-mat`/`uniform`/`20` (Bend/Quad/Sext/Oct) and no explicit setting at all (Multipole) to: `bend-kick-bend`/`uniform`/`10` for Bend (and, since a zero-angle SAD corrector converts to a plain `xt.Bend`, Correctors too); `rot-kick-rot-high-order`/`yoshida4`/`14` for Quadrupole, Sextupole, Octupole, and the newly-added `MODEL_MULT`/`INTEGRATOR_MULT` for Multipole.

Reasoning: a systematic, SAD-cross-validated study found `mat-kick-mat` carries a real, measured bias against an exact reference (`~3.8e-6` for a corrector, growing with multipole order to `~1.4e-4` for an octupole-like term), and that leaving `model`/`integrator` unset (the prior Multipole behaviour) silently resolves to Xsuite's `adaptive` default, confirmed unsafe for every element type that has one. `14` kicks for Quad/Sext/Oct/Mult is a deliberate, explicit tradeoff against the study's fully-validated `21` — both map to the same `yoshida4` internal slice-count family as Bend's `10` kicks (`ceil(14/7)=2` slices vs `ceil(21/7)=3`, ~33% cheaper), at a real but small accuracy cost specifically for Sextupole/Octupole/Multipole (no thick-map shortcut exists for `k2`/`k3`/multipole content the way one exists for Bend's `k0`/`h` and Quadrupole's `k1`).

Consequence: this closed the corrector-specific part of issue #55 entirely (all 14 previously-failing `test_corrector.py` instances now pass) — the corrector discrepancy was a pure model-choice bias, not a sign or converter-logic bug. It did not close the remaining bend element-offset part of #55 (a `DX`-offset combined with `ANGLE != 0`), which was confirmed structural and unaffected by kick count — SAD gives a genuine small nonzero orbit effect that Xsuite gives as numerical noise regardless of model or kicks; this needs its own investigation, not a config change. Solenoid was deliberately left out of this retune — it has no `model` attribute at all, and the study's own solenoid guidance (`uniform`+`50` for radiation-critical use) is a different pattern from the `yoshida4`+kicks approach used here. Adding uniform `zeta`/single-order-multipole test coverage as part of validating this retune also surfaced two small, separate converter bugs (a sign error and a missing-function crash in `MULT`'s `K0`/`SK0` handling) and one deeper, still-open question about how SAD's `ROTATE` element parameter and Xsuite's `xt.Rotation` element compose with a multipole kick (tracked as issue #101).
