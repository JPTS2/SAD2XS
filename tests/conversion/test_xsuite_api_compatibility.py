"""
================================================================================
Tests for Xsuite API compatibility assumptions
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

from sad2xs.config import Config

################################################################################
# Environment API
################################################################################
def test_xsuite_environment_variable_and_element_installation():
    """
    Xsuite environments should support the variable and element APIs SAD2XS uses.
    """
    environment = xt.Environment()
    environment["k_test"] = 0.2

    environment.new(
        name   = "test_quad",
        parent = xt.Quadrupole,
        length = 1.5,
        k1     = "k_test")

    assert environment["k_test"] == pytest.approx(0.2), (
        "Xsuite Environment should preserve scalar variables assigned by SAD2XS.")
    assert "test_quad" in environment.element_dict, (
        "Xsuite Environment should expose created elements through element_dict.")
    assert isinstance(environment.element_dict["test_quad"], xt.Quadrupole), (
        "Xsuite Environment should create elements with the requested parent class.")
    assert environment["test_quad"].k1 == pytest.approx(0.2), (
        "Xsuite Environment should resolve element fields backed by variables.")

def test_xsuite_environment_clone_mode_preserves_reversal_dependencies():
    """
    Xsuite environments should support clone mode used by reversed SAD lines.
    """
    environment = xt.Environment()
    environment.new(
        name            = "test_bend",
        parent          = xt.Bend,
        length          = 1.5,
        angle           = 0.03,
        edge_entry_angle = 0.01,
        edge_exit_angle  = 0.02)

    environment.new(
        name   = "-test_bend",
        parent = "test_bend",
        mode   = "clone")

    assert "-test_bend" in environment.element_dict, (
        "Xsuite Environment clone mode should create the reversed element name.")
    assert isinstance(environment["-test_bend"], xt.Bend), (
        "Xsuite Environment clone mode should preserve the cloned element type.")
    assert environment["-test_bend"].length == pytest.approx(
        environment["test_bend"].length), (
        "Xsuite Environment clone mode should preserve cloned element length.")
    assert environment["-test_bend"].angle == pytest.approx(
        environment["test_bend"].angle), (
        "Xsuite Environment clone mode should preserve cloned element angle.")

def test_xsuite_reference_particle_fields_used_by_sad2xs_exist():
    """
    Xsuite particles should expose the reference-particle fields SAD2XS sets.
    """
    environment = xt.Environment()
    environment["p0c"] = 1.0E9
    environment["q0"] = -1.0
    environment["mass0"] = xt.ELECTRON_MASS_EV

    environment.particle_ref = xt.Particles(
        p0c   = environment["p0c"],
        q0    = environment["q0"],
        mass0 = environment["mass0"])

    assert environment.particle_ref.p0c[0] == pytest.approx(1.0E9), (
        "Xsuite reference particles should expose p0c for converted lines.")
    assert environment.particle_ref.q0 == pytest.approx(-1.0), (
        "Xsuite reference particles should expose q0 for converted lines.")
    assert environment.particle_ref.mass0 == pytest.approx(xt.ELECTRON_MASS_EV), (
        "Xsuite reference particles should expose mass0 for converted lines.")

################################################################################
# Line API
################################################################################
def test_xsuite_line_preserves_named_element_order_and_lookup():
    """
    Xsuite lines should preserve names, order, lookup, and table element types.
    """
    drift = xt.Drift(length = 1.0)
    quadrupole = xt.Quadrupole(length = 0.5, k1 = 0.2)

    line = xt.Line(
        elements      = [drift, quadrupole],
        element_names = ["test_drift", "test_quad"])

    table = line.get_table()

    assert line.element_names == ["test_drift", "test_quad"], (
        "Xsuite Line should preserve the element order supplied by SAD2XS.")
    assert isinstance(line["test_quad"], xt.Quadrupole), (
        "Xsuite Line should return the named element type through line[name] lookup.")
    assert line["test_quad"].length == pytest.approx(quadrupole.length), (
        "Xsuite Line should preserve named element length through line[name] lookup.")
    assert line["test_quad"].k1 == pytest.approx(quadrupole.k1), (
        "Xsuite Line should preserve named element strength through line[name] lookup.")
    assert list(table.name[:2]) == ["test_drift", "test_quad"], (
        "Xsuite Line table should expose element names in line order.")
    assert list(table.element_type[:2]) == ["Drift", "Quadrupole"], (
        "Xsuite Line table should expose element_type names used by SAD2XS.")

def test_xsuite_trivial_twiss4d_call_shape_used_by_sad2xs():
    """
    Xsuite should accept the Twiss call shape used by SAD2XS comparison tests.
    """
    line = xt.Line(
        elements      = [xt.Drift(length = 1.0)],
        element_names = ["test_drift"])
    line.particle_ref = xt.Particles(
        p0c   = 1.0E9,
        q0    = 1.0,
        mass0 = xt.ELECTRON_MASS_EV)

    twiss_table = line.twiss4d(
        _continue_if_lost = True,
        start             = xt.START,
        end               = xt.END,
        betx              = 1.0,
        bety              = 1.0)

    assert "test_drift" in list(twiss_table.name), (
        "Xsuite twiss4d output should include the named element supplied by SAD2XS.")
    assert "_end_point" in list(twiss_table.name), (
        "Xsuite twiss4d output should include the endpoint used by SAD2XS tests.")

def test_xsuite_line_model_configuration_calls_used_by_sad2xs():
    """
    Xsuite lines should accept the model and integrator setup calls SAD2XS makes.
    """
    config = Config(_verbose = False)
    line = xt.Line(
        elements = [
            xt.Drift(length = 1.0),
            xt.Bend(length = 1.0, angle = 0.01),
            xt.Quadrupole(length = 1.0, k1 = 0.1),
            xt.Sextupole(length = 1.0, k2 = 0.2),
            xt.Octupole(length = 1.0, k3 = 0.3),
            xt.Multipole(length = 0.1, knl = [0.0, 0.1]),
            xt.UniformSolenoid(length = 1.0, ks = 0.1),
            xt.Cavity(voltage = 1.0, frequency = 2.0, lag = 0.0),
        ],
        element_names = [
            "test_drift",
            "test_bend",
            "test_quad",
            "test_sext",
            "test_oct",
            "test_mult",
            "test_sol",
            "test_cavi",
        ])

    table = line.get_table()

    line.set(
        table.rows[table.element_type == "Drift"],
        model = config.MODEL_DRIFT)
    line.set(
        table.rows[table.element_type == "Bend"],
        model               = config.MODEL_BEND,
        integrator          = config.INTEGRATOR_BEND,
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_BEND)
    line.set(
        table.rows[table.element_type == "Quadrupole"],
        model               = config.MODEL_QUAD,
        integrator          = config.INTEGRATOR_QUAD,
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_QUAD)
    line.set(
        table.rows[table.element_type == "Sextupole"],
        model               = config.MODEL_SEXT,
        integrator          = config.INTEGRATOR_SEXT,
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_SEXT)
    line.set(
        table.rows[table.element_type == "Octupole"],
        model               = config.MODEL_OCT,
        integrator          = config.INTEGRATOR_OCT,
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_OCT)
    line.set(
        table.rows[table.element_type == "Multipole"],
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_MULT)
    line.set(
        table.rows[table.element_type == "UniformSolenoid"],
        num_multipole_kicks = config.N_INTEGRATOR_KICKS_SOL)
    line.set(
        table.rows[table.element_type == "Cavity"],
        model         = config.MODEL_CAVI,
        integrator    = config.INTEGRATOR_CAVI,
        absolute_time = config.ABSOLUTE_TIME_CAVI)

    assert line["test_drift"].model == config.MODEL_DRIFT, (
        "Xsuite Line.set should apply SAD2XS drift model configuration.")
    assert line["test_bend"].model == config.MODEL_BEND, (
        "Xsuite Line.set should apply SAD2XS bend model configuration.")
    assert line["test_bend"].integrator == config.INTEGRATOR_BEND, (
        "Xsuite Line.set should apply SAD2XS bend integrator configuration.")
    assert line["test_quad"].num_multipole_kicks == (
        config.N_INTEGRATOR_KICKS_QUAD), (
        "Xsuite Line.set should apply SAD2XS quadrupole kick configuration.")
    assert line["test_cavi"].absolute_time == config.ABSOLUTE_TIME_CAVI, (
        "Xsuite Line.set should apply SAD2XS cavity absolute-time configuration.")

def test_xsuite_bend_model_configuration_call_used_by_sad2xs():
    """
    Xsuite lines should accept the bend edge model configuration SAD2XS makes.
    """
    config = Config(_verbose = False)
    line = xt.Line(
        elements      = [xt.Bend(length = 1.0, angle = 0.01)],
        element_names = ["test_bend"])

    line.configure_bend_model(edge = config.EDGE_MODEL_BEND)

    assert line["test_bend"].edge_entry_model == config.EDGE_MODEL_BEND, (
        "Xsuite configure_bend_model should apply the configured entry edge model.")
    assert line["test_bend"].edge_exit_model == config.EDGE_MODEL_BEND, (
        "Xsuite configure_bend_model should apply the configured exit edge model.")

def test_xsuite_line_table_exposes_writer_filter_fields_used_by_sad2xs():
    """
    Xsuite line tables should expose names and element types used by writers.
    """
    line = xt.Line(
        elements = [
            xt.Marker(),
            xt.Drift(length = 1.0),
            xt.Bend(length = 1.0, angle = 0.01),
            xt.Quadrupole(length = 1.0, k1 = 0.1),
            xt.Sextupole(length = 1.0, k2 = 0.2),
            xt.Octupole(length = 1.0, k3 = 0.3),
            xt.Multipole(length = 0.1, knl = [0.0, 0.1]),
            xt.UniformSolenoid(length = 1.0, ks = 0.1),
            xt.Cavity(voltage = 1.0, frequency = 2.0, lag = 0.0),
            xt.Translation(shift_x = 1.0E-3, shift_y = -2.0E-3),
            xt.TimeDelay(shift_zeta = 3.0E-3),
            xt.Rotation(rot_y_rad = 1.0),
            xt.LimitRect(min_x = -1.0, max_x = 1.0, min_y = -2.0, max_y = 2.0),
            xt.LimitEllipse(a = 1.0, b = 2.0),
        ],
        element_names = [
            "test_marker",
            "test_drift",
            "test_bend",
            "test_quad",
            "test_sext",
            "test_oct",
            "test_mult",
            "test_sol",
            "test_cavi",
            "test_translation",
            "test_timedelay",
            "test_rotation",
            "test_limitrect",
            "test_limitellipse",
        ])

    table = line.get_table()
    table_names = list(table.name)
    table_types = list(table.element_type)
    expected_type_by_name = {
        "test_marker":       "Marker",
        "test_drift":        "Drift",
        "test_bend":         "Bend",
        "test_quad":         "Quadrupole",
        "test_sext":         "Sextupole",
        "test_oct":          "Octupole",
        "test_mult":         "Multipole",
        "test_sol":          "UniformSolenoid",
        "test_cavi":         "Cavity",
        "test_translation":  "Translation",
        "test_timedelay":    "TimeDelay",
        "test_rotation":     "Rotation",
        "test_limitrect":    "LimitRect",
        "test_limitellipse": "LimitEllipse",
    }

    assert hasattr(table, "rows"), (
        "Xsuite Line table should expose rows filtering used by SAD2XS.")
    assert hasattr(table, "name"), (
        "Xsuite Line table should expose element names used by SAD2XS writers.")
    assert hasattr(table, "element_type"), (
        "Xsuite Line table should expose element_type used by SAD2XS writers.")

    for element_name, element_type in expected_type_by_name.items():
        assert element_name in table_names, (
            f"Xsuite Line table should include writer-visible name '{element_name}'.")
        row_index = table_names.index(element_name)
        assert table_types[row_index] == element_type, (
            f"Xsuite Line table should report '{element_type}' for '{element_name}'.")
        assert list(table.rows[table.element_type == element_type].name), (
            f"Xsuite Line table rows should support filtering by '{element_type}'.")

################################################################################
# Element API
################################################################################
@pytest.mark.parametrize(
    "element_name, element, expected_fields",
    [
        (
            "Drift",
            xt.Drift(length = 1.2),
            {"length": 1.2},
        ),
        (
            "Bend angle route",
            xt.Bend(length = 1.2, angle = 0.024, k1 = 0.03),
            {"length": 1.2, "angle": 0.024, "h": 0.02, "k1": 0.03},
        ),
        (
            "Bend corrector route",
            xt.Bend(length = 1.2, k0 = 0.04, k1 = 0.0),
            {"length": 1.2, "k0": 0.04, "h": 0.0, "k1": 0.0},
        ),
        (
            "Quadrupole",
            xt.Quadrupole(length = 1.2, k1 = 0.03),
            {"length": 1.2, "k1": 0.03},
        ),
        (
            "Sextupole",
            xt.Sextupole(length = 1.2, k2 = 0.04, k2s = 0.05),
            {"length": 1.2, "k2": 0.04, "k2s": 0.05},
        ),
        (
            "Octupole",
            xt.Octupole(length = 1.2, k3 = 0.06, k3s = 0.07),
            {"length": 1.2, "k3": 0.06, "k3s": 0.07},
        ),
        (
            "Multipole",
            xt.Multipole(length = 1.2, knl = [0.0, 0.1], ksl = [0.0, 0.2]),
            {"length": 1.2, "knl": [0.0, 0.1], "ksl": [0.0, 0.2]},
        ),
        (
            "Cavity",
            xt.Cavity(voltage = 3.0, frequency = 4.0, lag = 5.0),
            {"voltage": 3.0, "frequency": 4.0, "lag": 5.0},
        ),
        (
            "UniformSolenoid",
            xt.UniformSolenoid(length = 1.2, ks = 0.3),
            {"length": 1.2, "ks": 0.3},
        ),
        (
            "LimitRect",
            xt.LimitRect(min_x = -1.0, max_x = 2.0, min_y = -3.0, max_y = 4.0),
            {"min_x": -1.0, "max_x": 2.0, "min_y": -3.0, "max_y": 4.0},
        ),
        (
            "LimitEllipse",
            xt.LimitEllipse(a = 1.0, b = 2.0),
            {"a": 1.0, "b": 2.0},
        ),
    ])
def test_xsuite_element_attribute_contracts(
        element_name,
        element,
        expected_fields):
    """
    Xsuite elements should expose the attributes SAD2XS writes and reads.
    """
    for field, expected_value in expected_fields.items():
        assert hasattr(element, field), (
            f"Xsuite {element_name} should expose field '{field}' used by SAD2XS.")

        actual_value = getattr(element, field)
        if isinstance(expected_value, list):
            assert list(actual_value) == pytest.approx(expected_value), (
                f"Xsuite {element_name}.{field} should preserve SAD2XS values.")
        else:
            assert actual_value == pytest.approx(expected_value), (
                f"Xsuite {element_name}.{field} should preserve SAD2XS values.")

@pytest.mark.parametrize(
    "element_name, element, expected_fields",
    [
        (
            "Translation",
            xt.Translation(shift_x = 1.0E-3, shift_y = -2.0E-3),
            {"shift_x": 1.0E-3, "shift_y": -2.0E-3},
        ),
        (
            "TimeDelay",
            xt.TimeDelay(shift_zeta = 3.0E-3),
            {"shift_zeta": 3.0E-3},
        ),
        (
            "Rotation",
            xt.Rotation(rot_y_rad = -0.125, rot_x_rad = 0.25, rot_s_rad = -0.5),
            {"rot_y_rad": -0.125, "rot_x_rad": 0.25, "rot_s_rad": -0.5},
        ),
    ])
def test_xsuite_transform_element_contracts(
        element_name,
        element,
        expected_fields):
    """
    Current Xsuite transform elements should keep the API SAD2XS targets.
    """
    for field, expected_value in expected_fields.items():
        assert hasattr(element, field), (
            f"Xsuite {element_name} should expose field '{field}' used by SAD2XS. "
            "If this fails because Xsuite moved to a newer transform API, see "
            "issue #19.")
        assert getattr(element, field) == pytest.approx(expected_value), (
            f"Xsuite {element_name}.{field} should preserve SAD2XS values. "
            "If this fails because Xsuite moved to a newer transform API, see "
            "issue #19.")
