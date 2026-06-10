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
  -> apply solenoid and harmonic RF corrections
  -> configure element models and integrators
  -> apply requested line and charge reversals
  -> install offset markers
  -> write lattice and optics files
  -> reload the generated files and return the rebuilt line
```

When `_test_mode=True`, the function returns the converted line before writing and reloading output files.

Next release target: this layer should stay thin where possible. Conversion details should live in converter modules, writer details should live in output writer modules, and external SAD helper logic should stay separate.

## Public import surface

The current top-level package import exposes:

- `convert_sad_to_xsuite`;
- `write_lattice`;
- `write_optics`;
- `sad_helpers`.

This is the practical public surface today.

Next release target: future changes should reduce import-time coupling to `sad_helpers`, because helper functionality depends on an external SAD installation and additional Python packages.

## Configuration and shared types

`sad2xs/config.py` stores conversion settings and defaults.

`sad2xs/types.py` contains shared type aliases used across the converter and writer. Shared structures should remain small and explicit. They should not become a second hidden lattice model that competes with Xsuite.

## Converter subsystem

The converter modules in `sad2xs/converter/` are responsible for turning parsed SAD information into Xsuite objects.

Key responsibilities:

- `_001_parser.py`: parse SAD file content into structured sections.
- `_002_element_exclusion.py`: remove or skip elements that should not be converted directly.
- `_003_expression_converter.py`: translate SAD-style expressions into Python-compatible expressions.
- `_004_element_converter.py`: convert supported SAD element definitions into Xsuite elements.
- `_005_line_converter.py`: convert SAD line definitions into Xsuite line definitions.
- `_006_solenoid_converter.py`: handle solenoid-specific conversion details.
- `_007_harmonic_rf.py`: handle harmonic RF cases.
- `_008_reversals.py`: construct reversed elements and lines where needed.
- `_009_offset_markers.py`: install offset marker structures.
- `_010_write_lattice.py` and `_011_write_optics.py`: writer entry points that assemble output from the `sad2xs/output_writer/` modules.

Next release target: the converter should produce a valid Xsuite model and should not rely on the writer to repair conversion semantics.

## Output writer subsystem

The output writer modules in `sad2xs/output_writer/` generate Python lattice and optics files from the converted Xsuite model.

Current status: the writer accepts an `xt.Line` at the main `write_lattice` entry point and can fill some missing global variables from `line.particle_ref`.

Long-term direction: the writer should become a more complete reusable serializer for Xsuite lattices, not only the final step of a SAD2XS conversion. This matters because a user may rematch or modify an Xsuite lattice after conversion and still want readable SAD2XS-style output.

Next release target: writer output should prefer information from the Xsuite `Environment`, `Line`, and element objects over raw SAD data. Any remaining dependency on SAD-specific conversion context should be explicit.

## SAD helper subsystem

The modules in `sad2xs/sad_helpers/` call external SAD tools for operations such as tracking, survey, twiss, transfer matrix, emittance, and chromaticity calculations.

These helpers are valuable for validation and comparison, but they depend on an external SAD installation.

Current status: the top-level package re-exports `sad_helpers`, so import-time coupling to helper dependencies may still exist.

Next release target: importing and using the core converter should not require SAD helper dependencies to be available.

## Public and private validation

The repository may be validated against private or non-shareable lattices during development. Those lattices must not be required for public tests or CI, and public issues should use synthetic reproductions.

Public regression tests should isolate the converter behaviour being protected without depending on private accelerator files.
