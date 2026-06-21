"""
================================================================================
Tests for SAD2XS public import boundaries
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
import types

import sad2xs

################################################################################
# Public API — presence
################################################################################
def test_import_boundary_convert_sad_to_xsuite_is_importable():
    """
    convert_sad_to_xsuite is the primary user-facing entry point. It must be
    importable directly from the top-level sad2xs namespace.
    """
    assert hasattr(sad2xs, "convert_sad_to_xsuite"), (
        "'convert_sad_to_xsuite' should be accessible at the sad2xs top level.")


def test_import_boundary_write_lattice_is_importable():
    """
    write_lattice is a public writer entry point. It must be importable from
    the top-level namespace so users can call it without importing internals.
    """
    assert hasattr(sad2xs, "write_lattice"), (
        "'write_lattice' should be accessible at the sad2xs top level.")


def test_import_boundary_write_optics_is_importable():
    """
    write_optics is a public writer entry point. It must be importable from
    the top-level namespace.
    """
    assert hasattr(sad2xs, "write_optics"), (
        "'write_optics' should be accessible at the sad2xs top level.")


def test_import_boundary_sad_helpers_namespace_is_importable():
    """
    sad_helpers is the public namespace for SAD execution helpers. It must be
    accessible as a sub-namespace from the top-level import.
    """
    assert hasattr(sad2xs, "sad_helpers"), (
        "'sad_helpers' should be accessible as sad2xs.sad_helpers.")


################################################################################
# Public API — callability
################################################################################
def test_import_boundary_convert_sad_to_xsuite_is_callable():
    """
    convert_sad_to_xsuite must be callable, not a module, class, or constant.
    """
    assert callable(sad2xs.convert_sad_to_xsuite), (
        "sad2xs.convert_sad_to_xsuite should be callable.")


def test_import_boundary_write_lattice_is_callable():
    """
    write_lattice must be callable.
    """
    assert callable(sad2xs.write_lattice), (
        "sad2xs.write_lattice should be callable.")


def test_import_boundary_write_optics_is_callable():
    """
    write_optics must be callable.
    """
    assert callable(sad2xs.write_optics), (
        "sad2xs.write_optics should be callable.")


def test_import_boundary_sad_helpers_is_a_module():
    """
    sad_helpers must be a module so users can access helpers via attribute
    access (sad2xs.sad_helpers.twiss_sad etc.) rather than as a flat import.
    """
    assert isinstance(sad2xs.sad_helpers, types.ModuleType), (
        "sad2xs.sad_helpers should be a module, not a class or function.")
