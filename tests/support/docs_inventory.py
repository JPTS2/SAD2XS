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

################################################################################
# Paths
################################################################################
REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "tests"

# Generated diagnostic reports: git-ignored, and not documentation.
EXCLUDED_PREFIXES = ("tests/artifacts/",)

################################################################################
# External Names
#
# Backticked identifiers that are deliberately not defined in this repository.
# Anything not listed here must resolve, so a renamed internal symbol fails the
# documentation tests rather than going stale.
################################################################################
EXTERNAL_IDENTIFIERS = frozenset({
    "copy_from_env", "cpymad", "ks_profile", "radiation_flag", "xfail",
    "__cause__", "tcavfrin", "ttfrin", "tthin", "p_phi", "x_corr",
    "alfx2", "alfy1", "betx2", "bety1"})


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
    r"`((?:docs|tests|sad2xs|examples)/[\w/.\-]+\.(?:md|py|sad))`")

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

    Returns
    -------
    list of tuple
        `(cited_path, line_number)`.
    """
    found = []
    for number, line in enumerate(path.read_text().splitlines(), start = 1):
        found.extend((match.group(1), number) for match in _CITED_PATH.finditer(line))
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
# Test Counts
################################################################################
_README_COUNT_ROW = re.compile(r"^\s*\|\s*`(test_[a-z0-9_]+\.py)`\s*\|(.*)$")


def collected_counts() -> dict[str, int]:
    """
    Test instances pytest collects, per test file.

    Runs collection in a subprocess. Collection imports test modules but runs
    no test, so the SAD executable is never invoked.

    Returns
    -------
    dict
        Repository-relative test file path to instance count.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd             = REPO_ROOT,
        capture_output  = True,
        text            = True)

    counts: dict[str, int] = {}
    for line in result.stdout.splitlines():
        if "::" not in line:
            continue
        counts[line.split("::")[0]] = counts.get(line.split("::")[0], 0) + 1

    if not counts:
        raise RuntimeError(
            "pytest collection returned no tests. Collection output:\n"
            f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}")

    return counts


def readme_counts(readme: Path) -> dict[str, int]:
    """
    Per-file test counts declared in a folder README's coverage table.

    The count is the first numeric column of each table row naming a test
    file, which is the Tests column in every folder README.

    Returns
    -------
    dict
        Test file basename to declared count.
    """
    declared = {}
    for line in readme.read_text().splitlines():
        match = _README_COUNT_ROW.match(line)
        if not match:
            continue
        numbers = [cell.strip() for cell in match.group(2).split("|")
                   if cell.strip().isdigit()]
        if numbers:
            declared[match.group(1)] = int(numbers[0])
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
# Count Updating
################################################################################
def update_counts() -> list[str]:
    """
    Rewrite every declared test count to match what pytest collects.

    This is the writer half of `test_per_file_counts_match_collection`. Run it
    after adding or removing a test, rather than counting by hand.

    Returns
    -------
    list of str
        Repository-relative paths of the files that changed.
    """
    counts  = collected_counts()
    changed = []

    for readme in count_carrying_readmes():
        folder   = relative(readme.parent)
        original = readme.read_text()
        updated  = []

        for line in original.splitlines(keepends = True):
            match = _README_COUNT_ROW.match(line)
            if match and f"{folder}/{match.group(1)}" in counts:
                collected = counts[f"{folder}/{match.group(1)}"]
                cells     = line.split("|")
                for index, cell in enumerate(cells):
                    if cell.strip().isdigit():
                        cells[index] = cell.replace(cell.strip(), str(collected), 1)
                        break
                line = "|".join(cells)
            updated.append(line)

        if (text := "".join(updated)) != original:
            readme.write_text(text)
            changed.append(relative(readme))

    if _update_totals(counts):
        changed.append("tests/README.md")

    return changed


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


def _update_totals(counts: dict[str, int]) -> bool:
    """
    Rewrite the Suite Total table in `tests/README.md`. Returns True if changed.
    """
    readme   = TESTS_DIR / "README.md"
    original = readme.read_text()
    totals   = folder_totals(counts)
    text     = original

    for folder, number in totals.items():
        label = folder.removeprefix("tests/")
        text  = re.sub(
            rf"(\| `{re.escape(label)}/`[^|]*\|\s*)\d+(\s*\|)",
            rf"\g<1>{number}\g<2>", text)

    total = sum(counts.values())
    text  = re.sub(r"(\*\*)\d+( tests\*\*)", rf"\g<1>{total}\g<2>", text)
    text  = re.sub(r"(\| \*\*Total\*\* \| \*\*)\d+(\*\* \|)", rf"\g<1>{total}\g<2>", text)

    if text != original:
        readme.write_text(text)
        return True
    return False


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
