#!/usr/bin/env python

##
# Copyright (c) 2006-2014 Apple Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##

from __future__ import print_function

import sys
import errno
from os import listdir, environ as environment
from os.path import dirname, abspath, join as joinpath
from itertools import chain
import subprocess
from setuptools import setup, find_packages as setuptools_find_packages
from pip.req import parse_requirements



#
# Utilities
#

def find_packages():
    modules = [
        "twisted.plugins",
    ]

    return modules + setuptools_find_packages()


def version():
    """
    Compute the version number.
    """

    base_version = "0.1"

    branches = tuple(
        branch.format(
            project="twext",
            version=base_version,
        )
        for branch in (
            "tags/release/{project}-{version}",
            "branches/release/{project}-{version}-dev",
            "trunk",
        )
    )

    source_root = dirname(abspath(__file__))

    for branch in branches:
        cmd = ["svnversion", "-n", source_root, branch]

        try:
            svn_revision = subprocess.check_output(cmd)

        except OSError as e:
            if e.errno == errno.ENOENT:
                full_version = base_version + "-unknown"
                break
            raise

        if "S" in svn_revision:
            continue

        full_version = base_version

        if branch == "trunk":
            full_version += "b.trunk"
        elif branch.endswith("-dev"):
            full_version += "c.dev"

        if svn_revision in ("exported", "Unversioned directory"):
            full_version += "-unknown"
        else:
            full_version += "-r{revision}".format(revision=svn_revision)

        break
    else:
        full_version += "a.unknown"
        full_version += "-r{revision}".format(revision=svn_revision)

    return full_version


#
# Options
#

description = "Extensions to Twisted"

long_description = file(joinpath(dirname(__file__), "README.rst")).read()

url = "http://trac.calendarserver.org/wiki/twext"

classifiers = [
    "Development Status :: 2 - Pre-Alpha",
    "Framework :: Twisted",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 2 :: Only",
    "Topic :: Software Development :: Libraries :: Python Modules",
]


#
# Dependencies
#

requirements_dir = joinpath(dirname(__file__), "requirements")


def read_requirements(reqs_filename):
    return [
        str(r.req) for r in
        parse_requirements(joinpath(requirements_dir, reqs_filename))
    ]


setup_requirements = []

install_requirements = read_requirements("py_base.txt")

extras_requirements = dict(
    (reqs_filename[4:-4], read_requirements(reqs_filename))
    for reqs_filename in listdir(requirements_dir)
    if reqs_filename.startswith("py_opt_") and reqs_filename.endswith(".txt")
)

# Requirements for development and testing
develop_requirements = read_requirements("py_develop.txt")

if environment.get("_DEVELOP", "false") == "true":
    install_requirements.extend(develop_requirements)
    install_requirements.extend(chain(*extras_requirements.values()))

    # Remove cx_Oracle here because we don't automate it's installation.
    install_requirements = [
        r for r in install_requirements
        if not r.startswith("cx-Oracle")
    ]



#
# Set up Extension modules that need to be built
#

# from distutils.core import Extension

extensions = [
    # Extension("twext.python.sendmsg", sources=["twext/python/sendmsg.c"])
]

if sys.platform == "darwin":
    try:
        from twext.python import launchd
        extensions.append(launchd.ffi.verifier.get_extension())
    except ImportError:
        pass


#
# Run setup
#

def doSetup():
    # Write version file
    version_string = version()
    version_filename = joinpath(dirname(__file__), "twext", "version.py")
    version_file = file(version_filename, "w")
    try:
        version_file.write(
            'version = "{0}"\n\n'.format(version_string)
        )
    finally:
        version_file.close()

    setup(
        name="twextpy",
        version=version_string,
        description=description,
        long_description=long_description,
        url=url,
        classifiers=classifiers,
        author="Apple Inc.",
        author_email="calendarserver-dev@lists.macosforge.org",
        license="Apache License, Version 2.0",
        platforms=["all"],
        packages=find_packages(),
        package_data={},
        scripts=[],
        data_files=[],
        ext_modules=extensions,
        py_modules=[],
        setup_requires=setup_requirements,
        install_requires=install_requirements,
        extras_require=extras_requirements,
    )


#
# Main
#

if __name__ == "__main__":
    doSetup()
