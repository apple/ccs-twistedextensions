# -*- test-case-name: twext.who.opendirectory.test.test_service -*-
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

from __future__ import print_function

"""
OpenDirectory directory service implementation.
"""

from odframework import ODSession, ODNode, ODQuery

from twisted.python.constants import Names, NamedConstant
from twisted.python.constants import Values, ValueConstant

from twext.python.log import Logger

from ..idirectory import (
    DirectoryServiceError, QueryNotSupportedError,
    FieldName as BaseFieldName, RecordType as BaseRecordType,
)
from ..directory import (
    DirectoryService as BaseDirectoryService,
    DirectoryRecord as BaseDirectoryRecord,
)
from ..expression import (
    CompoundExpression, Operand, MatchExpression, MatchType, MatchFlags,
)
from ..util import iterFlags, ConstantsContainer

from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.credentials import IUsernamePassword, IUsernameHashedPassword
from twisted.cred.error import UnauthorizedLogin

from zope.interface import implements
from twisted.internet.defer import succeed, fail
from twisted.web.guard import DigestCredentialFactory
from twisted.cred.credentials import DigestedCredentials




#
# Exceptions
#

class OpenDirectoryError(DirectoryServiceError):
    """
    OpenDirectory error.
    """

    def __init__(self, message, odError):
        super(OpenDirectoryError, self).__init__(message)
        self.odError = odError



class OpenDirectoryConnectionError(OpenDirectoryError):
    """
    OpenDirectory connection error.
    """



class OpenDirectoryQueryError(OpenDirectoryError):
    """
    OpenDirectory query error.
    """



#
# Constants
#

class FieldName(Names):
    searchPath = NamedConstant()
    searchPath.description = "search path"
    searchPath.multiValue = False

    metaNodeLocation = NamedConstant()
    metaNodeLocation.description = "source OD node"
    metaNodeLocation.multiValue = False

    metaRecordName = NamedConstant()
    metaRecordName.description = "meta record name"
    metaRecordName.multiValue = False



#
# OD Constants
#

class ODSearchPath(Values):
    local = ValueConstant("/Local/Default")
    search = ValueConstant("/Search")



class ODRecordType(Values):
    user = ValueConstant("dsRecTypeStandard:Users")
    user.recordType = BaseRecordType.user

    group = ValueConstant("dsRecTypeStandard:Groups")
    group.recordType = BaseRecordType.group


    @classmethod
    def fromRecordType(cls, recordType):
        if not hasattr(cls, "_recordTypeByRecordType"):
            cls._recordTypeByRecordType = dict((
                (recordType.recordType, recordType)
                for recordType in cls.iterconstants()
            ))

        return cls._recordTypeByRecordType.get(recordType, None)



class ODAttribute(Values):
    searchPath = ValueConstant("dsAttrTypeStandard:SearchPath")
    searchPath.fieldName = FieldName.searchPath

    recordType = ValueConstant("dsAttrTypeStandard:RecordType")
    recordType.fieldName = BaseFieldName.recordType

    uid = ValueConstant("dsAttrTypeStandard:GeneratedUID")
    uid.fieldName = BaseFieldName.uid

    guid = ValueConstant("dsAttrTypeStandard:GeneratedUID")
    guid.fieldName = BaseFieldName.guid

    shortName = ValueConstant("dsAttrTypeStandard:RecordName")
    shortName.fieldName = BaseFieldName.shortNames

    fullName = ValueConstant("dsAttrTypeStandard:RealName")
    fullName.fieldName = BaseFieldName.fullNames

    emailAddress = ValueConstant("dsAttrTypeStandard:EMailAddress")
    emailAddress.fieldName = BaseFieldName.emailAddresses

    metaNodeLocation = ValueConstant(
        "dsAttrTypeStandard:AppleMetaNodeLocation"
    )
    metaNodeLocation.fieldName = FieldName.metaNodeLocation

    metaRecordName = ValueConstant("dsAttrTypeStandard:AppleMetaRecordName")
    metaRecordName.fieldName = FieldName.metaRecordName


    @classmethod
    def fromFieldName(cls, fieldName):
        if not hasattr(cls, "_attributesByFieldName"):
            cls._attributesByFieldName = dict((
                (attribute.fieldName, attribute)
                for attribute in cls.iterconstants()
                if hasattr(attribute, "fieldName")
            ))

        return cls._attributesByFieldName.get(fieldName, None)



class ODMatchType(Values):
    equals = ValueConstant(0x2001)
    equals.matchType = MatchType.equals

    startsWith = ValueConstant(0x2002)
    startsWith.matchType = MatchType.startsWith

    endsWith = ValueConstant(0x2003)
    endsWith.matchType = MatchType.endsWith

    contains = ValueConstant(0x2004)
    contains.matchType = MatchType.contains

    lessThan = ValueConstant(0x2005)
    lessThan.matchType = MatchType.lessThan

    greaterThan = ValueConstant(0x2006)
    greaterThan.matchType = MatchType.greaterThan

    lessThanOrEqualTo = ValueConstant(0x2007)
    lessThanOrEqualTo.matchType = MatchType.lessThanOrEqualTo

    greaterThanOrEqualTo = ValueConstant(0x2008)
    greaterThanOrEqualTo.matchType = MatchType.greaterThanOrEqualTo

    compound = ValueConstant(0x210B)
    compound.matchType = MatchType.compound


    @classmethod
    def fromMatchType(cls, matchType):
        if not hasattr(cls, "_matchTypeByMatchType"):
            cls._matchTypeByMatchType = dict((
                (matchType.matchType, matchType)
                for matchType in cls.iterconstants()
            ))

        return cls._matchTypeByMatchType.get(matchType, None)



class ODMatchFlags(Values):
    caseInsensitive = ValueConstant(0x100)



#
# Directory Service
#

class DirectoryService(BaseDirectoryService):
    """
    OpenDirectory directory service.
    """

    implements(ICredentialsChecker)
    credentialInterfaces = (IUsernamePassword, IUsernameHashedPassword)

    log = Logger()

    recordType = ConstantsContainer((
        BaseRecordType.user, BaseRecordType.group,
    ))

    fieldName = ConstantsContainer((BaseDirectoryService.fieldName, FieldName))



    def __init__(self, nodeName=ODSearchPath.search.value):
        """
        @param nodeName: the OpenDirectory node to query against.
        @type nodeName: bytes
        """
        self._nodeName = nodeName


    @property
    def nodeName(self):
        return self._nodeName


    @property
    def realmName(self):
        return "OpenDirectory Node {self.nodeName!r}".format(self=self)


    @property
    def session(self):
        """
        Get the underlying directory session.
        """
        self._connect()
        return self._session


    @property
    def node(self):
        """
        Get the underlying (network) directory node.
        """
        self._connect()
        return self._node


    # @property
    # def localNode(self):
    #     """
    #     Get the local node from the search path (if any), so that we can
    #     handle it specially.
    #     """
    #     if not hasattr(self, "_localNode"):
    #         if self.nodeName == ODSearchPath.search.value:
    #             result = getNodeAttributes(
    #                 self.node, ODSearchPath.search.value,
    #                 (ODAttribute.searchPath.value,)
    #             )
    #             if (
    #                 ODSearchPath.local.value in
    #                 result[ODAttribute.searchPath.value]
    #             ):
    #                 try:
    #                     self._localNode = odInit(ODSearchPath.local.value)
    #                 except ODError, e:
    #                     self.log.error(
    #                         "Failed to open local node: {error}}",
    #                         error=e,
    #                     )
    #                     raise OpenDirectoryError(e)
    #             else:
    #                 self._localNode = None

    #         elif self.nodeName == ODSearchPath.local.value:
    #             self._localNode = self.node

    #         else:
    #             self._localNode = None

    #     return self._localNode


    def _connect(self):
        """
        Connect to the directory server.

        @raises: L{OpenDirectoryConnectionError} if unable to connect.
        """
        if not hasattr(self, "_session"):
            session = ODSession.defaultSession()

            node, error = ODNode.nodeWithSession_name_error_(
                session, self.nodeName, None
            )

            if error:
                self.log.error(
                    "Error while trying to connect to OpenDirectory node "
                    "{source.nodeName!r}: {error}",
                    error=error
                )
                raise OpenDirectoryConnectionError(error)

            self._session = session
            self._node = node


    def _queryStringFromExpression(self, expression):
        """
        Converts either a MatchExpression or a CompoundExpression into a native
        OpenDirectory query string.

        @param expression: The expression
        @type expression: Either L{MatchExpression} or L{CompoundExpression}

        @return: A native OpenDirectory query string
        @rtype: C{unicode}
        """

        if isinstance(expression, MatchExpression):
            matchType = ODMatchType.fromMatchType(expression.matchType)
            if matchType is None:
                raise QueryNotSupportedError(
                    "Unknown match type: {0}".format(matchType)
                )
            odAttr = ODAttribute.fromFieldName(expression.fieldName).value
            queryString = {
                ODMatchType.equals.value: u"({attr}={value})",
                ODMatchType.startsWith.value: u"({attr}={value}*)",
                ODMatchType.endsWith.value: u"({attr}=*{value})",
                ODMatchType.contains.value: u"({attr}=*{value}*)",
                ODMatchType.lessThan.value: u"({attr}<{value})",
                ODMatchType.greaterThan.value: u"({attr}>{value})",
            }.get(matchType.value, u"({attr}=*{value}*)").format(
                attr=odAttr,
                value=expression.fieldValue
            )

        elif isinstance(expression, CompoundExpression):
            queryString = u""
            operand = u"&" if expression.operand is Operand.AND else u"|"
            if len(expression.expressions) > 1:
                queryString += u"("
                queryString += operand
            for subExpression in expression.expressions:
                queryString += self._queryStringFromExpression(subExpression)
            if len(expression.expressions) > 1:
                queryString += u")"

        return queryString


    def _queryFromCompoundExpression(self, expression):
        """
        Form an OpenDirectory query from a compound expression.

        @param expression: The compound expression.
        @type expression: L{CompoundExpression}

        @return: A native OpenDirectory query.
        @rtype: L{ODQuery}
        """

        queryString = self._queryStringFromExpression(expression)

        recordTypes = [t.value for t in ODRecordType.iterconstants()]
        attributes = [a.value for a in ODAttribute.iterconstants()]
        maxResults = 0

        query, error = ODQuery.queryWithNode_forRecordTypes_attribute_matchType_queryValues_returnAttributes_maximumResults_error_(
            self.node,
            recordTypes,
            None,
            ODMatchType.compound.value,
            queryString,
            attributes,
            maxResults,
            None
        )

        if error:
            self.log.error(
                "Error while forming OpenDirectory query: {error}",
                error=error
            )
            raise OpenDirectoryQueryError(error)

        return query



    def _queryFromMatchExpression(self, expression):
        """
        Form an OpenDirectory query from a match expression.

        @param expression: The match expression.
        @type expression: L{MatchExpression}

        @return: A native OpenDirectory query.
        @rtype: L{ODQuery}
        """
        if not isinstance(expression, MatchExpression):
            raise TypeError(expression)

        matchType = ODMatchType.fromMatchType(expression.matchType)
        if matchType is None:
            raise QueryNotSupportedError(
                "Unknown match type: {0}".format(matchType)
            )

        if MatchFlags.caseInsensitive in iterFlags(expression.flags):
            caseInsensitive = 0x100
        else:
            caseInsensitive = 0x0

        if expression.fieldName is self.fieldName.recordType:
            raise NotImplementedError()

        else:
            recordTypes = [t.value for t in ODRecordType.iterconstants()]
            attributes = [a.value for a in ODAttribute.iterconstants()]
            maxResults = 0

        query, error = ODQuery.queryWithNode_forRecordTypes_attribute_matchType_queryValues_returnAttributes_maximumResults_error_(
            self.node,
            recordTypes,
            ODAttribute.fromFieldName(expression.fieldName).value,
            matchType.value | caseInsensitive,
            expression.fieldValue,
            attributes,
            maxResults,
            None
        )

        if error:
            self.log.error(
                "Error while forming OpenDirectory query: {error}",
                error=error
            )
            raise OpenDirectoryQueryError(error)

        return query


    def _adaptODRecord(self, odRecord):
        """
        Adapt a native OpenDirectory record to a L{DirectoryRecord}.

        @param odRecord: A native OpenDirectory record.
        @type odRecord: L{ODRecord}

        @return: A directory record with the fields matching the attributes of
            C{odRecord}.
        @rtype: L{DirectoryRecord}
        """
        details, error = odRecord.recordDetailsForAttributes_error_(None, None)

        if error:
            self.log.error(
                "Error while reading OpenDirectory record: {error}",
                error=error
            )
            raise OpenDirectoryQueryError(error)

        fields = {}
        for name, values in details.iteritems():
            if name == ODAttribute.metaRecordName.value:
                # We get this field even though we did not ask for it...
                continue

            try:
                attribute = ODAttribute.lookupByValue(name)
            except ValueError:
                self.log.debug(
                    "Unexpected OpenDirectory record attribute: {attribute}",
                    attribute=name
                )
                continue
            fieldName = attribute.fieldName

            if type(values) is bytes:
                values = (unicode(values),)
            else:
                values = [unicode(v) for v in values]

            if BaseFieldName.isMultiValue(fieldName):
                fields[fieldName] = values
            else:
                assert len(values) == 1

                if fieldName is self.fieldName.recordType:
                    fields[fieldName] = ODRecordType.lookupByValue(
                        values[0]
                    ).recordType
                else:
                    fields[fieldName] = values[0]

        return DirectoryRecord(self, fields)


    def _recordsFromQuery(self, query):
        """
        Executes a query and generates directory records from it.

        @param query: A query.
        @type query: L{ODQuery}

        @return: The records produced by executing the query.
        @rtype: iterable of L{DirectoryRecord}
        """

        odRecords, error = query.resultsAllowingPartial_error_(False, None)

        if error:
            self.log.error(
                "Error while executing OpenDirectory query: {error}",
                error=error
            )
            raise OpenDirectoryQueryError(error)

        for odRecord in odRecords:
            yield self._adaptODRecord(odRecord)



    def recordsFromExpression(self, expression):
        """
        @param expression: an expression to apply
        @type expression: L{MatchExpression} or L{CompoundExpression}

        @return: The matching records.
        @rtype: deferred iterable of L{IDirectoryRecord}s

        @raises: L{QueryNotSupportedError} if the expression is not
            supported by this directory service.
        """

        try:
            if isinstance(expression, CompoundExpression):
                query = self._queryFromCompoundExpression(expression)
                return self._recordsFromQuery(query)

            elif isinstance(expression, MatchExpression):
                query = self._queryFromMatchExpression(expression)
                return self._recordsFromQuery(query)

        except QueryNotSupportedError:
            pass

        return BaseDirectoryService.recordsFromExpression(
            self, expression
        )


    def _getUserRecord(self, username):
        """
        Fetch the OD record for a given user.

        @return: ODRecord, or None
        """
        record, error = self.node.recordWithRecordType_name_attributes_error_(
            ODRecordType.user.value, username, None, None
        )
        if error:
            self.log.error(
                "Error while executing OpenDirectory query: {error}",
                error=error
            )
            raise OpenDirectoryQueryError("Could not look up user", error)

        return record


    def requestAvatarId(self, credentials):
        """
        Authenticate the credentials against OpenDirectory and return the
        corresponding directory record.

        @param: credentials: The credentials to authenticate.
        @type: credentials: L{ICredentials}

        @return: The directory record for the given credentials.
        @rtype: deferred L{DirectoryRecord}

        @raises: L{UnauthorizedLogin} if the credentials are not valid.
        """

        record = self._getUserRecord(credentials.username)

        if record is not None:

            if IUsernamePassword.providedBy(credentials):
                result, error = record.verifyPassword_error_(
                    credentials.password, None
                )
                if not error and result:
                    return succeed(self._adaptODRecord(record))

            elif isinstance(credentials, DigestedCredentials):
                try:
                    credentials.fields.setdefault("algorithm", "md5")
                    challenge = (
                        'Digest realm="{realm}", nonce="{nonce}", '
                        'algorithm={algorithm}'
                        .format(**credentials.fields)
                    )
                    response = credentials.fields["response"]
                except KeyError as e:
                    self.log.error(
                        "Error authenticating against OpenDirectory: "
                        "missing digest response field {field!r} in "
                        "{credentials.fields!r}",
                        field=e.args[0], credentials=credentials
                    )
                    return fail(UnauthorizedLogin())

                result, m1, m2, error = record.verifyExtendedWithAuthenticationType_authenticationItems_continueItems_context_error_(
                    "dsAuthMethodStandard:dsAuthNodeDIGEST-MD5",
                    [
                        credentials.username,
                        challenge,
                        response,
                        credentials.method,
                    ],
                    None, None, None
                )

                if not error and result:
                    return succeed(self._adaptODRecord(record))

        return fail(UnauthorizedLogin())


class CustomDigestCredentialFactory(DigestCredentialFactory):
    """
    DigestCredentialFactory without qop, to interop with OD.
    """

    def getChallenge(self, address):
        result = DigestCredentialFactory.getChallenge(self, address)
        del result["qop"]
        return result


class DirectoryRecord(BaseDirectoryRecord):
    """
    OpenDirectory directory record.
    """

    def __init__(self, service, fields):
         # Make sure that uid and guid are both set and equal
        uid = fields.get(service.fieldName.uid, None)
        guid = fields.get(service.fieldName.guid, None)

        if uid is not None and guid is not None:
            if uid != guid:
                raise ValueError(
                    "uid and guid must be equal ({uid} != {guid})"
                    .format(uid=uid, guid=guid)
                )
        elif uid is None:
            fields[service.fieldName.uid] = guid
        elif guid is None:
            fields[service.fieldName.guid] = uid

        super(DirectoryRecord, self).__init__(service, fields)


    requiredFields = BaseDirectoryRecord.requiredFields + (BaseFieldName.guid,)





if __name__ == "__main__":
    import sys

    service = DirectoryService()
    print(
        "Service = {service}\n"
        "Session = {service.session}\n"
        "Node = {service.node}\n"
        # "Local node = {service.localNode}\n"
        .format(service=service)
    )
    print("-" * 80)

    for shortName in sys.argv[1:]:
        print("Looking up short name: {0}".format(shortName))

        matchExpression = MatchExpression(
            service.fieldName.shortNames, shortName,
            matchType=MatchType.equals,
        )
        queryString = service._queryStringFromExpression(matchExpression)
        print(
            "\n...via MatchExpression, query={query!r}"
            .format(query=queryString)
        )
        print()

        for record in service.recordsFromExpression(matchExpression):
            print(record.description())

        compoundExpression = CompoundExpression(
            [
                MatchExpression(
                    service.fieldName.shortNames, shortName,
                    matchType=MatchType.contains
                ),
                MatchExpression(
                    service.fieldName.emailAddresses, shortName,
                    matchType=MatchType.contains
                ),
            ],
            Operand.OR
        )
        queryString = service._queryStringFromExpression(compoundExpression)
        print(
            "\n...via CompoundExpression, query={query!r}"
            .format(query=queryString)
        )
        print()

        for record in service.recordsFromExpression(compoundExpression):
            print(record.description())
            print()
