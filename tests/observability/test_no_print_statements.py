"""
================================================================================
Tests enforcing the SAD2XS terminal output policy at source level
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-04
================================================================================

All package terminal output goes through the sad2xs logger. A print() call
anywhere in the package bypasses the level control and quiet mode; runtime
tests only catch prints on code paths their lattices exercise, so this scans
every source file instead. (print statements inside generated-file string
templates are string literals, not call nodes, and pass the scan naturally.)
"""
################################################################################
# Required Packages
################################################################################
import ast
import pathlib

import sad2xs

################################################################################
# Source Scan
################################################################################
def test_no_print_calls_in_package():
    """
    No sad2xs module may call print(): use the module logger instead
    (see docs/contributing.md, "Terminal output policy").
    """
    package_root = pathlib.Path(sad2xs.__file__).parent

    offenders = []
    for path in sorted(package_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding = "utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"):
                offenders.append(
                    f"{path.relative_to(package_root)}:{node.lineno}")

    assert offenders == [], (
        "print() calls found in the sad2xs package — route output through "
        "the module logger (logging.getLogger(__name__)) instead: "
        f"{offenders}")
