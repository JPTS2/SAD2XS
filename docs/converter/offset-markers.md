# Offset markers

How SAD's `OFFSET` parameter on `MARK`, `MONI`, and `BEAMBEAM` elements is resolved into an insertion point.

Offset markers are handled by `sad2xs/converter/_008_offset_markers.py`. The insertion itself happens later, in `sad2xs/output_writer/_016_offset_markers.py`.

**On this page:**

- [What SAD's OFFSET does](#what-sads-offset-does)
- [Why the SAD sequence is used, not the Xsuite table](#why-the-sad-sequence-is-used-not-the-xsuite-table)
- [Interaction with reversed element order](#interaction-with-reversed-element-order)
- [Where the marker goes](#where-the-marker-goes)

## What SAD's OFFSET does

`OFFSET` places a marker at a fractional position relative to its own nominal location. It does not move the marker to an absolute `s`.

The rules were confirmed against the real SAD binary:

| `OFFSET` value | Effect |
| --- | --- |
| `0 <= OFFSET <= 1` | no operation, the marker stays where it is |
| otherwise | move `floor(OFFSET)` positions forward, then land at `(OFFSET mod 1)` through that element |

A reversed reference, written `-NAME`, walks the same `OFFSET` in the opposite direction, at `1 - OFFSET`.

## Why the SAD sequence is used, not the Xsuite table

"`N` positions forward" counts elements in **SAD's own declared sequence**, not in the converted Xsuite line.

The two are not interchangeable. One SAD element can become several Xsuite elements — a solenoid boundary becomes a four-component sub-line, and a quadrupole with fringe becomes up to three elements. Counting positions in the Xsuite table would therefore land in the wrong place.

`_flatten_sad_line_elements` expands the parsed `LINE` into its flat, ordered leaf sequence, which is SAD's own element numbering. It resolves nested lines recursively. A `-SUBLINE` reference reverses both the order and the sign of every leaf in its expansion.

A leaf's own `-` sign is kept rather than dropped. `create_reversed_component` names a reversed clone `-name`, so the sign is what distinguishes a forward reference from a reversed one.

## Interaction with reversed element order

`reverse_element_order=True` mirrors the line before this stage runs. It never touches the parsed SAD data.

The target element is therefore still found by walking SAD's forward-declared sequence. `OFFSET`'s "`N` positions forward" means physical adjacency in the declared lattice, not travel direction.

The resulting `s` is then mirrored the same way everything else is mirrored:

```text
s -> (total line length) - s
```

This was cross-checked against SAD's native `-LINE` reversal, which produces an identical offset-marker `s`.

## When a marker cannot be placed

No element type is excluded as a target. A marker is skipped for one reason only: its `s` falls where a negative-length element makes the `s` table non-monotonic, so two elements occupy the same `s` and "insert at `s`" has no unique answer.

These regions are found from SAD's own cumulative lengths, before any insertion is attempted. That matters because the generated lattice file inserts every marker in one batched call. A marker that cannot be placed would otherwise abort the batch and cost every other marker with it.

A skipped marker is warned about, with its own position and region logged at debug level.

SAD's `OFFSET` is unambiguous here, because it names an element and a fraction through it. The ambiguity appears only when SAD2XS collapses that to an absolute `s`, which the generated file's insertion format requires.

## Where the marker goes

Every moved marker is removed from the line at this stage, whether it was skipped or not.

A surviving marker is re-inserted only when the lattice file is generated. The in-memory line never gets it back. `convert_offset_markers` returns an `offset_marker_locations` dictionary, mapping each moved marker's base name to the list of `s`-positions it should be re-inserted at.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
