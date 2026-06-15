# Roundtrip Tests

This folder contains tests for generated-file import and write/reload
equivalence.

Use these tests when the contract spans conversion, writing, and importing the
generated Xsuite files. Tests that only assert writer text should live in
`tests/writer/`; tests that only assert conversion objects should live in
`tests/conversion/`.
