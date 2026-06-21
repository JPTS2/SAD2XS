"""
================================================================================
Tests for the convert_sad_to_xsuite public entry point
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
import sad2xs as s2x
import xtrack as xt

################################################################################
# Return Contract
################################################################################
def test_pipeline_entry_point_returns_xsuite_line(write_lattice):
    """
    convert_sad_to_xsuite should return an xt.Line when _test_mode is True.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 END);
        """,
        filename = "pipeline_returns_xsuite_line.sad")

    result = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert isinstance(result, xt.Line), (
        "convert_sad_to_xsuite should return an xt.Line when _test_mode is True.")


def test_pipeline_test_mode_does_not_write_output_files(write_lattice, tmp_path):
    """
    convert_sad_to_xsuite should not write any output files when _test_mode is True.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 END);
        """,
        filename = "pipeline_test_mode_no_files.sad")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        _verbose         = False,
        _test_mode       = True)

    written_files = list(output_dir.iterdir())

    assert len(written_files) == 0, (
        "convert_sad_to_xsuite should not write any output files when "
        f"_test_mode is True. Found: {[f.name for f in written_files]}.")


################################################################################
# Minimal Lattice Smoke Tests
################################################################################
def test_pipeline_markers_only_lattice_converts(write_lattice):
    """
    A SAD lattice containing only MARK elements should convert without error.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START END);
        """,
        filename = "pipeline_markers_only.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert isinstance(line, xt.Line), (
        "A markers-only SAD lattice should convert to an xt.Line.")
    assert "start" in line.element_names, (
        "Converted markers-only line should contain the 'start' marker.")
    assert "end" in line.element_names, (
        "Converted markers-only line should contain the 'end' marker.")


def test_pipeline_mark_drift_mark_lattice_converts(write_lattice):
    """
    A minimal mark-drift-mark SAD lattice should convert without error.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 END);
        """,
        filename = "pipeline_mark_drift_mark.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert isinstance(line, xt.Line), (
        "A mark-drift-mark SAD lattice should convert to an xt.Line.")
    assert line.element_names == ["start", "d1", "end"], (
        "Converted mark-drift-mark line should contain exactly the three "
        "expected elements in order.")


@pytest.mark.parametrize(
    "element_type, element_block",
    [
        (
            "DRIFT",
            "DRIFT       ELE     = (L = 1.0)",
        ),
        (
            "BEND",
            "BEND        ELE     = (L = 1.0 ANGLE = 0.01)",
        ),
        (
            "QUAD",
            "QUAD        ELE     = (L = 0.5 K1 = 0.1)",
        ),
        (
            "SEXT",
            "SEXT        ELE     = (L = 0.3 K2 = 0.1)",
        ),
        (
            "OCT",
            "OCT         ELE     = (L = 0.3 K3 = 0.1)",
        ),
        (
            "MULT",
            "MULT        ELE     = (L = 0.1 K0 = 0.001 K1 = 0.01)",
        ),
        (
            "CAVI",
            "CAVI        ELE     = (VOLT = 1000000 FREQ = 100000000)",
        ),
        (
            "SOL",
            "SOL         ELE     = (L = 0.5 BZ = 0.1)",
        ),
        (
            "MONI",
            "MONI        ELE     = ()",
        ),
        (
            "MARK",
            "MARK        ELE     = ()",
        ),
        (
            "APERT",
            "APERT       ELE     = (AX = 0.05 AY = 0.02)",
        ),
        (
            "BEAMBEAM",
            "BEAMBEAM    ELE     = ()",
        ),
    ])
def test_pipeline_single_element_type_lattice_converts(
        write_lattice,
        element_type,
        element_block):
    """
    A SAD lattice with a single core element type should convert without error.
    """
    lattice_path = write_lattice(
        f"""\
        MOMENTUM    = 1.0 GEV;

        {element_block};

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START ELE END);
        """,
        filename = f"pipeline_single_type_{element_type.lower()}.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert isinstance(line, xt.Line), (
        f"A SAD lattice with a single {element_type} element should convert "
        "to an xt.Line.")
    assert "ele" in line.element_names, (
        f"The converted line should contain the {element_type} element 'ele'.")


################################################################################
# All Allowed Element Types
################################################################################
def test_pipeline_lattice_with_all_allowed_element_types_converts(write_lattice):
    """
    A SAD lattice containing all SAD2XS-allowed element types should convert
    without error. COORD is excluded as it produces per-element transforms
    rather than a standalone Xsuite line element.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 0.5);
        BEND        B1      = (L = 1.0 ANGLE = 0.01);
        QUAD        Q1      = (L = 0.5 K1 = 0.1);
        SEXT        S1      = (L = 0.3 K2 = 0.1);
        OCT         O1      = (L = 0.3 K3 = 0.1);
        MULT        M1      = (L = 0.1 K0 = 0.001 K1 = 0.01);
        SOL         SOL1    = (L = 0.5 BZ = 0.1);
        CAVI        C1      = (VOLT = 1000000 FREQ = 100000000);
        MONI        MON1    = ();
        APERT       APT1    = (AX = 0.05 AY = 0.02);
        BEAMBEAM    BB1     = ();

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 B1 Q1 S1 O1 M1 SOL1 C1 MON1 APT1 BB1 END);
        """,
        filename = "pipeline_all_allowed_element_types.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert isinstance(line, xt.Line), (
        "A lattice with all allowed element types should convert to an xt.Line.")

    expected_names = [
        "start", "d1", "b1", "q1", "s1", "o1", "m1", "sol1", "c1",
        "mon1", "apt1", "bb1", "end"]

    for name in expected_names:
        assert name in line.element_names, (
            f"Converted all-types lattice should contain element '{name}'.")


################################################################################
# Element Names and Order
################################################################################
def test_pipeline_lowercases_sad_element_names(write_lattice):
    """
    SAD element names should appear as lowercase in the converted Xsuite line.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       UPPER_DRIFT = (L = 1.0);

        MARK        START       = ()
                    END         = ();

        LINE        TEST_LINE = (START UPPER_DRIFT END);
        """,
        filename = "pipeline_lowercases_names.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert all(name == name.lower() for name in line.element_names), (
        "All element names in the converted line should be lowercase. "
        f"Found non-lowercase names: "
        f"{[n for n in line.element_names if n != n.lower()]}.")
    assert "upper_drift" in line.element_names, (
        "SAD name 'UPPER_DRIFT' should appear as 'upper_drift' in the "
        "converted line.")


def test_pipeline_preserves_element_order(write_lattice):
    """
    Element order in the converted line should match the SAD LINE definition.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0)
                    D2      = (L = 2.0)
                    D3      = (L = 0.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 D2 D3 END);
        """,
        filename = "pipeline_preserves_element_order.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.element_names == ["start", "d1", "d2", "d3", "end"], (
        "Converted line element order should match the SAD LINE definition. "
        f"Got: {line.element_names}.")


################################################################################
# Element Type Mapping
################################################################################
@pytest.mark.parametrize(
    "element_block, element_name, expected_type, sad_keyword",
    [
        (
            "DRIFT       ELE     = (L = 1.0)",
            "ele",
            xt.Drift,
            "DRIFT",
        ),
        (
            "BEND        ELE     = (L = 1.0 ANGLE = 0.01)",
            "ele",
            xt.Bend,
            "BEND",
        ),
        (
            "QUAD        ELE     = (L = 0.5 K1 = 0.1)",
            "ele",
            xt.Quadrupole,
            "QUAD",
        ),
        (
            "SEXT        ELE     = (L = 0.3 K2 = 0.1)",
            "ele",
            xt.Sextupole,
            "SEXT",
        ),
        (
            "OCT         ELE     = (L = 0.3 K3 = 0.1)",
            "ele",
            xt.Octupole,
            "OCT",
        ),
        (
            "CAVI        ELE     = (VOLT = 1000000 FREQ = 100000000)",
            "ele",
            xt.Cavity,
            "CAVI",
        ),
        (
            "MARK        ELE     = ()",
            "ele",
            xt.Marker,
            "MARK",
        ),
        (
            "MONI        ELE     = ()",
            "ele",
            xt.Marker,
            "MONI",
        ),
        (
            "SOL         ELE     = (L = 0.5 BZ = 0.1)",
            "ele",
            xt.UniformSolenoid,
            "SOL",
        ),
        (
            "APERT       ELE     = (AX = 0.05 AY = 0.02)",
            "ele",
            xt.LimitEllipse,
            "APERT",
        ),
        (
            "BEAMBEAM    ELE     = ()",
            "ele",
            xt.Marker,
            "BEAMBEAM",
        ),
    ])
def test_pipeline_maps_sad_element_to_xsuite_type(
        write_lattice,
        element_block,
        element_name,
        expected_type,
        sad_keyword):
    """
    Each core SAD element type should map to the expected Xsuite element class.
    """
    lattice_path = write_lattice(
        f"""\
        MOMENTUM    = 1.0 GEV;

        {element_block};

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START ELE END);
        """,
        filename = f"pipeline_type_mapping_{sad_keyword.lower()}.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert element_name in line.element_names, (
        f"Converted line should contain the SAD {sad_keyword} element '{element_name}'.")
    assert isinstance(line[element_name], expected_type), (
        f"SAD {sad_keyword} should map to Xsuite {expected_type.__name__}. "
        f"Got {type(line[element_name]).__name__} instead.")


################################################################################
# Public Options
################################################################################
def test_pipeline_install_apertures_as_markers_preserves_same_name_mark(
        write_lattice):
    """
    install_apertures_as_markers should move APERT definitions into the marker
    collection without replacing an existing MARK with the same name.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        APERT       SHARED  = (AX = 0.05 AY = 0.02);

        MARK        START   = ()
                    SHARED  = ()
                    END     = ();

        LINE        TEST_LINE = (START SHARED END);
        """,
        filename = "pipeline_install_apertures_as_markers_precedence.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path              = str(lattice_path),
        output_directory              = "N/A",
        install_apertures_as_markers  = True,
        _verbose                      = False,
        _test_mode                    = True)

    assert line.element_names == ["start", "shared", "end"], (
        "install_apertures_as_markers should preserve the requested line order "
        f"when APERT and MARK share a name. Got: {line.element_names}.")
    assert isinstance(line["shared"], xt.Marker), (
        "When APERT and MARK share a name, install_apertures_as_markers should "
        "preserve the MARK definition instead of replacing it with an aperture.")


################################################################################
# Line Length
################################################################################
def test_pipeline_total_line_length_matches_sad(write_lattice):
    """
    The total length of the converted line should match the sum of SAD element lengths.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0)
                    D2      = (L = 2.0)
                    D3      = (L = 0.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 D2 D3 END);
        """,
        filename = "pipeline_total_length.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.get_length() == pytest.approx(3.5), (
        "Total converted line length should match the sum of SAD element lengths "
        "(1.0 + 2.0 + 0.5 = 3.5 m).")


def test_pipeline_individual_element_lengths_are_preserved(write_lattice):
    """
    Individual element lengths in the converted line should match SAD values.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       SHORT   = (L = 0.25)
                    MEDIUM  = (L = 1.5)
                    LONG    = (L = 3.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START SHORT MEDIUM LONG END);
        """,
        filename = "pipeline_individual_lengths.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line["short"].length == pytest.approx(0.25), (
        "Converted element 'short' should preserve its SAD length of 0.25 m.")
    assert line["medium"].length == pytest.approx(1.5), (
        "Converted element 'medium' should preserve its SAD length of 1.5 m.")
    assert line["long"].length == pytest.approx(3.0), (
        "Converted element 'long' should preserve its SAD length of 3.0 m.")


################################################################################
# Line Selection
################################################################################
def test_pipeline_auto_selects_only_defined_line(write_lattice):
    """
    When a single LINE is defined in the SAD file, it should be auto-selected.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0)
                    D2      = (L = 2.0);

        MARK        START   = ()
                    END     = ();

        LINE        MY_LINE = (START D1 D2 END);
        """,
        filename = "pipeline_auto_selects_only_line.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.element_names == ["start", "d1", "d2", "end"], (
        "When only one LINE is defined, the auto-selector should return that line. "
        f"Got element names: {line.element_names}.")


def test_pipeline_auto_selects_longest_line_from_multiple_definitions(write_lattice):
    """
    When multiple LINEs are defined, the longest by total length should be selected.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       SHORT_DRIFT = (L = 1.0)
                    LONG_DRIFT  = (L = 5.0);

        MARK        START       = ()
                    END         = ();

        LINE        SHORT_LINE  = (START SHORT_DRIFT END);
        LINE        LONG_LINE   = (START LONG_DRIFT END);
        """,
        filename = "pipeline_auto_selects_longest.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.get_length() == pytest.approx(5.0), (
        "The auto-selector should return the longest SAD LINE by total length. "
        "Expected LONG_LINE (5.0 m), not SHORT_LINE (1.0 m).")
    assert "long_drift" in line.element_names, (
        "The auto-selected line should contain 'long_drift', confirming "
        "LONG_LINE was chosen over SHORT_LINE.")


def test_pipeline_auto_selects_by_element_count_when_all_lines_zero_length(write_lattice):
    """
    When multiple LINEs all have zero total length, the one with the most
    elements should be selected.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        MARK        START   = ()
                    M1      = ()
                    M2      = ()
                    M3      = ()
                    END     = ();

        LINE        SHORT_LINE = (START M1 END);
        LINE        LONG_LINE  = (START M1 M2 M3 END);
        """,
        filename = "pipeline_auto_selects_by_element_count.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert "m3" in line.element_names, (
        "When all LINEs have zero length, the auto-selector should choose the "
        "line with the most elements. Expected LONG_LINE (5 elements) to be "
        "selected over SHORT_LINE (3 elements). "
        f"Got element names: {line.element_names}.")
    assert "m2" in line.element_names, (
        "Auto-selected line should contain 'm2', confirming LONG_LINE "
        "was chosen over SHORT_LINE.")


def test_pipeline_line_name_selects_requested_line(write_lattice):
    """
    An explicit line_name should select that SAD LINE instead of the automatic
    longest-line choice.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       SHORT_DRIFT = (L = 1.0)
                    LONG_DRIFT  = (L = 5.0);

        MARK        START       = ()
                    END         = ();

        LINE        SHORT_LINE  = (START SHORT_DRIFT END);
        LINE        LONG_LINE   = (START LONG_DRIFT END);
        """,
        filename = "pipeline_line_name_selects_requested.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "SHORT_LINE",
        _verbose         = False,
        _test_mode       = True)

    assert line.get_length() == pytest.approx(1.0), (
        "line_name='SHORT_LINE' should select SHORT_LINE even though LONG_LINE "
        "is longer. Expected length 1.0 m.")
    assert line.element_names == ["start", "short_drift", "end"], (
        "line_name='SHORT_LINE' should return the explicitly requested line. "
        f"Got element names: {line.element_names}.")


################################################################################
# Output and Reload
################################################################################
def test_pipeline_output_filename_controls_generated_file_names(
        write_lattice,
        tmp_path):
    """
    output_filename should control the generated lattice and optics filenames.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 END);
        """,
        filename = "pipeline_output_filename_input.sad")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        output_filename  = "custom_output_name",
        _verbose         = False)

    expected_files = {
        "custom_output_name.py",
        "custom_output_name_import_optics.py",
    }
    written_files = {path.name for path in output_dir.iterdir()}

    assert expected_files.issubset(written_files), (
        "output_filename should control the generated lattice and optics file "
        f"names. Expected at least {sorted(expected_files)}, got "
        f"{sorted(written_files)}.")


def test_pipeline_write_reload_preserves_test_mode_line_contract(
        write_lattice,
        tmp_path):
    """
    The non-test-mode write/reload path should return the same line contract as
    the pre-writer _test_mode path for a simple lattice.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);
        QUAD        Q1      = (L = 0.5 K1 = 0.2);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 Q1 END);
        """,
        filename = "pipeline_write_reload_equivalence.sad")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    line_test_mode = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        output_filename  = "reload_equivalence",
        _verbose         = False,
        _test_mode       = True)

    line_reloaded = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        output_filename  = "reload_equivalence",
        _verbose         = False)

    assert line_reloaded.element_names == line_test_mode.element_names, (
        "The write/reload path should preserve converted line element names. "
        f"Test mode: {line_test_mode.element_names}; reloaded: "
        f"{line_reloaded.element_names}.")
    assert line_reloaded.get_length() == pytest.approx(line_test_mode.get_length()), (
        "The write/reload path should preserve total line length.")
    assert line_reloaded.particle_ref.p0c[0] == pytest.approx(
        line_test_mode.particle_ref.p0c[0]), (
        "The write/reload path should preserve reference particle p0c.")

    for element_name in line_test_mode.element_names:
        assert type(line_reloaded[element_name]) is type(line_test_mode[element_name]), (
            "The write/reload path should preserve element classes. "
            f"Element '{element_name}' was {type(line_test_mode[element_name]).__name__} "
            f"in test mode and {type(line_reloaded[element_name]).__name__} "
            "after reload.")


def test_pipeline_generated_lattice_file_imports_into_xsuite_environment(
        write_lattice,
        tmp_path):
    """
    The generated lattice file should be loadable by a clean Xsuite Environment.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);
        QUAD        Q1      = (L = 0.5 K1 = 0.2);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 Q1 END);
        """,
        filename = "pipeline_generated_lattice_import_input.sad")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        output_filename  = "generated_lattice_import",
        _verbose         = False)

    generated_lattice_path = output_dir / "generated_lattice_import.py"

    env = xt.Environment()
    env.call(str(generated_lattice_path))

    assert "line" in env.lines, (
        "Generated lattice file should define an Xsuite line named 'line'.")
    assert env.lines["line"].element_names == ["start", "d1", "q1", "end"], (
        "Generated lattice file should preserve converted line element names "
        "when loaded into a clean Xsuite Environment.")


def test_pipeline_generated_optics_file_imports_after_generated_lattice(
        write_lattice,
        tmp_path):
    """
    The generated optics file should be loadable after the generated lattice file.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);
        CAVI        C1      = (VOLT = 1000000 FREQ = 100000000);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 C1 END);
        """,
        filename = "pipeline_generated_optics_import_input.sad")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        output_filename  = "generated_optics_import",
        _verbose         = False)

    generated_lattice_path = output_dir / "generated_optics_import.py"
    generated_optics_path = output_dir / "generated_optics_import_import_optics.py"

    env = xt.Environment()
    env.call(str(generated_lattice_path))
    env.call(str(generated_optics_path))
    line = env.lines["line"]

    assert line.particle_ref is not None, (
        "Generated optics file should restore the line reference particle.")
    assert line.particle_ref.p0c[0] == pytest.approx(1.0E9), (
        "Generated optics file should restore the SAD MOMENTUM as p0c.")
    assert line["c1"].voltage == pytest.approx(1000000), (
        "Generated optics file should preserve cavity voltage after import.")
    assert line["c1"].frequency == pytest.approx(100000000), (
        "Generated optics file should preserve cavity frequency after import.")


def test_pipeline_verbose_does_not_change_conversion_result(
        write_lattice,
        tmp_path,
        capsys):
    """
    Verbose logging should not change the converted line contract.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       TEST_D      = (L = 1.0);
        APERT       TEST_APERT  = (AX = 0.01 AY = 0.02);

        MARK        START       = ()
                    END         = ();

        LINE        RING        = (START TEST_D TEST_APERT END);
        """,
        filename = "pipeline_verbose_invariance.sad")

    line_quiet = s2x.convert_sad_to_xsuite(
        sad_lattice_path             = str(lattice_path),
        output_directory             = str(tmp_path),
        line_name                    = "RING",
        install_apertures_as_markers = True,
        _verbose                     = False,
        _test_mode                   = True)

    quiet_output = capsys.readouterr()

    line_verbose = s2x.convert_sad_to_xsuite(
        sad_lattice_path             = str(lattice_path),
        output_directory             = str(tmp_path),
        line_name                    = "RING",
        install_apertures_as_markers = True,
        _verbose                     = True,
        _test_mode                   = True)

    verbose_output = capsys.readouterr()

    assert quiet_output.out == "", (
        "Quiet conversion should not write to stdout.")
    assert verbose_output.out != "", (
        "Verbose conversion should write diagnostic progress to stdout.")
    assert line_quiet.element_names == line_verbose.element_names, (
        "Verbose logging should not change converted element names.")
    assert isinstance(line_quiet["test_apert"], xt.Marker), (
        "Quiet conversion should install APERT as Marker when requested.")
    assert isinstance(line_verbose["test_apert"], xt.Marker), (
        "Verbose conversion should install APERT as Marker when requested.")


################################################################################
# Reference Particle
################################################################################
def test_pipeline_attaches_reference_particle_to_line(write_lattice):
    """
    The converted line should have a reference particle attached with the
    p0c field used by SAD2XS. Field values are tested in test_reference_particle.py.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 END);
        """,
        filename = "pipeline_reference_particle_attached.sad")

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        _verbose         = False,
        _test_mode       = True)

    assert line.particle_ref is not None, (
        "The converted line should have a reference particle attached.")
    assert hasattr(line.particle_ref, "p0c"), (
        "The reference particle should expose the p0c field used by SAD2XS.")
