##
# Copyright (c) 2014 Apple Inc. All rights reserved.
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
LDAP constants.
"""

from twisted.python.constants import (
    Names, NamedConstant,  # Values, ValueConstant
)

from ..expression import MatchType



class LDAPMatchType(Names):
    """
    Constants for native LDAP match types.

    For each constant defined, if there is an equivalent L{MatchType} constant,
    the attribute C{matchType} reference that constant.  It is otherwise unset.

    For each constant defined, the attribute C{queryString} will be a
    L{unicode} format string that, when formatted, is an LDAP query string
    (eg. C{(attribute=value)}).  The format string may reference the following
    names:

      - C{notOp} for the "not" operator, which may be C{u"!"} or C{u""}.
      - C{attribute} for the name of the LDAP attribute to match.
      - C{value} for the value to match against.

    @cvar any: Attribute has any value.
    @cvar equals: Attribute equals value.
    @cvar startsWith: Attribute starts with value.
    @cvar endsWith: Attribute ends with value.
    @cvar contains: Attribute contains value.
    @cvar lessThan: Attribute is less than value.
    @cvar greaterThan: Attribute is greater than value.
    @cvar lessThanOrEqualTo: Attribute is less than or equal to value.
    @cvar greaterThanOrEqualTo: Attribute is greater than or equal to value.
    """

    any = NamedConstant()
    any.queryString = u"({notOp}{attribute}=*)"

    equals = NamedConstant()
    equals.matchType = MatchType.equals
    equals.queryString = u"({notOp}{attribute}={value})"

    startsWith = NamedConstant()
    startsWith.matchType = MatchType.startsWith
    startsWith.queryString = u"({notOp}{attribute}={value}*)"

    endsWith = NamedConstant()
    endsWith.matchType = MatchType.endsWith
    endsWith.queryString = u"({notOp}{attribute}=*{value})"

    contains = NamedConstant()
    contains.matchType = MatchType.contains
    contains.queryString = u"({notOp}{attribute}=*{value}*)"

    lessThan = NamedConstant()
    lessThan.matchType = MatchType.lessThan
    lessThan.queryString = u"({notOp}{attribute}<{value})"

    greaterThan = NamedConstant()
    greaterThan.matchType = MatchType.greaterThan
    greaterThan.queryString = u"({notOp}{attribute}>{value})"

    lessThanOrEqualTo = NamedConstant()
    lessThanOrEqualTo.matchType = MatchType.lessThanOrEqualTo
    lessThanOrEqualTo.queryString = u"({notOp}{attribute}<={value})"

    greaterThanOrEqualTo = NamedConstant()
    greaterThanOrEqualTo.matchType = MatchType.greaterThanOrEqualTo
    greaterThanOrEqualTo.queryString = u"({notOp}{attribute}>={value})"


    @classmethod
    def fromMatchType(cls, matchType):
        """
        Look up an L{LDAPMatchType} from a L{MatchType}.

        @param matchType: A match type.
        @type matchType: L{MatchType}

        @return: The cooresponding LDAP match type.
        @rtype: L{LDAPMatchType}
        """
        if not hasattr(cls, "_matchTypeByMatchType"):
            cls._matchTypeByMatchType = dict((
                (matchType.matchType, matchType)
                for matchType in cls.iterconstants()
                if hasattr(matchType, "matchType")
            ))

        return cls._matchTypeByMatchType.get(matchType, None)
