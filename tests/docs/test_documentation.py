"""
================================================================================
Tests for documentation consistency with the codebase
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-29
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import re
from pathlib import Path

from sad2xs.config import Config

from tests.support import docs_inventory as inventory
from tests.support.docs_inventory import REPO_ROOT, relative

################################################################################
# Test Parameters
#
# Each test walks every documentation file and reports the complete list of
# violations. A sweep that stops at the first failure would hide the rest.
################################################################################
MODELS_DOC     = REPO_ROOT / "docs" / "converter" / "models-integrators.md"
ELEMENTS_DOC   = REPO_ROOT / "docs" / "usage" / "supported-elements.md"
WRITER_DOC     = REPO_ROOT / "docs" / "writer" / "README.md"


################################################################################
# Helpers
################################################################################
def _report(violations: list[str]) -> str:
    """
    Format violations as an indented block for an assertion message.
    """
    return "\n".join(f"  {line}" for line in violations)


################################################################################
# Reference Integrity
################################################################################
def test_every_internal_link_resolves():
    """
    Every relative Markdown link points at a file that exists.

    Walks every tracked documentation file and resolves each link target
    against the repository. External links are not followed.
    """
    violations = []

    for doc in inventory.doc_files():
        for target, line in inventory.links(doc):
            path = target.split("#")[0].strip()
            if not path:
                continue
            if not (doc.parent / path).resolve().exists():
                violations.append(f"{relative(doc)}:{line}: {target}")

    assert not violations, (
        "Documentation links must point at files that exist. Broken links:\n"
        + _report(violations))


def test_every_anchor_resolves():
    """
    Every `#anchor` matches a heading in the file it points at.

    Anchors are compared against GitHub's own slug rules, so a heading reworded
    without updating its "On this page" entry fails here.
    """
    slugs      = {relative(doc): {slug for _, _, slug in inventory.headings(doc)}
                  for doc in inventory.doc_files()}
    violations = []

    for doc in inventory.doc_files():
        for target, line in inventory.links(doc):
            if "#" not in target:
                continue
            path, anchor = target.split("#", 1)
            resolved     = (doc.parent / path).resolve() if path else doc
            try:
                key = relative(resolved)
            except ValueError:
                continue
            if key in slugs and anchor not in slugs[key]:
                violations.append(f"{relative(doc)}:{line}: {target}")

    assert not violations, (
        "Documentation anchors must match a heading in the target file. "
        "Unresolved anchors:\n" + _report(violations))


def test_cited_section_headings_exist():
    """
    Every section of another document named in prose actually exists there.

    Prose names a section as `path.md` ("Section Name") or as `path.md`'s
    Section Name section. Neither form is a link, so no link checker sees it.
    This is how six references survived the documentation restructure while
    pointing at sections that had moved.
    """
    headings   = {relative(doc): {text for _, text, _ in inventory.headings(doc)}
                  for doc in inventory.doc_files()}
    violations = []

    for doc in inventory.doc_files():
        for cited_doc, section in inventory.cited_sections(doc):
            if cited_doc not in headings:
                violations.append(
                    f"{relative(doc)}: cites unknown document {cited_doc}")
            elif section not in headings[cited_doc]:
                violations.append(
                    f'{relative(doc)}: {cited_doc} has no section "{section}"')

    assert not violations, (
        "A document section named in prose must exist in the target file. "
        "Stale section references:\n" + _report(violations))


def test_cited_paths_are_tracked_files():
    """
    Every backticked repository path names a file tracked by git.

    Checking tracked status rather than presence on disk catches a reference to
    an untracked working file, which resolves locally and breaks for everyone
    else. It also catches deleted and renamed files without naming any folder.
    """
    tracked    = inventory.tracked_files()
    violations = []

    for doc in inventory.doc_files():
        for path, line in inventory.cited_paths(doc):
            if path not in tracked:
                violations.append(f"{relative(doc)}:{line}: {path}")

    assert not violations, (
        "Documentation must only cite files tracked by git. Untracked or "
        "missing paths:\n" + _report(violations))


def test_cited_test_names_exist():
    """
    Every backticked `test_*` name resolves to a real test function or file.

    Names are collected from the whole test tree, so a renamed test fails here
    rather than leaving a dead pointer in a README.
    """
    defined = set()
    for source in (REPO_ROOT / "tests").rglob("test_*.py"):
        defined.add(source.stem)
        defined.update(re.findall(r"^def (test_[a-z0-9_]+)", source.read_text(), re.M))

    violations = []
    for doc in inventory.doc_files():
        for name, line in inventory.cited_test_names(doc):
            if name not in defined:
                violations.append(f"{relative(doc)}:{line}: {name}")

    assert not violations, (
        "Documentation must only cite tests that exist. Unknown test names:\n"
        + _report(violations))


################################################################################
# Coverage Completeness
################################################################################
def test_every_test_file_has_a_coverage_table_row():
    """
    Every test file has a row, with a count, in its folder's coverage table.

    Driven from what pytest collects rather than from the READMEs, so a folder
    with no table at all fails here instead of being skipped. A skipped folder
    is the failure mode this test exists to prevent: `tests/conversion/` once
    held 85 tests and no table, and every count check passed regardless.
    """
    violations = []

    for path in sorted(inventory.collected_counts()):
        source = Path(path)
        readme = REPO_ROOT / source.parent / "README.md"

        if not readme.exists():
            violations.append(f"{source.parent}: has no README.md")
        elif source.name not in inventory.readme_counts(readme):
            violations.append(
                f"{relative(readme)}: no coverage table row for {source.name}")

    assert not violations, (
        "Every test file must have a coverage table row with a test count in "
        "its folder README. Missing entries:\n" + _report(violations))


def test_coverage_tables_have_the_standard_shape():
    """
    Every coverage table starts with the `File`, `Tests`, `Fail` columns.

    Counts are read from these columns by position, so a table that reorders
    or omits one would be misread rather than rejected. Reading `Fail` where
    `Tests` was meant is a silent wrong number, which is the failure this test
    exists to make loud.
    """
    violations = []

    for readme in sorted(inventory.TESTS_DIR.rglob("README.md")):
        for line, header, rows in inventory.coverage_tables(readme):
            if not any(inventory.names_a_test_file(row) for row in rows):
                continue                # a table of helper modules, not tests
            actual = tuple(header[:len(inventory.STANDARD_COLUMNS)])
            if actual != inventory.STANDARD_COLUMNS:
                violations.append(
                    f"{relative(readme)}:{line}: columns start "
                    f"{list(actual)}, expected {list(inventory.STANDARD_COLUMNS)}")

    assert not violations, (
        "Every coverage table must start with the columns "
        f"{list(inventory.STANDARD_COLUMNS)}. Non-standard tables:\n"
        + _report(violations))


################################################################################
# Agreement With The Code
################################################################################
def test_config_tables_match_config():
    """
    Documented element models, integrators, kick counts, and supported element
    lists match `sad2xs.config.Config`.

    These tables restate values that live in the code. The restatement is
    deliberate, because the surrounding prose explains the reasoning, so the
    two copies are checked instead of merged.
    """
    config     = Config()
    violations = []

    expected_models = {
        "Drift":      (config.MODEL_DRIFT, None,                     None),
        "Bend":       (config.MODEL_BEND,  config.INTEGRATOR_BEND,   config.N_INTEGRATOR_KICKS_BEND),
        "Quadrupole": (config.MODEL_QUAD,  config.INTEGRATOR_QUAD,   config.N_INTEGRATOR_KICKS_QUAD),
        "Sextupole":  (config.MODEL_SEXT,  config.INTEGRATOR_SEXT,   config.N_INTEGRATOR_KICKS_SEXT),
        "Octupole":   (config.MODEL_OCT,   config.INTEGRATOR_OCT,    config.N_INTEGRATOR_KICKS_OCT),
        "Multipole":  (config.MODEL_MULT,  config.INTEGRATOR_MULT,   config.N_INTEGRATOR_KICKS_MULT),
        "Cavity":     (config.MODEL_CAVI,  config.INTEGRATOR_CAVI,   None)}

    documented = {}
    for line in MODELS_DOC.read_text().splitlines():
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) == 4 and cells[0] in expected_models:
            documented[cells[0]] = tuple(cell.replace("`", "") for cell in cells[1:])

    for element, (model, integrator, kicks) in expected_models.items():
        if element not in documented:
            violations.append(f"models-integrators.md: no row for {element}")
            continue
        doc_model, doc_integrator, doc_kicks = documented[element]
        if doc_model != model:
            violations.append(
                f"models-integrators.md: {element} model is `{doc_model}`, "
                f"config says `{model}`")
        if integrator is not None and doc_integrator != integrator:
            violations.append(
                f"models-integrators.md: {element} integrator is "
                f"`{doc_integrator}`, config says `{integrator}`")
        if kicks is not None and doc_kicks != str(kicks):
            violations.append(
                f"models-integrators.md: {element} kicks is {doc_kicks}, "
                f"config says {kicks}")

    documented_sad = {
        name.lower() for name in
        re.findall(r"`([A-Z]+)`", ELEMENTS_DOC.read_text())}
    if missing := config.SAD_ALLOWED_ELEMENTS - documented_sad:
        violations.append(
            f"supported-elements.md: SAD types not documented: {sorted(missing)}")

    documented_writer = set(re.findall(r"`xt\.([A-Za-z]+)`", WRITER_DOC.read_text()))
    if missing := config.ALLOWED_ELEMENTS - documented_writer:
        violations.append(
            f"writer/README.md: Xsuite classes not documented: {sorted(missing)}")

    assert not violations, (
        "Documented configuration must match sad2xs/config.py. Disagreements:\n"
        + _report(violations))


################################################################################
# Test Counts
################################################################################
def test_per_file_counts_match_collection():
    """
    Every per-file test count in a folder README matches what pytest collects.

    Run `python -m tests.support.docs_inventory --update-counts` to fix a
    failure. The updater and this test share one implementation, so counts are
    never maintained by hand.
    """
    counts     = inventory.collected_counts()
    violations = []

    for readme in inventory.count_carrying_readmes():
        folder = relative(readme.parent)
        for name, declared in inventory.readme_counts(readme).items():
            collected = counts.get(f"{folder}/{name}")
            if collected is None:
                violations.append(f"{relative(readme)}: {name} is not collected")
            elif collected != declared:
                violations.append(
                    f"{relative(readme)}: {name} says {declared}, "
                    f"collected {collected}")

    assert not violations, (
        "Declared test counts must match collection. Run "
        "`python -m tests.support.docs_inventory --update-counts`. "
        "Mismatches:\n" + _report(violations))


def test_declared_failure_counts_match_known_issues():
    """
    Every `Fail` count in a folder README matches `known_issues.py`.

    Counted from collected instances carrying the `known_issue` marker, so the
    column tracks the markers instead of being maintained by hand. A README
    once declared `0` for a file with a known failure, and stated "All tests
    expected to pass" beside it, while the release waited on that same failure.
    """
    failures   = inventory.known_failure_counts()
    violations = []

    for readme in inventory.count_carrying_readmes():
        folder = relative(readme.parent)
        for name, declared in inventory.readme_failure_counts(readme).items():
            collected = failures.get(f"{folder}/{name}")
            if collected is None:
                violations.append(f"{relative(readme)}: {name} is not collected")
            elif collected != declared:
                violations.append(
                    f"{relative(readme)}: {name} declares {declared} known "
                    f"failures, collection has {collected}")

    assert not violations, (
        "Declared failure counts must match the known_issue markers. Run "
        "`python -m tests.support.docs_inventory --update-counts`. "
        "Mismatches:\n" + _report(violations))


def test_folder_and_suite_totals_match_collection():
    """
    The Suite Total table in `tests/README.md` matches what pytest collects.

    Checks each folder row and the total. The same updater fixes a failure
    here, including the contribution of this file itself.
    """
    counts     = inventory.collected_counts()
    totals     = inventory.folder_totals(counts)
    readme     = (REPO_ROOT / "tests" / "README.md").read_text()
    violations = []

    for folder, collected in sorted(totals.items()):
        label = folder.removeprefix("tests/")
        match = re.search(rf"\| `{re.escape(label)}/`[^|]*\|\s*(\d+)\s*\|", readme)
        if match is None:
            violations.append(f"tests/README.md: no Suite Total row for {label}/")
        elif int(match.group(1)) != collected:
            violations.append(
                f"tests/README.md: {label}/ says {match.group(1)}, "
                f"collected {collected}")

    total = sum(counts.values())
    match = re.search(r"\| \*\*Total\*\* \| \*\*(\d+)\*\* \|", readme)
    if match is None:
        violations.append("tests/README.md: no Total row in the Suite Total table")
    elif int(match.group(1)) != total:
        violations.append(
            f"tests/README.md: Total says {match.group(1)}, collected {total}")

    assert not violations, (
        "Suite totals must match collection. Run "
        "`python -m tests.support.docs_inventory --update-counts`. "
        "Mismatches:\n" + _report(violations))
