# -*- test-case-name: twext.who.test.test_ldap -*-
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

from twisted.python.constants import Values, ValueConstant
# from twisted.internet.defer import succeed, fail
# from twisted.web.guard import DigestCredentialFactory

from twext.python.log import Logger

from ..idirectory import (
    # DirectoryServiceError, DirectoryAvailabilityError,
    # InvalidDirectoryRecordError, QueryNotSupportedError,
    # FieldName as BaseFieldName,
    RecordType as BaseRecordType,
    # IPlaintextPasswordVerifier, IHTTPDigestVerifier,
)
from ..directory import (
    DirectoryService as BaseDirectoryService,
    # DirectoryRecord as BaseDirectoryRecord,
)
# from ..expression import (
#     CompoundExpression, Operand,
#     MatchExpression, MatchFlags,
# )
from ..util import (
    # iterFlags,
    ConstantsContainer,
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



#
# Exceptions
#

# class LDAPError(DirectoryServiceError):
#     """
#     LDAP error.
#     """

#     def __init__(self, message, odError=None):
#         super(LDAPError, self).__init__(message)
#         self.odError = odError



# class LDAPConnectionError(DirectoryAvailabilityError):
#     """
#     LDAP connection error.
#     """

#     def __init__(self, message, odError=None):
#         super(LDAPConnectionError, self).__init__(message)
#         self.odError = odError



# class LDAPQueryError(LDAPError):
#     """
#     LDAP query error.
#     """


# class LDAPDataError(LDAPError):
#     """
#     LDAP data error.
#     """



#
# LDAP Constants
#

class TLSRequireCertificate(Values):
    never   = ValueConstant(ldap.OPT_X_TLS_NEVER)
    allow   = ValueConstant(ldap.OPT_X_TLS_ALLOW)
    attempt = ValueConstant(ldap.OPT_X_TLS_TRY)
    demand  = ValueConstant(ldap.OPT_X_TLS_DEMAND)
    hard    = ValueConstant(ldap.OPT_X_TLS_HARD)


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
        tlsCACertificateFile=None,
        tlsCACertificateDirectory=None,
        tlsRequireCertificate=None,
        useTLS=False,
    ):
        self._url = url
        self._tlsCACertificateFile = tlsCACertificateFile
        self._tlsCACertificateDirectory = tlsCACertificateDirectory
        self._tlsRequireCertificate = tlsRequireCertificate
        self._useTLS = useTLS,


    @property
    def realmName(self):
        return u"{self.url}".format(self=self)


    @property
    def connection(self):
        """
        Get the underlying LDAP connection.
        """
        self._connect()
        return self._connection


    def _connect(self):
        """
        Connect to the directory server.

        @raises: L{LDAPConnectionError} if unable to connect.
        """
        if not hasattr(self, "_connection"):
            connection = ldap.initialize(self._url)

            def valueFor(constant):
                if constant is None:
                    return None
                else:
                    return constant.value

            for option, value in (
                (ldap.OPT_X_TLS_CACERTFILE, self._tlsCACertificateFile),
                (ldap.OPT_X_TLS_CACERTDIR, self._tlsCACertificateDirectory),
                (ldap.OPT_X_TLS, valueFor(self._tlsRequireCertificate)),
            ):
                if value is not None:
                    connection.set_option(option, value)

            if self._useTLS:
                connection.start_tls_s()

            self._connection = connection
