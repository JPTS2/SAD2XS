# Parsing and expressions

How SAD text becomes structured data: file parsing, expression conversion, and element exclusion.

Three converter modules run before any Xsuite element is created:

| Module | Job |
| --- | --- |
| `_001_parser.py` | read the SAD file into a structured dictionary |
| `_002_element_exclusion.py` | drop elements the user asked to exclude |
| `_003_expression_converter.py` | turn SAD globals and deferred expressions into live xdeps expressions |

## Parsing the SAD file

`parse_sad_file` is the entry point. It loads the raw text, cleans it, then extracts four kinds of content:

- **global parameters** — `MOMENTUM`, `MASS`, `CHARGE`, `FSHIFT`;
- **LINE definitions** — each line's ordered list of element names;
- **element definitions** — grouped by SAD element type;
- **deferred expressions** — symbolic values, kept as expressions rather than evaluated.

The result is a dictionary with keys `globals`, `lines`, `elements`, `expressions`, and `expression_line_numbers`.

SAD's own interactive commands (`ON`, `OFF`, `FFS`) are recognised and dropped. SAD2XS knows which line to convert from its `line_name` argument, so it does not need SAD's interactive command state.

### Reference particle fallbacks

Missing global parameters fall back to `Config`:

| SAD global | Fallback | If still missing |
| --- | --- | --- |
| `MASS` | `ref_particle_mass0` | defaults to the electron mass |
| `CHARGE` | `ref_particle_q0` | defaults to `+1` |
| `MOMENTUM` | `ref_particle_p0c` | **raises** |

`MOMENTUM` has no default. A lattice with no momentum in the file and none in the configuration cannot be converted.

### Errors that cite a line number

Parse errors report the source line number of the offending statement, in the form `"line N: ..."`. Sections are tracked with their line numbers as the file is split, which is what makes this possible.

`parse_sad_file` raises `ValueError` when:

- a SAD function definition (`:=`) is found;
- a `LINE` or element definition is malformed;
- an element name collides with a protected name, or with a different element type;
- no momentum is available from either the file or `Config`.

SAD function definitions are rejected deliberately, not parsed. See the parser-hardening decision in [design decisions](../development/design-decisions.md).

## Excluding elements

`exclude_elements` removes the elements named in the `excluded_elements` option. Matching is case-insensitive.

It matches both a name and its explicit reversal, which SAD marks with a leading `-`. An element excluded in one direction is therefore also excluded in the other.

Removed elements are dropped from every element-type dictionary and from every `LINE` component list. The parsed data is mutated in place.

## Converting expressions

`convert_expressions` registers SAD globals and deferred expressions as live xdeps expressions in the Xsuite environment. Registering them as expressions, rather than evaluating them to numbers, is what keeps the converted lattice tunable after conversion.

Global variables and deferred expressions may reference each other in any order. The converter cannot know a safe order in advance, so it does not compute one. Instead it retries each group up to ten times, registering whichever entries resolve on each pass. It stops when every entry has converted, or when a pass makes no further progress.

If any entry still cannot be resolved after ten passes, `convert_expressions` raises `ValueError`. A circular reference and an invalid reference both fail this way.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
