# Installation Tests

This folder contains tests for installer and installation helper behaviour.

Use these tests for command construction, executable discovery, platform
installation policy, and minimal SAD executable smoke checks. Do not run
destructive installation steps from tests.

Installation-specific input files, such as `sad_installation_test.sad`, live
beside these tests. Use a shared `tests/fixtures/` folder only when fixture data
is reused across unrelated test areas.
