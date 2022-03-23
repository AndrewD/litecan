#!/usr/bin/env python3
# manual setup: python3 setup.py develop --user

from setuptools import setup

setup(
    name="ctucanfd",
    packages=["ctucanfd"],
    include_package_data=True,
    package_data={"": ["rtl_lst.txt", "ctucanfd/ctucanfd_ip_core/src/**/*.vhd"] },
)
