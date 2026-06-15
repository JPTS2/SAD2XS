# Test Support

This folder contains reusable support modules for the test suite.

Support modules should make tests clearer without hiding the behaviour under
test. Keep shared constants, diagnostic writers, and small assertion helpers
here.

Files in this folder are not test modules. They should be safe to import and
should not run SAD, write temporary files, or perform assertions at import time.
