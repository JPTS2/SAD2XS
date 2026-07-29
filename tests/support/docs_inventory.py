"""
================================================================================
Documentation Inventory
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
import subprocess
import sys
from pathlib import Path

from tests.support.known_issues import known_issue_for

################################################################################
# Paths
################################################################################
REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "tests"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

# Generated diagnostic reports: git-ignored, and not documentation.
EXCLUDED_PREFIXES = ("tests/artifacts/",)

# Every coverage table starts with these three columns, in this order. Later
# columns are free. Fixing the order is what lets a count be read by position
# instead of by "first cell that happens to be a number".
STANDARD_COLUMNS = ("File", "Tests", "Fail")


################################################################################
# Repository Contents
################################################################################
def tracked_files() -> set[str]:
    """
    Every file tracked by git, as repository-relative POSIX paths.

    Falls back to a filesystem walk when git is unavailable, for example in a
    source archive with no repository metadata. The fallback cannot detect an
    untracked file, so it is weaker, not equivalent.

    Returns
    -------
    set of str
        Repository-relative paths.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd             = REPO_ROOT,
            capture_output  = True,
            text            = True,
            check           = True)
        return set(result.stdout.split())
    except (OSError, subprocess.CalledProcessError):
        return {
            str(path.relative_to(REPO_ROOT).as_posix())
            for path in REPO_ROOT.rglob("*") if path.is_file()}


def doc_files() -> list[Path]:
    """
    Every tracked Markdown file that counts as documentation.

    Returns
    -------
    list of Path
        Absolute paths, sorted for deterministic test output.
    """
    return sorted(
        REPO_ROOT / name
        for name in tracked_files()
        if name.endswith(".md") and not name.startswith(EXCLUDED_PREFIXES))


def relative(path: Path) -> str:
    """
    Repository-relative POSIX form of a path, for readable failure messages.
    """
    return path.relative_to(REPO_ROOT).as_posix()


################################################################################
# Markdown Structure
################################################################################
def github_slug(heading: str) -> str:
    """
    Convert heading text into the anchor GitHub generates for it.

    GitHub lowercases, drops backticks and punctuation, then replaces each
    remaining space with a hyphen. It does not collapse repeated spaces and
    does not strip a trailing hyphen, so neither does this.

    Parameters
    ----------
    heading : str
        Heading text, without its leading `#` characters.

    Returns
    -------
    str
        The anchor, without a leading `#`.
    """
    slug = heading.strip().lower().replace("`", "")
    slug = re.sub(r"[^\w\s-]", "", slug)
    return slug.replace(" ", "-")


def headings(path: Path) -> list[tuple[int, str, str]]:
    """
    Every Markdown heading in a file.

    Returns
    -------
    list of tuple
        `(level, text, slug)` for each heading, in document order.
    """
    found = []
    for match in re.finditer(r"^(#{1,6})\s+(.*)$", path.read_text(), re.M):
        text = match.group(2).strip()
        found.append((len(match.group(1)), text, github_slug(text)))
    return found


def links(path: Path) -> list[tuple[str, int]]:
    """
    Every Markdown link target in a file, with its line number.

    External links (`http`, `mailto:`) are excluded: this module checks
    repository-internal references only.

    Returns
    -------
    list of tuple
        `(target, line_number)`, where target may carry an `#anchor`.
    """
    found = []
    for number, line in enumerate(path.read_text().splitlines(), start = 1):
        for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", line):
            target = match.group(1).strip()
            if not target.startswith(("http", "mailto:")):
                found.append((target, number))
    return found


################################################################################
# Citations
################################################################################
_CITED_PATH     = re.compile(
    r"`((?:docs|tests|sad2xs|examples|\.github)/[\w/.\-]+\.(?:md|py|sad|yml))`")

# YAML files are cited by bare filename, without their folder: `run_tests.yml`
# rather than `.github/workflows/run_tests.yml`.
_CITED_YAML = re.compile(r"`([\w.\-]+\.yml)`")

# Two prose forms name a section of another document:
#   `path.md` ("Section Name")        -- parenthetical, may wrap a line
#   `path.md`'s Section Name section  -- possessive, single line
# Both are length-bounded so an unclosed quote cannot swallow the rest of the
# file and report a nonsense section name.
_CITED_SECTION_PAREN = re.compile(
    r"`((?:docs|tests)/[\w/.\-]+\.md)`\s*\(\"([^\"]{1,120})\"", re.S)
_CITED_SECTION_POSS  = re.compile(
    r"`((?:docs|tests)/[\w/.\-]+\.md)`'s\s+([^\n]{1,60}?)\s+section")

_CITED_TEST_NAME = re.compile(r"`(test_[a-z0-9_]+)`")

# Backticked `test_*` names that are not tests: workflow inputs and similar.
NON_TEST_IDENTIFIERS = frozenset({"test_files", "test_template"})


def cited_paths(path: Path) -> list[tuple[str, int]]:
    """
    Every backticked repository file path in a document.

    A bare `*.yml` filename is resolved by basename against the tracked files,
    because YAML files are cited without their folder and do not all live in
    the same one: workflows sit under `.github/workflows/`, `environment.yml`
    at the repository root.

    Returns
    -------
    list of tuple
        `(cited_path, line_number)`.
    """
    tracked = tracked_files()
    by_name = {name.rsplit("/", 1)[-1]: name for name in tracked}

    found = []
    for number, line in enumerate(path.read_text().splitlines(), start = 1):
        found.extend((match.group(1), number) for match in _CITED_PATH.finditer(line))
        for match in _CITED_YAML.finditer(line):
            name = match.group(1)
            if "/" in name:
                continue                    # already matched by _CITED_PATH
            # Unresolvable names keep the workflow folder, so the failure
            # message names a plausible location rather than a bare filename.
            found.append(
                (by_name.get(name, f".github/workflows/{name}"), number))
    return found


def cited_sections(path: Path) -> list[tuple[str, str]]:
    """
    Every section of another document named in prose.

    Section names may wrap across lines, so the text is matched as a whole
    rather than line by line, and internal whitespace is normalised.

    Returns
    -------
    list of tuple
        `(document_path, section_name)`.
    """
    text  = path.read_text()
    found = []
    for pattern in (_CITED_SECTION_PAREN, _CITED_SECTION_POSS):
        for match in pattern.finditer(text):
            section = " ".join(match.group(2).split())
            found.append((match.group(1), section))
    return found


def cited_test_names(path: Path) -> list[tuple[str, int]]:
    """
    Every backticked `test_*` name in a document.

    Returns
    -------
    list of tuple
        `(name, line_number)`.
    """
    found = []
    for number, line in enumerate(path.read_text().splitlines(), start = 1):
        found.extend(
            (match.group(1), number)
            for match in _CITED_TEST_NAME.finditer(line)
            if match.group(1) not in NON_TEST_IDENTIFIERS)
    return found


################################################################################
# Coverage Tables
################################################################################
_TEST_FILE_CELL = re.compile(r"^`(test_[a-z0-9_]+\.py)`$")


def names_a_test_file(row: list[str]) -> bool:
    """
    Whether a table row's first cell names a test file.

    Distinguishes a coverage table from a table of helper modules, which
    carries no counts and is not held to the coverage-table column shape.
    """
    return bool(row) and bool(_TEST_FILE_CELL.match(row[0]))


def _cells(line: str) -> list[str]:
    """
    Cells of a Markdown table row, without the leading and trailing empties.
    """
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def coverage_tables(readme: Path) -> list[tuple[int, list[str], list[list[str]]]]:
    """
    Every coverage table in a folder README.

    A coverage table is any Markdown table whose first column header is `File`.
    Reading the header rather than guessing at column positions is what makes
    a mis-ordered table a detectable error instead of a silent misparse.

    Returns
    -------
    list of tuple
        `(header_line_number, header_cells, data_rows)` for each table.
    """
    lines  = readme.read_text().splitlines()
    tables = []

    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        header = _cells(line)
        if not header or header[0] != "File":
            continue

        rows   = []
        cursor = index + 2                              # skip the separator row
        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            rows.append(_cells(lines[cursor]))
            cursor += 1
        tables.append((index + 1, header, rows))

    return tables


def readme_counts(readme: Path) -> dict[str, int]:
    """
    Per-file test counts declared in a folder README's coverage table.

    The count is read from the `Tests` column by position, which
    `test_coverage_tables_have_the_standard_shape` pins to index 1.

    Returns
    -------
    dict
        Test file basename to declared count.
    """
    return _column_values(readme, STANDARD_COLUMNS.index("Tests"))


def readme_failure_counts(readme: Path) -> dict[str, int]:
    """
    Per-file known-failure counts declared in a folder README's coverage table.

    Returns
    -------
    dict
        Test file basename to declared failure count.
    """
    return _column_values(readme, STANDARD_COLUMNS.index("Fail"))


def _column_values(readme: Path, column: int) -> dict[str, int]:
    """
    Integer values of one column, keyed by the test file each row names.
    """
    declared = {}
    for _, header, rows in coverage_tables(readme):
        if len(header) <= column or header[column] != STANDARD_COLUMNS[column]:
            continue
        for row in rows:
            match = _TEST_FILE_CELL.match(row[0]) if row else None
            if match and len(row) > column and row[column].isdigit():
                declared[match.group(1)] = int(row[column])
    return declared


def count_carrying_readmes() -> list[Path]:
    """
    Folder READMEs that declare per-file test counts in a table.

    Returns
    -------
    list of Path
        Absolute paths, sorted.
    """
    return sorted(
        readme for readme in TESTS_DIR.rglob("README.md")
        if readme_counts(readme))


################################################################################
# Collection
################################################################################
_NODEIDS: list[str] | None = None


def collect_nodeids() -> list[str]:
    """
    Every test node pytest collects, as a node id.

    Runs collection in a subprocess. Collection imports test modules but runs
    no test, so the SAD executable is never invoked. The result is cached, so
    a test session runs collection once however many checks consume it.

    A non-zero exit status is an error, not a smaller collection. A module that
    fails to import still lets pytest report every other test, so without this
    check the counts updater would quietly write the deflated numbers into the
    READMEs and bake the breakage in.

    Returns
    -------
    list of str
        Collected node ids.
    """
    global _NODEIDS
    if _NODEIDS is not None:
        return _NODEIDS

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd             = REPO_ROOT,
        capture_output  = True,
        text            = True)

    if result.returncode != 0:
        raise RuntimeError(
            f"pytest collection failed with exit status {result.returncode}. "
            "Fix collection before trusting or updating any test count. "
            f"Output:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")

    nodeids = [line for line in result.stdout.splitlines() if "::" in line]

    if not nodeids:
        raise RuntimeError(
            "pytest collection returned no tests. Collection output:\n"
            f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}")

    _NODEIDS = nodeids
    return _NODEIDS


def collected_counts() -> dict[str, int]:
    """
    Test instances pytest collects, per test file.

    Returns
    -------
    dict
        Repository-relative test file path to instance count.
    """
    counts: dict[str, int] = {}
    for nodeid in collect_nodeids():
        path = nodeid.split("::")[0]
        counts[path] = counts.get(path, 0) + 1
    return counts


def known_failure_counts() -> dict[str, int]:
    """
    Collected instances carrying a known-issue marker, per test file.

    Counts collected instances rather than `KNOWN_ISSUES` entries, so a
    parametrised known failure contributes once per parametrisation, which is
    what a reader of a `Fail` column expects to see.

    Returns
    -------
    dict
        Repository-relative test file path to known-failure count.
    """
    counts: dict[str, int] = {}
    for nodeid in collect_nodeids():
        path = nodeid.split("::")[0]
        counts.setdefault(path, 0)
        if known_issue_for(nodeid) is not None:
            counts[path] += 1
    return counts


def folder_totals(counts: dict[str, int]) -> dict[str, int]:
    """
    Collected test instances per test folder.

    Returns
    -------
    dict
        Repository-relative folder path to instance count.
    """
    totals: dict[str, int] = {}
    for path, number in counts.items():
        folder = str(Path(path).parent.as_posix())
        totals[folder] = totals.get(folder, 0) + number
    return totals


################################################################################
# Count Updating
################################################################################
def update_counts() -> list[str]:
    """
    Rewrite every declared test and failure count to match what pytest collects.

    This is the writer half of `test_per_file_counts_match_collection` and
    `test_declared_failure_counts_match_known_issues`. Run it after adding or
    removing a test, rather than counting by hand.

    Returns
    -------
    list of str
        Repository-relative paths of the files that changed.
    """
    counts   = collected_counts()
    failures = known_failure_counts()
    changed  = []

    for readme in count_carrying_readmes():
        folder   = relative(readme.parent)
        original = readme.read_text()
        lines    = original.splitlines(keepends = True)

        for index, line in enumerate(lines):
            if not line.lstrip().startswith("|"):
                continue
            cells = _cells(line)
            match = _TEST_FILE_CELL.match(cells[0]) if cells else None
            if not match:
                continue
            key = f"{folder}/{match.group(1)}"
            if key not in counts:
                continue
            lines[index] = _rewrite_row(
                line, {
                    STANDARD_COLUMNS.index("Tests"): counts[key],
                    STANDARD_COLUMNS.index("Fail"):  failures.get(key, 0)})

        if (text := "".join(lines)) != original:
            readme.write_text(text)
            changed.append(relative(readme))

    if _update_totals(counts):
        changed.append("tests/README.md")

    return changed


def _rewrite_row(line: str, values: dict[int, int]) -> str:
    """
    Replace numeric cells of a table row by column index, preserving padding.
    """
    parts = line.split("|")
    # parts[0] is the text before the leading pipe, so data column N is at N+1.
    for column, value in values.items():
        position = column + 1
        if position >= len(parts) or not parts[position].strip().isdigit():
            continue
        parts[position] = parts[position].replace(
            parts[position].strip(), str(value), 1)
    return "|".join(parts)


def _update_totals(counts: dict[str, int]) -> bool:
    """
    Rewrite the Suite Total table in `tests/README.md`. Returns True if changed.

    Every substitution here must match exactly once. A pattern that matched
    nothing means the table was renamed and the total silently stopped being
    maintained; a pattern that matched twice means the substitution is reaching
    beyond the total it was written for and overwriting an unrelated number.
    """
    readme   = TESTS_DIR / "README.md"
    original = readme.read_text()
    totals   = folder_totals(counts)
    text     = original

    for folder, number in totals.items():
        label = folder.removeprefix("tests/")
        text  = _substitute_once(
            text,
            rf"(\| `{re.escape(label)}/`[^|]*\|\s*)\d+(\s*\|)",
            rf"\g<1>{number}\g<2>",
            f"Suite Total row for {label}/")

    total = sum(counts.values())
    text  = _substitute_once(
        text, r"(\*\*)\d+( tests\*\*)", rf"\g<1>{total}\g<2>",
        "headline test total")
    text  = _substitute_once(
        text, r"(\| \*\*Total\*\* \| \*\*)\d+(\*\* \|)", rf"\g<1>{total}\g<2>",
        "Suite Total table Total row")

    if text != original:
        readme.write_text(text)
        return True
    return False


def _substitute_once(text: str, pattern: str, replacement: str, what: str) -> str:
    """
    Substitute a pattern that must occur exactly once in `tests/README.md`.
    """
    occurrences = len(re.findall(pattern, text))
    if occurrences != 1:
        raise RuntimeError(
            f"The {what} in tests/README.md matched {occurrences} times, "
            "expected exactly 1. Updating it would corrupt the file, so no "
            "counts were written.")
    return re.sub(pattern, replacement, text)


################################################################################
# Command Line Entry Point
################################################################################
def main() -> int:
    """
    Update declared test counts in place.

    Usage: `python -m tests.support.docs_inventory --update-counts`
    """
    if "--update-counts" not in sys.argv:
        print(__doc__)
        print("Usage: python -m tests.support.docs_inventory --update-counts")
        return 1

    changed = update_counts()
    if changed:
        print("Updated test counts in:")
        for name in changed:
            print(f"  {name}")
    else:
        print("Test counts are already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
