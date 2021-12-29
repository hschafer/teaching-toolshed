import pathlib
from setuptools import find_packages, setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="teaching-toolshed",
    version="0.0.5",
    description="Helpful libraries for running classes",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/hschafer/teaching-toolshed",
    author="Hunter Schafer",
    author_email="hschafer@cs.washington.edu",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
    packages=find_packages(),
    include_package_data=True,
    install_requires=["requests", "pandas"],
)

