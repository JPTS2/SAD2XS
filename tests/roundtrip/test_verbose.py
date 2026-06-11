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
import textwrap

import xtrack as xt

import sad2xs as s2x

################################################################################
# Helpers
################################################################################
def write_aperture_lattice(tmp_path):
    """
    Write a small SAD lattice containing one aperture element.
    """
    lattice_path = tmp_path / "aperture_lattice.sad"
    lattice_path.write_text(textwrap.dedent("""\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_D      = (L = 1.0);
        APERT       TEST_APERT  = (AX = 0.01 AY = 0.02);

        MARK        START       = ()
                    END         = ();

        LINE        RING        = (START TEST_D TEST_APERT END);
        """))

    return lattice_path

################################################################################
# Verbosity Behavior
################################################################################
def test_verbose_does_not_change_aperture_marker_conversion(tmp_path, capsys):
    """
    Aperture-to-marker conversion should not depend on `_verbose`.
    """
    lattice_path = write_aperture_lattice(tmp_path)

    line_quiet = s2x.convert_sad_to_xsuite(
        sad_lattice_path             = str(lattice_path),
        output_directory             = str(tmp_path),
        line_name                    = "RING",
        install_apertures_as_markers = True,
        _verbose                     = False,
        _test_mode                   = True)

    captured = capsys.readouterr()

    line_verbose = s2x.convert_sad_to_xsuite(
        sad_lattice_path             = str(lattice_path),
        output_directory             = str(tmp_path),
        line_name                    = "RING",
        install_apertures_as_markers = True,
        _verbose                     = True,
        _test_mode                   = True)

    assert captured.out == ""
    assert line_quiet.element_names == line_verbose.element_names
    assert isinstance(line_quiet["test_apert"], xt.Marker)
    assert isinstance(line_verbose["test_apert"], xt.Marker)
