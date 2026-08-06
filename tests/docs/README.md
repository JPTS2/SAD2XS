# Documentation Tests

This folder contains tests that keep the documentation consistent with the
codebase.

Documentation in this repository carries load-bearing facts: element models,
supported element lists, empirically-established SAD behaviour, and pointers
between pages. When the code moves and a document does not, a reader is sent
somewhere that no longer exists. These tests catch that.

## What These Tests Detect

**Staleness, not wrongness.** Every check is an exact match against something
the repository already knows: a file exists, a heading exists, a name resolves,
a number matches collection.

They cannot tell whether a sentence is true. A README once stated the opposite
of the code on three separate points, in fluent prose, with every path and name
valid. Nothing here would have caught it. Physics claims, tolerances, and
measured values are reviewed by people, not by this folder.

## What Belongs Here

- Reference integrity: links, anchors, cited sections, cited paths, cited test
  names.
- Agreement between a documented table and the constant it restates.
- Coverage completeness: every test file named in its folder README.
- Docstrings on every top-level definition, and the standard header on every
  module.
- Declared test counts matching what pytest collects.
- Declared failure counts matching the `known_issue` markers.
- Coverage tables all having the same column shape.

## What Does Not Belong Here

- Converter physics, parser rules, or writer correctness.
- Prose style, voice, or line length. These are brittle to assert and would
  fight legitimate edits.
- Anything requiring a judgement about whether a statement is correct.

## Coverage

Does not require the SAD binary. Each test walks every documentation file and
reports the complete list of violations, so one failure names every offender
rather than stopping at the first.

| File | Tests | Fail | Failure root cause |
|------|-------|------|--------------------|
| `test_documentation.py` | 11 | 0 | — |
| `test_docstrings.py` | 3 | 0 | — |

### Reference integrity

| Test | What it asserts |
|------|-----------------|
| `test_every_internal_link_resolves` | every relative Markdown link points at a file that exists |
| `test_every_anchor_resolves` | every `#anchor` matches a heading, using GitHub's own slug rules |
| `test_cited_section_headings_exist` | a section named in prose exists in the document it names |
| `test_cited_paths_are_tracked_files` | every backticked repository path is tracked by git |
| `test_cited_test_names_exist` | every backticked `test_*` name resolves to a real test |

`test_cited_section_headings_exist` is the reason this folder exists. Prose
names a section as `path.md` ("Section Name") or as `path.md`'s Section Name
section. Neither form is a link, so no link checker sees it. Six references
survived a documentation restructure pointing at sections that had moved, and
every mechanical check still passed because the files themselves existed.

`test_cited_paths_are_tracked_files` checks tracked status rather than presence
on disk. A reference to an untracked working file resolves on the machine that
wrote it and breaks for everyone else. Checking git makes a local run agree with
CI, and needs no folder name hard-coded into the test.

### Coverage and agreement

| Test | What it asserts |
|------|-----------------|
| `test_every_test_file_has_a_coverage_table_row` | no test file is missing from its folder README |
| `test_coverage_tables_have_the_standard_shape` | every coverage table starts with the `File`, `Tests`, `Fail` columns |
| `test_config_tables_match_config` | documented models, integrators, kick counts, and element lists match `Config` |
| `test_declared_failure_counts_match_known_issues` | each `Fail` count matches `known_issues.py` |

A file missing from a coverage table reads as untested. That is worse than a
wrong count, because nothing signals the behaviour is protected at all.

Every coverage table starts with the columns `File`, `Tests`, `Fail`. Later
columns are free, so a folder can add whatever it needs. Counts are read from
the fixed columns by position, which is why the shape is asserted: a table that
swapped `Tests` and `Fail` would otherwise be misread rather than rejected. A
table listing helper modules rather than test files is not a coverage table and
is not held to the shape.

### Test counts

| Test | What it asserts |
|------|-----------------|
| `test_per_file_counts_match_collection` | each per-file count in a folder README matches collection |
| `test_folder_and_suite_totals_match_collection` | the Suite Total table in `tests/README.md` matches collection |

**Do not update these counts, or the `Fail` counts, by hand.** Run:

```bash
python -m tests.support.docs_inventory --update-counts
```

The updater and the tests share one implementation in
`tests/support/docs_inventory.py`, so a passing test means the files match what
the updater would write. This is the same arrangement as a formatter and its
`--check` mode.

Counts come from `pytest --collect-only` in a subprocess. Collection imports
test modules but runs no test, so the SAD executable is never invoked.

A non-zero exit status from collection raises rather than counting what
survived. A module that fails to import still lets pytest report every other
test, so a partial collection would otherwise be written into the READMEs as
if it were the real total.

Each Suite Total substitution must match exactly once. A pattern matching twice
would overwrite an unrelated number elsewhere in the file, so the updater
refuses to write anything instead.

### Docstrings and module headers

`test_docstrings.py` walks every tracked `.py` file in `sad2xs/` and `tests/`.

| Test | What it asserts |
|------|-----------------|
| `test_every_module_carries_the_standard_header` | every module docstring has an `Authors`/`Email`/`Date` block |
| `test_every_module_header_date_is_an_iso_date` | every header `Date` parses as `YYYY-MM-DD` |
| `test_every_definition_has_a_docstring` | every top-level function, class, and method has a docstring |

Nested functions are exempt. Fixtures and closures are read together with the
code around them, so a docstring on each one adds words without adding meaning.

The `Date` check is format only. The field is maintained by hand, and whether a
date is *correct* is not something the repository can know.

## Known Limitations

- Only the two prose forms above are recognised as section citations. A
  reference phrased another way is not checked.
- `test_cited_paths_are_tracked_files` falls back to a plain existence check
  when git is unavailable, such as in a source archive. The fallback cannot
  detect an untracked file.
- `NON_TEST_IDENTIFIERS` in `tests/support/docs_inventory.py` lists backticked
  `test_*` names that are not tests, such as workflow inputs. Extend it rather
  than loosening the pattern.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
