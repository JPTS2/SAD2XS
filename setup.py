from setuptools import setup, find_packages

with open("README.md", "r") as f:
    description = f.read()

setup(
    name                            = "sad2xs",
    version                         = "0.0.5",
    date                            = "24-04-2024",
    description                     = "Conversion of SAD lattices to Xtrack format",
    long_description                = description,
    long_description_content_type   = "text/markdown",
    author                          = "J. Salvesen, G. Iadarola",
    author_email                    = "john.salvesen@cern.ch",
    url                             = "https://github.com/JPTS2/SAD2XS",
    packages                        = find_packages(),
    include_package_data            = True,
    install_requires                = [
        "numpy>=1.0",
        "xtrack>=0.73"],
    license                         = 'Apache 2.0',
    project_urls                    = {
        "Bug Tracker":      "https://github.com/JPTS2/SAD2XS/issues",
        "Documentation":    "https://github.com/JPTS2/SAD2XS/blob/main/README.md",
        "Source Code":      "https://github.com/JPTS2/SAD2XS",})
