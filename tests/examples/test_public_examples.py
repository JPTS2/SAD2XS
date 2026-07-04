"""
================================================================================
Tests for public example lattice assets
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
import os
import re
from pathlib import Path

import numpy as np
import pytest
import xtrack as xt

import sad2xs as s2x
from sad2xs.config import Config

################################################################################
# Test Data
################################################################################
REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_EXAMPLE_LATTICE_DIR = REPO_ROOT / "examples" / "lattices"
PUBLIC_EXAMPLE_DIR = REPO_ROOT / "examples"

PUBLIC_EXAMPLE_LATTICES = [
    "fccee_zh.sad",
    "fccee_tt_collimation.sad",
    "fccee_sol.sad",
]

################################################################################
# SAD-vs-Xsuite Twiss Comparison Helpers
#
# SAD numbers repeated copies of a named element from 1; Xsuite/sad2xs number
# them from 0. A handful of names (e.g. reversed-installation copies like
# "-bc0") don't even follow that consistently. So a raw name match silently
# compares unrelated physical locations -- confirmed empirically: without the
# corrections below, betx/bety/alfx/alfy/mux/muy diffs of thousands of metres
# and radians show up between elements that just happen to share a name.
#
# The matching used here: split "base.N", shift SAD's index down by one,
# require the (base, index) key to be unique on both sides, exclude Drifts
# and SAD-internal "$"-prototype names (both auto-split/auto-numbered in a
# way that doesn't correspond between the two codes), and cross-check with
# the element's own s position (< 1 m apart on a ring tens of km long) to
# catch any remaining convention mismatches. This reduces real SAD-vs-Xsuite
# agreement to sub-metre/sub-percent residuals -- see
# dev/xsuite_model_integrators/fcc_sol_lattice_check.py for the full study.
################################################################################
_NAME_INDEX_RE = re.compile(r"^(.*)\.(\d+)$")

def _split_name(name: str):
    match = _NAME_INDEX_RE.match(name)
    if match:
        return match.group(1).lower(), int(match.group(2))
    return name.lower(), None

TWISS_COLUMN_TOLERANCES = {
    "x":     dict(atol = 1e-6,  rtol = 0),
    "px":    dict(atol = 1e-6,  rtol = 0),
    "y":     dict(atol = 1e-6,  rtol = 0),
    "py":    dict(atol = 1e-6,  rtol = 0),
    "zeta":  dict(atol = 1e-5,  rtol = 0),
    "delta": dict(atol = 1e-9,  rtol = 0),
    "betx":  dict(atol = 1.0,   rtol = 5e-3),
    "bety":  dict(atol = 1.0,   rtol = 5e-3),
    "alfx":  dict(atol = 0.5,   rtol = 1e-2),
    "alfy":  dict(atol = 0.5,   rtol = 1e-2),
    "dx":    dict(atol = 1e-4,  rtol = 0),
    "dpx":   dict(atol = 1e-4,  rtol = 0),
    "dy":    dict(atol = 1e-4,  rtol = 0),
    "dpy":   dict(atol = 1e-4,  rtol = 0),
    "mux":   dict(atol = 1e-3,  rtol = 0),
    "muy":   dict(atol = 1e-3,  rtol = 0),
}

def _matched_sad_xsuite_twiss(line, tw_sad):
    """
    Match an Xsuite Twiss table (from `line.twiss4d()`) to a SAD Twiss table
    (from `sad2xs.sad_helpers.twiss_sad`) by identically-named elements,
    correcting for the indexing/naming pitfalls described above.

    Returns two same-length, same-order DataFrames (Xsuite rows, SAD rows)
    ready for column-by-column comparison.
    """
    tw = line.twiss4d().to_pandas()
    tt = line.get_table(attr = True).to_pandas()[["name", "element_type"]]
    tw = tw.merge(tt, on = "name", how = "left")
    tw_sad = tw_sad.to_pandas() if hasattr(tw_sad, "to_pandas") else tw_sad.copy()

    xs_base, xs_idx = zip(*tw["name"].map(_split_name))
    tw["base"], tw["idx"] = xs_base, xs_idx
    sad_base, sad_idx = zip(*tw_sad["name"].map(_split_name))
    tw_sad["base"] = sad_base
    tw_sad["idx"]  = [i - 1 if i is not None else None for i in sad_idx]

    tw["key"]     = list(zip(tw["base"], tw["idx"]))
    tw_sad["key"] = list(zip(tw_sad["base"], tw_sad["idx"]))

    non_drift_xs   = tw[(tw["element_type"] != "Drift") & (~tw["base"].str.contains(r"\$"))]
    non_dollar_sad = tw_sad[~tw_sad["base"].str.contains(r"\$")]

    xs_counts  = non_drift_xs["key"].value_counts()
    sad_counts = non_dollar_sad["key"].value_counts()
    common_keys = sorted(
        set(xs_counts[xs_counts == 1].index) & set(sad_counts[sad_counts == 1].index),
        key = str)

    xs_rows  = non_drift_xs.set_index("key").loc[common_keys]
    sad_rows = non_dollar_sad.set_index("key").loc[common_keys]

    same_position = np.abs(xs_rows["s"].to_numpy() - sad_rows["s"].to_numpy()) < 1.0
    return xs_rows[same_position], sad_rows[same_position]

def _assert_twiss_matches_sad(line, tw_sad, min_matched_elements):
    """
    Assert that `line`'s Twiss agrees with SAD's, element-by-element, for
    every identically-named element that survives the matching in
    `_matched_sad_xsuite_twiss`. `min_matched_elements` is a sanity floor on
    the match itself -- if the matching logic silently stops finding
    elements (e.g. a naming-scheme change), this fails loudly instead of the
    comparison quietly running on a near-empty set.
    """
    xs_rows, sad_rows = _matched_sad_xsuite_twiss(line, tw_sad)

    assert len(xs_rows) >= min_matched_elements, (
        f"Only matched {len(xs_rows)} identically-named elements between "
        f"Xsuite and SAD twiss (expected at least {min_matched_elements}). "
        "This likely means the name-matching logic itself broke, not that "
        "the physics is wrong -- check element naming conventions.")

    for column, tol in TWISS_COLUMN_TOLERANCES.items():
        np.testing.assert_allclose(
            xs_rows[column].to_numpy(),
            sad_rows[column].to_numpy(),
            atol = tol["atol"],
            rtol = tol["rtol"],
            err_msg = (
                f"Xsuite '{column}' disagrees with SAD for at least one "
                "identically-named element beyond tolerance."))

################################################################################
# Public Example Lattice Conversion Smoke Tests
################################################################################
@pytest.mark.parametrize("lattice_filename", PUBLIC_EXAMPLE_LATTICES)
def test_public_example_lattice_converts_in_test_mode(lattice_filename):
    """
    Public committed example lattices should remain loadable by the converter.
    """
    lattice_path = PUBLIC_EXAMPLE_LATTICE_DIR / lattice_filename

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _verbose         = False,
        _test_mode       = True)

    assert isinstance(line, xt.Line), (
        f"Public example lattice {lattice_filename} should convert to an "
        "Xsuite Line.")
    assert len(line.element_names) > 0, (
        f"Public example lattice {lattice_filename} should produce a non-empty "
        "Xsuite line.")
    assert line.particle_ref is not None, (
        f"Public example lattice {lattice_filename} should attach a reference "
        "particle.")


################################################################################
# Public Example Write and Reload Tests
################################################################################
@pytest.mark.parametrize("lattice_filename", PUBLIC_EXAMPLE_LATTICES)
def test_public_example_lattice_writes_and_reloads(lattice_filename, tmp_path):
    """
    The full user workflow for public example lattices should succeed: convert,
    write with write_lattice and write_optics, reload in a fresh Xsuite
    environment, and recover a non-empty line with a reference particle. This
    tests the path a user follows when running the committed examples.
    """
    lattice_path = PUBLIC_EXAMPLE_LATTICE_DIR / lattice_filename

    line = s2x.convert_sad_to_xsuite(
        sad_lattice_path = str(lattice_path),
        output_directory = "N/A",
        line_name        = "RING",
        _verbose         = False,
        _test_mode       = True)

    output_dir   = tmp_path / "output"
    output_dir.mkdir()
    stem         = Path(lattice_filename).stem
    lattice_out  = f"{stem}_lattice"
    optics_out   = f"{stem}_optics"

    s2x.write_lattice(
        line                    = line,
        output_filename         = lattice_out,
        output_directory        = str(output_dir),
        output_header           = f"Write+reload test: {lattice_filename}",
        offset_marker_locations = None,
        config                  = Config(_verbose = False))

    s2x.write_optics(
        line              = line,
        output_filename   = optics_out,
        output_directory  = str(output_dir),
        output_header     = f"Write+reload test: {lattice_filename}",
        config            = Config(_verbose = False))

    env = xt.Environment()
    env.call(str(output_dir / f"{lattice_out}.py"))
    env.call(str(output_dir / f"{optics_out}.py"))

    reloaded = env.lines["line"]

    assert len(reloaded.element_names) > 0, (
        f"Reloaded line from {lattice_filename} should be non-empty. "
        f"Got {len(reloaded.element_names)} elements.")
    assert reloaded.particle_ref is not None, (
        f"Reloaded line from {lattice_filename} should carry a reference "
        "particle after write+reload.")


################################################################################
# Public Example SAD-vs-Xsuite Optics Regression Tests
#
# Regression tests for the class of bug where a global model/integrator
# default silently produces a badly wrong periodic optics solution for a
# real (coupled, tilted-magnet) lattice while every unit/smoke test above
# still passes -- see dev/xsuite_model_integrators/fcc_sol_lattice_check.py.
################################################################################
_FCCEE_SOL_DISFRIN_COMMANDS = """
LINE["DISFRIN", "ESL*"]     = 1;
LINE["DISFRIN", "ESR*"]     = 1;
LINE["DISFRIN", "ESCR*"]    = 1;
LINE["DISFRIN", "ESCL*"]    = 1;
LINE["F1", "ESL*"]          = 0;
LINE["F1", "ESR*"]          = 0;
LINE["F1", "ESCL*"]         = 0;
LINE["F1", "ESCR*"]         = 0;"""

def test_public_example_003_fccee_sol_matches_sad(tmp_path):
    """
    examples/003_fccee_sol.py's converted line should match SAD's own Twiss,
    element-by-element, within TWISS_COLUMN_TOLERANCES.

    Deliberately does NOT use _test_mode=True: that returns the line before
    the write+reload step that resolves internal "::"-scoped replica names
    down to the final "."-suffixed names a real user (and SAD) sees, which
    the name-matching above depends on.
    """
    original_cwd = os.getcwd()
    os.chdir(PUBLIC_EXAMPLE_DIR)
    try:
        rebuilt_path = "lattices/fccee_sol_rebuilt_test_003.sad"
        s2x.sad_helpers.rebuild_sad_lattice(
            lattice_filepath    = "lattices/fccee_sol.sad",
            line_name           = "RING",
            additional_commands = _FCCEE_SOL_DISFRIN_COMMANDS,
            output_filepath     = rebuilt_path)

        tw_sad = s2x.sad_helpers.twiss_sad(
            lattice_filepath          = rebuilt_path,
            line_name                 = "RING",
            calc6d                    = False,
            closed                    = True,
            reverse_element_order     = False,
            reverse_survey_horizontal = False,
            additional_commands       = "")

        line = s2x.convert_sad_to_xsuite(
            sad_lattice_path            = rebuilt_path,
            line_name                   = "RING",
            excluded_elements           = None,
            user_multipole_replacements = None,
            reverse_element_order       = False,
            reverse_survey_horizontal   = False,
            reverse_charge_sign         = False,
            output_directory            = str(tmp_path),
            output_filename             = "fcc_sol_003",
            _verbose                    = False)

        os.remove(rebuilt_path)
    finally:
        os.chdir(original_cwd)

    _assert_twiss_matches_sad(line, tw_sad, min_matched_elements = 5000)

def test_public_example_004_fccee_sol_e_ep_matches_sad(tmp_path):
    """
    examples/004_fccee_sol_e-e+.py's positron and electron rings should each
    match their own (correspondingly reversed) SAD Twiss, element-by-element,
    within TWISS_COLUMN_TOLERANCES. The electron ring exercises
    reverse_charge_sign together with reverse_survey_horizontal.

    Deliberately does NOT use _test_mode=True: see the docstring on
    test_public_example_003_fccee_sol_matches_sad above.
    """
    original_cwd = os.getcwd()
    os.chdir(PUBLIC_EXAMPLE_DIR)
    try:
        rebuilt_path = "lattices/fccee_sol_rebuilt_test_004.sad"
        s2x.sad_helpers.rebuild_sad_lattice(
            lattice_filepath    = "lattices/fccee_sol.sad",
            line_name           = "RING",
            additional_commands = _FCCEE_SOL_DISFRIN_COMMANDS,
            output_filepath     = rebuilt_path)

        twp_sad = s2x.sad_helpers.twiss_sad(
            lattice_filepath          = rebuilt_path,
            line_name                 = "RING",
            calc6d                    = False,
            closed                    = True,
            reverse_element_order     = False,
            reverse_survey_horizontal = False,
            additional_commands       = "")
        twe_sad = s2x.sad_helpers.twiss_sad(
            lattice_filepath          = rebuilt_path,
            line_name                 = "RING",
            calc6d                    = False,
            closed                    = True,
            reverse_element_order     = False,
            reverse_survey_horizontal = True,
            additional_commands       = "")

        linep = s2x.convert_sad_to_xsuite(
            sad_lattice_path            = "lattices/fccee_sol.sad",
            line_name                   = "RING",
            excluded_elements           = None,
            user_multipole_replacements = None,
            reverse_element_order       = False,
            reverse_survey_horizontal   = False,
            reverse_charge_sign         = False,
            output_directory            = str(tmp_path),
            output_filename             = "fcc_sol_004_p",
            _verbose                    = False)
        linee = s2x.convert_sad_to_xsuite(
            sad_lattice_path            = "lattices/fccee_sol.sad",
            line_name                   = "RING",
            excluded_elements           = None,
            user_multipole_replacements = None,
            reverse_element_order       = False,
            reverse_survey_horizontal   = True,
            reverse_charge_sign         = True,
            output_directory            = str(tmp_path),
            output_filename             = "fcc_sol_004_e",
            _verbose                    = False)

        os.remove(rebuilt_path)
    finally:
        os.chdir(original_cwd)

    _assert_twiss_matches_sad(linep, twp_sad, min_matched_elements = 5000)
    _assert_twiss_matches_sad(linee, twe_sad, min_matched_elements = 5000)


################################################################################
# Public Example Script Contract Tests
################################################################################
def test_public_example_scripts_reference_committed_lattices():
    """
    Public example scripts should reference lattice files committed under
    examples/lattices. Each script file must exist, the lattice it references
    must exist, and the lattice filename must appear verbatim in the script
    content. The content check catches a script that references a lattice by
    a name that no longer exists or was renamed.
    """
    script_to_lattice = {
        "001_fccee_zh.py":             "fccee_zh.sad",
        "002_fccee_tt_collimation.py": "fccee_tt_collimation.sad",
        "003_fccee_sol.py":            "fccee_sol.sad",
        "004_fccee_sol_e-e+.py":       "fccee_sol.sad",
    }

    for script_name, lattice_filename in script_to_lattice.items():
        script_path  = REPO_ROOT / "examples" / script_name
        lattice_path = PUBLIC_EXAMPLE_LATTICE_DIR / lattice_filename

        assert script_path.exists(), (
            f"Public example script {script_name} should be committed.")
        assert lattice_path.exists(), (
            f"Public example script {script_name} should reference committed "
            f"lattice {lattice_filename}.")

        content = script_path.read_text(encoding = "utf-8")
        assert lattice_filename in content, (
            f"Public example script {script_name} should reference lattice "
            f"'{lattice_filename}' by name in its content. This catches a "
            "script pointing to a lattice that was renamed or removed.")
