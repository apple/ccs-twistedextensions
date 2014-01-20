# -*- test-case-name: twext.who.ldap.test.test_service -*-
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
LDAP directory service implementation.
"""

from uuid import UUID

import ldap

from twisted.python.constants import Names, NamedConstant
from twisted.internet.defer import succeed, inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from twisted.cred.credentials import IUsernamePassword

from twext.python.log import Logger
from twext.python.types import MappingProxyType

from ..idirectory import (
    DirectoryServiceError, DirectoryAvailabilityError,
    FieldName as BaseFieldName, RecordType as BaseRecordType,
)
from ..directory import (
    DirectoryService as BaseDirectoryService,
    DirectoryRecord as BaseDirectoryRecord,
)
from ..expression import MatchExpression
from ..util import ConstantsContainer
from ._constants import LDAPAttribute, LDAPObjectClass
from ._util import (
    ldapQueryStringFromMatchExpression,
    ldapQueryStringFromCompoundExpression,
)



#
# Exceptions
#

class LDAPError(DirectoryServiceError):
    """
    LDAP error.
    """

    def __init__(self, message, ldapError=None):
        super(LDAPError, self).__init__(message)
        self.ldapError = ldapError



class LDAPConfigurationError(ValueError):
    """
    LDAP configuration error.
    """



class LDAPConnectionError(DirectoryAvailabilityError):
    """
    LDAP connection error.
    """

    def __init__(self, message, ldapError=None):
        super(LDAPConnectionError, self).__init__(message)
        self.ldapError = ldapError



class LDAPBindAuthError(LDAPConnectionError):
    """
    LDAP bind auth error.
    """



class LDAPQueryError(LDAPError):
    """
    LDAP query error.
    """



#
# Data type extentions
#

class FieldName(Names):
    dn = NamedConstant()
    dn.description = u"distinguished name"



#
# LDAP schema descriptions
#

class RecordTypeSchema(object):
    """
    Describes the LDAP schema for a record type.
    """
    def __init__(self, relativeDN, attributes):
        """
        @param relativeDN: The relative distinguished name for the record type.
            This is prepended to the service's base distinguished name when
            searching for records of this type.
        @type relativeDN: L{unicode}

        @param attributes: Attribute/value pairs that are expected for records
            of this type.
        @type attributes: iterable of sequences containing two L{unicode}s
        """
        self.relativeDN = relativeDN
        self.attributes = tuple(tuple(pair) for pair in attributes)



# We use strings (constant.value) instead of constants for the values in
# these mappings because it's meant to be configurable by application users,
# and user input forms such as config files aren't going to be able to use
# the constants.

# Maps field name -> LDAP attribute names
DEFAULT_FIELDNAME_ATTRIBUTE_MAP = MappingProxyType({
    FieldName.dn: (LDAPAttribute.dn.value,),
    BaseFieldName.guid: (LDAPAttribute.generatedUUID.value,),
    BaseFieldName.shortNames: (LDAPAttribute.uid.value,),
    BaseFieldName.fullNames: (LDAPAttribute.cn.value,),
    BaseFieldName.emailAddresses: (LDAPAttribute.mail.value,),
    BaseFieldName.password: (LDAPAttribute.userPassword.value,),
})

# Information about record types
DEFAULT_RECORDTYPE_SCHEMAS = MappingProxyType({

    BaseRecordType.user: RecordTypeSchema(
        # ou=person
        relativeDN=u"ou={0}".format(LDAPObjectClass.person.value),

        # (objectClass=inetOrgPerson)
        attributes=(
            (
                LDAPAttribute.objectClass.value,
                LDAPObjectClass.inetOrgPerson.value,
            ),
        ),
    ),

    BaseRecordType.group: RecordTypeSchema(
        # ou=groupOfNames
        relativeDN=u"ou={0}".format(LDAPObjectClass.groupOfNames.value),

        # (objectClass=groupOfNames)
        attributes=(
            (
                LDAPAttribute.objectClass.value,
                LDAPObjectClass.groupOfNames.value,
            ),
        ),
    ),

})



#
# Directory Service
#

class DirectoryService(BaseDirectoryService):
    """
    LDAP directory service.
    """

    log = Logger()

    fieldName = ConstantsContainer((BaseFieldName, FieldName))

    recordType = ConstantsContainer((
        BaseRecordType.user, BaseRecordType.group,
    ))


    def __init__(
        self,
        url,
        baseDN,
        credentials=None,
        timeout=None,
        tlsCACertificateFile=None,
        tlsCACertificateDirectory=None,
        useTLS=False,
        fieldNameToAttributesMap=DEFAULT_FIELDNAME_ATTRIBUTE_MAP,
        recordTypeSchemas=DEFAULT_RECORDTYPE_SCHEMAS,
        uidField=BaseFieldName.uid,
        _debug=False,
    ):
        """
        @param url: The URL of the LDAP server to connect to.
        @type url: L{unicode}

        @param baseDN: The base DN for queries.
        @type baseDN: L{unicode}

        @param credentials: The credentials to use to authenticate with the
            LDAP server.
        @type credentials: L{IUsernamePassword}

        @param timeout: A timeout, in seconds, for LDAP queries.
        @type timeout: number

        @param tlsCACertificateFile: ...
        @type tlsCACertificateFile: L{FilePath}

        @param tlsCACertificateDirectory: ...
        @type tlsCACertificateDirectory: L{FilePath}

        @param useTLS: Enable the use of TLS.
        @type useTLS: L{bool}

        @param fieldNameToAttributesMap: A mapping of field names to LDAP
            attribute names.
        @type fieldNameToAttributesMap: mapping with L{NamedConstant} keys and
            sequence of L{unicode} values

        @param recordTypeSchemas: Schema information for record types.
        @type recordTypeSchemas: mapping from L{NamedConstant} to
            L{RecordTypeSchema}
        """

        self.url = url
        self._baseDN = baseDN
        self._credentials = credentials
        self._timeout = timeout

        if tlsCACertificateFile is None:
            self._tlsCACertificateFile = None
        else:
            self._tlsCACertificateFile = tlsCACertificateFile.path

        if tlsCACertificateDirectory is None:
            self._tlsCACertificateDirectory = None
        else:
            self._tlsCACertificateDirectory = tlsCACertificateDirectory.path

        self._useTLS = useTLS

        if _debug:
            self._debug = 255
        else:
            self._debug = None

        if self.fieldName.recordType in fieldNameToAttributesMap:
            raise TypeError("Record type field may not be mapped")

        self._fieldNameToAttributesMap = fieldNameToAttributesMap
        self._attributeToFieldNameMap = reverseDict(
            "Field name", fieldNameToAttributesMap
        )
        self._recordTypeSchemas = recordTypeSchemas
        self._uidField = uidField


    @property
    def realmName(self):
        return u"{self.url}".format(self=self)


    @inlineCallbacks
    def _connect(self):
        """
        Connect to the directory server.

        @returns: A deferred connection object.
        @rtype: deferred L{ldap.ldapobject.LDAPObject}

        @raises: L{LDAPConnectionError} if unable to connect.
        """
        if not hasattr(self, "_connection"):
            self.log.info("Connecting to LDAP at {log_source.url}")
            connection = ldap.initialize(self.url)

            # FIXME: Use trace_file option to wire up debug logging when
            # Twisted adopts the new logging stuff.

            for option, value in (
                (ldap.OPT_TIMEOUT, self._timeout),
                (ldap.OPT_X_TLS_CACERTFILE, self._tlsCACertificateFile),
                (ldap.OPT_X_TLS_CACERTDIR, self._tlsCACertificateDirectory),
                (ldap.OPT_DEBUG_LEVEL, self._debug),
            ):
                if value is not None:
                    connection.set_option(option, value)

            if self._useTLS:
                self.log.info("Starting TLS for {log_source.url}")
                yield deferToThread(connection.start_tls_s)

            if self._credentials is not None:
                if IUsernamePassword.providedBy(self._credentials):
                    try:
                        yield deferToThread(
                            connection.simple_bind_s,
                            self._credentials.username,
                            self._credentials.password,
                        )
                        self.log.info(
                            "Bound to LDAP as {credentials.username}",
                            credentials=self._credentials
                        )
                    except (
                        ldap.INVALID_CREDENTIALS, ldap.INVALID_DN_SYNTAX
                    ) as e:
                        self.log.error(
                            "Unable to bind to LDAP as {credentials.username}",
                            credentials=self._credentials
                        )
                        raise LDAPBindAuthError(
                            self._credentials.username, e
                        )

                else:
                    raise LDAPConnectionError(
                        "Unknown credentials type: {0}"
                        .format(self._credentials)
                    )

            self._connection = connection

        returnValue(self._connection)


    @inlineCallbacks
    def _recordsFromQueryString(self, queryString):
        connection = yield self._connect()

        self.log.info("Performing LDAP query: {query}", query=queryString)

        try:
            reply = connection.search_s(
                self._baseDN, ldap.SCOPE_SUBTREE, queryString  # FIXME: attrs
            )
        except ldap.FILTER_ERROR as e:
            self.log.error(
                "Unable to perform query {0!r}: {1}"
                .format(queryString, e)
            )
            raise LDAPQueryError("Unable to perform query", e)

        records = []

        # self._uidField is the name of the field in
        # self._fieldNameToAttributesMap that tells us which LDAP attribute
        # we are using to determine the UID of the record.

        uidAttribute = self._fieldNameToAttributesMap[self._uidField][0]

        # recordTypeAttributes = set(chain(*[
        #     info[u"attributes"].iterkeys()
        #     for info in self._recordTypeInfo.itervalues()
        # ]))

        for dn, recordData in reply:

            # Fetch the UID

            try:
                uid = recordData[uidAttribute]
            except KeyError:
                self.log.debug(
                    "Ignoring LDAP record data; no UID attribute "
                    "({log_source._uidField}): {recordData!r}",
                    recordData=recordData
                )
                continue

            # Determine the record type

            recordType = recordTypeForRecordData(
                self._recordTypeSchemas, recordData
            )

            if recordType is None:
                self.log.debug(
                    "Ignoring LDAP record data; unable to determine record "
                    "type: {recordData!r}",
                    recordData=recordData,
                )
                continue

            # Populate a fields dictionary

            fields = {}

            for attribute, value in recordData.iteritems():
                fieldName = self._attributeToFieldNameMap.get(attribute, None)
                if fieldName is None:
                    self.log.debug(
                        "Unmapped LDAP attribute {attribute!r} in record "
                        "data: {recordData!r}",
                        attribute=attribute, recordData=recordData,
                    )

                valueType = self.fieldName.valueType(fieldName)

                if valueType in (unicode, UUID):
                    fields[fieldName] = valueType(value)

                else:
                    raise LDAPConfigurationError(
                        "Unknown value type {0} for field {1}".format(
                            valueType, fieldName
                        )
                    )

            # Set record type and uid fields

            fields[self.fieldName.recordType] = recordType
            fields[self.fieldName.uid] = uid
            fields[self.fieldName.dn] = dn

            # Make a record object from fields.

            record = DirectoryRecord(self, fields)
            records.append(record)

        self.log.debug("LDAP results: {records}", records=records)

        returnValue(records)


    def recordsFromNonCompoundExpression(self, expression, records=None):
        if isinstance(expression, MatchExpression):
            queryString = ldapQueryStringFromMatchExpression(
                expression,
                self._fieldNameToAttributesMap, self._recordTypeSchemas
            )
            return self._recordsFromQueryString(queryString)

        return BaseDirectoryService.recordsFromNonCompoundExpression(
            self, expression, records=records
        )


    def recordsFromCompoundExpression(self, expression, records=None):
        if not expression.expressions:
            return succeed(())

        queryString = ldapQueryStringFromCompoundExpression(
            expression,
            self._fieldNameToAttributesMap, self._recordTypeSchemas
        )
        return self._recordsFromQueryString(queryString)


    # def updateRecords(self, records, create=False):
    #     for record in records:
    #         return fail(NotAllowedError("Record updates not allowed."))
    #     return succeed(None)


    # def removeRecords(self, uids):
    #     for uid in uids:
    #         return fail(NotAllowedError("Record removal not allowed."))
    #     return succeed(None)



class DirectoryRecord(BaseDirectoryRecord):
    """
    LDAP directory record.
    """

    @inlineCallbacks
    def members(self):
        if self.recordType != self.service.recordType.group:
            returnValue(())

        raise NotImplementedError()


    @inlineCallbacks
    def groups(self):
        raise NotImplementedError()



def reverseDict(sourceName, source):
    new = {}

    for key, values in source.iteritems():
        for value in values:
            if value in new:
                raise LDAPConfigurationError(
                    u"{0} map has duplicate values: {1}"
                    .format(sourceName, value)
                )
            new[value] = key

    return new


def recordTypeForRecordData(recordTypeSchemas, recordData):
    """
    Given info about record types, determine the record type for a blob of
    LDAP record data.

    @param recordTypeSchemas: Schema information for record types.
    @type recordTypeSchemas: mapping from L{NamedConstant} to
        L{RecordTypeSchema}

    @param recordData: LDAP record data.
    @type recordData: mapping
    """

    for recordType, schema in recordTypeSchemas.iteritems():
        for attribute, value in schema.attributes:
            if recordData.get(attribute, None) != value:
                break
        else:
            return recordType

    return None
