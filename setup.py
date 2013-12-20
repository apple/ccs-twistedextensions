#!/usr/bin/env python

##
# Copyright (c) 2013 Apple Inc. All rights reserved.
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
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "support"))

from version import version


def find_packages():
    modules = [
        "twisted.plugins",
    ]

    excludes = [
        ".svn",
        "_trial_temp",
        "build",
    ]

    for root, dirs, files in os.walk("."):
        for exclude in excludes:
            if exclude in dirs:
                dirs.remove(exclude)

        if "__init__.py" in files:
            modules.append(".".join(root.split(os.path.sep)[1:]))

    return modules


#
# Options
#

description = "Extentions to Twisted",
long_description = """
Extentions to the Twisted Framework (http://twistedmatrix.com/).
"""

classifiers = None


#
# Write version file
#

version_number, version_info = version()

version_string = (
    "{number} ({info})"
    .format(number=version_number, info=version_info)
)
version_file = file(os.path.join("twext", "version.py"), "w")
version_file.write('version = "{version}"\n'.format(version=version_string))
version_file.close()


#
# Set up Extension modules that need to be built
#

from distutils.core import Extension

extensions = [
    Extension("twext.python.sendmsg", sources=["twext/python/sendmsg.c"])
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
    from distutils.core import setup

    setup(
        name="twext",
        version=version_string,
        description=description,
        long_description=long_description,
        url="http://trac.calendarserver.org/wiki/twext",
        classifiers=classifiers,
        author="Apple Inc.",
        author_email=None,
        license="Apache License, Version 2.0",
        platforms=["all"],
        packages=find_packages(),
        package_data={},
        scripts=[],
        data_files=[],
        ext_modules=extensions,
        py_modules=[],
    )


#
# Main
#

if __name__ == "__main__":
    doSetup()
