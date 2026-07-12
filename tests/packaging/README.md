# Packaging Tests

This folder contains tests for package metadata and import boundaries.

Use these tests to protect the package's release contract and public API
surface. Runtime converter behaviour belongs in the conversion, writer, or
parser test areas.

## What Belongs Here

- Package metadata correctness (name, version format, author contact, license,
  declared dependencies).
- Public API surface checks (what is and is not importable from `sad2xs`).
- Import-time assumptions (the package loads without side-effects at the
  top level).

## What Does Not Belong Here

- Converter correctness or physics comparisons.
- Writer output format.
- SAD parser rules.

## Coverage

### `test_release_metadata.py` — 8 tests, all expected to pass

Reads installed package metadata via `importlib.metadata` and verifies
structural correctness. Does not pin specific values — it tests format and
presence so the checks remain valid across version bumps.

| Test | What it asserts |
|------|-----------------|
| `test_release_metadata_package_name_is_a_non_empty_string` | `Name` field exists and is a non-empty string |
| `test_release_metadata_version_follows_semver_format` | `Version` matches `^\d+\.\d+\.\d+` |
| `test_release_metadata_author_field_is_a_non_empty_string` | `Author` field exists and is non-empty |
| `test_release_metadata_author_email_contains_at_symbol` | `Author-email` contains `@` |
| `test_release_metadata_license_field_is_a_non_empty_string` | `License` field exists and is non-empty |
| `test_release_metadata_xsuite_is_listed_as_a_dependency` | A current coherent `xsuite` bundle appears in `install_requires` |
| `test_release_metadata_numpy_is_listed_as_a_dependency` | `numpy` appears in `install_requires` |
| `test_release_metadata_tfs_is_an_optional_extra_not_a_hard_dependency` | `tfs-pandas` is listed under `extras_require`, not `install_requires` |

### `test_import_boundaries.py` — 9 tests, all expected to pass

Imports `sad2xs` and verifies the public API surface. Checks presence and
type of each public symbol. Does not test that internal submodules are hidden
(Python's import machinery exposes them as side-effects of relative imports,
which is expected and acceptable behaviour).

| Test | What it asserts |
|------|-----------------|
| `test_import_boundary_convert_sad_to_xsuite_is_importable` | `sad2xs.convert_sad_to_xsuite` exists |
| `test_import_boundary_write_lattice_is_importable` | `sad2xs.write_lattice` exists |
| `test_import_boundary_write_optics_is_importable` | `sad2xs.write_optics` exists |
| `test_import_boundary_sad_helpers_namespace_is_importable` | `sad2xs.sad_helpers` exists |
| `test_import_boundary_convert_sad_to_xsuite_is_callable` | `sad2xs.convert_sad_to_xsuite` is callable |
| `test_import_boundary_write_lattice_is_callable` | `sad2xs.write_lattice` is callable |
| `test_import_boundary_write_optics_is_callable` | `sad2xs.write_optics` is callable |
| `test_import_boundary_sad_helpers_is_a_module` | `sad2xs.sad_helpers` is a `types.ModuleType` |
| `test_import_boundary_core_import_does_not_require_tfs` | `import sad2xs` succeeds with `tfs` blocked at the import-system level |
