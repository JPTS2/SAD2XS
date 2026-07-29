"""
================================================================================
Tests for docstring and module header coverage
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
import ast
import re
from datetime import date
from pathlib import Path

from tests.support.docs_inventory import REPO_ROOT, relative, tracked_files

################################################################################
# Test Parameters
#
# Both checks walk every tracked Python file and report the complete list of
# violations, so one failure names every offender rather than the first.
################################################################################
SOURCE_ROOTS = ("sad2xs/", "tests/")

# The standard module header, as every file in the project carries it.
_HEADER_FIELDS = re.compile(
    r"Authors:\s*\S.*\nEmail:\s*\S.*\nDate:\s*(\S+)", re.M)


################################################################################
# Helpers
################################################################################
def _report(violations: list[str]) -> str:
    """
    Format violations as an indented block for an assertion message.
    """
    return "\n".join(f"  {line}" for line in violations)


def source_files() -> list[Path]:
    """
    Every tracked Python file in the package and the test suite.

    Returns
    -------
    list of Path
        Absolute paths, sorted for deterministic test output.
    """
    return sorted(
        REPO_ROOT / name
        for name in tracked_files()
        if name.endswith(".py") and name.startswith(SOURCE_ROOTS))


def documented_definitions(tree: ast.Module) -> list[ast.AST]:
    """
    Every definition in a module that is required to carry a docstring.

    Top-level functions and classes, plus the methods of those classes. A
    function nested inside another function is excluded: fixtures and closures
    are read together with the code around them, and requiring a docstring on
    each one adds words without adding meaning.

    Parameters
    ----------
    tree : ast.Module
        The parsed module.

    Returns
    -------
    list of ast.AST
        The definition nodes, in source order.
    """
    definitions = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.append(node)
        if isinstance(node, ast.ClassDef):
            definitions.extend(
                member for member in node.body
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)))
    return definitions


################################################################################
# Module Headers
################################################################################
def test_every_module_carries_the_standard_header():
    """
    Every Python file opens with the project's `Authors`/`Email`/`Date` header.

    The header states who to ask about a file and when it last changed. A file
    added without one loses both, and nothing else in the suite would notice.
    """
    violations = []

    for source in source_files():
        docstring = ast.get_docstring(ast.parse(source.read_text()))
        if docstring is None:
            violations.append(f"{relative(source)}: no module docstring")
        elif not _HEADER_FIELDS.search(docstring):
            violations.append(
                f"{relative(source)}: docstring has no Authors/Email/Date block")

    assert not violations, (
        "Every module must carry the standard header. Missing headers:\n"
        + _report(violations))


def test_every_module_header_date_is_an_iso_date():
    """
    Every header `Date:` is a real date in `YYYY-MM-DD` form.

    The field is maintained by hand, so the format is what can be checked. A
    date written another way still reads, but stops sorting and comparing.
    """
    violations = []

    for source in source_files():
        docstring = ast.get_docstring(ast.parse(source.read_text())) or ""
        match     = _HEADER_FIELDS.search(docstring)
        if match is None:
            continue                        # reported by the header test above
        try:
            date.fromisoformat(match.group(1))
        except ValueError:
            violations.append(f"{relative(source)}: Date is {match.group(1)!r}")

    assert not violations, (
        "Every header Date must be an ISO YYYY-MM-DD date. Malformed dates:\n"
        + _report(violations))


################################################################################
# Docstrings
################################################################################
def test_every_definition_has_a_docstring():
    """
    Every top-level function, class, and method carries a docstring.

    Nested functions are exempt. Test bodies are the other large exemption:
    a test's own docstring is checked here, but the helpers defined inside it
    are not.
    """
    violations = []

    for source in source_files():
        tree = ast.parse(source.read_text())
        for node in documented_definitions(tree):
            if ast.get_docstring(node) is None:
                violations.append(
                    f"{relative(source)}:{node.lineno}: {node.name}")

    assert not violations, (
        "Every top-level function, class, and method must have a docstring. "
        "Missing docstrings:\n" + _report(violations))
