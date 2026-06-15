# Element Conversion Tests

This folder contains conversion tests for individual SAD element families.

Each file should protect one element mnemonic or one tightly related group.
The usual progression is direct converter checks, full conversion pipeline
checks, then SAD optics or tracking comparisons where relevant.

Shared element fixtures live in `conftest.py`. Cross-file support should live
in `tests/support/` rather than being copied between element files.
