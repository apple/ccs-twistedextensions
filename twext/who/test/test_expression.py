##
# Copyright (c) 2013-2014 Apple Inc. All rights reserved.
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
Directory service expression tests.
"""

from twisted.trial import unittest

from ..idirectory import FieldName
from ..expression import MatchExpression, MatchType, MatchFlags



class MatchFlagsTest(unittest.TestCase):
    """
    Tests for L{MatchFlags}.
    """

    def test_predicator_none(self):
        """
        Predicator for flags without L{MatchFlags.NOT} does not invert.
        """
        predicator = MatchFlags.predicator(MatchFlags.none)

        for boolean in (True, False):
            self.assertEquals(bool(predicator(boolean)), boolean)


    def test_predicator_NOT(self):
        """
        Predicator for flags with L{MatchFlags.NOT} does not invert.
        """
        predicator = MatchFlags.predicator(MatchFlags.NOT)

        for boolean in (True, False):
            self.assertNotEquals(bool(predicator(boolean)), boolean)


    def test_normalizer_none(self):
        """
        Normalizer for flags without L{MatchFlags.caseInsensitive} does not
        lowercase.
        """
        normalizer = MatchFlags.normalizer(MatchFlags.none)

        self.assertEquals(normalizer(u"ThInGo"), u"ThInGo")


    def test_normalizer_insensitive(self):
        """
        Normalizer for flags with L{MatchFlags.caseInsensitive} lowercases.
        """
        normalizer = MatchFlags.normalizer(MatchFlags.caseInsensitive)

        self.assertEquals(normalizer(u"ThInGo"), u"thingo")



class MatchExpressionTest(unittest.TestCase):
    """
    Tests for L{MatchExpression}.
    """

    def test_initBadType_value(self):
        """
        L{MatchExpression.__init__} raises if the field value doesn't match the
        expected type for the field.
        """
        # guid field expects a UUID, not a string.
        self.assertRaises(
            TypeError,
            MatchExpression,
            FieldName.guid, u"00000000-0000-0000-0000-000000000000"
        )


    def test_repr_name(self):
        """
        L{MatchExpression.__repr__} emits field name and value.
        """
        self.assertEquals(
            "<MatchExpression: u'full names' equals u'Wilfredo Sanchez'>",
            repr(MatchExpression(
                FieldName.fullNames,
                u"Wilfredo Sanchez",
            )),
        )

    def test_repr_type(self):
        """
        L{MatchExpression.__repr__} emits match type.
        """
        self.assertEquals(
            "<MatchExpression: u'full names' contains u'Sanchez'>",
            repr(MatchExpression(
                FieldName.fullNames,
                u"Sanchez",
                matchType=MatchType.contains,
            )),
        )

    def test_repr_flags(self):
        """
        L{MatchExpression.__repr__} emits flags.
        """
        self.assertEquals(
            "<MatchExpression: u'full names' starts with u'Wilfredo' (not)>",
            repr(MatchExpression(
                FieldName.fullNames,
                u"Wilfredo",
                matchType=MatchType.startsWith,
                flags=MatchFlags.NOT,
            )),
        )
        self.assertEquals(
            "<MatchExpression: u'full names' starts with u'Wilfredo' "
            "(not|case insensitive)>",
            repr(MatchExpression(
                FieldName.fullNames,
                u"Wilfredo",
                matchType=MatchType.startsWith,
                flags=(MatchFlags.NOT | MatchFlags.caseInsensitive),
            )),
        )
