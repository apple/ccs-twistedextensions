##
# Copyright (c) 2010-2014 Apple Inc. All rights reserved.
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

from ...expression import (
    CompoundExpression, Operand, MatchExpression, MatchType, MatchFlags
)
from .._service import DirectoryService
from .._util import (
    ldapQueryStringFromMatchExpression,
)



class LDAPQueryTestCase(unittest.TestCase):
    """
    Tests for LDAP query generation.
    """

    def attrMap(self, service):
        """
        Create a mapping from field names to LDAP attribute names.
        The attribute names returned here are not real LDAP attribute names,
        but we don't care for these tests, since we're not actually connecting
        to LDAP.
        """
        return dict([(c, c.name) for c in service.fieldName.iterconstants()])


    def test_queryStringFromMatchExpression_matchTypes(self):
        """
        Match expressions with each match type produces the correct
        operator=value string.
        """
        service = DirectoryService()

        for matchType, expected in (
            (MatchType.equals, u"=xyzzy"),
            (MatchType.startsWith, u"=xyzzy*"),
            (MatchType.endsWith, u"=*xyzzy"),
            (MatchType.contains, u"=*xyzzy*"),
            (MatchType.lessThan, u"<xyzzy"),
            (MatchType.greaterThan, u">xyzzy"),
            (MatchType.lessThanOrEqualTo, u"<=xyzzy"),
            (MatchType.greaterThanOrEqualTo, u">=xyzzy"),
        ):
            expression = MatchExpression(
                service.fieldName.shortNames, u"xyzzy",
                matchType=matchType
            )
            queryString = ldapQueryStringFromMatchExpression(
                expression, self.attrMap(service)
            )
            self.assertEquals(
                queryString,
                u"({attribute}{expected})".format(
                    attribute="shortNames", expected=expected
                )
            )


    def test_queryStringFromMatchExpression_match_not(self):
        """
        Match expression with the C{NOT} flag adds the C{!} operator.
        """
        service = DirectoryService()

        expression = MatchExpression(
            service.fieldName.shortNames, u"xyzzy",
            flags=MatchFlags.NOT
        )
        queryString = ldapQueryStringFromMatchExpression(
            expression, self.attrMap(service)
        )
        self.assertEquals(
            queryString,
            u"(!{attribute}=xyzzy)".format(
                attribute="shortNames",
            )
        )


    def test_queryStringFromMatchExpression_match_caseInsensitive(self):
        """
        Match expression with the C{caseInsensitive} flag adds the C{??????}
        operator.
        """
        service = DirectoryService()

        expression = MatchExpression(
            service.fieldName.shortNames, u"xyzzy",
            flags=MatchFlags.caseInsensitive
        )
        queryString = ldapQueryStringFromMatchExpression(
            expression, self.attrMap(service)
        )
        self.assertEquals(
            queryString,
            u"???????({attribute}=xyzzy)".format(
                attribute="shortNames",
            )
        )

    test_queryStringFromMatchExpression_match_caseInsensitive.todo = (
        "unimplemented"
    )


    def test_queryStringFromMatchExpression_match_quoting(self):
        """
        Special characters are quoted properly.
        """
        service = DirectoryService()

        expression = MatchExpression(
            service.fieldName.fullNames,
            u"\\xyzzy: a/b/(c)* ~~ >=< ~~ &| \0!!"
        )
        queryString = ldapQueryStringFromMatchExpression(
            expression, self.attrMap(service)
        )
        self.assertEquals(
            queryString,
            u"({attribute}={expected})".format(
                attribute="fullNames",
                expected=(
                    u"\\5Cxyzzy: a\\2Fb\\2F\\28c\\29\\2A "
                    "\\7E\\7E \\3E\\3D\\3C \\7E\\7E \\26\\7C \\00!!"
                )
            )
        )


    # def test_queryStringFromExpression(self):
    #     service = DirectoryService()

    #     # CompoundExpressions

    #     expression = CompoundExpression(
    #         [
    #             MatchExpression(
    #                 service.fieldName.uid, u"a",
    #                 matchType=MatchType.contains
    #             ),
    #             MatchExpression(
    #                 service.fieldName.guid, u"b",
    #                 matchType=MatchType.contains
    #             ),
    #             MatchExpression(
    #                 service.fieldName.shortNames, u"c",
    #                 matchType=MatchType.contains
    #             ),
    #             MatchExpression(
    #                 service.fieldName.emailAddresses, u"d",
    #                 matchType=MatchType.startsWith
    #             ),
    #             MatchExpression(
    #                 service.fieldName.fullNames, u"e",
    #                 matchType=MatchType.equals
    #             ),
    #         ],
    #         Operand.AND
    #     )
    #     queryString = service._queryStringFromExpression(expression)
    #     self.assertEquals(
    #         queryString,
    #         (
    #             u"(&(dsAttrTypeStandard:GeneratedUID=*a*)"
    #             u"(dsAttrTypeStandard:GeneratedUID=*b*)"
    #             u"(dsAttrTypeStandard:RecordName=*c*)"
    #             u"(dsAttrTypeStandard:EMailAddress=d*)"
    #             u"(dsAttrTypeStandard:RealName=e))"
    #         )
    #     )

    #     expression = CompoundExpression(
    #         [
    #             MatchExpression(
    #                 service.fieldName.shortNames, u"a",
    #                 matchType=MatchType.contains
    #             ),
    #             MatchExpression(
    #                 service.fieldName.emailAddresses, u"b",
    #                 matchType=MatchType.startsWith
    #             ),
    #             MatchExpression(
    #                 service.fieldName.fullNames, u"c",
    #                 matchType=MatchType.equals
    #             ),
    #         ],
    #         Operand.OR
    #     )
    #     queryString = service._queryStringFromExpression(expression)
    #     self.assertEquals(
    #         queryString,
    #         (
    #             u"(|(dsAttrTypeStandard:RecordName=*a*)"
    #             u"(dsAttrTypeStandard:EMailAddress=b*)"
    #             u"(dsAttrTypeStandard:RealName=c))"
    #         )
    #     )
