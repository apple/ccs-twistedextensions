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

"""
LDAP directory service tests.
"""

import ldap
from mockldap import MockLdap

from twisted.python.filepath import FilePath
from twisted.internet.defer import inlineCallbacks
from twisted.cred.credentials import UsernamePassword
from twisted.trial import unittest

# from ...expression import (
#     CompoundExpression, Operand, MatchExpression, MatchType, MatchFlags
# )
from .._service import (
    DEFAULT_URL,
    LDAPBindAuthError,
    DirectoryService, DirectoryRecord,
)


from ...test import test_directory



class BaseTestCase(object):
    """
    Tests for L{DirectoryService}.
    """

    url = DEFAULT_URL
    realmName = unicode(DEFAULT_URL)


    def setUp(self):
        # super(BaseTestCase, self).setUp()
        self.mockLDAP = MockLdap(mockDirectoryData)
        self.mockLDAP.start()


    def tearDown(self):
        self.mockLDAP.stop()
        # super(BaseTestCase, self).tearDown()


    def service(self, **kwargs):
        return DirectoryService(**kwargs)



class DirectoryServiceConvenienceTestMixIn(BaseTestCase):
    def _unimplemented(self):
        raise NotImplementedError()

    _unimplemented.todo = "unimplemented"


    test_recordWithUID = _unimplemented
    test_recordWithGUID = _unimplemented
    test_recordsWithRecordType = _unimplemented
    test_recordWithShortName = _unimplemented
    test_recordsWithEmailAddress = _unimplemented



class DirectoryServiceTest(
    DirectoryServiceConvenienceTestMixIn,
    test_directory.BaseDirectoryServiceTest,
    unittest.TestCase,
):
    serviceClass = DirectoryService
    directoryRecordClass = DirectoryRecord


    @inlineCallbacks
    def test_connect_defaults(self):
        """
        Connect with default arguments.
        """
        service = self.service()
        connection = yield service._connect()

        self.assertEquals(connection.methods_called(), ["initialize"])

        for option in (
            ldap.OPT_TIMEOUT,
            ldap.OPT_X_TLS_CACERTFILE,
            ldap.OPT_X_TLS_CACERTDIR,
            ldap.OPT_DEBUG_LEVEL,
        ):
            self.assertRaises(KeyError, connection.get_option, option)

        self.assertFalse(connection.tls_enabled)


    def test_connect_withUsernamePassword_invalid(self):
        """
        Connect with UsernamePassword credentials.
        """
        credentials = UsernamePassword(
            "cn=wsanchez,ou=calendarserver,o=org",
            "__password__"
        )
        service = self.service(credentials=credentials)
        self.assertFailure(service._connect(), LDAPBindAuthError)


    @inlineCallbacks
    def test_connect_withOptions(self):
        """
        Connect with default arguments.
        """
        service = self.service(
            timeout=18,
            tlsCACertificateFile=FilePath("/path/to/cert"),
            tlsCACertificateDirectory=FilePath("/path/to/certdir"),
            debug=True,
        )
        connection = yield service._connect()

        self.assertEquals(
            connection.methods_called(),
            [
                "initialize",
                "set_option", "set_option", "set_option", "set_option",
            ]
        )

        opt = lambda k: connection.get_option(k)

        self.assertEquals(opt(ldap.OPT_TIMEOUT), 18)
        self.assertEquals(opt(ldap.OPT_X_TLS_CACERTFILE), "/path/to/cert")
        self.assertEquals(opt(ldap.OPT_X_TLS_CACERTDIR), "/path/to/certdir")
        self.assertEquals(opt(ldap.OPT_DEBUG_LEVEL), 255)

        # Tested in test_connect_defaults, but test again here since we're
        # setting SSL options and we want to be sure they don't somehow enable
        # SSL implicitly.
        self.assertFalse(connection.tls_enabled)


    @inlineCallbacks
    def test_connect_withTLS(self):
        """
        Connect with TLS enabled.
        """
        service = self.service(useTLS=True)
        connection = yield service._connect()

        self.assertEquals(
            connection.methods_called(),
            ["initialize", "start_tls_s"]
        )

        self.assertTrue(connection.tls_enabled)



mockDirectoryData = dict(
)
