"""
================================================================================
Package Setup
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-20
================================================================================
"""

################################################################################
# Required Modules
################################################################################
from setuptools import setup, find_packages

################################################################################
# Load README data for long description
################################################################################
with open("README.md", "r", encoding = "utf-8") as f:
    description = f.read()

################################################################################
# Create setup
################################################################################
setup(
    name                            = "sad2xs",
    version                         = "0.2.0",
    date                            = "09-12-2025",
    description                     = "Conversion of SAD lattices to Xtrack format",
    long_description                = description,
    long_description_content_type   = "text/markdown",
    author                          = "J. Salvesen",
    author_email                    = "john.salvesen@cern.ch",
    url                             = "https://github.com/JPTS2/SAD2XS",
    packages                        = find_packages(),
    include_package_data            = True,
    install_requires                = [
        "numpy>=1.0",
        "pyyaml>=6.0",
        "xsuite>=0.53.2"],
    extras_require                  = {
        # Required for sad2xs.sad_helpers in addition to a working SAD executable
        "sad_helpers": ["tfs-pandas", "tqdm"],
        # Required for sad2xs.xsuite_helpers.plot_xsuite_sad_comparison
        "plotting": ["matplotlib"]},
    license                         = "Apache 2.0",
    download_url                    = "https://pypi.python.org/pypi/sad2xs",
    project_urls                    = {
        "Bug Tracker":      "https://github.com/JPTS2/SAD2XS/issues",
        "Documentation":    "https://github.com/JPTS2/SAD2XS/blob/main/README.md",
        "Source Code":      "https://github.com/JPTS2/SAD2XS"})
