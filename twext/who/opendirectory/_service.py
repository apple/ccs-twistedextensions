# -*- test-case-name: twext.who.opendirectory.test.test_service -*-
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

from __future__ import print_function

"""
OpenDirectory directory service implementation.
"""

from uuid import UUID
from zope.interface import implementer

from twisted.internet.defer import succeed, fail, inlineCallbacks, returnValue
from twisted.web.guard import DigestCredentialFactory

from twext.python.log import Logger

from ..idirectory import (
    DirectoryServiceError, DirectoryAvailabilityError,
    InvalidDirectoryRecordError, QueryNotSupportedError,
    FieldName as BaseFieldName, RecordType as BaseRecordType,
    IPlaintextPasswordVerifier, IHTTPDigestVerifier,
)
from ..directory import (
    DirectoryService as BaseDirectoryService,
    DirectoryRecord as BaseDirectoryRecord,
)
from ..expression import (
    CompoundExpression, Operand,
    MatchExpression, MatchFlags,
)
from ..ldap._util import LDAP_QUOTING_TABLE
from ..util import ConstantsContainer, firstResult

from ._odframework import ODSession, ODNode, ODQuery
from ._constants import (
    FieldName,
    ODSearchPath, ODRecordType, ODAttribute, ODMatchType, ODAuthMethod,
)



#
# Exceptions
#

class OpenDirectoryError(DirectoryServiceError):
    """
    OpenDirectory error.
    """

    def __init__(self, message, odError=None):
        super(OpenDirectoryError, self).__init__(message)
        self.odError = odError



class OpenDirectoryConnectionError(DirectoryAvailabilityError):
    """
    OpenDirectory connection error.
    """

    def __init__(self, message, odError=None):
        super(OpenDirectoryConnectionError, self).__init__(message)
        self.odError = odError



class OpenDirectoryQueryError(OpenDirectoryError):
    """
    OpenDirectory query error.
    """



class OpenDirectoryDataError(OpenDirectoryError):
    """
    OpenDirectory data error.
    """



#
# Directory Service
#

class DirectoryService(BaseDirectoryService):
    """
    OpenDirectory directory service.
    """
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
        return u"OpenDirectory Node {self.nodeName!r}".format(self=self)


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
    #                     raise OpenDirectoryError("", e)
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
                raise OpenDirectoryConnectionError(
                    "Unable to connect to OpenDirectory node",
                    error
                )

            self._session = session
            self._node = node


    def _queryStringFromMatchExpression(self, expression):
        """
        Generates an OD query string from a match expression.

        @param expression: A match expression.
        @type expression: L{MatchExpression}

        @return: tuple(OD query string, query's OD record type string)
        @rtype: tuple(C{unicode}, C{unicode})
        """
        matchType = ODMatchType.fromMatchType(expression.matchType)
        if matchType is None:
            raise QueryNotSupportedError(
                "Unknown match type: {0}".format(matchType)
            )

        flags = tuple(expression.flags)

        if MatchFlags.NOT in flags:
            notOp = u"!"
        else:
            notOp = u""

        # if MatchFlags.caseInsensitive not in flags:
        #     raise QueryNotSupportedError(
        #         "Case sensitive searches are not supported by LDAP"
        #     )

        if expression.fieldName is self.fieldName.recordType:
            return (notOp, ODRecordType.fromRecordType(expression.fieldValue))

        if expression.fieldName is self.fieldName.uid:
            odAttr = ODAttribute.guid
            value = expression.fieldValue

        else:
            odAttr = ODAttribute.fromFieldName(expression.fieldName)
            if odAttr is None:
                raise OpenDirectoryQueryError(
                    "Unknown field name: {0}"
                    .format(expression.fieldName)
                )
            value = expression.fieldValue

        value = unicode(value)  # We want unicode
        value = value.translate(LDAP_QUOTING_TABLE)  # Escape special chars

        return (
            matchType.queryString.format(
                notOp=notOp, attribute=odAttr.value, value=value
            ),
            None,
        )


    def _queryStringFromCompoundExpression(self, expression, recordTypes):
        """
        Generates an OD query string from a compound expression.

        @param expression: A compound expression.
        @type expression: L{MatchExpression}

        @param recordTypes: allowed OD record type strings
        @type recordTypes: set(C{unicode})

        @return: tuple(OD query string, set(query's OD record type strings))
        @rtype: (C{unicode}, set(C{unicode}))
        """
        if recordTypes is None:
            recordTypes = set(ODRecordType.iterconstants())

        queryTokens = []
        for subExpression in expression.expressions:
            queryToken, subExpRecordTypes = self._queryStringFromExpression(
                subExpression, recordTypes
            )
            if subExpRecordTypes:
                if isinstance(subExpRecordTypes, unicode):
                    if bool(expression.operand is Operand.AND) != bool(queryToken): # AND or NOR
                        if expression.operand is Operand.AND:
                            recordTypes = recordTypes & set([subExpRecordTypes])
                        else:
                            recordTypes = recordTypes - set([subExpRecordTypes])
                        queryToken = None
                    else:
                        raise QueryNotSupportedError(
                            "Record type matches must AND or NOR"
                        )
                else:
                    recordTypes = subExpRecordTypes

            if queryToken:
                queryTokens.append(queryToken)

        if queryTokens:
            if len(queryTokens) > 1:
                if expression.operand is Operand.AND:
                    queryTokens[:0] = (u"&")
                else:
                    queryTokens[:0] = (u"|")

            if len(queryTokens) > 2:
                queryTokens[:0] = (u"(")
                queryTokens.append(u")")

        return (u"".join(queryTokens), recordTypes)


    def _queryStringFromExpression(self, expression, recordTypes=None):
        """
        Converts either a MatchExpression or a CompoundExpression into an LDAP
        query string.

        @param expression: An expression.
        @type expression: L{MatchExpression} or L{CompoundExpression}

        @param recordTypes: allowed OD record type strings
        @type recordTypes: set(C{unicode})

        @return: tuple(OD query string, set(query's OD record type strings))
        @rtype: (C{unicode}, set(C{unicode}))
        """

        if isinstance(expression, MatchExpression):
            return self._queryStringFromMatchExpression(
                expression
            )

        if isinstance(expression, CompoundExpression):
            return self._queryStringFromCompoundExpression(
                expression, recordTypes
            )

        raise QueryNotSupportedError(
            "Unknown expression type: {0!r}".format(expression)
        )


    def _queryFromCompoundExpression(self, expression):
        """
        Form an OpenDirectory query from a compound expression.

        @param expression: A compound expression.
        @type expression: L{CompoundExpression}

        @return: A native OpenDirectory query or None if query will return no records
        @rtype: L{ODQuery}
        """

        queryString, recordTypes = self._queryStringFromExpression(expression)
        if not recordTypes:
            return None

        if queryString:
            matchType = ODMatchType.compound.value
        else:
            matchType = ODMatchType.any.value

        query, error = self._buildQuery(
            recordTypes=recordTypes,
            matchType=matchType,
            queryString=queryString,
        )

        if error:
            self.log.error(
                "Error while forming OpenDirectory compound query: {error}",
                error=error
            )
            raise OpenDirectoryQueryError(
                "Unable to form OpenDirectory compound query", error
            )

        return query


    def _queryFromMatchExpression(self, expression, recordType=None):
        """
        Form an OpenDirectory query from a match expression.

        @param expression: A match expression.
        @type expression: L{MatchExpression}

        @param recordType: A record type to insert into the query.
        @type recordType: L{NamedConstant}

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
        matchType = matchType.value

        flags = tuple(expression.flags)

        if MatchFlags.caseInsensitive in flags:
            caseInsensitive = 0x100
        else:
            caseInsensitive = 0x0

        # For OpenDirectory, use guid for uid:
        if expression.fieldName is self.fieldName.uid:
            expression.fieldName = self.fieldName.guid

        if expression.fieldName is self.fieldName.recordType:
            if (
                recordType is not None and
                expression.fieldValue is not recordType
            ):
                raise ValueError(
                    "recordType argument does not match expression"
                )

            recordTypes = ODRecordType.fromRecordType(expression.fieldValue)
            if MatchFlags.NOT in flags:
                recordTypes = None

            matchType = ODMatchType.any.value
            queryAttribute = None
            queryValue = None

        else:
            if MatchFlags.NOT in flags:
                raise NotImplementedError()

            if recordType is None:
                recordTypes = None
            else:
                recordTypes = (ODRecordType.fromRecordType(recordType),)

            queryAttribute = ODAttribute.fromFieldName(
                expression.fieldName
            ).value

            # TODO: Add support other value types:
            valueType = self.fieldName.valueType(expression.fieldName)
            if valueType == UUID:
                queryValue = unicode(expression.fieldValue).upper()
            else:
                queryValue = unicode(expression.fieldValue)

        query, error = self._buildQuery(
            recordTypes=recordTypes,
            matchType=(matchType | caseInsensitive),
            queryAttribute=queryAttribute,
            queryString=queryValue,
        )

        if error:
            self.log.error(
                "Error while forming OpenDirectory match query: {error}",
                error=error
            )
            raise OpenDirectoryQueryError(
                "Unable to form OpenDirectory match query", error
            )

        return query


    def _buildQuery(
        self, recordTypes, matchType, queryString, queryAttribute=None
    ):
        if not hasattr(self, "_odQuery"):
            self._odQuery = getattr(
                ODQuery,
                "queryWithNode_"
                "forRecordTypes_"
                "attribute_"
                "matchType_"
                "queryValues_"
                "returnAttributes_"
                "maximumResults_error_"
            )

        if not hasattr(self, "_odAttributes"):
            self._odAttributes = [a.value for a in ODAttribute.iterconstants()]

        if recordTypes is None:
            recordTypes = ODRecordType.itervalues()

        return self._odQuery(
            self.node,                       # node
            (t.value for t in recordTypes),  # record types
            queryAttribute,                  # attribute
            matchType,                       # matchType
            queryString,                     # queryString
            self._odAttributes,              # return attributes
            0,                               # max results
            None                             # error
        )


    def _recordsFromQuery(self, query):
        """
        Executes a query and generates directory records from it.

        @param query: A query.
        @type query: L{ODQuery}

        @return: The records produced by executing the query.
        @rtype: iterable of L{DirectoryRecord}
        """

        # FIXME: This is blocking.
        # We can call scheduleInRunLoop:forMode:, which will call back to
        # its delegate...

        if query is None:
            return succeed(tuple())

        odRecords, error = query.resultsAllowingPartial_error_(False, None)

        if error:
            self.log.error(
                "Error while executing OpenDirectory query: {error}",
                error=error
            )
            return fail(OpenDirectoryQueryError(
                "Unable to execute OpenDirectory query", error
            ))

        result = []
        for odRecord in odRecords:
            try:
                record = DirectoryRecord(self, odRecord)
            except InvalidDirectoryRecordError as e:
                self.log.warn(
                    "Invalid OpenDirectory record ({error}).  "
                    "Fields: {error.fields}",
                    error=e
                )
                continue

            result.append(record)

        return succeed(result)


    def recordsFromNonCompoundExpression(self, expression, records=None):
        if isinstance(expression, MatchExpression):
            try:
                query = self._queryFromMatchExpression(expression)
                return self._recordsFromQuery(query)

            except QueryNotSupportedError:
                pass  # Let the superclass try

        return BaseDirectoryService.recordsFromNonCompoundExpression(
            self, expression
        )


    def recordsFromCompoundExpression(self, expression, records=None):
        try:
            query = self._queryFromCompoundExpression(expression)
            return self._recordsFromQuery(query)

        except QueryNotSupportedError:
            return BaseDirectoryService.recordsFromCompoundExpression(
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
                "Error while looking up user: {error}",
                error=error
            )
            raise OpenDirectoryQueryError("Unable to look up user", error)

        return record


    @inlineCallbacks
    def recordWithUID(self, uid):
        returnValue(firstResult(
            (yield self.recordsWithFieldValue(BaseFieldName.uid, uid))
        ))


    @inlineCallbacks
    def recordWithGUID(self, guid):
        returnValue(firstResult(
            (yield self.recordsWithFieldValue(BaseFieldName.guid, guid))
        ))


    @inlineCallbacks
    def recordWithShortName(self, recordType, shortName):
        try:
            query = self._queryFromMatchExpression(
                MatchExpression(self.fieldName.shortNames, shortName),
                recordType=recordType
            )
            results = yield self._recordsFromQuery(query)

            try:
                record = firstResult(results)
            except DirectoryServiceError:
                self.log.error(
                    "Duplicate records for name: {name} ({recordType})"
                    .format(name=shortName, recordType=recordType.name)
                )
                raise

            returnValue(record)

        except QueryNotSupportedError:
            # Let the superclass try
            returnValue((yield BaseDirectoryService.recordWithShortName(
                self, recordType, shortName)))



@implementer(IPlaintextPasswordVerifier, IHTTPDigestVerifier)
class DirectoryRecord(BaseDirectoryRecord):
    """
    OpenDirectory directory record.
    """

    log = Logger()

    # GUID is a required attribute for OD records.
    requiredFields = BaseDirectoryRecord.requiredFields + (BaseFieldName.guid,)


    def __init__(self, service, odRecord):
        details, error = odRecord.recordDetailsForAttributes_error_(None, None)

        if error:
            self.log.error(
                "Error while reading OpenDirectory record: {error}",
                error=error
            )
            raise OpenDirectoryDataError(
                "Unable to read OpenDirectory record", error
            )

        def coerceType(fieldName, value):
            # Record type field value needs to be looked up
            if fieldName is service.fieldName.recordType:
                return ODRecordType.lookupByValue(value).recordType

            # Otherwise, cast to the valueType specified by the field name
            valueType = service.fieldName.valueType(fieldName)
            try:
                return valueType(value)
            except BaseException as e:
                raise OpenDirectoryDataError(
                    "Unable to coerce OD value {0!r} to type {1}: {2}"
                    .format(value, valueType, e)
                )

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
                values = (coerceType(fieldName, values),)
            else:
                values = tuple(coerceType(fieldName, v) for v in values)

            if service.fieldName.isMultiValue(fieldName):
                fields[fieldName] = values
            else:
                assert len(values) == 1
                fields[fieldName] = values[0]

        # Set uid from guid
        try:
            guid = fields[service.fieldName.guid]
        except KeyError:
            raise InvalidDirectoryRecordError(
                "GUID field is required.", fields
            )

        fields[service.fieldName.uid] = unicode(guid).upper()

        super(DirectoryRecord, self).__init__(service, fields)
        self._odRecord = odRecord


    def __hash__(self):
        return hash(self.guid)


    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.service == other.service and
                self.guid == other.guid
            )
        return NotImplemented


    #
    # Verifiers for twext.who.checker stuff.
    #

    def verifyPlaintextPassword(self, password):
        result, error = self._odRecord.verifyPassword_error_(password, None)

        if error:
            return succeed(False)

        return succeed(result)


    def verifyHTTPDigest(
        self, username, realm, uri, nonce, cnonce,
        algorithm, nc, qop, response, method,
    ):
        challenge = (
            'Digest realm="{realm}", nonce="{nonce}", algorithm={algorithm}'
            .format(
                realm=realm, nonce=nonce, algorithm=algorithm
            )
        )

        if qop:
            responseArg = (
                'username="%s",realm="%s",algorithm=%s,'
                'nonce="%s",cnonce="%s",nc=%s,qop=%s,'
                'digest-uri="%s",response=%s'
                % (
                    username, realm, algorithm, nonce, cnonce, nc, qop,
                    uri, response
                )
            )
        else:
            responseArg = (
                'Digest username="%s", uri="%s", response=%s'
                % (username, uri, response)
            )

        # print("username = {0!r}".format(username))
        # print("realm = {0!r}".format(realm))
        # print("uri = {0!r}".format(uri))
        # print("nonce = {0!r}".format(nonce))
        # print("cnonce = {0!r}".format(cnonce))
        # print("algorithm = {0!r}".format(algorithm))
        # print("nc = {0!r}".format(nc))
        # print("qop = {0!r}".format(qop))
        # print("response = {0!r}".format(response))
        # print("method = {0!r}".format(method))
        # print("challenge = {0!r}".format(challenge))

        result, m1, m2, error = self._odRecord.verifyExtendedWithAuthenticationType_authenticationItems_continueItems_context_error_(
            ODAuthMethod.digestMD5.value,
            [username, challenge, responseArg, method],
            None, None, None
        )

        # print(result, m1, m2, error)

        if error:
            return succeed(False)

        return succeed(result)


    @inlineCallbacks
    def members(self):
        members = set()
        for uid in getattr(self, "memberUIDs", ()):
            members.add((yield self.service.recordWithUID(uid)))
        for uid in getattr(self, "nestedGroupsUIDs", ()):
            members.add((yield self.service.recordWithUID(uid)))
        returnValue(members)


    # @inlineCallbacks
    # FIXME: need to implement
    def groups(self):
        groups = set()
        return succeed(groups)



class NoQOPDigestCredentialFactory(DigestCredentialFactory):
    """
    DigestCredentialFactory without qop, to interop with OD.
    """

    def getChallenge(self, address):
        result = DigestCredentialFactory.getChallenge(self, address)
        del result["qop"]
        return result
