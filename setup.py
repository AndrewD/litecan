#!/usr/bin/env python3
# manual setup: python3 setup.py develop --user

from setuptools import setup
from setuptools import find_packages


setup(
    name="litecan",
    packages=find_packages(exclude=("test*", "sim*", "doc*", "examples*")),
)
