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

from zope.interface import implementer

from twisted.python.constants import Names, NamedConstant
from twisted.internet.defer import succeed, fail
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
    # CompoundExpression, Operand,
    MatchExpression, MatchFlags,
)
from ..util import iterFlags, ConstantsContainer

from ._odframework import ODSession, ODNode, ODQuery
from ._constants import (
    ODSearchPath, ODRecordType, ODAttribute, ODMatchType, ODAuthMethod
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
# Constants
#

class FieldName(Names):
    searchPath = NamedConstant()
    searchPath.description = u"search path"
    searchPath.multiValue = False

    metaNodeLocation = NamedConstant()
    metaNodeLocation.description = u"source OD node"
    metaNodeLocation.multiValue = False

    metaRecordName = NamedConstant()
    metaRecordName.description = u"meta record name"
    metaRecordName.multiValue = False



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


    # def _queryStringFromExpression(self, expression):
    #     """
    #     Converts either a MatchExpression or a CompoundExpression into a
    #     native OpenDirectory query string.

    #     @param expression: The expression
    #     @type expression: Either L{MatchExpression} or L{CompoundExpression}

    #     @return: A native OpenDirectory query string
    #     @rtype: C{unicode}
    #     """

    #     if isinstance(expression, MatchExpression):
    #         matchType = ODMatchType.fromMatchType(expression.matchType)
    #         if matchType is None:
    #             raise QueryNotSupportedError(
    #                 "Unknown match type: {0}".format(matchType)
    #             )

    #         if expression.fieldName is self.fieldName.uid:
    #             odAttr = ODAttribute.guid.value
    #             value = expression.fieldValue
    #         else:
    #             odAttr = ODAttribute.fromFieldName(expression.fieldName)
    #             if odAttr is None:
    #                 raise OpenDirectoryQueryError(
    #                     "Unknown field name: {0}"
    #                     .format(expression.fieldName)
    #                 )
    #             odAttr = odAttr.value
    #             value = expression.fieldValue

    #         value = unicode(value)

    #         # FIXME: Shouldn't the value be quoted somehow?
    #         queryString = {
    #             ODMatchType.equals.value: u"({attr}={value})",
    #             ODMatchType.startsWith.value: u"({attr}={value}*)",
    #             ODMatchType.endsWith.value: u"({attr}=*{value})",
    #             ODMatchType.contains.value: u"({attr}=*{value}*)",
    #             ODMatchType.lessThan.value: u"({attr}<{value})",
    #             ODMatchType.greaterThan.value: u"({attr}>{value})",
    #         }.get(matchType.value, u"({attr}=*{value}*)").format(
    #             attr=odAttr,
    #             value=value
    #         )

    #     elif isinstance(expression, CompoundExpression):
    #         queryString = u""
    #         operand = u"&" if expression.operand is Operand.AND else u"|"

    #         if len(expression.expressions) > 1:
    #             queryString += u"("
    #             queryString += operand

    #         for subExpression in expression.expressions:
    #             queryString += self._queryStringFromExpression(subExpression)

    #         if len(expression.expressions) > 1:
    #             queryString += u")"

    #     return queryString


    # def _queryFromCompoundExpression(self, expression):
    #     """
    #     Form an OpenDirectory query from a compound expression.

    #     @param expression: The compound expression.
    #     @type expression: L{CompoundExpression}

    #     @return: A native OpenDirectory query.
    #     @rtype: L{ODQuery}
    #     """

    #     queryString = self._queryStringFromExpression(expression)

    #     recordTypes = [t.value for t in ODRecordType.iterconstants()]
    #     attributes = [a.value for a in ODAttribute.iterconstants()]
    #     maxResults = 0

    #     query, error = ODQuery.queryWithNode_forRecordTypes_attribute_matchType_queryValues_returnAttributes_maximumResults_error_(
    #         self.node,
    #         recordTypes,
    #         None,
    #         ODMatchType.compound.value,
    #         queryString,
    #         attributes,
    #         maxResults,
    #         None
    #     )

    #     if error:
    #         self.log.error(
    #             "Error while forming OpenDirectory compound query: {error}",
    #             error=error
    #         )
    #         raise OpenDirectoryQueryError(
    #             "Unable to form OpenDirectory compound query", error
    #         )

    #     return query



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
        matchType = matchType.value

        if MatchFlags.caseInsensitive in iterFlags(expression.flags):
            caseInsensitive = 0x100
        else:
            caseInsensitive = 0x0

        fetchAttributes = [a.value for a in ODAttribute.iterconstants()]
        maxResults = 0

        if expression.fieldName is self.fieldName.recordType:
            recordTypes = ODRecordType.fromRecordType(
                expression.fieldValue
            ).value
            matchType = ODMatchType.all.value
            queryAttribute = None
            queryValue = None

        else:
            recordTypes = [t.value for t in ODRecordType.iterconstants()]
            queryAttribute = ODAttribute.fromFieldName(
                expression.fieldName
            ).value
            queryValue = expression.fieldValue

        query, error = ODQuery.queryWithNode_forRecordTypes_attribute_matchType_queryValues_returnAttributes_maximumResults_error_(
            self.node,
            recordTypes,
            queryAttribute,
            matchType | caseInsensitive,
            queryValue,
            fetchAttributes,
            maxResults,
            None
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
                self.log.error(
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
                pass

        return BaseDirectoryService.recordsFromNonCompoundExpression(
            self, expression
        )


    #
    # Commented out because:
    #  (a) generating queries as strings is janky; note that quoting is
    #      problematic, so queries with characters like ")" don't work.
    #  (b) it removes a lot of code.
    #
    # What I'd like to see is a way to nest ODQuery objects, but I can't see
    # any support for that in the OD framework.
    #
    # This seems to also work with the local node.  -wsanchez
    #
    # def recordsFromCompoundExpression(self, expression, records=None):
    #     try:
    #         query = self._queryFromCompoundExpression(expression)
    #         return (self._recordsFromQuery(query)

    #     except QueryNotSupportedError:
    #         return BaseDirectoryService.recordsFromCompoundExpression(
    #             self, expression
    #         )


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

        fields[service.fieldName.uid] = unicode(guid)

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
            return False

        return result


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

        print("username = {0!r}".format(username))
        print("realm = {0!r}".format(realm))
        print("uri = {0!r}".format(uri))
        print("nonce = {0!r}".format(nonce))
        print("cnonce = {0!r}".format(cnonce))
        print("algorithm = {0!r}".format(algorithm))
        print("nc = {0!r}".format(nc))
        print("qop = {0!r}".format(qop))
        print("response = {0!r}".format(response))
        print("method = {0!r}".format(method))
        print("challenge = {0!r}".format(challenge))

        result, m1, m2, error = self._odRecord.verifyExtendedWithAuthenticationType_authenticationItems_continueItems_context_error_(
            ODAuthMethod.digestMD5.value,
            [username, challenge, response, method],
            None, None, None
        )

        print(result, m1, m2, error)

        if error:
            return False

        return result



class NoQOPDigestCredentialFactory(DigestCredentialFactory):
    """
    DigestCredentialFactory without qop, to interop with OD.
    """

    def getChallenge(self, address):
        result = DigestCredentialFactory.getChallenge(self, address)
        del result["qop"]
        return result
