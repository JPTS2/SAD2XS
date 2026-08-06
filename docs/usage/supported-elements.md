# Supported elements

"Is my element supported?" has two answers, because conversion and output are separate steps.

| Question | Answer |
| --- | --- |
| Which SAD elements can the converter read? | [element conversion](../converter/elements.md) |
| Which Xsuite elements survive a write and reload? | [output writer](../writer/README.md) |

A normal `convert_sad_to_xsuite` call does both. It converts the SAD file, writes the lattice and optics files, then reloads the line from those files and returns it. A full conversion therefore needs the element to be supported by **both** steps.

## Reading a SAD lattice

The converter reads these SAD element types: `DRIFT`, `BEND`, `QUAD`, `SEXT`, `OCT`, `MULT`, `CAVI`, `APERT`, `SOL`, `COORD`, `MARK`, `MONI`, `BEAMBEAM`, and `MAP`. A `BEND` with no angle is treated as a corrector, on its own conversion path.

Being read is not the same as being fully modelled. `MONI`, `BEAMBEAM`, and `MAP` become transparent markers: they keep their place in the line but carry no physics. Several other elements carry accepted limitations, such as the solenoid fringe kick and the cavity RF-focusing kick.

See [element conversion](../converter/elements.md) for what each type becomes, and [limitations](limitations.md) for what is not reproduced.

## Writing and reloading

The writer serialises Xsuite classes, not SAD types. By this point the SAD input is no longer the model.

The two sets do not map one to one. A single SAD element can become several Xsuite elements: a bound solenoid becomes a four-component sub-line, an RF-carrying `MULT` becomes alternating multipole and cavity slices, and a quadrupole with fringe parameters becomes up to three elements.

See [output writer](../writer/README.md) for the class list and what each preserves.

## Unsupported input

An unsupported SAD element type fails clearly. Silent loss of physics information is worse than a loud error.

Parse errors cite the source line number, so an unsupported or malformed definition can be found directly in the SAD file. See [parsing and expressions](../converter/parsing.md).

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
