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
from ._constants import LDAPOperand, LDAPMatchType, LDAPMatchFlags



def ldapQueryStringFromQueryStrings(operand, queryStrings):
    """
    Combines LDAP query strings into a single query string.

    @param operand: An LDAP operand (C{u"&"} or C{u"|"}).
    @type operand: L{unicode}

    @param queryStrings: LDAP query strings.
    @type queryStrings: iterable of L{unicode}
    """
    if len(queryStrings) == 1:
        return queryStrings[0]

    elif len(queryStrings) > 1:
        queryTokens = []
        queryTokens.append(u"(")
        queryTokens.append(operand)
        queryTokens.extend(queryStrings)
        queryTokens.append(u")")
        return u"".join(queryTokens)

    else:
        return u""


def ldapQueryStringFromMatchExpression(
    expression, fieldNameToAttributeMap, recordTypeToObjectClassMap
):
    """
    Generates an LDAP query string from a match expression.

    @param expression: A match expression.
    @type expression: L{MatchExpression}

    @param fieldNameToAttributeMap: A mapping from field names to native LDAP
        attribute names.
    @type fieldNameToAttributeMap: L{dict} with L{FieldName} keys and sequence
        of L{unicode} values.

    @param recordTypeToObjectClassMap: A mapping from L{RecordType}s to native
        LDAP object class names.
    @type recordTypeToObjectClassMap: L{dict} with L{RecordType} keys and
        sequence of L{unicode} values.

    @return: An LDAP query string.
    @rtype: L{unicode}

    @raises QueryNotSupportedError: If the expression's match type is unknown,
        or if the expresion references an unknown field name (meaning a field
        name not in C{fieldNameToAttributeMap}).
    """

    matchType = LDAPMatchType.fromMatchType(expression.matchType)
    if matchType is None:
        raise QueryNotSupportedError(
            "Unknown match type: {0}".format(matchType)
        )

    flags = tuple(iterFlags(expression.flags))

    if MatchFlags.NOT in flags:
        notOp = LDAPMatchFlags.NOT.value
        operand = LDAPOperand.AND.value
    else:
        notOp = u""
        operand = LDAPOperand.OR.value

    # FIXME: It doesn't look like LDAP queries can be case sensitive.
    # This would mean that it's up to the callers to filter out the false
    # positives...
    #
    # if MatchFlags.caseInsensitive not in flags:
    #     raise NotImplementedError("Need to handle case sensitive")

    fieldName = expression.fieldName
    try:
        attributes = fieldNameToAttributeMap[fieldName]
    except KeyError:
        raise QueryNotSupportedError(
            "Unmapped field name: {0}".format(expression.fieldName)
        )

    if fieldName is FieldName.recordType:
        try:
            values = recordTypeToObjectClassMap[expression.fieldValue]
        except KeyError:
            raise QueryNotSupportedError(
                "Unmapped record type: {0}".format(expression.fieldValue)
            )
    else:
        values = (unicode(expression.fieldValue),)

    # Escape special LDAP query characters
    values = [value.translate(LDAP_QUOTING_TABLE) for value in values]
    del value  # Symbol used below; ensure non-reuse of data

    # Compose an query using each of the LDAP attributes cooresponding to the
    # target field name.

    if notOp:
        valueOperand = LDAPOperand.OR.value
    else:
        valueOperand = LDAPOperand.AND.value

    queryStrings = [
        ldapQueryStringFromQueryStrings(
            valueOperand,
            [
                matchType.queryString.format(
                    notOp=notOp, attribute=attribute, value=value
                )
                for value in values
            ]
        )
        for attribute in attributes
    ]

    return ldapQueryStringFromQueryStrings(operand, queryStrings)


def ldapQueryStringFromCompoundExpression(
    expression, fieldNameToAttributeMap, recordTypeToObjectClassMap
):
    """
    Generates an LDAP query string from a compound expression.

    @param expression: A compound expression.
    @type expression: L{MatchExpression}

    @param fieldNameToAttributeMap: A mapping from field names to native LDAP
        attribute names.
    @type fieldNameToAttributeMap: L{dict} with L{FieldName} keys and sequence
        of L{unicode} values.

    @param recordTypeToObjectClassMap: A mapping from L{RecordType}s to native
        LDAP object class names.
    @type recordTypeToObjectClassMap: L{dict} with L{RecordType} keys and
        sequence of L{unicode} values.

    @return: An LDAP query string.
    @rtype: L{unicode}

    @raises QueryNotSupportedError: If any sub-expression cannot be converted
        to an LDAP query.
    """
    if expression.operand is Operand.AND:
        operand = LDAPOperand.AND.value

    elif expression.operand is Operand.OR:
        operand = LDAPOperand.OR.value

    queryStrings = [
        ldapQueryStringFromExpression(
            subExpression,
            fieldNameToAttributeMap, recordTypeToObjectClassMap
        )
        for subExpression in expression.expressions
    ]

    return ldapQueryStringFromQueryStrings(operand, queryStrings)


def ldapQueryStringFromExpression(
    expression, fieldNameToAttributeMap, recordTypeToObjectClassMap
):
    """
    Converts an expression into an LDAP query string.

    @param expression: An expression.
    @type expression: L{MatchExpression} or L{CompoundExpression}

    @param fieldNameToAttributeMap: A mapping from field names to native LDAP
        attribute names.
    @type fieldNameToAttributeMap: L{dict} with L{FieldName} keys and sequence
        of L{unicode} values.

    @param recordTypeToObjectClassMap: A mapping from L{RecordType}s to native
        LDAP object class names.
    @type recordTypeToObjectClassMap: L{dict} with L{RecordType} keys and
        sequence of L{unicode} values.

    @return: An LDAP query string.
    @rtype: L{unicode}

    @raises QueryNotSupportedError: If the expression cannot be converted to an
        LDAP query.
    """

    if isinstance(expression, MatchExpression):
        return ldapQueryStringFromMatchExpression(
            expression, fieldNameToAttributeMap, recordTypeToObjectClassMap
        )

    if isinstance(expression, CompoundExpression):
        return ldapQueryStringFromCompoundExpression(
            expression, fieldNameToAttributeMap, recordTypeToObjectClassMap
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
