# -*- test-case-name: twext.who.ldap.test.test_util -*-
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

from ..idirectory import QueryNotSupportedError, FieldName
from ..expression import (
    CompoundExpression, Operand,
    MatchExpression, MatchFlags,
)
from ..util import iterFlags
from ._constants import LDAPMatchType



def ldapQueryStringFromMatchExpression(
    expression, fieldNameMap, recordTypeMap
):
    """
    Generates an LDAP query string from a match expression.

    @param expression: A match expression.
    @type expression: L{MatchExpression}

    @param fieldNameMap: A mapping from L{FieldName}s to native LDAP attribute
        names.
    @type fieldNameMap: L{dict}

    @param recordTypeMap: A mapping from L{RecordType}s to native LDAP object
        class names.
    @type recordTypeMap: L{dict}

    @return: An LDAP query string.
    @rtype: C{unicode}

    @raises QueryNotSupportedError: If the expression's match type is unknown,
        or if the expresion references an unknown field name (meaning a field
        name not in C{fieldNameMap}).
    """
    matchType = LDAPMatchType.fromMatchType(expression.matchType)
    if matchType is None:
        raise QueryNotSupportedError(
            "Unknown match type: {0}".format(matchType)
        )

    flags = tuple(iterFlags(expression.flags))

    if MatchFlags.NOT in flags:
        notOp = u"!"
    else:
        notOp = u""

    # FIXME: It doesn't look like LDAP queries can be case sensitive.
    # This would mean that it's up to the callers to filter out the false
    # positives...
    #
    # if MatchFlags.caseInsensitive not in flags:
    #     raise NotImplementedError("Need to handle case sensitive")

    fieldName = expression.fieldName
    try:
        attribute = fieldNameMap[fieldName]
    except KeyError:
        raise QueryNotSupportedError(
            "Unmapped field name: {0}".format(expression.fieldName)
        )

    if fieldName is FieldName.recordType:
        try:
            value = recordTypeMap[expression.fieldValue]
        except KeyError:
            raise QueryNotSupportedError(
                "Unmapped record type: {0}".format(expression.fieldValue)
            )
    else:
        value = unicode(expression.fieldValue)

    value = value.translate(LDAP_QUOTING_TABLE)  # Escape special chars

    return matchType.queryString.format(
        notOp=notOp, attribute=attribute, value=value
    )


def ldapQueryStringFromCompoundExpression(
    expression, fieldNameMap, recordTypeMap
):
    """
    Generates an LDAP query string from a compound expression.

    @param expression: A compound expression.
    @type expression: L{MatchExpression}

    @param fieldNameMap: A mapping from L{FieldName}s to native LDAP attribute
        names.
    @type fieldNameMap: L{dict}

    @return: An LDAP query string.
    @rtype: C{unicode}

    @raises QueryNotSupportedError: If any sub-expression cannot be converted
        to an LDAP query.
    """
    queryTokens = []

    if len(expression.expressions) > 1:
        queryTokens.append(u"(")

        if expression.operand is Operand.AND:
            queryTokens.append(u"&")
        else:
            queryTokens.append(u"|")

    for subExpression in expression.expressions:
        queryTokens.append(
            ldapQueryStringFromExpression(
                subExpression, fieldNameMap, recordTypeMap
            )
        )

    if len(expression.expressions) > 1:
        queryTokens.append(u")")

    return u"".join(queryTokens)


def ldapQueryStringFromExpression(
    expression, fieldNameMap, recordTypeMap
):
    """
    Converts an expression into an LDAP query string.

    @param fieldNameMap: A mapping from L{FieldName}s to native LDAP attribute
        names.
    @type fieldNameMap: L{dict}

    @param expression: An expression.
    @type expression: L{MatchExpression} or L{CompoundExpression}

    @return: A native OpenDirectory query string
    @rtype: C{unicode}

    @raises QueryNotSupportedError: If the expression cannot be converted to an
        LDAP query.
    """

    if isinstance(expression, MatchExpression):
        return ldapQueryStringFromMatchExpression(
            expression, fieldNameMap, recordTypeMap
        )

    if isinstance(expression, CompoundExpression):
        return ldapQueryStringFromCompoundExpression(
            expression, fieldNameMap, recordTypeMap
        )

    raise QueryNotSupportedError(
        "Unknown expression type: {0!r}".format(expression)
    )


LDAP_QUOTING_TABLE = {
    ord(u"\\"): u"\\5C",
    ord(u"/"): u"\\2F",

    ord(u"("): u"\\28",
    ord(u")"): u"\\29",
    ord(u"*"): u"\\2A",

    ord(u"<"): u"\\3C",
    ord(u"="): u"\\3D",
    ord(u">"): u"\\3E",
    ord(u"~"): u"\\7E",

    ord(u"&"): u"\\26",
    ord(u"|"): u"\\7C",

    ord(u"\0"): u"\\00",
}
