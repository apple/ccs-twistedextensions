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
OpenDirectory service tests.
"""

from twisted.trial import unittest
from twext.who.opendirectory import DirectoryService
from twext.who.expression import (
    CompoundExpression, MatchExpression, MatchType, Operand
)



class OpenDirectoryServiceTestCase(unittest.TestCase):
    """
    Tests for L{DirectoryService}.
    """

    def test_queryStringFromExpression(self):
        service = DirectoryService()

        # MatchExpressions

        for matchType, expected in (
            (MatchType.equals, u"=xyzzy"),
            (MatchType.startsWith, u"=xyzzy*"),
            (MatchType.endsWith, u"=*xyzzy"),
            (MatchType.contains, u"=*xyzzy*"),
        ):
            expression = MatchExpression(
                service.fieldName.shortNames, u"xyzzy",
                matchType=matchType
            )
            queryString = service._queryStringFromExpression(expression)
            self.assertEquals(
                queryString,
                u"(dsAttrTypeStandard:RecordName{exp})".format(exp=expected)
            )

        # CompoundExpressions

        expression = CompoundExpression(
            [
                MatchExpression(
                    service.fieldName.uid, u"a",
                    matchType=MatchType.contains
                ),
                MatchExpression(
                    service.fieldName.guid, u"b",
                    matchType=MatchType.contains
                ),
                MatchExpression(
                    service.fieldName.shortNames, u"c",
                    matchType=MatchType.contains
                ),
                MatchExpression(
                    service.fieldName.emailAddresses, u"d",
                    matchType=MatchType.startsWith
                ),
                MatchExpression(
                    service.fieldName.fullNames, u"e",
                    matchType=MatchType.equals
                ),
            ],
            Operand.AND
        )
        queryString = service._queryStringFromExpression(expression)
        self.assertEquals(
            queryString,
            (
                u"(&(dsAttrTypeStandard:GeneratedUID=*a*)"
                u"(dsAttrTypeStandard:GeneratedUID=*b*)"
                u"(dsAttrTypeStandard:RecordName=*c*)"
                u"(dsAttrTypeStandard:EMailAddress=d*)"
                u"(dsAttrTypeStandard:RealName=e))"
            )
        )

        expression = CompoundExpression(
            [
                MatchExpression(
                    service.fieldName.shortNames, u"a",
                    matchType=MatchType.contains
                ),
                MatchExpression(
                    service.fieldName.emailAddresses, u"b",
                    matchType=MatchType.startsWith
                ),
                MatchExpression(
                    service.fieldName.fullNames, u"c",
                    matchType=MatchType.equals
                ),
            ],
            Operand.OR
        )
        queryString = service._queryStringFromExpression(expression)
        self.assertEquals(
            queryString,
            (
                u"(|(dsAttrTypeStandard:RecordName=*a*)"
                u"(dsAttrTypeStandard:EMailAddress=b*)"
                u"(dsAttrTypeStandard:RealName=c))"
            )
        )
