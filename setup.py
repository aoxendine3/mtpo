import os
from setuptools import setup, find_packages

setup(
    name="mtpo",
    version="5.0.0",
    package_dir={"": "python"},
    packages=find_packages(where="python"),
    include_package_data=True,
)
