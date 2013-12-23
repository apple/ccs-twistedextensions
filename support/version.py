#!/usr/bin/env python

##
# Copyright (c) 2006-2013 Apple Inc. All rights reserved.
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

from os import chdir
from os.path import dirname, abspath
import subprocess



def version():
    #
    # Compute the version number.
    #

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

    source_root = dirname(dirname(abspath(__file__)))
    chdir(source_root)

    for branch in branches:
        cmd = ["svnversion", "-n", source_root, branch]
        svn_revision = subprocess.check_output(cmd)

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



if __name__ == "__main__":
    base_version = version()
    print(
        "{version}"
        .format(version=base_version)
    )
