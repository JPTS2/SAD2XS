# Architecture

SAD2XS converts SAD lattice descriptions into Xsuite objects and can write Python files that rebuild the converted model.

The current package is organised as a single project with several internal subsystems:

```text
SAD input
  -> parser and expression handling
  -> element filtering and conversion
  -> Xsuite Environment and Line construction
  -> post-conversion corrections and line operations
  -> output writer
```

The module numbering inside `sad2xs/converter/` reflects the historical pipeline order. It is useful for navigation, but it should not be treated as a public API promise.

## Top-level orchestration

`sad2xs/main.py` is the main orchestration layer. The public conversion entry point is `convert_sad_to_xsuite`.

The current orchestration flow is:

```text
parse SAD input
  -> exclude requested elements
  -> optionally convert apertures to markers
  -> create an Xsuite Environment
  -> convert expressions and globals
  -> create the reference particle
  -> convert elements
  -> convert lines
  -> select the requested or longest line
  -> apply solenoid corrections
  -> configure element models and integrators
  -> apply requested line and charge reversals
  -> install offset markers
  -> write lattice and optics files
  -> reload the generated files and return the rebuilt line
```

When `_test_mode=True`, the function returns the converted line before writing and reloading output files.

Conversion details live in converter modules. Writer details live in output writer modules. External SAD helper logic stays separate.

## Public import surface

The top-level package exposes:

- `convert_sad_to_xsuite`;
- `write_lattice`;
- `write_optics`;
- `sad_helpers`.

`sad_helpers` is imported lazily, on first access (PEP 562). It depends on an external SAD installation and extra Python packages, so importing the core converter does not load it.

## Configuration and shared types

`sad2xs/config.py` stores conversion settings and defaults.

`sad2xs/types.py` contains shared type aliases used across the converter and writer. Shared structures should remain small and explicit. They should not become a second hidden lattice model that competes with Xsuite.

## Converter subsystem

The converter modules in `sad2xs/converter/` are responsible for turning parsed SAD information into Xsuite objects.

Key responsibilities:

- `_001_parser.py`: parse SAD file content into structured sections. Parse errors cite the source line number; SAD function definitions (`:=`) are rejected explicitly rather than silently misparsed — see `docs/design-decisions.md`.
- `_002_element_exclusion.py`: remove or skip elements that should not be converted directly.
- `_003_expression_converter.py`: translate SAD-style expressions into Python-compatible expressions.
- `_004_element_converter.py`: convert supported SAD element definitions into Xsuite elements.
- `_005_line_converter.py`: convert SAD line definitions into Xsuite line definitions.
- `_006_solenoid_converter.py`: handle solenoid-specific conversion details.
- `_007_reversals.py`: construct reversed elements and lines where needed.
- `_008_offset_markers.py`: install offset marker structures.
- `_009_write_lattice.py` and `_010_write_optics.py`: writer entry points that assemble output from the `sad2xs/output_writer/` modules.

Conversion semantics are the converter's responsibility. The writer serialises the model that the converter built; it does not repair it.

## Output writer subsystem

The output writer modules in `sad2xs/output_writer/` generate Python lattice and optics files from the converted Xsuite model.

The writer accepts an `xt.Line` at the main `write_lattice` entry point. It fills some missing global variables from `line.particle_ref`.

Writer output is generated from the Xsuite `Environment`, `Line`, and element objects rather than from raw SAD data.

The writer is not a general Xsuite serialiser. It still carries SAD2XS-specific assumptions, and it writes deferred (xdeps) expressions as literal floats. Both are tracked in the [issue tracker](https://github.com/JPTS2/sad2xs/issues).

## SAD helper subsystem

The modules in `sad2xs/sad_helpers/` call external SAD tools for operations such as tracking, survey, twiss, transfer matrix, emittance, and chromaticity calculations.

These helpers are valuable for validation and comparison, but they depend on an external SAD installation.

The core converter does not require them. `sad_helpers` is imported lazily, so importing and using the converter works without the helper dependencies installed. `tests/packaging/test_import_boundaries.py` protects this boundary.

## Public and private validation

The repository may be validated against private or non-shareable lattices during development. Those lattices must not be required for public tests or CI, and public issues should use synthetic reproductions.

Public regression tests should isolate the converter behaviour being protected without depending on private accelerator files.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
