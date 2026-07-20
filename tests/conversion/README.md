# Conversion Tests

This folder contains tests for SAD-to-Xsuite conversion behaviour.

Conversion tests start after SAD text has been parsed. They protect how parsed
SAD data becomes Xsuite objects, how the public conversion pipeline assembles a
line, and how converted lines compare with SAD optics or tracking.

## What Belongs Here

- Direct converter tests that call an element converter with parsed element
  dictionaries and assert on the produced Xsuite objects.
- Pipeline tests that call `convert_sad_to_xsuite` and assert on names, order,
  generated elements, user options, or reference-particle behaviour.
- Physics equivalence tests that compare converted Xsuite optics or tracking
  against SAD.
- Compatibility tests for Xsuite APIs that the converter relies on.

## What Does Not Belong Here

- SAD text parsing rules. Those belong in `tests/parser/`.
- Generated lattice or optics writer formatting. That belongs in
  `tests/writer/`.
- SAD helper command construction and output parsing. Those belong in
  `tests/sad_helpers/`.

## Subfolders

- `elements/`: one file per SAD element family or closely related element
  group. These tests usually combine direct converter checks, full pipeline
  checks, and SAD comparison checks for that element.
- `pipeline/`: public conversion pipeline behaviour that is not owned by one
  element family, such as excluded elements, offset markers, reference
  particles, line selection, generated-file import, write/reload behaviour,
  line reversal, reverse charge, and user options.

Top-level files cover cross-cutting behaviour: `test_converter_helpers.py`
(converter helper functions), `test_xsuite_api_compatibility.py` (Xsuite APIs
the converter relies on), and `test_coupled_twiss_convention.py` (the
coupled-twiss comparison convention against SAD — proves SAD reports
Edwards-Teng optics and `R / sqrt(1 + det R)` coupling matrices, validates
`tests/support/coupled_optics.py`, and anchors each case with SAD-vs-Xsuite
transfer-matrix equality; see `docs/sad-helpers.md`).

## Element Test Shape

Element files should prefer this order when practical:

- local constants and helper functions;
- direct converter behaviour;
- public pipeline behaviour;
- SAD Twiss comparisons;
- SAD tracking comparisons;
- edge cases that are specific to that element family.

Large element families may need more internal sections. Solenoid handling is
intentionally extensive because bound solenoid regions, reference transforms,
and supported inserted elements interact in ways that are difficult to express
as small isolated tests.

## Shared Fixtures

`conftest.py` provides conversion-wide fixtures:

- `write_lattice`: writes a dedented temporary SAD lattice;
- `sad2xs_config`: quiet config for deterministic conversion tests.

`elements/conftest.py` provides element-converter fixtures:

- `xsuite_environment`: empty Xsuite environment for direct converter tests;
- `parsed_elements`: helper for minimal parsed element dictionaries;
- `assert_environment_element`: assertion helper for environment contents.

Use `tests.support.diagnostics` for Markdown failure reports. SAD reference
calls should use the public `sad2xs.sad_helpers` API.

## Artifacts

Physics comparison tests may write ignored Markdown diagnostics under
`tests/artifacts/conversion/`. Keep artifact paths aligned with the test source,
for example `tests/artifacts/conversion/elements/bend/`.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
