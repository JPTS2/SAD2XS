"""
(Unofficial) SAD to XSuite Converter: SAD Helpers Internal Utilities
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-24
"""

################################################################################
# Mathematica Output Guard
################################################################################
_MATHEMATICA_UNDEFINED = frozenset({
    "medium",
    "$DefaultFontWeight",
    "Indeterminate",
    "ComplexInfinity",
    "DirectedInfinity"})

def _check_mathematica_output(raw: str) -> None:
    found = [s for s in _MATHEMATICA_UNDEFINED if s in raw]
    if found:
        raise ValueError(
            f"SAD output contains Mathematica undefined symbols {found}. "
            f"The lattice configuration is physically degenerate "
            f"(SAD exited 0 but the computation failed). "
            f"SAD warnings should appear in the stdout above.")
