# -*- test-case-name: twext.who.test.test_util -*-
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

__all__ = [
    "OpenDirectoryError",
    "DirectoryService",
    "DirectoryRecord",
]

from itertools import chain

from odframework import ODSession, ODNode, ODQuery

from twext.python.log import Logger
from twisted.python.constants import Names, NamedConstant
from twisted.python.constants import Values, ValueConstant

from twext.who.idirectory import (
    DirectoryServiceError, QueryNotSupportedError,
    FieldName as BaseFieldName,
    RecordType as BaseRecordType,
)
from twext.who.directory import (
    DirectoryService as BaseDirectoryService,
    DirectoryRecord as BaseDirectoryRecord,
)
from twext.who.expression import CompoundExpression, Operand
from twext.who.expression import MatchExpression, MatchType, MatchFlags
from twext.who.util import iterFlags, ConstantsContainer



#
# Exceptions
#

class OpenDirectoryError(DirectoryServiceError):
    """
    OpenDirectory error.
    """

    def __init__(self, message, odError):
        super(DirectoryService, self).__init__(message)
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
    log = Logger()

    fieldName = ConstantsContainer(chain(
        BaseDirectoryService.fieldName.iterconstants(),
        FieldName.iterconstants()
    ))


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
    #     Get the local node from the search path (if any), so that we can handle
    #     it specially.
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


    def recordsFromMatchExpression(self, expression):
        """
        Find records matching a match expression.

        @param expression: an expression to apply
        @type expression: L{MatchExpression}

        @return: The matching records.
        @rtype: deferred iterable of L{IDirectoryRecord}s

        @raises: L{QueryNotSupportedError} if the expression is not
            supported by this directory service.
        """
        query = self._queryFromMatchExpression(expression)
        return self._recordsFromQuery(query)


    def recordsFromExpression(self, expression):
        try:
            if isinstance(expression, CompoundExpression):
                raise NotImplementedError(Operand)
            elif isinstance(expression, MatchExpression):
                return self.recordsFromMatchExpression(expression)

        except QueryNotSupportedError:
            pass

        return BaseDirectoryService.recordsFromExpression(
            self, expression
        )



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

    for shortName in sys.argv:
        matchMorgen = MatchExpression(
            service.fieldName.shortNames, shortName,
            matchType=MatchType.equals,
        )
        for record in service.recordsFromExpression(matchMorgen):
            print("*" * 80)
            print(record.description())
