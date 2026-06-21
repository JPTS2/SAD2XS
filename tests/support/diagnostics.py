"""
================================================================================
Test Diagnostic Report Helpers
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

################################################################################
# Report Paths
################################################################################
DEFAULT_ARTIFACT_ROOT = Path("tests") / "artifacts"

def slugify(value: object) -> str:
    """
    Convert a test name or parameter value into a deterministic file-safe slug.
    """
    slug = str(value).strip().lower()
    slug = slug.replace("+", "p").replace("-", "m").replace(".", "p")
    slug = re.sub(r"[^a-z0-9_]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "value"

def diagnostic_report_path(
        test_name: str,
        category: str | Path,
        parameters: Mapping[str, object] | None = None,
        artifact_root: str | Path = DEFAULT_ARTIFACT_ROOT) -> Path:
    """
    Build the deterministic Markdown report path for one test case.
    """
    report_name = slugify(test_name)

    if parameters:
        parameter_slug = "__".join(
            f"{slugify(key)}_{slugify(value)}"
            for key, value in sorted(parameters.items()))
        report_name = f"{report_name}__{parameter_slug}"

    return Path(artifact_root) / Path(category) / f"{report_name}.md"

################################################################################
# Formatting Helpers
################################################################################
def _format_value(value: object) -> str:
    """
    Format scalar values consistently for Markdown tables.
    """
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.12e}"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if value is None:
        return ""
    return str(value)

def _normalise_coordinate_map(
        coordinates: Mapping[str, Sequence[float] | np.ndarray]) -> dict[str, np.ndarray]:
    """
    Convert coordinate mappings to one-dimensional NumPy arrays.
    """
    return {
        name: np.atleast_1d(np.asarray(values, dtype = float))
        for name, values in coordinates.items()
    }

def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """
    Build a simple Markdown table.
    """
    header_row = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body_rows = [
        "| " + " | ".join(_format_value(value) for value in row) + " |"
        for row in rows
    ]
    return "\n".join([header_row, separator, *body_rows])

def _coordinate_rows(
        coordinates: Mapping[str, np.ndarray],
        coordinate_names: Sequence[str]) -> list[list[object]]:
    """
    Build particle-indexed coordinate rows.
    """
    n_rows = max(len(coordinates[name]) for name in coordinate_names)
    rows = []
    for idx in range(n_rows):
        rows.append([
            idx,
            *[
                coordinates[name][idx] if idx < len(coordinates[name]) else None
                for name in coordinate_names
            ],
        ])
    return rows

def _difference_rows(
        sad_coordinates: Mapping[str, np.ndarray],
        xsuite_coordinates: Mapping[str, np.ndarray],
        coordinate_names: Sequence[str]) -> list[list[object]]:
    """
    Build rows containing SAD, Xsuite, and difference values.
    """
    n_rows = max(len(sad_coordinates[name]) for name in coordinate_names)
    rows = []
    for idx in range(n_rows):
        row: list[object] = [idx]
        for name in coordinate_names:
            sad_value = sad_coordinates[name][idx]
            xsuite_value = xsuite_coordinates[name][idx]
            row.extend([sad_value, xsuite_value, xsuite_value - sad_value])
        rows.append(row)
    return rows

def _summary_rows(
        sad_coordinates: Mapping[str, np.ndarray],
        xsuite_coordinates: Mapping[str, np.ndarray],
        coordinate_names: Sequence[str],
        tolerances: Mapping[str, tuple[float, float]]) -> list[list[object]]:
    """
    Build coordinate-level tolerance summary rows.
    """
    rows = []
    for name in coordinate_names:
        sad_values = sad_coordinates[name]
        xsuite_values = xsuite_coordinates[name]
        differences = xsuite_values - sad_values
        atol, rtol = tolerances.get(name, (0.0, 0.0))
        passed = bool(np.all(np.isclose(
            sad_values,
            xsuite_values,
            atol = atol,
            rtol = rtol)))
        rows.append([
            name,
            np.max(np.abs(differences)),
            np.max(np.abs(differences) / np.maximum(np.abs(sad_values), atol)),
            atol,
            rtol,
            passed,
        ])
    return rows

def _write_report(path: Path, sections: Sequence[str]) -> Path:
    """
    Write a Markdown diagnostic report and return its path.
    """
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text("\n\n".join(section.rstrip() for section in sections) + "\n")
    return path

################################################################################
# Tracking Reports
################################################################################
def write_tracking_failure_report(
        report_path: str | Path,
        title: str,
        lattice_text: str,
        initial_coordinates: Mapping[str, Sequence[float] | np.ndarray],
        sad_coordinates: Mapping[str, Sequence[float] | np.ndarray],
        xsuite_coordinates: Mapping[str, Sequence[float] | np.ndarray],
        tolerances: Mapping[str, tuple[float, float]],
        parameters: Mapping[str, object] | None = None,
        notes: Sequence[str] | None = None) -> Path:
    """
    Write a self-contained Markdown report for a failed tracking comparison.
    """
    coordinate_names = [
        name for name in ["x", "px", "y", "py", "zeta", "delta"]
        if name in sad_coordinates and name in xsuite_coordinates
    ]
    initial_names = [
        name for name in ["x", "px", "y", "py", "zeta", "delta"]
        if name in initial_coordinates
    ]

    initial = _normalise_coordinate_map(initial_coordinates)
    sad = _normalise_coordinate_map(sad_coordinates)
    xsuite = _normalise_coordinate_map(xsuite_coordinates)

    difference_headers = ["i"]
    for name in coordinate_names:
        difference_headers.extend([f"sad_{name}", f"xsuite_{name}", f"diff_{name}"])

    sections = [
        f"# {title}",
        "## Parameters\n\n" + (
            _markdown_table(
                headers = ["name", "value"],
                rows = list(parameters.items()))
            if parameters else "No parameters supplied."),
        "## SAD Lattice\n\n```sad\n" + lattice_text.strip() + "\n```",
        "## Initial Coordinates\n\n" + _markdown_table(
            headers = ["i", *initial_names],
            rows = _coordinate_rows(initial, initial_names)),
        "## Final Coordinate Differences\n\n" + _markdown_table(
            headers = difference_headers,
            rows = _difference_rows(sad, xsuite, coordinate_names)),
        "## Tolerance Summary\n\n" + _markdown_table(
            headers = ["coord", "max_abs_diff", "max_scaled_diff", "atol", "rtol", "pass"],
            rows = _summary_rows(sad, xsuite, coordinate_names, tolerances)),
    ]

    if notes:
        sections.append(
            "## Notes\n\n" + "\n".join(f"- {note}" for note in notes))

    return _write_report(Path(report_path), sections)

################################################################################
# Twiss Reports
################################################################################
def write_twiss_failure_report(
        report_path: str | Path,
        title: str,
        lattice_text: str,
        sad_values: Mapping[str, float],
        xsuite_values: Mapping[str, float],
        tolerances: Mapping[str, tuple[float, float]],
        parameters: Mapping[str, object] | None = None,
        notes: Sequence[str] | None = None) -> Path:
    """
    Write a self-contained Markdown report for a failed Twiss comparison.
    """
    value_names = [
        name for name in sad_values
        if name in xsuite_values
    ]

    rows = []
    summary_rows = []
    for name in value_names:
        sad_value = float(sad_values[name])
        xsuite_value = float(xsuite_values[name])
        difference = xsuite_value - sad_value
        atol, rtol = tolerances.get(name, (0.0, 0.0))
        passed = bool(np.isclose(
            sad_value,
            xsuite_value,
            atol = atol,
            rtol = rtol))

        rows.append([name, sad_value, xsuite_value, difference])
        summary_rows.append([
            name,
            abs(difference),
            abs(difference) / max(abs(sad_value), atol),
            atol,
            rtol,
            passed,
        ])

    sections = [
        f"# {title}",
        "## Parameters\n\n" + (
            _markdown_table(
                headers = ["name", "value"],
                rows = list(parameters.items()))
            if parameters else "No parameters supplied."),
        "## SAD Lattice\n\n```sad\n" + lattice_text.strip() + "\n```",
        "## Twiss Values\n\n" + _markdown_table(
            headers = ["name", "sad", "xsuite", "diff"],
            rows = rows),
        "## Tolerance Summary\n\n" + _markdown_table(
            headers = ["name", "abs_diff", "scaled_diff", "atol", "rtol", "pass"],
            rows = summary_rows),
    ]

    if notes:
        sections.append(
            "## Notes\n\n" + "\n".join(f"- {note}" for note in notes))

    return _write_report(Path(report_path), sections)
