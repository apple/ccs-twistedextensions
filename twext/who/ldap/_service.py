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
    # InvalidDirectoryRecordError, QueryNotSupportedError,
    # FieldName as BaseFieldName,
    RecordType as BaseRecordType,
    # IPlaintextPasswordVerifier, IHTTPDigestVerifier,
)
from ..directory import (
    DirectoryService as BaseDirectoryService,
    DirectoryRecord as BaseDirectoryRecord,
)
# from ..expression import (
#     CompoundExpression, Operand,
#     MatchExpression, MatchFlags,
# )
from ..util import (
    # iterFlags,
    ConstantsContainer,
)
# from ._constants import LDAP_QUOTING_TABLE



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
        url="ldap://localhost/",
        credentials=None,
        timeout=None,
        tlsCACertificateFile=None,
        tlsCACertificateDirectory=None,
        useTLS=False,
        debug=False,
    ):
        self.url = url
        self.credentials = credentials
        self._timeout = timeout
        self._tlsCACertificateFile = tlsCACertificateFile
        self._tlsCACertificateDirectory = tlsCACertificateDirectory
        self._useTLS = useTLS,

        if debug:
            self._debug = 255
        else:
            self._debug = None


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
                (ldap.OPT_DEBUG_LEVEL, self._debug),
                (ldap.OPT_TIMEOUT, self._timeout),
                (ldap.OPT_X_TLS_CACERTFILE, self._tlsCACertificateFile),
                (ldap.OPT_X_TLS_CACERTDIR, self._tlsCACertificateDirectory),
            ):
                if value is not None:
                    connection.set_option(option, value)

            if self._useTLS:
                yield deferToThread(connection.start_tls_s)

            if self.credentials is not None:
                if IUsernamePassword.providedBy(self.credentials):
                    try:
                        yield deferToThread(
                            connection.simple_bind_s,
                            self.credentials.username,
                            self.credentials.password,
                        )
                        self.log.info(
                            "Bound to LDAP as {credentials.username}",
                            credentials=self.credentials
                        )
                    except ldap.INVALID_CREDENTIALS as e:
                        self.log.info(
                            "Unable to bind to LDAP as {credentials.username}",
                            credentials=self.credentials
                        )
                        raise LDAPConnectionError(str(e), e)

                else:
                    raise LDAPConnectionError(
                        "Unknown credentials type: {0}"
                        .format(self.credentials)
                    )

            self._connection = connection

        returnValue(self._connection)



class DirectoryRecord(BaseDirectoryRecord):
    """
    LDAP directory record.
    """
