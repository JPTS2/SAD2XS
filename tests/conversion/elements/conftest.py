"""
================================================================================
Shared fixtures for SAD element conversion tests
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the MIT License.
See LICENSE.txt for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-12
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import textwrap

import pytest
import xtrack as xt

from sad2xs.config import Config

################################################################################
# File Fixtures
################################################################################
@pytest.fixture
def write_lattice(tmp_path):
    """
    Write a temporary SAD lattice file for conversion tests.
    """
    def _write_lattice(content, filename = "test_lattice.sad"):
        lattice_path = tmp_path / filename
        lattice_path.write_text(textwrap.dedent(content))
        return lattice_path

    return _write_lattice

################################################################################
# Converter Fixtures
################################################################################
@pytest.fixture
def sad2xs_config():
    """
    Return a quiet SAD2XS config suitable for deterministic unit tests.
    """
    return Config(_verbose = False)

@pytest.fixture
def xsuite_environment():
    """
    Return an empty Xsuite environment for direct element converter tests.
    """
    return xt.Environment()

@pytest.fixture
def parsed_elements():
    """
    Build a minimal parsed-elements dictionary for one SAD element type.
    """
    def _parsed_elements(element_type, element_name, element_variables = None):
        if element_variables is None:
            element_variables = {}

        return {
            element_type: {
                element_name: element_variables,
            },
        }

    return _parsed_elements

################################################################################
# Assertion Fixtures
################################################################################
@pytest.fixture
def assert_environment_element():
    """
    Assert that an Xsuite environment contains an element of the expected type.
    """
    def _assert_environment_element(environment, element_name, element_type):
        assert element_name in environment.element_dict, (
            f"Expected element '{element_name}' to be present in the Xsuite "
            "environment.")
        assert isinstance(environment.element_dict[element_name], element_type), (
            f"Expected element '{element_name}' to be a "
            f"{element_type.__name__}.")
        return environment.element_dict[element_name]

    return _assert_environment_element
