# Conversion options

Every option accepted by `convert_sad_to_xsuite`, what it does, and when to use it.

```python
import sad2xs

line = sad2xs.convert_sad_to_xsuite(
    sad_lattice_path = "lattice.sad",
    output_directory = "output",
    line_name        = "RING")
```

The call returns an `xt.Line`. It also writes a lattice file and an optics file, then reloads the line from those files, so the returned line matches the generated output.

**On this page:**

- [Required](#required)
- [Choosing what to convert](#choosing-what-to-convert)
- [Naming the output](#naming-the-output)
- [Reversals](#reversals)
- [Apertures](#apertures)
- [Converter configuration](#converter-configuration)

## Required

| Option | Meaning |
| --- | --- |
| `sad_lattice_path` | path to the input SAD lattice file |
| `output_directory` | directory to write the generated lattice and optics files into |

## Choosing what to convert

**`line_name`** — the SAD line to convert. When not given, the converter selects the longest line: by length, or by element count if every element is thin.

Set this whenever the file defines more than one line. Relying on the default means the selection changes if the lattice changes.

**`excluded_elements`** — element names to drop before conversion. Matching is case-insensitive, and it matches both a name and its explicit reversal, so an element excluded in one direction is also excluded in the other.

**`user_multipole_replacements`** — per-element overrides controlling how specific `MULT` elements convert. Matched by name prefix. Use this where a multipole is physically a quadrupole, sextupole, octupole, or bend and should convert to that single-purpose element rather than a general multipole. See [element conversion](../converter/elements.md).

## Naming the output

| Option | Default |
| --- | --- |
| `output_filename` | the input filename, without its `.sad` extension |
| `output_header` | a generic header |

`output_header` is stamped into both generated files. Setting it to something identifying the machine and the conversion makes the generated files self-describing.

## Reversals

Four flags transform the line. They interact with each other and with the reference particle's charge, so they are documented together in [line reversals](../converter/line-reversals.md).

| Option | Effect |
| --- | --- |
| `reverse_element_order` | reverse the element order of the selected line |
| `reverse_survey_horizontal` | mirror the survey horizontally, reversing bend directions |
| `reverse_survey_vertical` | mirror the survey vertically, reversing bend directions |
| `reverse_charge_sign` | flip the sign of the reference particle's charge |

Read that page before combining them. The solenoid `ks` depends on the charge sign, so `reverse_charge_sign` is not independent of the others.

## Apertures

**`install_apertures_as_markers`** — convert `APERT` elements to markers instead of aperture objects.

Use this when you want the aperture positions preserved in the line but no aperture limits applied during tracking. It also allows an `APERT` and a `MARK` element to share a name, which the parser otherwise rejects as a collision.

## Converter configuration

Any further keyword argument is forwarded to `Config`. This is how element models, integrators, kick counts, tolerances, and the fringe-import flags are overridden.

```python
line = sad2xs.convert_sad_to_xsuite(
    sad_lattice_path        = "lattice.sad",
    output_directory        = "output",
    N_INTEGRATOR_KICKS_QUAD = 21)
```

The defaults are chosen deliberately and are documented, with the reasoning, in [models and integrators](../converter/models-integrators.md). Read that before overriding them — several of the defaults exist because the obvious alternative fails on a real lattice.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
