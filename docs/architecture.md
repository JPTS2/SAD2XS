# Architecture

A map of the repository: which subsystem owns what, and where each is documented.

SAD2XS converts SAD lattice descriptions into Xsuite objects, and writes Python files that rebuild the converted model.

```text
SAD input
  -> parser and expression handling
  -> element filtering and conversion
  -> Xsuite Environment and Line construction
  -> post-conversion corrections and line operations
  -> output writer
```

**On this page:**

- [Package layout](#package-layout)
- [Top-level orchestration](#top-level-orchestration)
- [Public import surface](#public-import-surface)
- [Configuration and shared types](#configuration-and-shared-types)
- [Converter subsystem](#converter-subsystem)
- [Output writer subsystem](#output-writer-subsystem)
- [SAD helper subsystem](#sad-helper-subsystem)
- [Public and private validation](#public-and-private-validation)

## Package layout

| Path | Subsystem | Documentation |
| --- | --- | --- |
| `sad2xs/main.py` | orchestration, public entry point | this page |
| `sad2xs/converter/` | SAD to Xsuite conversion | [converter](converter/README.md) |
| `sad2xs/output_writer/` | serialisation to lattice and optics files | [output writer](writer/README.md) |
| `sad2xs/sad_helpers/` | wrappers around external SAD calculations | [SAD helpers](helpers/sad-helpers.md) |
| `sad2xs/xsuite_helpers/` | utilities operating purely on an `xt.Line` | [Xsuite helpers](helpers/xsuite-helpers.md) |
| `sad2xs/config.py` | conversion settings and defaults | [models and integrators](converter/models-integrators.md) |
| `sad2xs/types.py` | shared type aliases | this page |

The module numbering inside `sad2xs/converter/` reflects the historical pipeline order. It is useful for navigation, but it is not a public API promise.

## Top-level orchestration

`sad2xs/main.py` is the orchestration layer. The public conversion entry point is `convert_sad_to_xsuite`.

It parses the SAD input, builds the Xsuite model, applies post-conversion corrections, writes the lattice and optics files, then reloads the line from those files and returns it. The full step-by-step pipeline is documented in [the conversion model](converter/README.md).

When `_test_mode=True`, the function returns the converted line before writing and reloading output files.

Conversion details live in converter modules. Writer details live in output writer modules. External SAD helper logic stays separate.

Every option accepted by `convert_sad_to_xsuite` is documented in [conversion options](usage/conversion-options.md).

## Public import surface

The top-level package exposes:

- `convert_sad_to_xsuite`;
- `write_lattice`;
- `write_optics`;
- `sad_helpers`.

`sad_helpers` is imported lazily, on first access (PEP 562). It depends on an external SAD installation and extra Python packages, so importing the core converter does not load it.

## Configuration and shared types

`sad2xs/config.py` stores conversion settings and defaults. The element model, integrator, and kick-count defaults are the most consequential of these, and are documented with their reasoning in [models and integrators](converter/models-integrators.md).

`sad2xs/types.py` contains shared type aliases used across the converter and writer. Shared structures should remain small and explicit. They should not become a second hidden lattice model that competes with Xsuite.

## Converter subsystem

The converter modules in `sad2xs/converter/` turn parsed SAD information into Xsuite objects.

| Module | Responsibility | Documentation |
| --- | --- | --- |
| `_001_parser.py` | parse SAD file content into structured sections | [parsing](converter/parsing.md) |
| `_002_element_exclusion.py` | remove user-excluded elements | [parsing](converter/parsing.md) |
| `_003_expression_converter.py` | translate SAD expressions into xdeps expressions | [parsing](converter/parsing.md) |
| `_004_element_converter.py` | convert SAD element definitions into Xsuite elements | [element conversion](converter/elements.md) |
| `_005_line_converter.py` | convert SAD line definitions into Xsuite lines | [the conversion model](converter/README.md) |
| `_006_solenoid_converter.py` | solenoid region handling | [solenoids](converter/solenoids.md) |
| `_007_reversals.py` | reversed elements and lines | [line reversals](converter/line-reversals.md) |
| `_008_offset_markers.py` | resolve offset marker positions | [offset markers](converter/offset-markers.md) |
| `_009_write_lattice.py`, `_010_write_optics.py` | writer entry points | [output writer](writer/README.md) |

Conversion semantics are the converter's responsibility. The writer serialises the model that the converter built; it does not repair it.

## Output writer subsystem

The output writer modules in `sad2xs/output_writer/` generate Python lattice and optics files from the converted Xsuite model.

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
