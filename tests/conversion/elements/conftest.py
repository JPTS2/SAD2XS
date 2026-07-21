"""
================================================================================
Shared fixtures for SAD element conversion tests
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-06-21
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import xtrack as xt

from sad2xs.sad_helpers import rebuild_sad_lattice

################################################################################
# SAD Rebuild Fixture
################################################################################
@pytest.fixture
def rebuild_lattice(tmp_path):
    """
    Rebuild a SAD lattice via SAD and return the rebuilt file path.

    Runs rebuild_sad_lattice on the given lattice_path and returns a Path to the
    rebuilt file. Must be called after os.chdir(tmp_path) so that SAD's relative
    file references resolve correctly.
    """
    def _rebuild_lattice(lattice_path, line_name = "TEST_LINE"):
        rebuilt_name = lattice_path.name.replace(".sad", "_rebuilt.sad")
        rebuild_sad_lattice(
            lattice_filepath = lattice_path.name,
            line_name        = line_name,
            output_filepath  = rebuilt_name)
        return tmp_path / rebuilt_name

    return _rebuild_lattice

################################################################################
# Converter Fixtures
################################################################################
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
            f"Expected element `{element_name}` to be present in the Xsuite "
            "environment.")
        assert isinstance(environment.element_dict[element_name], element_type), (
            f"Expected element `{element_name}` to be a "
            f"{element_type.__name__}.")
        return environment.element_dict[element_name]

    return _assert_environment_element
