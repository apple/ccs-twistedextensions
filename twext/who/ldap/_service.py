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

import ldap

# from zope.interface import implementer

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from twisted.cred.credentials import IUsernamePassword
# from twisted.web.guard import DigestCredentialFactory

from twext.python.log import Logger

from ..idirectory import (
    DirectoryServiceError, DirectoryAvailabilityError,
    # InvalidDirectoryRecordError,
    # QueryNotSupportedError,
    # FieldName as BaseFieldName,
    RecordType as BaseRecordType,
    # IPlaintextPasswordVerifier, IHTTPDigestVerifier,
)
from ..directory import (
    DirectoryService as BaseDirectoryService,
    DirectoryRecord as BaseDirectoryRecord,
)
from ..expression import (
    # CompoundExpression, Operand,
    MatchExpression,  # MatchFlags,
)
from ..util import (
    # iterFlags,
    ConstantsContainer,
)
from ._constants import DEFAULT_FIELDNAME_MAP, DEFAULT_RECORDTYPE_MAP
from ._util import (
    ldapQueryStringFromMatchExpression,
    ldapQueryStringFromCompoundExpression,
    # ldapQueryStringFromExpression,
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
        debug=False,
        fieldNameMap=DEFAULT_FIELDNAME_MAP,
        recordTypeMap=DEFAULT_RECORDTYPE_MAP,
    ):
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

        if debug:
            self._debug = 255
        else:
            self._debug = None

        self._fieldNameMap = fieldNameMap
        self._recordTypeMap = recordTypeMap


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

        # print("+" * 80)
        # print("Query:", repr(queryString))

        reply = connection.search_s(
            self._baseDN, ldap.SCOPE_SUBTREE, queryString  # attrs
        )

        # print("Reply:", repr(reply))
        # print("+" * 80)

        records = []

        for recordData in reply:
            raise NotImplementedError(reply)

        returnValue(records)


    def recordsFromNonCompoundExpression(self, expression, records=None):
        if isinstance(expression, MatchExpression):
            queryString = ldapQueryStringFromMatchExpression(
                expression, self._fieldNameMap, self._recordTypeMap
            )
            return self._recordsFromQueryString(queryString)

        return BaseDirectoryService.recordsFromNonCompoundExpression(
            self, expression, records=records
        )


    def recordsFromCompoundExpression(self, expression, records=None):
        if not expression.expressions:
            return ()

        queryString = ldapQueryStringFromCompoundExpression(
            expression, self._fieldNameMap, self._recordTypeMap
        )
        return self._recordsFromQueryString(queryString)



class DirectoryRecord(BaseDirectoryRecord):
    """
    LDAP directory record.
    """
