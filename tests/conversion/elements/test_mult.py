"""
================================================================================
Tests for SAD parser comment handling
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-11
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import xtrack as xt

from sad2xs.config import Config
from sad2xs.converter._004_element_converter import convert_multipoles

################################################################################
# Thin Multipole Replacement Errors
################################################################################
@pytest.mark.parametrize(
    "element_variables",
    [
        {"k1": "0.01"},
        {"l": "0", "k1": "0.01"},
    ])
def test_thin_multipole_replacement_raises_clear_error(element_variables):
    """
    A thin SAD MULT cannot currently be replaced by a thick element type.

    The replacement path divides integrated multipole strengths by the element
    length. Missing and zero lengths should therefore fail before any division is
    attempted.
    """
    parsed_elements = {
        "mult": {
            "test_mult": element_variables,
        },
    }

    with pytest.raises(ValueError, match = "Cannot replace thin SAD multipole"):
        convert_multipoles(
            parsed_elements              = parsed_elements,
            environment                  = xt.Environment(),
            user_multipole_replacements  = {"test": "Quadrupole"},
            config                       = Config(_verbose = False))
