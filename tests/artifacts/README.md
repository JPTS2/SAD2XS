# Test Artifacts

This folder contains generated diagnostic Markdown reports produced by selected
physics comparison tests.

Artifacts should be deterministic, readable, and scoped to the test that
created them. They are local debugging evidence for difficult SAD-to-Xsuite
comparisons, not general-purpose fixtures.

Generated artifact files are ignored by Git. Keep this README tracked so the
folder's purpose remains clear.

Use paths that mirror the source test area, for example
`conversion/elements/sol/` for solenoid conversion diagnostics.
