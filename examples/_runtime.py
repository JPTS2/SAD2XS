"""
================================================================================
Runtime bootstrapping for SAD2XS examples
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-16
================================================================================
"""
################################################################################
# Required Modules
################################################################################
import os
import sys
from pathlib import Path

DEFAULT_OUTPUT_DIR = "out"

################################################################################
# Runtime Setup
################################################################################
def configure_example_runtime(output_dir = DEFAULT_OUTPUT_DIR) -> str:
    """
    Configure paths for running an example script from any working directory.

    The examples and SAD helper functions use paths relative to the examples
    folder. This function adds the repository root to `sys.path`, changes the
    working directory to the examples folder, creates the output folder, and
    returns it as a string for `convert_sad_to_xsuite`.
    """
    example_dir = Path(__file__).resolve().parent
    repo_root   = example_dir.parent

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    os.chdir(example_dir)

    Path(output_dir).mkdir(parents = True, exist_ok = True)

    return str(output_dir)
