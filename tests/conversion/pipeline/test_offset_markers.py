"""
================================================================================
Tests for offset marker handling in the SAD2XS conversion pipeline
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-15
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import pytest
import sad2xs as s2x

################################################################################
# Default Behaviour
################################################################################
def test_pipeline_offset_marker_absent_without_offset_parameter(write_lattice, tmp_path):
    """
    A SAD MARK element with no OFFSET parameter should remain in the converted
    line at its original s-position. The absence of OFFSET is the selector:
    only markers that carry an OFFSET parameter are removed and reinserted.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 2.0);
        DRIFT       D2      = (L = 2.0);

        MARK        M1      = ();

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 M1 D2 END);
        """,
        filename = "offset_marker_default.sad")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        _verbose         = False)

    assert "m1" in list(line.element_names), (
        "A SAD MARK without an OFFSET parameter should remain in the converted "
        f"line. Got: {list(line.element_names)}.")


################################################################################
# MARK Element Offset
################################################################################
def test_pipeline_offset_marker_mark_moved_to_computed_s_position(write_lattice, tmp_path):
    """
    A SAD MARK with OFFSET = 1.5 (Case 2: OFFSET > 1) should be removed from
    its original position and reinserted at the computed s-position inside the
    following element. With the marker immediately before D2 (L = 2.0), the
    computed position is s(D2) + 2.0 * 0.5 = 3.0. D2 is split at the insertion
    point, confirming the marker was placed inside the element rather than at
    its boundary.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 2.0);
        DRIFT       D2      = (L = 2.0);

        MARK        M1      = (OFFSET = 1.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 M1 D2 END);
        """,
        filename = "offset_marker_mark_case2.sad")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        _verbose         = False)

    tt = line.get_table(attr = True)

    assert "m1" in list(line.element_names), (
        "A SAD MARK with OFFSET = 1.5 should be reinserted at the computed "
        f"s-position. Got: {list(line.element_names)}.")
    assert tt["s", "m1"] == pytest.approx(3.0), (
        "With OFFSET = 1.5, M1 should be reinserted at s = s(D2) + L(D2) * 0.5 "
        f"""= 2.0 + 1.0 = 3.0. Got: {tt["s", "m1"]:.6f}.""")
    assert "d2..0" in list(line.element_names), (
        "D2 should be split at the marker insertion point, producing `d2..0`. "
        f"Got: {list(line.element_names)}.")


################################################################################
# Fractional Offset Below One (Case 1: marker stays in place)
################################################################################
def test_pipeline_offset_marker_fractional_offset_below_one_stays_in_place(
        write_lattice, tmp_path):
    """
    A SAD MARK with 0 <= OFFSET < 1 (Case 1) should stay at its own nominal
    s-position -- confirmed against real SAD (survey_sad): a marker with
    OFFSET = 0.5 lands at the exact same s as one with no OFFSET at all, not
    50% into the following element. With M1 immediately before D2 (L = 2.0,
    starting at s = 2.0), the nominal and expected position is s = 2.0.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 2.0);
        DRIFT       D2      = (L = 2.0);

        MARK        M1      = (OFFSET = 0.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 M1 D2 END);
        """,
        filename = "offset_marker_case1_fractional.sad")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        _verbose         = False)

    tt = line.get_table(attr = True)

    assert "m1" in list(line.element_names), (
        "A SAD MARK with OFFSET = 0.5 should remain in the converted line. "
        f"Got: {list(line.element_names)}.")
    assert tt["s", "m1"] == pytest.approx(2.0), (
        "With OFFSET = 0.5 (Case 1), M1 should stay at its own nominal "
        f"""s = 2.0, not move into D2. Got: {tt["s", "m1"]:.6f}.""")
    assert "d2..0" not in list(line.element_names), (
        "A Case 1 offset marker should never split the following element. "
        f"Got: {list(line.element_names)}.")


def test_pipeline_offset_marker_offset_exactly_one_stays_in_place(
        write_lattice, tmp_path):
    """
    OFFSET = 1.0 is the upper (inclusive) boundary of Case 1. Confirmed
    against real SAD: it behaves identically to OFFSET = 0.5 and OFFSET = 0
    -- the marker stays at its own nominal s-position, it does not walk one
    full element further (which would land it at s = 5.0, the front of D3,
    rather than s = 2.0). D2 and D3 have different lengths so the two
    hypotheses are numerically distinguishable.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 2.0);
        DRIFT       D2      = (L = 3.0);
        DRIFT       D3      = (L = 4.0);

        MARK        M1      = (OFFSET = 1.0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 M1 D2 D3 END);
        """,
        filename = "offset_marker_case1_boundary.sad")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        _verbose         = False)

    tt = line.get_table(attr = True)

    assert tt["s", "m1"] == pytest.approx(2.0), (
        "With OFFSET = 1.0 (Case 1's inclusive upper boundary), M1 should "
        "stay at its own nominal s = 2.0, not walk one full element further "
        f"""to s = 5.0. Got: {tt["s", "m1"]:.6f}.""")


################################################################################
# MONI Element Offset
################################################################################
def test_pipeline_offset_marker_moni_moved_to_computed_s_position(write_lattice, tmp_path):
    """
    A SAD MONI element with OFFSET = 1.5 should be treated identically to a
    MARK with OFFSET: removed from its original position and reinserted at the
    computed s-position inside the following element. With the monitor before
    D2 (L = 2.0), the expected s-position is 3.0.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 2.0);
        DRIFT       D2      = (L = 2.0);

        MONI        BPM1    = (OFFSET = 1.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 BPM1 D2 END);
        """,
        filename = "offset_marker_moni_case2.sad")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        _verbose         = False)

    tt = line.get_table(attr = True)

    assert "bpm1" in list(line.element_names), (
        "A SAD MONI with OFFSET = 1.5 should be reinserted at the computed "
        f"s-position. Got: {list(line.element_names)}.")
    assert tt["s", "bpm1"] == pytest.approx(3.0), (
        "With OFFSET = 1.5, BPM1 should be reinserted at s = s(D2) + L(D2) * 0.5 "
        f"""= 2.0 + 1.0 = 3.0. Got: {tt["s", "bpm1"]:.6f}.""")


################################################################################
# Non-Offset Marker Preservation
################################################################################
def test_pipeline_offset_marker_non_offset_marker_preserved_alongside_offset_marker(
        write_lattice, tmp_path):
    """
    When an offset marker and a non-offset marker coexist, the non-offset marker
    should remain at its original s-position. The selection is purely by the
    presence of the OFFSET parameter: M1 (with OFFSET = 1.5) is moved inside
    D1, while M2 (without OFFSET) stays at its original position at s = 4.0.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 4.0);
        DRIFT       D2      = (L = 4.0);

        MARK        M1      = (OFFSET = 1.5);
        MARK        M2      = ();

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START M1 D1 M2 D2 END);
        """,
        filename = "offset_marker_preserved.sad")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        _verbose         = False)

    tt = line.get_table(attr = True)

    assert "m1" in list(line.element_names), (
        "Offset marker M1 should be reinserted in the line at the computed "
        f"s-position. Got: {list(line.element_names)}.")
    assert "m2" in list(line.element_names), (
        "Non-offset marker M2 should remain in the line at its original position. "
        f"Got: {list(line.element_names)}.")
    assert tt["s", "m2"] == pytest.approx(4.0), (
        "Non-offset marker M2 should remain at its original s = 4.0. "
        f"""Got: {tt["s", "m2"]:.6f}.""")


################################################################################
# Multiple Offset Markers
################################################################################
def test_pipeline_offset_marker_multiple_offset_markers_all_moved(write_lattice, tmp_path):
    """
    When multiple offset markers are present, each should be independently moved
    to its own computed s-position. M1 (OFFSET = 1.5, before D1 of L = 4.0) is
    inserted at s = 2.0; M2 (OFFSET = 1.5, before D2 of L = 4.0) is inserted
    at s = 6.0. Both markers are present in the final line at their respective
    computed positions.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 4.0);
        DRIFT       D2      = (L = 4.0);

        MARK        M1      = (OFFSET = 1.5);
        MARK        M2      = (OFFSET = 1.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START M1 D1 M2 D2 END);
        """,
        filename = "offset_marker_multiple.sad")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        _verbose         = False)

    tt = line.get_table(attr = True)

    assert "m1" in list(line.element_names), (
        "First offset marker M1 should be reinserted at the computed s-position. "
        f"Got: {list(line.element_names)}.")
    assert "m2" in list(line.element_names), (
        "Second offset marker M2 should be reinserted at the computed s-position. "
        f"Got: {list(line.element_names)}.")
    assert tt["s", "m1"] == pytest.approx(2.0), (
        "M1 (before D1 of L = 4.0, OFFSET = 1.5) should be reinserted at "
        f"""s = 0.0 + 4.0 * 0.5 = 2.0. Got: {tt["s", "m1"]:.6f}.""")
    assert tt["s", "m2"] == pytest.approx(6.0), (
        "M2 (before D2 of L = 4.0, OFFSET = 1.5) should be reinserted at "
        f"""s = 4.0 + 4.0 * 0.5 = 6.0. Got: {tt["s", "m2"]:.6f}.""")


################################################################################
# Reversed Marker Reference
################################################################################
def test_pipeline_offset_marker_reversed_reference_moved_to_computed_s_position(
        write_lattice, tmp_path):
    """
    A SAD MARK with OFFSET = 1.5 (Case 2), referenced with SAD's `-` (reversed)
    sign, should be installed 0.5 of the way into the element *preceding* its
    nominal position -- not the element following it. Confirmed against real
    SAD (survey_sad) on this exact lattice: the forward M placement lands at
    s = 3.0 (0.5 into D2, the drift following its own nominal slot); the
    reversed -M placement lands at s = 5.0 (0.5 into D3, the drift preceding
    its own nominal slot), not s = 7.0 (which is where 0.5 into D4, the
    following drift, would put it).
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D       = (L = 2.0);

        MARK        M       = (OFFSET = 1.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D M D D -M D END);
        """,
        filename = "offset_marker_reversed_case2.sad")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        _verbose         = False)

    tt = line.get_table(attr = True)

    assert tt["s", "m.0"] == pytest.approx(3.0), (
        "The forward M placement should be unaffected by this fix: 0.5 into "
        f"""the following drift, s = 3.0. Got: {tt["s", "m.0"]:.6f}.""")
    assert tt["s", "m.1"] == pytest.approx(5.0), (
        "The reversed -M placement should be installed 0.5 into the drift "
        "*preceding* its nominal position (s = 5.0), matching real SAD, not "
        "0.5 into the following drift (s = 7.0). "
        f"""Got: {tt["s", "m.1"]:.6f}.""")


################################################################################
# Solenoid Exclusion
################################################################################
def test_pipeline_offset_marker_solenoid_exclusion_removes_marker_permanently(
        write_lattice, tmp_path):
    """
    When the Case 2 target element (floor(OFFSET) elements ahead) is an
    xt.UniformSolenoid, the marker is excluded from offset_marker_locations and
    is not reinserted. The solenoid itself is not affected. This tests the
    production guard that prevents slicing of solenoid elements.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;

        DRIFT       D1      = (L = 2.0);
        SOL         S1      = (L = 2.0 BZ = 0.1);

        MARK        M1      = (OFFSET = 1.5);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 M1 S1 END);
        """,
        filename = "offset_marker_solenoid.sad")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        _verbose         = False)

    assert "m1" not in list(line.element_names), (
        "An offset marker whose Case 2 target is a solenoid should be excluded "
        "from offset_marker_locations and not reinserted in the line. "
        f"Got: {list(line.element_names)}.")
    assert "s1" in list(line.element_names), (
        "The solenoid S1 should remain in the line after the offset marker is "
        f"excluded. Got: {list(line.element_names)}.")


################################################################################
# String Expression Offset
################################################################################
def test_pipeline_offset_marker_symbolic_expression_resolves_to_computed_s_position(
        write_lattice,
        tmp_path):
    """
    A SAD MARK with OFFSET supplied through a SAD expression should resolve in
    the conversion expression context and be reinserted at the computed
    s-position. Offset expressions must not be resolved through bare Python
    eval() without SAD variables in scope.
    """
    lattice_path = write_lattice(
        """\
        MOMENTUM    = 1.0 GEV;
        L0          = 1.5;

        DRIFT       D1      = (L = 2.0);
        DRIFT       D2      = (L = 2.0);

        MARK        M1      = (OFFSET = L0);

        MARK        START   = ()
                    END     = ();

        LINE        TEST_LINE = (START D1 M1 D2 END);
        """,
        filename = "offset_marker_string_expr.sad")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = str(output_dir),
        _verbose         = False)

    tt = line.get_table(attr = True)

    assert "m1" in list(line.element_names), (
        "A SAD MARK with symbolic OFFSET = L0 should be reinserted in the "
        "converted line after expression resolution. If this raises NameError, "
        "offset marker conversion is still using bare eval() without the SAD "
        "expression context.")
    assert tt["s", "m1"] == pytest.approx(3.0), (
        "With L0 = 1.5, M1 should be reinserted at s = s(D2) + L(D2) * 0.5 "
        f"""= 2.0 + 1.0 = 3.0. Got: {tt["s", "m1"]:.6f}.""")
