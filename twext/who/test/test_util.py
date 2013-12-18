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

"""
Directory service utility tests.
"""

from itertools import chain

from twisted.trial import unittest
from twisted.python.constants import (
    Names, NamedConstant, Flags, FlagConstant,
)

from ..idirectory import DirectoryServiceError
from ..util import ConstantsContainer, uniqueResult, describe



class Tools(Names):
    hammer = NamedConstant()
    screwdriver = NamedConstant()

    hammer.description = u"nail pounder"
    screwdriver.description = u"screw twister"


class MoreTools(Names):
    saw = NamedConstant()

    saw.description = u"z maker"


class Instruments(Names):
    hammer = NamedConstant()
    chisel = NamedConstant()



class Switches(Flags):
    r = FlagConstant()
    g = FlagConstant()
    b = FlagConstant()

    r.description = u"red"
    g.description = u"green"
    b.description = u"blue"

    black = FlagConstant()



class ConstantsContainerTest(unittest.TestCase):
    """
    Tests for L{ConstantsContainer}.
    """

    def test_constants_from_constants(self):
        """
        Initialize a container from some constants.
        """
        constants = set((Tools.hammer, Tools.screwdriver, Instruments.chisel))
        self.assertEquals(
            set(ConstantsContainer(constants).iterconstants()),
            constants,
        )


    def test_constants_from_containers(self):
        """
        Initialize a container from other containers.
        """
        self.assertEquals(
            set(ConstantsContainer((Tools, MoreTools)).iterconstants()),
            set(chain(Tools.iterconstants(), MoreTools.iterconstants())),
        )


    def test_constants_from_iterables(self):
        """
        Initialize a container from iterables of constants.
        """
        self.assertEquals(
            set(
                ConstantsContainer((
                    Tools.iterconstants(), MoreTools.iterconstants()
                )).iterconstants()
            ),
            set(chain(Tools.iterconstants(), MoreTools.iterconstants())),
        )


    def test_conflictingClasses(self):
        """
        A container can't contain two constants with the same name.
        """
        self.assertRaises(TypeError, ConstantsContainer, (Tools, Switches))


    def test_conflictingNames(self):
        """
        A container can't contain two constants with the same name.
        """
        self.assertRaises(ValueError, ConstantsContainer, (Tools, Instruments))


    def test_attrs(self):
        """
        Constants are assessible via attributes.
        """
        container = ConstantsContainer((
            Tools.hammer, Tools.screwdriver, Instruments.chisel
        ))

        self.assertEquals(container.hammer, Tools.hammer)
        self.assertEquals(container.screwdriver, Tools.screwdriver)
        self.assertEquals(container.chisel, Instruments.chisel)
        self.assertRaises(AttributeError, lambda: container.plugh)


    def test_iterconstants(self):
        """
        L{ConstantsContainer.iterconstants}C{()} produces the contained
        constants.
        """
        constants = set((Tools.hammer, Tools.screwdriver, Instruments.chisel))
        container = ConstantsContainer(constants)

        self.assertEquals(
            set(container.iterconstants()),
            constants,
        )


    def test_lookupByName(self):
        """
        Constants are assessible via L{ConstantsContainer.lookupByName}.
        """
        constants = set((
            Instruments.hammer,
            Tools.screwdriver,
            Instruments.chisel,
        ))
        container = ConstantsContainer(constants)

        self.assertEquals(
            container.lookupByName("hammer"),
            Instruments.hammer,
        )
        self.assertEquals(
            container.lookupByName("screwdriver"),
            Tools.screwdriver,
        )
        self.assertEquals(
            container.lookupByName("chisel"),
            Instruments.chisel,
        )

        self.assertRaises(
            ValueError,
            container.lookupByName, "plugh",
        )



class UtilTest(unittest.TestCase):
    """
    Miscellaneous tests.
    """

    def test_uniqueResult(self):
        self.assertEquals(1, uniqueResult((1,)))
        self.assertRaises(DirectoryServiceError, uniqueResult, (1, 2, 3))


    def test_describe(self):
        self.assertEquals(u"nail pounder", describe(Tools.hammer))
        self.assertEquals(u"hammer", describe(Instruments.hammer))


    def test_describeFlags(self):
        self.assertEquals(u"blue", describe(Switches.b))
        self.assertEquals(u"red|green", describe(Switches.r | Switches.g))
        self.assertEquals(u"blue|black", describe(Switches.b | Switches.black))
