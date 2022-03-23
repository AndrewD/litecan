#!/usr/bin/env python3
# manual setup: python3 setup.py develop --user

from setuptools import setup
from setuptools import find_packages
import os


extra_files = ["rtl_lst.txt"]

cdir = os.path.dirname(__file__)
mdir = os.path.abspath(os.path.join(cdir, 'ctucanfd'))
sdir = os.path.abspath(os.path.join(mdir, 'ctucanfd_ip_core'))

with open(os.path.join(mdir, 'rtl_lst.txt')) as f:
    for line in f:
        srcfile = os.path.join(sdir, line.strip().replace('rtl', 'src'))
        extra_files.append(srcfile)

setup(
    name="ctucanfd",
    packages=["ctucanfd"],
    include_package_data=True,
    package_data={"": extra_files},
)
