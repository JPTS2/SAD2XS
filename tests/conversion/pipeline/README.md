# Conversion Pipeline Tests

This folder contains tests for public conversion pipeline behaviour that is not
owned by one SAD element family.

Use this folder for options and line-level behaviour such as the public
`convert_sad_to_xsuite` entry point, explicit line selection, write/reload
behaviour, excluded elements, offset markers, reference-particle setup,
multipole replacements, reverse charge, reverse element order, and reverse bend
direction.

Element-family physics belongs in `tests/conversion/elements/`; this folder
should stay focused on pipeline orchestration and public conversion options.
