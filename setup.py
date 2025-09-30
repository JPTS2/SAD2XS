"""
Package setup for SAD2XS Converter
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       30-09-2025
"""

################################################################################
# Required Modules
################################################################################
from setuptools import setup, find_packages

################################################################################
# Load README data for long description
################################################################################
with open("README.md", "r") as f:
    description = f.read()

################################################################################
# Create setup
################################################################################
setup(
    name                            = "sad2xs",
    version                         = "0.1.0",
    date                            = "30-09-2025",
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
        "xtrack>=0.92"],
    license                         = 'Apache 2.0',
    download_url                    = "https://pypi.python.org/pypi/sad2xs",
    project_urls                    = {
        "Bug Tracker":      "https://github.com/JPTS2/SAD2XS/issues",
        "Documentation":    "https://github.com/JPTS2/SAD2XS/blob/main/README.md",
        "Source Code":      "https://github.com/JPTS2/SAD2XS"})
