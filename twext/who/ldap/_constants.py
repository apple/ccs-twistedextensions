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
    Names, NamedConstant, Values, ValueConstant
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



class RFC4519Attribute(Values):
    """
    See U{RFC 4519, section 2<http://tools.ietf.org/html/rfc4519#section-2>}.
    """
    businessCategory = ValueConstant(u"businessCategory")
    countryName = ValueConstant(u"c")
    commonName = ValueConstant(u"cn")
    domainComponent = ValueConstant(u"dc")
    description = ValueConstant(u"description")
    destinationIndicator = ValueConstant(u"destinationIndicator")
    distinguishedName = ValueConstant(u"distinguishedName")
    dnQualifier = ValueConstant(u"dnQualifier")
    enhancedSearchGuide = ValueConstant(u"enhanced search guide")
    facsimileTelephoneNumber = ValueConstant(u"facsimileTelephoneNumber")
    generationQualifier = ValueConstant(u"generationQualifier")
    givenName = ValueConstant(u"givenName")
    houseIdentifier = ValueConstant(u"houseIdentifier")
    initials = ValueConstant(u"initials")
    internationalISDNNumber = ValueConstant(u"internationalISDNNumber")
    localityName = ValueConstant(u"l")
    member = ValueConstant(u"member")
    name = ValueConstant(u"name")
    organizationName = ValueConstant(u"o")
    organizationalUnitName = ValueConstant(u"ou")
    owner = ValueConstant(u"owner")
    physicalDeliveryOfficeName = ValueConstant(u"physicalDeliveryOfficeName")
    postalAddress = ValueConstant(u"postalAddress")
    postalCode = ValueConstant(u"postalCode")
    postOfficeBox = ValueConstant(u"postOfficeBox")
    preferredDeliveryMethod = ValueConstant(u"preferredDeliveryMethod")
    registeredAddress = ValueConstant(u"registeredAddress")
    roleOccupant = ValueConstant(u"roleOccupant")
    searchGuide = ValueConstant(u"searchGuide")
    seeAlso = ValueConstant(u"seeAlso")
    serialNumber = ValueConstant(u"serialNumber")
    surname = ValueConstant(u"sn")
    stateOrProvinceName = ValueConstant(u"st")
    street = ValueConstant(u"street")
    telephoneNumber = ValueConstant(u"telephoneNumber")
    teletexTerminalIdentifier = ValueConstant(u"teletexTerminalIdentifier")
    telexNumber = ValueConstant(u"telexNumber")
    title = ValueConstant(u"title")
    userid = ValueConstant(u"uid")
    uniqueMember = ValueConstant(u"uniqueMember")
    userPassword = ValueConstant(u"userPassword")
    x121Address = ValueConstant(u"x121Address")
    x500UniqueIdentifier = ValueConstant(u"x500UniqueIdentifier")


for c in RFC4519Attribute.iterconstants():
    if c.name != c.value:
        setattr(RFC4519Attribute, c.value, c)


class RFC4519ObjectClass(Values):
    """
    See U{RFC 4519, section 3<http://tools.ietf.org/html/rfc4519#section-2>}.
    """
    applicationProcess = ValueConstant(u"applicationProcess")
    country = ValueConstant(u"country")
    dcObject = ValueConstant(u"dcObject")
    device = ValueConstant(u"device")
    groupOfNames = ValueConstant(u"groupOfNames")
    groupOfUniqueNames = ValueConstant(u"groupOfUniqueNames")
    locality = ValueConstant(u"locality")
    organization = ValueConstant(u"organization")
    organizationalPerson = ValueConstant(u"organizationalPerson")
    organizationalRole = ValueConstant(u"organizationalRole")
    organizationalUnit = ValueConstant(u"organizationalUnit")
    person = ValueConstant(u"person")
    residentialPerson = ValueConstant(u"residentialPerson")
    uidObject = ValueConstant(u"uidObject")
