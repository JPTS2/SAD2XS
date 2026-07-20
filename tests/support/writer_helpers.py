"""
================================================================================
Shared write+reload helper for writer test modules
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-17
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import xtrack as xt

import sad2xs as s2x
from sad2xs.config import Config

################################################################################
# Write + Reload
################################################################################
def write_and_load(line, tmp_path, output_header = "Writer test", offset_marker_locations = None):
    """
    Write a line using the public SAD2XS writer entry points, reload it in a
    clean Xsuite environment, and return the environment and reloaded line.

    Returning the environment allows tests to inspect and modify optics
    variables, which verifies that strength parameters are written as live
    deferred expressions rather than baked-in constants.

    Pass offset_marker_locations to test the offset-marker insertion mechanism.
    """
    output_dir = tmp_path / "writer_output"
    output_dir.mkdir()

    s2x.write_lattice(
        line                    = line,
        output_filename         = "test_lattice",
        output_directory        = str(output_dir),
        output_header           = output_header,
        offset_marker_locations = offset_marker_locations,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = "test_lattice_import_optics",
        output_directory  = str(output_dir),
        output_header     = output_header,
        config            = Config(_verbose = False))

    env = xt.Environment()
    env.call(str(output_dir / "test_lattice.py"))
    env.call(str(output_dir / "test_lattice_import_optics.py"))

    return env, env.lines["line"]

def writer_roundtrip(line, tmp_path, output_header = "Writer test"):
    """
    Write and reload a line. Returns the reloaded line only.
    """
    _, reloaded_line = write_and_load(line, tmp_path, output_header)
    return reloaded_line
