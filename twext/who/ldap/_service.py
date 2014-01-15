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

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from twisted.cred.credentials import IUsernamePassword

from twext.python.log import Logger

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



# Maps field name -> LDAP attribute name
DEFAULT_FIELDNAME_MAP = {
    BaseFieldName.guid: LDAPAttribute.generatedUUID.value,
    BaseFieldName.recordType: LDAPAttribute.objectClass.value,
    BaseFieldName.shortNames: LDAPAttribute.uid.value,
    BaseFieldName.fullNames: LDAPAttribute.cn.value,
    BaseFieldName.emailAddresses: LDAPAttribute.mail.value,
    BaseFieldName.password: LDAPAttribute.userPassword.value,
}


# Maps record type -> LDAP object class name
DEFAULT_RECORDTYPE_MAP = {
    BaseRecordType.user: LDAPObjectClass.person.value,
    BaseRecordType.group: LDAPObjectClass.groupOfUniqueNames.value,
}



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



# class LDAPQueryError(LDAPError):
#     """
#     LDAP query error.
#     """



# class LDAPDataError(LDAPError):
#     """
#     LDAP data error.
#     """



#
# Directory Service
#

class DirectoryService(BaseDirectoryService):
    """
    LDAP directory service.
    """

    log = Logger()

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
        fieldNameToAttributeMap=DEFAULT_FIELDNAME_MAP,
        recordTypeToObjectClassMap=DEFAULT_RECORDTYPE_MAP,
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

        @param fieldNameToAttributeMap: A mapping of field names to LDAP
            attribute names.
        @type fieldNameToAttributeMap: mapping with L{NamedConstant} keys and
            L{unicode} values

        @param recordTypeToObjectClassMap: A mapping of record types to LDAP
            object classes.
        @type recordTypeToObjectClassMap: mapping with L{NamedConstant} keys
            and L{unicode} values
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

        def reverseDict(source):
            new = {}

            for k, v in source.iteritems():
                if v in new:
                    raise LDAPConfigurationError(
                        u"Field name map has duplicate values: {0}".format(v)
                    )
                new[v] = k

            return new

        self._fieldNameToAttributeMap = fieldNameToAttributeMap
        self._attributeToFieldNameMap = reverseDict(fieldNameToAttributeMap)

        self._recordTypeToObjectClassMap = recordTypeToObjectClassMap
        self._objectClassToRecordTypeMap = reverseDict(
            recordTypeToObjectClassMap
        )

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
            self.log.info("Connecting to LDAP at {source.url}")
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
                self.log.info("Starting TLS for {source.url}")
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

        self.log.debug("Performing LDAP query: {query}", query=queryString)

        reply = connection.search_s(
            self._baseDN, ldap.SCOPE_SUBTREE, queryString  # attrs
        )

        records = []

        # Note: self._uidField is the name of the field in
        # self._fieldNameToAttributeMap that tells us which LDAP attribute
        # we are using to determine the UID of the record.

        uidField = self.fieldName.uid
        uidAttribute = self._fieldNameToAttributeMap[self._uidField]

        recordTypeField = self.fieldName.recordType
        recordTypeAttribute = (
            self._fieldNameToAttributeMap[self.fieldName.recordType]
        )

        for dn, recordData in reply:

            if recordTypeAttribute not in recordData:
                self.log.debug(
                    "Ignoring LDAP record data with no record type attribute "
                    "{source.fieldName.recordType!r}: {recordData!r}",
                    self=self, recordData=recordData
                )
                continue

            # Make a dict of fields -> values from the incoming dict of
            # attributes -> values.

            fields = dict([
                (self._attributeToFieldNameMap[k], v)
                for k, v in recordData.iteritems()
                if k in self._attributeToFieldNameMap
            ])

            # Make sure the UID is populated

            try:
                fields[uidField] = recordData[uidAttribute]
            except KeyError:
                self.log.debug(
                    "Ignoring LDAP record data with no UID attribute "
                    "{source._uidField!r}: {recordData!r}",
                    self=self, recordData=recordData
                )
                continue


            # Coerce data to the correct type

            for fieldName, value in fields.iteritems():
                valueType = self.fieldName.valueType(fieldName)

                if fieldName is recordTypeField:
                    value = self._objectClassToRecordTypeMap[value]
                elif valueType in (unicode, UUID):
                    value = valueType(value)
                else:
                    raise LDAPConfigurationError(
                        "Unknown value type {0} for field {1}".format(
                            valueType, fieldName
                        )
                    )

                fields[fieldName] = value

            # Make a record object from fields.

            record = DirectoryRecord(self, fields)
            records.append(record)

        self.log.debug("LDAP results: {records}", records=records)

        returnValue(records)


    def recordsFromNonCompoundExpression(self, expression, records=None):
        if isinstance(expression, MatchExpression):
            queryString = ldapQueryStringFromMatchExpression(
                expression,
                self._fieldNameToAttributeMap, self._recordTypeToObjectClassMap
            )
            return self._recordsFromQueryString(queryString)

        return BaseDirectoryService.recordsFromNonCompoundExpression(
            self, expression, records=records
        )


    def recordsFromCompoundExpression(self, expression, records=None):
        if not expression.expressions:
            return ()

        queryString = ldapQueryStringFromCompoundExpression(
            expression,
            self._fieldNameToAttributeMap, self._recordTypeToObjectClassMap
        )
        return self._recordsFromQueryString(queryString)



class DirectoryRecord(BaseDirectoryRecord):
    """
    LDAP directory record.
    """
