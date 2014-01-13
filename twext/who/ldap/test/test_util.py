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

from ...idirectory import QueryNotSupportedError
from ...expression import (
    CompoundExpression, Operand, MatchExpression, MatchType, MatchFlags
)
from .._service import DirectoryService
from .._util import (
    ldapQueryStringFromMatchExpression,
    ldapQueryStringFromCompoundExpression,
    ldapQueryStringFromExpression,
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
            expected = u"({attribute}{expected})".format(
                attribute="shortNames", expected=expected
            )
            self.assertEquals(queryString, expected)


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
        expected = u"(!{attribute}=xyzzy)".format(
            attribute="shortNames",
        )
        self.assertEquals(queryString, expected)


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
        expected = u"???????({attribute}=xyzzy)".format(
            attribute="shortNames",
        )
        self.assertEquals(queryString, expected)


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
        expected = u"({attribute}={expected})".format(
            attribute="fullNames",
            expected=(
                u"\\5Cxyzzy: a\\2Fb\\2F\\28c\\29\\2A "
                "\\7E\\7E \\3E\\3D\\3C \\7E\\7E \\26\\7C \\00!!"
            )
        )
        self.assertEquals(queryString, expected)


    def test_queryStringFromMatchExpression_unknownFieldName(self):
        """
        Unknown expression.
        """
        service = DirectoryService()

        expression = MatchExpression(
            object(), u"xyzzy",
        )

        self.assertRaises(
            QueryNotSupportedError,
            ldapQueryStringFromMatchExpression,
            expression, self.attrMap(service)
        )


    def test_queryStringFromMatchExpression_unknownMatchType(self):
        """
        Unknown expression.
        """
        service = DirectoryService()

        expression = MatchExpression(
            service.fieldName.shortNames, u"xyzzy",
            matchType=object()
        )

        self.assertRaises(
            QueryNotSupportedError,
            ldapQueryStringFromMatchExpression,
            expression, self.attrMap(service)
        )


    def test_queryStringFromCompoundExpression_single(
        self, queryFunction=ldapQueryStringFromCompoundExpression
    ):
        """
        Compound expression with a single sub-expression.

        Should result in the same query string as just the sub-expression
        would.

        The Operand shouldn't make any difference here, so we test AND and OR,
        expecting the same result.
        """
        service = DirectoryService()

        for operand in (Operand.AND, Operand.OR):
            matchExpression = MatchExpression(
                service.fieldName.shortNames, u"xyzzy"
            )
            compoundExpression = CompoundExpression(
                [matchExpression],
                operand
            )
            queryString = queryFunction(
                compoundExpression, self.attrMap(service)
            )
            expected = u"{match}".format(
                match=ldapQueryStringFromMatchExpression(
                    matchExpression, self.attrMap(service)
                )
            )
            self.assertEquals(queryString, expected)


    def test_queryStringFromCompoundExpression_multiple(
        self, queryFunction=ldapQueryStringFromCompoundExpression
    ):
        """
        Compound expression with multiple sub-expressions.

        The sub-expressions should be grouped with the given operand.
        """
        service = DirectoryService()

        for (operand, token) in ((Operand.AND, u"&"), (Operand.OR, u"|")):
            matchExpression1 = MatchExpression(
                service.fieldName.shortNames, u"xyzzy"
            )
            matchExpression2 = MatchExpression(
                service.fieldName.shortNames, u"plugh"
            )
            compoundExpression = CompoundExpression(
                [matchExpression1, matchExpression2],
                operand
            )
            queryString = queryFunction(
                compoundExpression, self.attrMap(service)
            )
            expected = u"({op}{match1}{match2})".format(
                op=token,
                match1=ldapQueryStringFromMatchExpression(
                    matchExpression1, self.attrMap(service)
                ),
                match2=ldapQueryStringFromMatchExpression(
                    matchExpression2, self.attrMap(service)
                ),
            )
            self.assertEquals(queryString, expected)


    def test_queryStringFromExpression_match(self):
        """
        Match expression.
        """
        service = DirectoryService()

        matchExpression = MatchExpression(
            service.fieldName.shortNames, u"xyzzy"
        )
        queryString = ldapQueryStringFromExpression(
            matchExpression, self.attrMap(service)
        )
        expected = ldapQueryStringFromMatchExpression(
            matchExpression, self.attrMap(service)
        )
        self.assertEquals(queryString, expected)


    def test_queryStringFromExpression_compound(self):
        """
        Compound expression.
        """
        self.test_queryStringFromCompoundExpression_single(
            queryFunction=ldapQueryStringFromExpression
        )
        self.test_queryStringFromCompoundExpression_multiple(
            queryFunction=ldapQueryStringFromExpression
        )


    def test_queryStringFromExpression_unknown(self):
        """
        Unknown expression.
        """
        service = DirectoryService()

        self.assertRaises(
            QueryNotSupportedError,
            ldapQueryStringFromExpression,
            object(), self.attrMap(service)
        )
