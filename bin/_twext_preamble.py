##
# Copyright (c) 2011-2014 Apple Inc. All rights reserved.
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

"""
This module is the shared preamble for all twext shell commands, to
set up their environment properly.  It's explicitly not installed
along with the code, and is used only to initialize the environment
for a development checkout of the code.
"""

import sys
from os.path import dirname, join as joinpath
from site import addsitedir

bindir = dirname(__file__)
srcroot = dirname(bindir)
depslib = joinpath(srcroot, ".develop", "lib")

addsitedir(depslib)
sys.path.insert(0, srcroot)

if False:
    print("PYTHONPATH:")
    for path in sys.path:
        print("  ", path)
